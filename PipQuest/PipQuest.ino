// =====================================================================
//  PIP QUEST  -  a side-scrolling platformer for the Arduboy
//
//  Controls:  LEFT / RIGHT  move
//             A             jump (tap = small jump, hold = high jump)
//             B             run - and with a power-up:
//                             Spark Flower: B shoots bouncing sparks
//                             Feather:      hold B to fly, hold A to glide
//  Title:     B toggles sound
//
//  Power-ups come out of ? blocks that hold an item:
//    Berry   - Pip grows big, can break bricks and survive one hit
//    Flower  - (when big) shoot sparks with B
//    Feather - (when big) fly with B
//  Lives are infinite; you restart from the last checkpoint flag.
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
constexpr int16_t FLY_V      = -30;
constexpr int16_t GLIDE_V    = 12;
constexpr uint8_t FLY_MAX    = 150;   // frames of flight per landing
constexpr uint8_t MAX_ENEMIES = 16;
constexpr uint8_t MAX_POPS    = 4;
constexpr uint8_t MAX_SPARKS  = 2;

constexpr int EEPROM_ADDR  = EEPROM_STORAGE_SPACE_START + 160;
constexpr uint8_t EEPROM_MAGIC = 0x5B;

enum GameState : uint8_t { TITLE, PLAYING, DYING, CLEAR, WIN };
enum Power : uint8_t { SMALL, BIG, SPARK, WING };
enum EnemyType : uint8_t { BLOB, SNAIL, SHELL, SPIKY };
enum EnemyState : uint8_t { E_GONE, E_WAITING, E_ACTIVE, E_SQUASHED, E_POOF };

// ------------------------------------------------------------ game data
struct Enemy {
  int16_t x, y;      // pixels
  int8_t  dir;       // -1 left, 1 right (a shell with dir 0 is sitting still)
  uint8_t type;
  uint8_t state;
  uint8_t timer;     // squash/poof time, or kick grace time for shells
};

struct Pop {         // coin that pops out of a ? block
  int16_t x, y;
  uint8_t t;
};

struct Item {        // power-up
  int16_t x, y;
  int8_t  dir;
  uint8_t type;      // ITEM_BERRY, ITEM_FLOWER, ITEM_FEATHER
  uint8_t rise;      // > 0 while it climbs out of the block
  bool    active;
};

struct Spark {
  int16_t x, y;
  int8_t  vx, vy;
  bool    active;
};

GameState state = TITLE;
uint8_t  levelNum;
uint8_t  coins;
uint16_t score;
uint16_t hiScore;
uint8_t  stateTimer;

int16_t px, py;      // player position (1/16 pixel), py is the top of Pip
int16_t vx, vy;      // player velocity (1/16 pixel per frame)
bool    onGround;
bool    facingLeft;
bool    flying;
uint8_t coyote;      // frames left to still jump after walking off a ledge
uint8_t jumpBuffer;  // frames a jump press is remembered before landing
uint8_t walkAnim;
uint8_t power;
uint8_t invuln;      // blink frames after getting hit
uint8_t flyMeter;
int16_t checkX;      // checkpoint x in pixels, -1 = level start
int16_t camX;

Enemy enemies[MAX_ENEMIES];
Pop   pops[MAX_POPS];
Spark sparks[MAX_SPARKS];
Item  item;
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
// 'U' is an emptied block.
char tileAt(int16_t tx, int16_t ty) {
  if (tx < 0 || tx >= LEVEL_W) return '#';     // invisible side walls
  if (ty < 0 || ty >= LEVEL_H) return '.';     // open sky / bottomless pits
  char c = rawTile(tx, ty);
  if (c == 0 || c == 'e' || c == 't' || c == 'k' || c == 'S') return '.';
  if (isUsed(tx, ty)) return (c == '?' || c == 'M' || c == 'W') ? 'U' : '.';
  return c;
}

bool isSolid(char c) {
  return c == '#' || c == 'B' || c == '?' || c == 'U' || c == 'P' || c == 'M' || c == 'W';
}

