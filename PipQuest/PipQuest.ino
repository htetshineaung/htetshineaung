// =====================================================================
//  PIP QUEST  -  a side-scrolling platformer for the Arduboy
//
//  Controls:  LEFT / RIGHT  move
//             A             jump (tap = small jump, hold = high jump)
//             B             run - and with a power-up:
//                             Spark Flower: B shoots bouncing sparks
//                             Feather:      hold B to fly, hold A to glide
//  Title:     B toggles sound
//  Title:     UP / DOWN picks the starting level (up to the furthest reached)
//
//  Power-ups come out of ? blocks that hold an item:
//    Berry   - Pip grows big, can break bricks and survive one hit
//    Flower  - (when big) shoot sparks with B
//    Feather - (when big) fly with B
//  128 levels are built from the level number (see the level builder below).
//  You have 5 lives (+1 every 100 coins). After a Game Over you can continue
//  from the same level with a fresh score.
// =====================================================================
#include <Arduboy2.h>
#include <EEPROM.h>
#include "sprites.h"
#include "levels.h"

Arduboy2 arduboy;
BeepPin1 beep;

// ------------------------------------------------------------ constants
constexpr int16_t TILE       = 8;
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
constexpr uint8_t START_LIVES = 5;
constexpr uint8_t MAX_CHUNKS  = LEVEL_W / 8;

constexpr int EEPROM_ADDR  = EEPROM_STORAGE_SPACE_START + 160;
constexpr uint8_t EEPROM_MAGIC = 0x5C;   // then hiScore (2 bytes), furthest level (1)

enum GameState : uint8_t { TITLE, INTRO, PLAYING, DYING, CLEAR, GAMEOVER, WIN };
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
uint8_t  maxLevel;   // furthest level reached (saved)
uint8_t  lives;
uint8_t  theme;      // 0 hills, 1 spike hills, 2 cave, 3 sky
uint8_t  numChunks;  // the level is numChunks sections of 8 columns
int16_t  levelW;     // level width in tiles
int16_t  levelPx;    // level width in pixels
uint8_t  chType[MAX_CHUNKS], chG[MAX_CHUNKS], chA[MAX_CHUNKS], chB[MAX_CHUNKS];
uint16_t rngState;
uint8_t  coins;
uint16_t score;
uint16_t hiScore;
uint8_t  stateTimer;
uint8_t  selLevel;   // level picked on the title screen

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

// ------------------------------------------------------------ level builder
// Each level is a row of 8-column sections. Every section is one feature
// (a gap, pipes, a hill, stairs...) with its own random size, so no two levels
// are alike. The random numbers come from the level number, so a level is
// the same every time you play it. Difficulty rises with the level number.
enum Feature : uint8_t {
  F_FLAT, F_GAP, F_PIPE, F_BLOCKS, F_STAIRS, F_SPIKES, F_HILL, F_PLATFORM,
  F_SQUAD, F_WALL, NUM_FEATURES, F_START, F_GOAL_STAIRS, F_FLAG
};
const uint8_t featureWeight[4][NUM_FEATURES] PROGMEM = {
  // flat gap pipe blocks stairs spikes hill platform squad wall
  {  2,   3,   3,   3,     2,     1,     3,   1,       2,    1 },   // hills
  {  1,   3,   2,   2,     2,     4,     2,   2,       2,    2 },   // spike hills
  {  2,   3,   2,   4,     2,     2,     1,   0,       3,    3 },   // cave
  {  0,   3,   0,   2,     1,     0,     1,   6,       1,    0 },   // sky
};

uint16_t mix(uint16_t x) {                     // small deterministic hash
  x ^= x << 7;
  x ^= x >> 9;
  x ^= x << 8;
  return x * 40503u;
}

uint8_t rnd8() {                               // next random byte from the level's seed
  rngState ^= rngState << 7;
  rngState ^= rngState >> 9;
  rngState ^= rngState << 8;
  return rngState >> 3;
}

uint8_t rnd(uint8_t n) {                       // 0..n-1
  return rnd8() % n;
}

uint8_t upTo(uint8_t lo, uint8_t hi) {         // lo..hi inclusive
  return lo + rnd(hi - lo + 1);
}

