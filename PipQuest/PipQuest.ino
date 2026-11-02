// =====================================================================
//  PIP QUEST  -  a side-scrolling platformer for the Arduboy
//
//  Controls:  LEFT / RIGHT  move
//             A             jump  (hold for a higher jump)
//             B (hold)      run
//  Title:     B toggles sound
//
//  Stomp the blobs, bump ? blocks for coins, smash bricks from below,
//  avoid spikes and pits, and touch the flag pole to clear the level.
// =====================================================================
#include <Arduboy2.h>
#include <EEPROM.h>
#include "sprites.h"
#include "levels.h"

Arduboy2 arduboy;
BeepPin1 beep;

// ------------------------------------------------------------ constants
constexpr int16_t TILE       = 8;
constexpr int16_t LEVEL_PX   = LEVEL_W * TILE;
constexpr int16_t GRAVITY    = 6;     // physics values are in 1/16 pixel
constexpr int16_t MAX_FALL   = 64;
constexpr int16_t JUMP_V     = -74;
constexpr int16_t RUN_JUMP_V = -82;
constexpr int16_t WALK_MAX   = 22;
constexpr int16_t RUN_MAX    = 36;
constexpr int16_t STOMP_V    = -50;
constexpr uint8_t START_LIVES = 3;
constexpr uint8_t MAX_ENEMIES = 16;
constexpr uint8_t MAX_POPS    = 4;

constexpr int EEPROM_ADDR  = EEPROM_STORAGE_SPACE_START + 160;
constexpr uint8_t EEPROM_MAGIC = 0x5A;

enum GameState : uint8_t { TITLE, PLAYING, DYING, CLEAR, GAMEOVER, WIN };

// ------------------------------------------------------------ game data
struct Enemy {
  int16_t x, y;      // pixels
  int8_t  dir;
  uint8_t state;     // 0 gone, 1 waiting off-screen, 2 walking, 3 squashed
  uint8_t timer;
};

struct Pop {         // coin that pops out of a ? block
  int16_t x, y;
  uint8_t t;
};

GameState state = TITLE;
uint8_t  levelNum;
uint8_t  lives;
uint8_t  coins;
uint16_t score;
uint16_t hiScore;
uint8_t  stateTimer;

int16_t px, py;      // player position (1/16 pixel)
int16_t vx, vy;      // player velocity (1/16 pixel per frame)
int16_t startX, startY;
bool    onGround;
bool    facingLeft;
uint8_t walkAnim;
int16_t camX;

Enemy enemies[MAX_ENEMIES];
Pop   pops[MAX_POPS];
uint8_t usedBits[(LEVEL_W * LEVEL_H + 7) / 8];  // collected coins, hit blocks

// ------------------------------------------------------------ sound
void sfx(uint16_t hz, uint8_t frames) {
  if (arduboy.audio.enabled()) beep.tone(beep.freq(hz), frames);
}

// ------------------------------------------------------------ tiles
bool isUsed(int16_t tx, int16_t ty) {
  uint16_t i = ty * LEVEL_W + tx;
  return usedBits[i >> 3] & (1 << (i & 7));
}

void setUsed(int16_t tx, int16_t ty) {
  uint16_t i = ty * LEVEL_W + tx;
  usedBits[i >> 3] |= (1 << (i & 7));
}

char rawTile(int16_t tx, int16_t ty) {
  return pgm_read_byte(&levels[levelNum][ty][tx]);
}

// Tile at grid position, after taking collected/broken tiles into account.
// 'U' is a used (empty) ? block.
char tileAt(int16_t tx, int16_t ty) {
  if (tx < 0 || tx >= LEVEL_W) return '#';     // invisible side walls
  if (ty < 0 || ty >= LEVEL_H) return '.';     // open sky / bottomless pits
  char c = rawTile(tx, ty);
  if (c == 0 || c == 'e' || c == 'S') return '.';
  if (isUsed(tx, ty)) return (c == '?') ? 'U' : '.';
  return c;
}

bool isSolid(char c) {
  return c == '#' || c == 'B' || c == '?' || c == 'U' || c == 'P';
}

