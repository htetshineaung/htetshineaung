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
Each of the 128 levels is built from its level number, so it is the same every
time you play it, but no two levels are alike. A level is a row of sections,
each one a feature with its own random size: gaps, single or double pipes,
hills, staircases (some with a pit at the top), block rows with coins and
power-ups, spike pits with brick bridges, enemy squads, brick walls and
floating platforms. The same feature never shows up more than twice in a row.

Themes rotate: Hills, Spike Hills, Cave (with a brick ceiling) and Sky (lots
of floating platforms). As the level number goes up, levels get longer
(112 to 200 tiles) and gaps get wider, with taller pipes and stairs, more
spikes and bigger enemy squads. Snails and spikies gradually replace blobs,
and from level 49 some enemies walk twice as fast.

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

## Change the levels
The level builder is `buildLevel()` and `rawTile()` in `PipQuest.ino`. The
`featureWeight` table there sets how often each feature appears in each theme.
The pixel art lives in `tools/gen_assets.py`; run `python3 tools/gen_assets.py`
after editing it to regenerate `sprites.h`.