void buildLevel() {
  uint8_t d = levelNum;
  theme = d & 3;
  rngState = mix(d * 31 + 7) | 1;
  uint8_t mid = 11 + d / 8;                    // longer levels later on
  if (mid > MAX_CHUNKS - 3) mid = MAX_CHUNKS - 3;
  numChunks = mid + 3;
  levelW = numChunks * 8;
  levelPx = levelW * TILE;

  bool cave = theme == 2;
  uint8_t maxGap = d < 6 ? 2 : d < 30 ? 3 : 4;
  uint8_t maxEnemy = d < 10 ? 1 : d < 40 ? 2 : 3;
  uint8_t maxSpike = 1 + d / 20;
  if (maxSpike > 4) maxSpike = 4;
  uint8_t maxPipe = cave ? 2 : (d < 10 ? 2 : 3);
  uint8_t maxStair = cave ? 2 : (2 + d / 25 > 4 ? 4 : 2 + d / 25);
  uint8_t enemies = 0;
  uint8_t prev = F_START, prev2 = F_START;

  chType[0] = F_START;
  chG[0] = 6;
  for (uint8_t i = 1; i <= mid; i++) {
    // pick a feature by weight, never the same as one of the last two
    uint8_t t = F_FLAT;
    for (uint8_t tries = 0; tries < 12; tries++) {
      uint8_t total = 0, w[NUM_FEATURES];
      for (uint8_t f = 0; f < NUM_FEATURES; f++) {
        w[f] = pgm_read_byte(&featureWeight[theme][f]);
        if ((f == F_SPIKES && d < 4) || (f == F_SQUAD && d < 3) || (f == F_WALL && d < 6)) w[f] = 0;
        total += w[f];
      }
      uint8_t r = rnd(total);
      for (t = 0; r >= w[t]; t++) r -= w[t];
      if (t != prev && t != prev2) break;
    }
    if (i == 2) t = F_BLOCKS;                  // a power-up early in every level
    if (i == 1 && t == F_BLOCKS) t = cave ? F_PIPE : F_HILL;
    uint8_t a = 0, b = rnd8(), g = 6;
    switch (t) {
      case F_FLAT:     a = rnd(3); b = rnd(maxEnemy + 1); break;
      case F_GAP:      a = upTo(1, maxGap); break;
      case F_PIPE:     a = upTo(1, maxPipe); break;
      case F_BLOCKS:   a = upTo(2, 6); b &= 0x7F; break;
      case F_STAIRS:   a = upTo(2, maxStair); break;
      case F_SPIKES:   a = upTo(1, maxSpike); break;
      case F_HILL:     g = (cave || d < 8) ? 5 : upTo(4, 5); a = rnd(4); break;
      case F_PLATFORM: a = rnd(cave ? 2 : 3); break;
      case F_SQUAD:    a = upTo(2, maxEnemy + 1); break;
      case F_WALL:     a = upTo(2, cave ? 2 : 3); break;
    }
    // keep within the number of enemies the game can track
    uint8_t want = 0;
    if (t == F_FLAT) want = b;
    else if (t == F_SQUAD) want = a;
    else if (t == F_PIPE || t == F_BLOCKS || t == F_PLATFORM) want = b & 1;
    else if (t == F_HILL) want = a & 1;
    if (enemies + want > MAX_ENEMIES - 1) {
      if (t == F_FLAT) b = 0;
      else if (t == F_SQUAD) t = F_FLAT, a = 1, b = 0;
      else if (t == F_HILL) a &= ~1;
      else b &= ~1;
      want = 0;
    }
    enemies += want;
    chType[i] = t;
    chG[i] = g;
    chA[i] = a;
    chB[i] = b;
    prev2 = prev;
    prev = t;
  }
  // power-up blocks: always one early, and sometimes a second one later
  chB[2] |= 0x80;
  if (d >= 10 && rnd(2)) {
    for (uint8_t i = mid; i > 4; i--) {
      if (chType[i] == F_BLOCKS) { chB[i] |= 0x80; break; }
    }
  }
  chType[mid + 1] = F_GOAL_STAIRS;
  chA[mid + 1] = cave ? 4 : upTo(3, 5);
  chType[mid + 2] = F_FLAG;
  chG[mid + 1] = chG[mid + 2] = 6;
}