bool solidAt(int16_t x, int16_t y) {           // pixel coordinates
  return isSolid(tileAt(x >> 3, y >> 3));
}

// Is anything solid in the vertical span y..y+h-1 at column x?
bool wallAt(int16_t x, int16_t y, int16_t h) {
  int16_t last = y + h - 1;
  for (int16_t yy = y; ; yy += TILE) {
    if (yy > last) yy = last;
    if (solidAt(x, yy)) return true;
    if (yy == last) return false;
  }
}

int16_t playerH() {
  return power == SMALL ? 8 : 16;
}

// ------------------------------------------------------------ level setup
void loadLevel() {
  memset(usedBits, 0, sizeof(usedBits));
  memset(pops, 0, sizeof(pops));
  memset(enemies, 0, sizeof(enemies));
  memset(sparks, 0, sizeof(sparks));
  item.active = false;
  int16_t startX = 2 * TILE;
  int16_t startY = 5 * TILE;
  uint8_t n = 0;
  for (int16_t ty = 0; ty < LEVEL_H; ty++) {
    for (int16_t tx = 0; tx < LEVEL_W; tx++) {
      char c = rawTile(tx, ty);
      if (c == 'S') {
        startX = tx * TILE;
        startY = ty * TILE;
      } else if ((c == 'e' || c == 't' || c == 'k') && n < MAX_ENEMIES) {
        Enemy &e = enemies[n++];
        e.x = tx * TILE;
        e.y = ty * TILE;
        e.dir = -1;
        e.type = (c == 'e') ? BLOB : (c == 't') ? SNAIL : SPIKY;
        e.state = E_WAITING;
      }
    }
  }
  if (checkX >= 0) {
    startX = checkX;
    startY = 5 * TILE;
  }
  px = startX << 4;
  py = (startY + 8 - playerH()) << 4;
  vx = vy = 0;
  onGround = false;
  facingLeft = false;
  flying = false;
  coyote = jumpBuffer = 0;
  invuln = 0;
  flyMeter = FLY_MAX;
  camX = startX - 56;
  if (camX < 0) camX = 0;
  if (camX > LEVEL_PX - WIDTH) camX = LEVEL_PX - WIDTH;
  // enemies behind a checkpoint don't come back
  if (checkX >= 0) {
    for (uint8_t i = 0; i < MAX_ENEMIES; i++) {
      if (enemies[i].x < startX + 24) enemies[i].state = E_GONE;
    }
  }
  state = PLAYING;
}

void newGame() {
  levelNum = 0;
  coins = 0;
  score = 0;
  power = SMALL;
  checkX = -1;
  loadLevel();
}

void addScore(uint16_t pts) {
  score = (score > 65535 - pts) ? 65535 : score + pts;
}

void addCoin() {
  addScore(100);
  if (++coins >= 100) coins = 0;
  sfx(1319, 4);
}

void killPlayer() {
  state = DYING;
  stateTimer = 90;
  vy = -70;
  vx = 0;
  flying = false;
  sfx(196, 30);
}

// Grow or shrink while keeping Pip's feet where they are
void setPower(uint8_t p) {
  int16_t oldH = playerH();
  power = p;
  py += (oldH - playerH()) << 4;
}