bool solidAt(int16_t x, int16_t y) {           // pixel coordinates
  return isSolid(tileAt(x >> 3, y >> 3));
}

// ------------------------------------------------------------ level setup
void loadLevel() {
  memset(usedBits, 0, sizeof(usedBits));
  memset(pops, 0, sizeof(pops));
  memset(enemies, 0, sizeof(enemies));
  startX = 2 * TILE;
  startY = 5 * TILE;
  uint8_t n = 0;
  for (int16_t ty = 0; ty < LEVEL_H; ty++) {
    for (int16_t tx = 0; tx < LEVEL_W; tx++) {
      char c = rawTile(tx, ty);
      if (c == 'S') {
        startX = tx * TILE;
        startY = ty * TILE;
      } else if (c == 'e' && n < MAX_ENEMIES) {
        enemies[n].x = tx * TILE;
        enemies[n].y = ty * TILE;
        enemies[n].dir = -1;
        enemies[n].state = 1;
        n++;
      }
    }
  }
  px = startX << 4;
  py = startY << 4;
  vx = vy = 0;
  onGround = false;
  facingLeft = false;
  camX = 0;
  state = PLAYING;
}

void newGame() {
  levelNum = 0;
  lives = START_LIVES;
  coins = 0;
  score = 0;
  loadLevel();
}

void addScore(uint16_t pts) {
  score = (score > 65535 - pts) ? 65535 : score + pts;
}

void addCoin() {
  addScore(100);
  if (++coins >= 50) {                         // 50 coins = extra life
    coins = 0;
    if (lives < 9) lives++;
    sfx(1568, 12);
  } else {
    sfx(1319, 4);
  }
}

void killPlayer() {
  state = DYING;
  stateTimer = 90;
  vy = -70;
  vx = 0;
  sfx(196, 30);
}

// ------------------------------------------------------------ high score
void loadHiScore() {
  if (EEPROM.read(EEPROM_ADDR) == EEPROM_MAGIC) {
    EEPROM.get(EEPROM_ADDR + 1, hiScore);
  } else {
    hiScore = 0;
  }
}

void saveHiScore() {
  if (score > hiScore) {
    hiScore = score;
    EEPROM.update(EEPROM_ADDR, EEPROM_MAGIC);
    EEPROM.put(EEPROM_ADDR + 1, hiScore);
  }
}

// ------------------------------------------------------------ blocks
void spawnPop(int16_t x, int16_t y) {
  for (uint8_t i = 0; i < MAX_POPS; i++) {
    if (pops[i].t == 0) {
      pops[i].x = x;
      pops[i].y = y;
      pops[i].t = 16;
      return;
    }
  }
}

void bumpTile(int16_t tx, int16_t ty) {
  char c = tileAt(tx, ty);
  if (c == '?') {
    setUsed(tx, ty);
    spawnPop(tx * TILE, ty * TILE - TILE);
    addCoin();
  } else if (c == 'B') {
    setUsed(tx, ty);                           // brick breaks
    addScore(50);
    sfx(220, 4);
  } else {
    sfx(110, 3);
    return;
  }
  // knock out any enemy standing on the bumped block
  for (uint8_t i = 0; i < MAX_ENEMIES; i++) {
    Enemy &e = enemies[i];
    if (e.state == 2 && e.y + 8 == ty * TILE &&
        e.x + 7 >= tx * TILE && e.x <= tx * TILE + 7) {
      e.state = 3;
      e.timer = 20;
      addScore(200);
    }
  }
}