// The tile the level builder puts at (tx, ty), before anything was collected.
char rawTile(int16_t tx, int16_t ty) {
  if (ty == 0) return '.';
  uint8_t ch = tx >> 3, c = tx & 7;
  uint8_t t = chType[ch], g = chG[ch], a = chA[ch], b = chB[ch];
  bool cave = theme == 2;
  if (cave && ty == 1 && ch < numChunks - 2) return 'B';   // cave ceiling
  bool ground = ty >= g;
  switch (t) {
    case F_START:
      return ground ? '#' : (ty == 5 && c == 2) ? 'S' : '.';

    case F_FLAT:                               // a: coins, b: enemies
      if (ground) return '#';
      if (ty == g - 1 && b && (c == 4 || (b > 1 && c == 6) || (b > 2 && c == 2))) return 'e';
      if (a == 1 && ty == g - 3 && c >= 2 && c <= 5) return 'o';
      if (a == 2 && ((ty == g - 3 && (c == 3 || c == 4)) || (ty == g - 2 && (c == 2 || c == 5)))) return 'o';
      return '.';

    case F_GAP: {                              // a: width
      uint8_t s = (8 - a) / 2;
      bool pit = c >= s && c < s + a;
      if (ground) return pit ? '.' : '#';
      if ((b & 1) && ty == g - 3 && c + 1 >= s && c <= s + a) return 'o';
      return '.';
    }

    case F_PIPE: {                             // a: height, b: 2nd pipe / enemy
      if (ground) return '#';
      bool two = (b & 2) && !cave;
      uint8_t h2 = (a == 1) ? 2 : a - 1;
      if ((c == 1 || c == 2) && ty >= g - a) return 'P';
      if (two && (c == 5 || c == 6) && ty >= g - h2) return 'P';
      if (!two && (b & 1) && c == 5 && ty == g - 1) return 'e';
      return '.';
    }

    case F_BLOCKS: {                           // a: length, b: extras, bit 7: power-up
      if (ground) return '#';
      uint8_t r = g - 3, s = (8 - a) / 2;
      bool in = c >= s && c < s + a;
      if (ty == r && in) {
        if ((b & 0x80) && c == s + a / 2) return (theme == 3 || (b & 0x40)) ? 'W' : 'M';
        return (mix(tx * 13 + levelNum) & 3) == 0 ? '?' : 'B';
      }
      if ((b & 2) && ty == r - 1 && in && r - 1 > (cave ? 1 : 0)) return 'o';
      if ((b & 1) && ty == g - 1 && c == s + a - 1) return 'e';
      return '.';
    }

    case F_STAIRS: {                           // a: height, b bit 0: pit at the top
      uint8_t h;
      if (c < a) h = c + 1;
      else if (c >= 8 - a) h = 8 - c;
      else h = (b & 1) ? 0 : a;                // pit between the two staircases
      if (h == 0) return '.';
      return ty >= g - h ? '#' : '.';
    }

    case F_SPIKES: {                           // a: width
      if (ground) return '#';
      uint8_t s = (8 - a) / 2;
      bool in = c >= s && c < s + a;
      if (ty == g - 1 && in) return 's';
      if (a >= 3 && ty == g - 3 && in) return 'B';         // a brick bridge above
      if (a >= 3 && ty == g - 4 && in && g - 4 > (cave ? 1 : 0) && (b & 1)) return 'o';
      return '.';
    }

    case F_HILL:                               // a: enemy / coins on top
      if (ground) return '#';
      if ((a & 1) && ty == g - 1 && c == 5) return 'e';
      if ((a & 2) && ty == g - 2 && c >= 2 && c <= 5) return 'o';
      return '.';

    case F_PLATFORM: {                         // a: platform height
      uint8_t pr = g - 1 - a;
      if (ground) return c < 2 ? '#' : '.';
      if (ty == pr && c >= 3 && c <= 5) return '#';
      if ((b & 1) && ty == pr - 1 && c == 4) return 'e';
      if ((b & 2) && ty == pr - 1 && (c == 3 || c == 5)) return 'o';
      return '.';
    }

    case F_SQUAD:                              // a: enemies, b bit 0: lead snail
      if (ground) return '#';
      if (ty == g - 1 && (c & 1) && (c >> 1) < a) return (c == 1 && (b & 1)) ? 't' : 'e';
      if ((b & 2) && ty == g - 3 && c >= 2 && c <= 5) return 'o';
      return '.';

    case F_WALL:                               // a: height, b bit 0: ? on top
      if (ground) return '#';
      if (c == 4 && ty >= g - a) return 'B';
      if ((b & 1) && !cave && c == 4 && ty == g - a - 2) return '?';
      return '.';

    case F_GOAL_STAIRS: {                      // a: tallest step
      if (ground) return '#';
      uint8_t h = (c >= 1 && c <= a) ? c : (c > a && c <= a + 1 ? a : 0);
      return (h && ty >= 6 - h) ? '#' : '.';
    }

    case F_FLAG:
      if (ground) return '#';
      return c == 3 ? 'F' : '.';
  }
  return '.';
}

