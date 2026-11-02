# Pip Quest (Arduboy)

An original side-scrolling platformer for the [Arduboy](https://arduboy.com).
Guide Pip through **128 levels**: stomp enemies, kick shells, bump `?` blocks
for coins and power-ups, smash bricks, and touch the flag pole to win.

## Controls
| Button | Action |
|---|---|
| Left / Right | Move |
| A | Jump (tap for a small jump, hold for a high jump) |
| B | Run, plus your power-up's move (below) |
| Up / Down on title screen | Pick the starting level (up to the furthest you reached) |
| B on title screen | Sound on/off |

## Power-ups
Some `?` blocks hold a power-up instead of a coin.

| Power-up | What it does | B button |
|---|---|---|
| **Berry** | Pip grows big: survives one hit, breaks bricks | Run |
| **Spark Flower** (when big) | Shoot bouncing sparks that beat any enemy | Tap to shoot |
| **Feather** (when big) | Fly, with a flight meter on the score bar | Hold to fly, and hold A while falling to glide |

If you get hit while powered up, you shrink back to small Pip instead of
losing a life.

## Lives
You start with **5 lives** and get an extra life for every 100 coins. After a
**Game Over**, press A to continue from the same level (score and lives reset)
or B to go back to the title. The Arduboy saves the furthest level you reached
and your high score.

## Levels
The 128 levels are built from the level number, out of 8-column pieces in
`tools/gen_assets.py`. The themes rotate (Hills, Hills, Cave, Sky), and
harder pieces and tougher enemies appear as the level number goes up.

## Enemies
- **Blob**: stomp it.
- **Snail**: stomp it and it hides in its shell. Walk into the shell or stomp
  it to kick it. A sliding shell knocks out every enemy it hits, but watch out
  when it bounces back at you.
- **Spiky**: don't stomp it! Beat it with sparks or a shell.

## Install
**Arduino IDE**
1. Install the Arduino IDE.
2. Open *Library Manager* and install **Arduboy2**.
3. Pick the board **Arduino Leonardo** (or install the Arduboy board package).
4. Open `PipQuest/PipQuest.ino`, plug in the Arduboy and click **Upload**.

On an Apple-chip Mac, if you get `bad CPU type in executable`, install Rosetta 2
with `softwareupdate --install-rosetta --agree-to-license` and restart the IDE.

**arduino-cli**
```sh
arduino-cli lib install Arduboy2
arduino-cli compile --fqbn arduino:avr:leonardo PipQuest
arduino-cli upload  --fqbn arduino:avr:leonardo -p /dev/ttyACM0 PipQuest
```

## Make your own level pieces
Edit the `PIECES` list in `tools/gen_assets.py` (one character per 8x8 tile,
the legend is at the top of the list), then run `python3 tools/gen_assets.py`
to regenerate `levels.h` and `sprites.h`.