void hurtPlayer() {
  if (invuln) return;
  if (power != SMALL) {
    setPower(SMALL);
    invuln = 90;
    sfx(150, 15);
  } else {
    killPlayer();
  }
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

void defeatEnemy(Enemy &e) {
  e.state = E_POOF;
  e.timer = 12;
  addScore(200);
  sfx(880, 4);
}

void bumpTile(int16_t tx, int16_t ty) {
  char c = tileAt(tx, ty);
  if (c == '?') {
    setUsed(tx, ty);
    spawnPop(tx * TILE, ty * TILE - TILE);
    addCoin();
  } else if (c == 'M' || c == 'W') {
    setUsed(tx, ty);
    item.active = true;
    item.x = tx * TILE;
    item.y = ty * TILE;
    item.rise = TILE;
    item.dir = 1;
    if (power == SMALL) item.type = ITEM_BERRY;
    else item.type = (c == 'W') ? ITEM_FEATHER : ITEM_FLOWER;
    sfx(523, 10);
  } else if (c == 'B' && power != SMALL) {
    setUsed(tx, ty);                           // big Pip smashes bricks
    addScore(50);
    sfx(220, 4);
  } else {
    sfx(110, 3);                               // small Pip just bumps it
  }
  // knock out any enemy standing on the bumped block
  for (uint8_t i = 0; i < MAX_ENEMIES; i++) {
    Enemy &e = enemies[i];
    if (e.state == E_ACTIVE && e.y + 8 == ty * TILE &&
        e.x + 7 >= tx * TILE && e.x <= tx * TILE + 7) {
      defeatEnemy(e);
    }
  }
}

// ------------------------------------------------------------ sparks
void shootSpark() {
  for (uint8_t i = 0; i < MAX_SPARKS; i++) {
    Spark &s = sparks[i];
    if (!s.active) {
      s.active = true;
      s.x = (px >> 4) + (facingLeft ? -2 : 6);
      s.y = (py >> 4) + 4;
      s.vx = facingLeft ? -3 : 3;
      s.vy = 0;
      sfx(1047, 3);
      return;
    }
  }
}

void updateSparks() {
  for (uint8_t i = 0; i < MAX_SPARKS; i++) {
    Spark &s = sparks[i];
    if (!s.active) continue;
    s.x += s.vx;
    if (solidAt(s.x + (s.vx > 0 ? 3 : 0), s.y + 1)) {   // hit a wall
      s.active = false;
      continue;
    }
    if (s.vy < 3) s.vy++;
    s.y += s.vy;
    if (s.vy > 0 && (solidAt(s.x, s.y + 3) || solidAt(s.x + 3, s.y + 3))) {
      s.y = ((s.y + 3) >> 3) * TILE - 4;                // bounce
      s.vy = -3;
    }
    if (s.x < camX - 8 || s.x > camX + WIDTH || s.y > HEIGHT) {
      s.active = false;
      continue;
    }
    for (uint8_t j = 0; j < MAX_ENEMIES; j++) {
      Enemy &e = enemies[j];
      if (e.state == E_ACTIVE && s.x + 3 >= e.x && s.x <= e.x + 7 &&
          s.y + 3 >= e.y && s.y <= e.y + 7) {
        defeatEnemy(e);
        s.active = false;
        break;
      }
    }
  }
}

// ------------------------------------------------------------ items
void updateItem() {
  if (!item.active) return;
  if (item.rise) {                             // climb out of the block
    if (arduboy.frameCount & 1) {
      item.y--;
      item.rise--;
    }
    return;
  }
  if (item.type == ITEM_BERRY) {               // berries roll away
    int16_t nx = item.x + item.dir;
    int16_t edge = (item.dir > 0) ? nx + 7 : nx;
    if (solidAt(edge, item.y + 4)) item.dir = -item.dir;
    else item.x = nx;
    if (!solidAt(item.x + 1, item.y + 8) && !solidAt(item.x + 6, item.y + 8)) item.y += 2;
  }
  if (item.y > HEIGHT || item.x < camX - 16) {
    item.active = false;
    return;
  }

  int16_t X = px >> 4, Y = py >> 4, h = playerH();
  if (X + 6 >= item.x && X + 1 <= item.x + 7 && Y + h - 1 >= item.y && Y <= item.y + 7) {
    item.active = false;
    addScore(1000);
    if (item.type == ITEM_BERRY) {
      if (power == SMALL) setPower(BIG);
    } else if (item.type == ITEM_FLOWER) {
      setPower(SPARK);
    } else {
      setPower(WING);
      flyMeter = FLY_MAX;
    }
    sfx(1568, 20);
  }
}

// ------------------------------------------------------------ player
void updatePlayer() {
  int16_t h = playerH();
  bool bHeld = arduboy.pressed(B_BUTTON);
  int16_t maxV = bHeld ? RUN_MAX : WALK_MAX;   // B always runs as well
  int16_t accel = onGround ? 3 : 2;

  if (arduboy.pressed(LEFT_BUTTON)) {
    if (vx > -maxV) { vx -= accel; if (vx < -maxV) vx = -maxV; }
    facingLeft = true;
  } else if (arduboy.pressed(RIGHT_BUTTON)) {
    if (vx < maxV) { vx += accel; if (vx > maxV) vx = maxV; }
    facingLeft = false;
  } else if (onGround) {
    if (vx > 0) { vx -= 3; if (vx < 0) vx = 0; }
    else if (vx < 0) { vx += 3; if (vx > 0) vx = 0; }
  }
  // let go of B while running: ease back down to walking speed
  if (vx > maxV) { vx -= 2; if (vx < maxV) vx = maxV; }
  if (vx < -maxV) { vx += 2; if (vx > -maxV) vx = -maxV; }

  if (arduboy.justPressed(A_BUTTON)) jumpBuffer = 6;
  else if (jumpBuffer) jumpBuffer--;
  if (jumpBuffer && coyote) {
    vy = (abs(vx) > WALK_MAX) ? RUN_JUMP_V : JUMP_V;
    onGround = false;
    jumpBuffer = 0;
    coyote = 0;
    sfx(660, 4);
  }

  // power-up actions on B
  if (power == SPARK && arduboy.justPressed(B_BUTTON)) shootSpark();
  flying = false;
  if (power == WING && !onGround) {
    if (bHeld && flyMeter > 0) {
      flying = true;
      if (vy > FLY_V) {                        // rise (never slows a jump down)
        vy -= GRAVITY + 6;
        if (vy < FLY_V) vy = FLY_V;
        flyMeter--;
        if ((arduboy.frameCount & 7) == 0) sfx(330, 2);
      }
    } else if (arduboy.pressed(A_BUTTON) && vy > GLIDE_V - GRAVITY) {
      vy = GLIDE_V - GRAVITY;                  // glide down slowly
    }
  }
  if (onGround) flyMeter = (flyMeter > FLY_MAX - 3) ? FLY_MAX : flyMeter + 3;

  if (!flying && !arduboy.pressed(A_BUTTON) && vy < -48) vy = -48;  // tap = small jump
  vy += GRAVITY;
  if (vy > MAX_FALL) vy = MAX_FALL;
  if (flying && (py >> 4) < 2 && vy < 0) vy = 0;   // fly no higher than the score bar

  // --- horizontal movement and collision (hitbox is x+1..x+6, y..y+h-1)
  // Walls only stop Pip when he moves into them. If he is already overlapping
  // a block (e.g. he grew under a low ceiling) he can walk out of it.
  int16_t oldX = px >> 4, Y = py >> 4;
  px += vx;
  int16_t X = px >> 4;
  if (vx > 0) {
    int16_t r = X + 6;
    if (wallAt(r, Y, h) && !wallAt(oldX + 6, Y, h)) {
      X = (r >> 3) * TILE - 7;
      px = X << 4;
      vx = 0;
    }
  } else if (vx < 0) {
    int16_t l = X + 1;
    if (wallAt(l, Y, h) && !wallAt(oldX + 1, Y, h)) {
      X = ((l >> 3) + 1) * TILE - 1;
      px = X << 4;
      vx = 0;
    }
  }
  if (px < 0) px = 0;                          // never leave the level
  if (px > (LEVEL_PX - 8) << 4) px = (LEVEL_PX - 8) << 4;
  X = px >> 4;

  // --- vertical movement and collision
  py += vy;
  Y = py >> 4;
  onGround = false;
  if (vy > 0) {
    int16_t b = Y + h - 1;
    if (solidAt(X + 1, b) || solidAt(X + 6, b)) {
      Y = (b >> 3) * TILE - h;
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
  // Standing still only sinks a fraction of a pixel per frame, so also check
  // the row just below the feet; otherwise onGround flickers every other frame.
  if (!onGround && vy >= 0 && ((Y + h) & 7) == 0 &&
      (solidAt(X + 1, Y + h) || solidAt(X + 6, Y + h))) {
    py = Y << 4;
    vy = 0;
    onGround = true;
  }
  if (onGround) coyote = 6;
  else if (coyote) coyote--;

  // --- pickups, hazards and checkpoints
  for (int16_t ty = Y >> 3; ty <= (Y + h - 1) >> 3; ty++) {
    for (int16_t tx = (X + 1) >> 3; tx <= (X + 6) >> 3; tx++) {
      char c = tileAt(tx, ty);
      if (c == 'o') {
        setUsed(tx, ty);
        addCoin();
      } else if (c == 's' && Y + h - 1 >= ty * TILE + 3) {
        killPlayer();                          // spikes hurt even big Pip
        return;
      } else if (c == 'K' && checkX < tx * TILE) {
        checkX = tx * TILE;
        sfx(988, 10);
      }
    }
  }

  // The goal counts the whole pole column, so Pip can't jump over the top of it.
  for (int16_t tx = (X + 1) >> 3; tx <= (X + 6) >> 3; tx++) {
    if (tileAt(tx, LEVEL_H - 3) == 'F') {
      state = CLEAR;
      stateTimer = 150;
      flying = false;
      int16_t hh = (Y < 0) ? 0 : (Y >> 4);     // grab the pole higher = more points
      addScore((uint16_t)(5 - (hh > 4 ? 4 : hh)) * 400);
      sfx(784, 30);
      return;
    }
  }

  if (Y > HEIGHT + 8) {                        // fell into a pit
    killPlayer();
    return;
  }

  if (vx != 0 && onGround) walkAnim++;
  if (invuln) invuln--;

  // camera
  camX = X - 56;
  if (camX < 0) camX = 0;
  if (camX > LEVEL_PX - WIDTH) camX = LEVEL_PX - WIDTH;
}

// ------------------------------------------------------------ enemies
bool enemiesTouch(const Enemy &a, const Enemy &b) {
  return abs(a.x - b.x) < 8 && abs(a.y - b.y) < 8;
}

void kickShell(Enemy &e, int16_t playerX) {
  e.dir = (playerX + 4 < e.x + 4) ? 1 : -1;
  e.timer = 10;                                // can't hurt Pip right after a kick
  addScore(100);
  sfx(440, 4);
}

void updateEnemies() {
  int16_t X = px >> 4, Y = py >> 4, h = playerH();
  for (uint8_t i = 0; i < MAX_ENEMIES; i++) {
    Enemy &e = enemies[i];
    if (e.state == E_GONE) continue;
    if (e.state == E_WAITING) {                // wake when nearly on screen
      if (e.x < camX + WIDTH + 8) e.state = E_ACTIVE;
      else continue;
    }
    if (e.state == E_SQUASHED || e.state == E_POOF) {
      if (--e.timer == 0) e.state = E_GONE;
      continue;
    }
    if (e.timer) e.timer--;

    // move
    if (e.type == SHELL) {
      if (e.dir) {                             // sliding shell: fast
        int16_t nx = e.x + e.dir * 3;
        int16_t edge = (e.dir > 0) ? nx + 7 : nx;
        if (solidAt(edge, e.y + 4)) {
          e.dir = -e.dir;
          sfx(110, 2);
        } else {
          e.x = nx;
        }
        if (e.x < camX - 32 || e.x > camX + WIDTH + 32) { e.state = E_GONE; continue; }
      }
    } else if (arduboy.frameCount & 1) {       // walkers: half a pixel per frame
      int16_t nx = e.x + e.dir;
      int16_t edge = (e.dir > 0) ? nx + 7 : nx;
      if (solidAt(edge, e.y + 4)) e.dir = -e.dir;
      else e.x = nx;
    }
    if (!solidAt(e.x + 1, e.y + 8) && !solidAt(e.x + 6, e.y + 8)) e.y += 2;
    if (e.y > HEIGHT) { e.state = E_GONE; continue; }

    // sliding shells knock out everything they hit; walkers turn around
    for (uint8_t j = 0; j < MAX_ENEMIES; j++) {
      Enemy &o = enemies[j];
      if (j == i || o.state != E_ACTIVE || !enemiesTouch(e, o)) continue;
      if (e.type == SHELL && e.dir) {
        defeatEnemy(o);
      } else if (e.type != SHELL && o.type != SHELL &&
                 ((e.dir > 0 && o.x > e.x) || (e.dir < 0 && o.x < e.x))) {
        e.dir = -e.dir;
      }
    }

    // touch the player
    if (X + 1 < e.x + 7 && X + 6 > e.x && Y < e.y + 8 && Y + h > e.y + 1) {
      bool stomp = vy > 0 && Y + h - 1 < e.y + 5;
      if (stomp && e.type != SPIKY) {
        if (e.type == BLOB) {
          e.state = E_SQUASHED;
          e.timer = 20;
          addScore(200);
        } else if (e.type == SNAIL) {
          e.type = SHELL;                      // snail hides in its shell
          e.dir = 0;
          e.timer = 8;
          addScore(200);
        } else if (e.dir) {
          e.dir = 0;                           // stop a sliding shell
          e.timer = 8;
        } else {
          kickShell(e, X);
        }
        vy = arduboy.pressed(A_BUTTON) ? JUMP_V : STOMP_V;
        sfx(880, 4);
      } else if (e.type == SHELL && e.dir == 0) {
        if (!e.timer) kickShell(e, X);         // walk into a shell to kick it
      } else if (!(e.type == SHELL && e.timer)) {
        hurtPlayer();
        if (state != PLAYING) return;
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
    for (int16_t ty = 1; ty < LEVEL_H; ty++) {
      char c = tileAt(tx, ty);
      int8_t f = -1;
      switch (c) {
        case '#': f = TILE_GROUND; break;
        case 'B': f = TILE_BRICK; break;
        case '?': case 'M': case 'W': f = TILE_QUESTION; break;
        case 'U': f = TILE_USED; break;
        case 'o': f = coinFrame; break;
        case 's': f = TILE_SPIKE; break;
        case 'K': f = (checkX == tx * TILE) ? TILE_CHECK_ON : TILE_CHECK_OFF; break;
        case 'F': f = (tileAt(tx, ty - 1) == 'F') ? TILE_POLE : TILE_FLAG; break;
        case 'P': {
          bool left = tileAt(tx - 1, ty) != 'P';
          bool top = tileAt(tx, ty - 1) != 'P';
          f = top ? (left ? TILE_PIPE_TOP_L : TILE_PIPE_TOP_R)
                  : (left ? TILE_PIPE_L : TILE_PIPE_R);
          break;
        }
      }
      if (f >= 0) Sprites::drawSelfMasked(sx, ty * TILE, tileSprite, f);
    }
  }

  for (uint8_t i = 0; i < MAX_POPS; i++) {
    if (pops[i].t) Sprites::drawSelfMasked(pops[i].x - camX, pops[i].y, tileSprite, coinFrame);
  }

  if (item.active) {
    int16_t sx = item.x - camX;
    Sprites::drawSelfMasked(sx, item.y, itemSprite, item.type);
    if (item.rise) {                           // keep the block drawn in front
      int16_t blockY = item.y + TILE - item.rise;
      arduboy.fillRect(sx, blockY, 8, 8, BLACK);
      Sprites::drawSelfMasked(sx, blockY, tileSprite, TILE_USED);
    }
  }

  for (uint8_t i = 0; i < MAX_SPARKS; i++) {
    if (sparks[i].active) Sprites::drawSelfMasked(sparks[i].x - camX, sparks[i].y, itemSprite, ITEM_SPARK);
  }

  uint8_t anim = (arduboy.frameCount >> 4) & 1;
  for (uint8_t i = 0; i < MAX_ENEMIES; i++) {
    Enemy &e = enemies[i];
    int16_t sx = e.x - camX;
    if (e.state == E_POOF) {
      Sprites::drawSelfMasked(sx, e.y, itemSprite, ITEM_POOF);
    } else if (e.state == E_SQUASHED) {
      Sprites::drawSelfMasked(sx, e.y, blobSprite, 2);
    } else if (e.state == E_ACTIVE) {
      switch (e.type) {
        case BLOB:  Sprites::drawSelfMasked(sx, e.y, blobSprite, anim); break;
        case SNAIL: Sprites::drawSelfMasked(sx, e.y, snailSprite, anim + (e.dir < 0 ? 2 : 0)); break;
        case SHELL: Sprites::drawSelfMasked(sx, e.y, shellSprite, 0); break;
        case SPIKY: Sprites::drawSelfMasked(sx, e.y, spikySprite, anim); break;
      }
    }
  }
}

void drawPlayer() {
  if (invuln && (arduboy.frameCount & 2)) return;   // blink after a hit
  uint8_t pose;
  if (flying) pose = ((arduboy.frameCount >> 2) & 1) ? 2 : 0;   // flap
  else if (!onGround || state == DYING) pose = 2;
  else if (vx != 0) pose = (walkAnim >> 2) & 1;
  else pose = 0;
  if (facingLeft) pose += 3;
  int16_t sx = (px >> 4) - camX;
  int16_t sy = py >> 4;
  if (power == SMALL) {
    arduboy.fillRect(sx + 1, sy, 6, 8, BLACK);  // keep Pip visible over tiles
    Sprites::drawSelfMasked(sx, sy, heroSprite, pose);
  } else {
    arduboy.fillRect(sx + 1, sy, 6, 16, BLACK);
    Sprites::drawSelfMasked(sx, sy, heroBigSprite, (power - 1) * 6 + pose);
  }
}

void printNum(uint16_t n, uint8_t digits) {
  uint16_t lim = 10;
  for (uint8_t d = 1; d < digits; d++, lim *= 10) {
    if (n < lim) arduboy.print('0');
  }
  arduboy.print(n);
}

void drawHud() {
  arduboy.fillRect(0, 0, WIDTH, 8, BLACK);
  arduboy.setCursor(0, 0);
  arduboy.print(F("W"));
  arduboy.print(levelNum + 1);
  arduboy.setCursor(18, 0);
  arduboy.print(F("$"));
  printNum(coins, 2);
  if (power == SPARK) {
    Sprites::drawSelfMasked(44, 0, itemSprite, ITEM_FLOWER);
  } else if (power == WING) {
    Sprites::drawSelfMasked(44, 0, itemSprite, ITEM_FEATHER);
    arduboy.drawRect(54, 2, 22, 4, WHITE);     // flight meter
    arduboy.fillRect(55, 3, flyMeter * 20 / FLY_MAX, 2, WHITE);
  } else if (power == BIG) {
    Sprites::drawSelfMasked(44, 0, itemSprite, ITEM_BERRY);
  }
  arduboy.setCursor(98, 0);
  printNum(score, 5);
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
  Sprites::drawSelfMasked(104, 48, tileSprite, TILE_PIPE_TOP_L);
  Sprites::drawSelfMasked(112, 48, tileSprite, TILE_PIPE_TOP_R);
  Sprites::drawSelfMasked(88, 48, blobSprite, (arduboy.frameCount >> 4) & 1);
  Sprites::drawSelfMasked(20, 40, heroBigSprite, (arduboy.frameCount >> 3) & 1);

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
      if (arduboy.justPressed(A_BUTTON)) newGame();
      break;

    case PLAYING:
      updatePlayer();
      if (state == PLAYING) updateEnemies();
      updateSparks();
      updateItem();
      updatePops();
      drawWorld();
      drawPlayer();
      drawHud();
      break;

    case DYING:
      // Pip hops up and falls off the screen, then restarts (infinite lives)
      if (stateTimer < 70) {
        py += vy;
        vy += 4;
      }
      drawWorld();
      if ((py >> 4) < HEIGHT) drawPlayer();
      drawHud();
      if (--stateTimer == 0) {
        power = SMALL;
        loadLevel();
      }
      break;

    case CLEAR:
      updatePops();
      drawWorld();
      drawPlayer();
      drawHud();
      printCentered(F("WORLD CLEAR!"), 12, 24, 1);
      if (--stateTimer == 0) {
        checkX = -1;
        saveHiScore();
        if (++levelNum >= NUM_LEVELS) {
          saveHiScore();
          state = WIN;
        } else {
          loadLevel();
        }
      }
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