// Tile at grid position, after taking collected/broken tiles into account.
// 'U' is an emptied block.
char tileAt(int16_t tx, int16_t ty) {
  if (tx < 0 || tx >= levelW) return '#';      // invisible side walls
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
  buildLevel();
  memset(usedBits, 0, sizeof(usedBits));
  memset(pops, 0, sizeof(pops));
  memset(enemies, 0, sizeof(enemies));
  memset(sparks, 0, sizeof(sparks));
  item.active = false;
  int16_t startX = 2 * TILE;
  int16_t startY = 5 * TILE;
  uint8_t n = 0;
  for (int16_t ty = 0; ty < LEVEL_H; ty++) {
    for (int16_t tx = 0; tx < levelW; tx++) {
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
        if (c == 'e') {                        // later levels get tougher enemies
          uint16_t r = mix(levelNum * 128 + tx);
          uint8_t chance = levelNum / 6;
          if (chance > 10) chance = 10;
          if ((r & 15) < chance) e.type = (r & 32) ? SPIKY : SNAIL;
        }
        e.state = E_WAITING;
      }
    }
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
  if (camX > levelPx - WIDTH) camX = levelPx - WIDTH;
  state = PLAYING;
}

void startLevel() {                            // show "LEVEL n" first
  state = INTRO;
  stateTimer = 90;
}

void newGame(uint8_t level) {
  levelNum = level;
  lives = START_LIVES;
  coins = 0;
  score = 0;
  power = SMALL;
  startLevel();
}

void addScore(uint16_t pts) {
  score = (score > 65535 - pts) ? 65535 : score + pts;
}

