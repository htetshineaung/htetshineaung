# Pip Quest (Arduboy)

An original side-scrolling platformer for the [Arduboy](https://arduboy.com).
Guide Pip through 2 levels: stomp blobs, bump `?` blocks for coins, smash
bricks, jump over pits and spikes, and touch the flag pole to win.

## Controls
| Button | Action |
|---|---|
| Left / Right | Move |
| A | Jump (hold A for a higher jump) |
| B (hold) | Run (a running jump goes further) |
| B on title screen | Sound on/off |

You get 3 lives and an extra life for every 50 coins. Stomping blobs, coins,
bricks and grabbing the flag high up all add to your score. Your high score
is saved.

## Install
**Arduino IDE**
1. Install the Arduino IDE.
2. Open *Library Manager* and install **Arduboy2**.
3. Pick the board **Arduino Leonardo** (or install the Arduboy board package).
4. Open `PipQuest/PipQuest.ino`, plug in the Arduboy and click **Upload**.

**arduino-cli**
```sh
arduino-cli lib install Arduboy2
arduino-cli compile --fqbn arduino:avr:leonardo PipQuest
arduino-cli upload  --fqbn arduino:avr:leonardo -p /dev/ttyACM0 PipQuest
```

## Make your own levels
The levels are text in `levels.h`, one character per 8x8 tile, 8 rows of 128:

`.` sky, `#` ground, `B` brick, `?` coin block, `P` pillar, `o` coin,
`s` spikes, `e` blob, `S` player start, `F` flag pole.

You can edit `levels.h` directly, or edit `tools/gen_assets.py`, which builds
the levels and the pixel-art sprites, and then run `python3 tools/gen_assets.py`.