// ------------------------------------------------------------ player
void updatePlayer() {
  bool running = arduboy.pressed(B_BUTTON);
  int16_t maxV = running ? RUN_MAX : WALK_MAX;
  int16_t accel = onGround ? 3 : 2;

  if (arduboy.pressed(LEFT_BUTTON)) {
    vx -= accel;
    facingLeft = true;
  } else if (arduboy.pressed(RIGHT_BUTTON)) {
    vx += accel;
    facingLeft = false;
  } else if (onGround) {
    if (vx > 0) { vx -= 2; if (vx < 0) vx = 0; }
    else if (vx < 0) { vx += 2; if (vx > 0) vx = 0; }
  }
  if (vx > maxV) vx = (vx - 2 > maxV) ? vx - 2 : maxV;
  if (vx < -maxV) vx = (vx + 2 < -maxV) ? vx + 2 : -maxV;

  if (arduboy.justPressed(A_BUTTON) && onGround) {
    vy = (abs(vx) > WALK_MAX) ? RUN_JUMP_V : JUMP_V;
    onGround = false;
    sfx(660, 4);
  }
  if (!arduboy.pressed(A_BUTTON) && vy < -24) vy = -24;  // short hop
  vy += GRAVITY;
  if (vy > MAX_FALL) vy = MAX_FALL;

  // --- horizontal movement and collision (hitbox is x+1..x+6, y..y+7)
  px += vx;
  int16_t X = px >> 4, Y = py >> 4;
  if (vx > 0) {
    int16_t r = X + 6;
    if (solidAt(r, Y) || solidAt(r, Y + 7)) {
      X = (r >> 3) * TILE - 7;
      px = X << 4;
      vx = 0;
    }
  } else if (vx < 0) {
    int16_t l = X + 1;
    if (solidAt(l, Y) || solidAt(l, Y + 7)) {
      X = ((l >> 3) + 1) * TILE - 1;
      px = X << 4;
      vx = 0;
    }
  }

  // --- vertical movement and collision
  py += vy;
  Y = py >> 4;
  onGround = false;
  if (vy > 0) {
    int16_t b = Y + 7;
    if (solidAt(X + 1, b) || solidAt(X + 6, b)) {
      Y = (b >> 3) * TILE - TILE;
      py = Y << 4;
      vy = 0;
      onGround = true;
    }
  } else if (vy < 0) {
    if (solidAt(X + 1, Y) || solidAt(X + 6, Y)) {
      int16_t ty = Y >> 3;
      int16_t cx = (X + 4) >> 3;               // prefer the block above center
      if (!isSolid(tileAt(cx, ty))) cx = solidAt(X + 1, Y) ? (X + 1) >> 3 : (X + 6) >> 3;
      Y = (ty + 1) * TILE;
      py = Y << 4;
      vy = 0;
      bumpTile(cx, ty);
    }
  }

  // --- pickups, hazards and the goal
  for (int16_t ty = Y >> 3; ty <= (Y + 7) >> 3; ty++) {
    for (int16_t tx = (X + 1) >> 3; tx <= (X + 6) >> 3; tx++) {
      char c = tileAt(tx, ty);
      if (c == 'o') {
        setUsed(tx, ty);
        addCoin();
      } else if (c == 's' && Y + 7 >= ty * TILE + 3) {
        killPlayer();
        return;
      } else if (c == 'F') {
        state = CLEAR;
        stateTimer = 150;
        addScore((uint16_t)(5 - (Y >> 4 > 4 ? 4 : Y >> 4)) * 400);  // higher = more
        sfx(784, 30);
        return;
      }
    }
  }

  if (Y > HEIGHT + 8) {                        // fell into a pit
    killPlayer();
    return;
  }

  if (vx != 0 && onGround) walkAnim++;

  // camera
  camX = X - 56;
  if (camX < 0) camX = 0;
  if (camX > LEVEL_PX - WIDTH) camX = LEVEL_PX - WIDTH;
}