void addCoin() {
  addScore(100);
  if (++coins >= 100) {                        // 100 coins = extra life
    coins = 0;
    if (lives < 99) lives++;
    sfx(1568, 20);
  } else {
    sfx(1319, 4);
  }
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
void loadSave() {
  if (EEPROM.read(EEPROM_ADDR) == EEPROM_MAGIC) {
    EEPROM.get(EEPROM_ADDR + 1, hiScore);
    maxLevel = EEPROM.read(EEPROM_ADDR + 3);
    if (maxLevel >= NUM_LEVELS) maxLevel = 0;
  } else {
    hiScore = 0;
    maxLevel = 0;
  }
}

void writeSave() {                             // EEPROM.update skips unchanged bytes
  if (score > hiScore) hiScore = score;
  if (levelNum > maxLevel && levelNum < NUM_LEVELS) maxLevel = levelNum;
  EEPROM.update(EEPROM_ADDR, EEPROM_MAGIC);
  EEPROM.put(EEPROM_ADDR + 1, hiScore);
  EEPROM.update(EEPROM_ADDR + 3, maxLevel);
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
  if (px > (levelPx - 8) << 4) px = (levelPx - 8) << 4;
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

  // --- pickups and hazards
  for (int16_t ty = Y >> 3; ty <= (Y + h - 1) >> 3; ty++) {
    for (int16_t tx = (X + 1) >> 3; tx <= (X + 6) >> 3; tx++) {
      char c = tileAt(tx, ty);
      if (c == 'o') {
        setUsed(tx, ty);
        addCoin();
      } else if (c == 's' && Y + h - 1 >= ty * TILE + 3) {
        killPlayer();                          // spikes hurt even big Pip
        return;
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
  if (camX > levelPx - WIDTH) camX = levelPx - WIDTH;
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
    } else if ((arduboy.frameCount & 1) || (levelNum >= 48 && (i & 1))) {
      // walkers: half a pixel per frame (some are twice as fast later on)
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
    if (tx >= levelW) break;
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
  arduboy.print(F("L"));
  arduboy.print(levelNum + 1);
  arduboy.setCursor(26, 0);
  arduboy.print(F("x"));
  arduboy.print(lives);
  arduboy.setCursor(44, 0);
  arduboy.print(F("$"));
  printNum(coins, 2);
  if (power == SPARK) {
    Sprites::drawSelfMasked(64, 0, itemSprite, ITEM_FLOWER);
  } else if (power == WING) {
    Sprites::drawSelfMasked(64, 0, itemSprite, ITEM_FEATHER);
    arduboy.drawRect(74, 2, 20, 4, WHITE);     // flight meter
    arduboy.fillRect(75, 3, flyMeter * 18 / FLY_MAX, 2, WHITE);
  } else if (power == BIG) {
    Sprites::drawSelfMasked(64, 0, itemSprite, ITEM_BERRY);
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
  arduboy.setCursor(28, 20);
  arduboy.print(F("LEVEL "));
  if (selLevel > 0) arduboy.print('<');
  arduboy.print(selLevel + 1);
  if (selLevel < maxLevel) arduboy.print('>');
  arduboy.setCursor(0, 31);
  arduboy.print(F("HI "));
  arduboy.print(hiScore);
  arduboy.setCursor(80, 31);
  arduboy.print(arduboy.audio.enabled() ? F("B:SND ON") : F("B:SNDOFF"));
}

void drawIntro() {
  arduboy.setCursor(40, 18);
  arduboy.print(F("LEVEL "));
  arduboy.print(levelNum + 1);
  Sprites::drawSelfMasked(50, 34, heroSprite, 0);
  arduboy.setCursor(62, 34);
  arduboy.print(F("x "));
  arduboy.print(lives);
}

// ------------------------------------------------------------ main loop
void setup() {
  arduboy.begin();
  arduboy.setFrameRate(60);
  beep.begin();
  loadSave();
  selLevel = maxLevel;
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
      if (arduboy.justPressed(UP_BUTTON) && selLevel < maxLevel) selLevel++;
      if (arduboy.justPressed(DOWN_BUTTON) && selLevel > 0) selLevel--;
      if (arduboy.justPressed(A_BUTTON)) newGame(selLevel);
      break;

    case INTRO:
      drawIntro();
      if (--stateTimer == 0) loadLevel();
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
      // Pip hops up and falls off the screen
      if (stateTimer < 70) {
        py += vy;
        vy += 4;
      }
      drawWorld();
      if ((py >> 4) < HEIGHT) drawPlayer();
      drawHud();
      if (--stateTimer == 0) {
        power = SMALL;
        if (--lives == 0) {
          writeSave();
          state = GAMEOVER;
          stateTimer = 60;
        } else {
          startLevel();
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
          writeSave();
          state = WIN;
        } else {
          writeSave();
          selLevel = maxLevel;
          startLevel();
        }
      }
      break;

    case GAMEOVER:
      printCentered(F("GAME OVER"), 9, 6, 2);
      arduboy.setCursor(28, 28);
      arduboy.print(F("SCORE "));
      arduboy.print(score);
      arduboy.setCursor(4, 44);
      arduboy.print(F("A:CONTINUE  B:TITLE"));
      if (stateTimer) {
        stateTimer--;
      } else if (arduboy.justPressed(A_BUTTON)) {
        newGame(levelNum);                     // same level, fresh score and lives
      } else if (arduboy.justPressed(B_BUTTON)) {
        selLevel = maxLevel;
        state = TITLE;
      }
      break;

    case WIN:
      printCentered(F("YOU WIN!"), 8, 8, 2);
      printCentered(F("PIP IS HOME"), 11, 28, 1);
      arduboy.setCursor(28, 44);
      arduboy.print(F("SCORE "));
      arduboy.print(score);
      if (arduboy.justPressed(A_BUTTON)) {
        selLevel = maxLevel;
        state = TITLE;
      }
      break;
  }

  arduboy.display();
}