// ------------------------------------------------------------ enemies
void updateEnemies() {
  int16_t X = px >> 4, Y = py >> 4;
  for (uint8_t i = 0; i < MAX_ENEMIES; i++) {
    Enemy &e = enemies[i];
    if (e.state == 0) continue;
    if (e.state == 1) {                        // wake when nearly on screen
      if (e.x < camX + WIDTH + 8) e.state = 2;
      else continue;
    }
    if (e.state == 3) {
      if (--e.timer == 0) e.state = 0;
      continue;
    }

    // walk at half a pixel per frame, turn around at walls
    if (arduboy.frameCount & 1) {
      int16_t nx = e.x + e.dir;
      int16_t edge = (e.dir > 0) ? nx + 7 : nx;
      if (solidAt(edge, e.y + 4)) e.dir = -e.dir;
      else e.x = nx;
    }
    // fall
    if (!solidAt(e.x + 1, e.y + 8) && !solidAt(e.x + 6, e.y + 8)) e.y += 2;
    if (e.y > HEIGHT) { e.state = 0; continue; }

    // bump into other enemies
    for (uint8_t j = 0; j < MAX_ENEMIES; j++) {
      Enemy &o = enemies[j];
      if (j != i && o.state == 2 && abs(o.x - e.x) < 8 && abs(o.y - e.y) < 8 &&
          ((e.dir > 0 && o.x > e.x) || (e.dir < 0 && o.x < e.x))) {
        e.dir = -e.dir;
      }
    }

    // touch the player
    if (X + 1 < e.x + 7 && X + 6 > e.x && Y < e.y + 8 && Y + 8 > e.y + 1) {
      if (vy > 0 && Y + 7 < e.y + 5) {
        e.state = 3;
        e.timer = 20;
        vy = arduboy.pressed(A_BUTTON) ? JUMP_V : STOMP_V;
        addScore(200);
        sfx(880, 4);
      } else {
        killPlayer();
        return;
      }
    }
  }
}

void updatePops() {
  for (uint8_t i = 0; i < MAX_POPS; i++) {
    if (pops[i].t) {
      pops[i].t--;
      pops[i].y -= (pops[i].t > 8) ? 2 : -1;
    }
  }
}

// ------------------------------------------------------------ drawing
void drawWorld() {
  int16_t firstCol = camX >> 3;
  int16_t off = camX & 7;
  uint8_t coinFrame = ((arduboy.frameCount >> 3) & 1) ? TILE_COIN2 : TILE_COIN1;

  for (int16_t col = 0; col <= WIDTH / TILE; col++) {
    int16_t tx = firstCol + col;
    if (tx >= LEVEL_W) break;
    int16_t sx = col * TILE - off;
    for (int16_t ty = 0; ty < LEVEL_H; ty++) {
      char c = tileAt(tx, ty);
      int8_t f = -1;
      switch (c) {
        case '#': f = TILE_GROUND; break;
        case 'B': f = TILE_BRICK; break;
        case '?': f = TILE_QUESTION; break;
        case 'U': f = TILE_USED; break;
        case 'P': f = TILE_PILLAR; break;
        case 'o': f = coinFrame; break;
        case 's': f = TILE_SPIKE; break;
        case 'F': f = (tileAt(tx, ty - 1) == 'F') ? TILE_POLE : TILE_FLAG; break;
      }
      if (f >= 0) Sprites::drawSelfMasked(sx, ty * TILE, tileSprite, f);
    }
  }

  for (uint8_t i = 0; i < MAX_POPS; i++) {
    if (pops[i].t) Sprites::drawSelfMasked(pops[i].x - camX, pops[i].y, tileSprite, coinFrame);
  }

  for (uint8_t i = 0; i < MAX_ENEMIES; i++) {
    Enemy &e = enemies[i];
    if (e.state >= 2) {
      uint8_t f = (e.state == 3) ? 2 : ((arduboy.frameCount >> 4) & 1);
      Sprites::drawSelfMasked(e.x - camX, e.y, blobSprite, f);
    }
  }
}

void drawPlayer() {
  uint8_t f;
  if (!onGround || state == DYING) f = 2;
  else if (vx != 0) f = (walkAnim >> 2) & 1;
  else f = 0;
  if (facingLeft) f += 3;
  int16_t sx = (px >> 4) - camX;
  int16_t sy = py >> 4;
  arduboy.fillRect(sx + 1, sy, 6, 8, BLACK);   // keep Pip visible over tiles
  Sprites::drawSelfMasked(sx, sy, heroSprite, f);
}

void drawHud() {
  arduboy.fillRect(0, 0, WIDTH, 8, BLACK);
  arduboy.setCursor(0, 0);
  arduboy.print(F("L"));
  arduboy.print(levelNum + 1);
  arduboy.setCursor(22, 0);
  arduboy.print(F("x"));
  arduboy.print(lives);
  arduboy.setCursor(46, 0);
  arduboy.print(F("$"));
  arduboy.print(coins);
  arduboy.setCursor(92, 0);
  if (score < 10000) arduboy.print('0');
  if (score < 1000) arduboy.print('0');
  if (score < 100) arduboy.print('0');
  if (score < 10) arduboy.print('0');
  arduboy.print(score);
}

void printCentered(const __FlashStringHelper *s, uint8_t len, int16_t y, uint8_t size) {
  arduboy.setTextSize(size);
  arduboy.setCursor((WIDTH - len * 6 * size) / 2, y);
  arduboy.print(s);
  arduboy.setTextSize(1);
}

void drawTitle() {
  for (int16_t x = 0; x < WIDTH; x += TILE) {
    Sprites::drawSelfMasked(x, 56, tileSprite, TILE_GROUND);
  }
  Sprites::drawSelfMasked(56, 40, tileSprite, TILE_BRICK);
  Sprites::drawSelfMasked(64, 40, tileSprite, TILE_QUESTION);
  Sprites::drawSelfMasked(72, 40, tileSprite, TILE_BRICK);
  Sprites::drawSelfMasked(100, 48, blobSprite, (arduboy.frameCount >> 4) & 1);
  Sprites::drawSelfMasked(20, 48, heroSprite, (arduboy.frameCount >> 3) & 1);

  printCentered(F("PIP QUEST"), 9, 2, 2);
  if ((arduboy.frameCount >> 5) & 1) printCentered(F("PRESS A"), 7, 22, 1);
  arduboy.setCursor(0, 31);
  arduboy.print(F("HI "));
  arduboy.print(hiScore);
  arduboy.setCursor(80, 31);
  arduboy.print(arduboy.audio.enabled() ? F("B:SND ON") : F("B:SNDOFF"));
}

// ------------------------------------------------------------ main loop
void setup() {
  arduboy.begin();
  arduboy.setFrameRate(60);
  beep.begin();
  loadHiScore();
}

void loop() {
  if (!arduboy.nextFrame()) return;
  arduboy.pollButtons();
  beep.timer();
  arduboy.clear();

  switch (state) {
    case TITLE:
      drawTitle();
      if (arduboy.justPressed(B_BUTTON)) {
        if (arduboy.audio.enabled()) arduboy.audio.off();
        else arduboy.audio.on();
        arduboy.audio.saveOnOff();
        sfx(880, 5);
      }
      if (arduboy.justPressed(A_BUTTON)) {
        arduboy.initRandomSeed();
        newGame();
      }
      break;

    case PLAYING:
      updatePlayer();
      if (state == PLAYING) updateEnemies();
      updatePops();
      drawWorld();
      drawPlayer();
      drawHud();
      break;

    case DYING:
      // Pip hops up and falls off the screen
      if (stateTimer < 70) {
        py += vy;
        vy += 4;
      }
      drawWorld();
      if ((py >> 4) < HEIGHT) drawPlayer();
      drawHud();
      if (--stateTimer == 0) {
        if (--lives == 0) {
          saveHiScore();
          state = GAMEOVER;
          stateTimer = 255;
        } else {
          loadLevel();
        }
      }
      break;

    case CLEAR:
      updatePops();
      drawWorld();
      drawPlayer();
      drawHud();
      printCentered(F("LEVEL CLEAR!"), 12, 24, 1);
      if (--stateTimer == 0) {
        if (++levelNum >= NUM_LEVELS) {
          saveHiScore();
          state = WIN;
        } else {
          loadLevel();
        }
      }
      break;

    case GAMEOVER:
      printCentered(F("GAME OVER"), 9, 16, 2);
      arduboy.setCursor(28, 40);
      arduboy.print(F("SCORE "));
      arduboy.print(score);
      if (stateTimer) stateTimer--;
      else if (arduboy.justPressed(A_BUTTON)) state = TITLE;
      break;

    case WIN:
      printCentered(F("YOU WIN!"), 8, 8, 2);
      printCentered(F("PIP IS HOME"), 11, 28, 1);
      arduboy.setCursor(28, 44);
      arduboy.print(F("SCORE "));
      arduboy.print(score);
      if (arduboy.justPressed(A_BUTTON)) state = TITLE;
      break;
  }

  arduboy.display();
}
