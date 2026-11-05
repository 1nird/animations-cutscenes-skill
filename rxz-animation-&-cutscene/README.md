# rxz · Roblox Animation + Cutscenes

One Claude Code skill, in one folder. It authors Roblox character animation and
cutscene camera work **as data**, verifies it with numbers and a contact sheet,
and plays it in Studio — with no Blender, no rig file, and no asset upload.

## Install

Copy the `roblox-animation` folder into the folder Claude Code reads:

| OS | Where |
|---|---|
| Windows | `C:\Users\<you>\.claude\skills` |
| macOS / Linux | `~/.claude/skills` |

The result must be `.claude/skills/roblox-animation/SKILL.md`. Restart Claude Code.

If the rxz Roblox Skills pack is installed, remove its `roblox-animation` folder
first — same name, different pipeline.

## What it does

A Roblox animation is a tree of per-joint rotations, not a video and not a Blender
action. So the skill writes a spec of poses over time, builds a real
`KeyframeSequence`, checks the feet and the timing with forward kinematics, renders
a contact sheet, and only then plays it.

**Animation half**

- Five-pose actions: guard, anticipation, contact, follow-through, recovery.
- 30 fps, 0.3–0.7 s combat, 5-stud proportions, exaggerated silhouettes.
- Degree tables for cross, jab, hook, roundhouse, hit react, death, walk, run,
  idle and emotes, plus prop-carry rules.
- The traps that actually break clips: torso twist direction, compounding joints,
  ankle counter-rotation, `Core` priority masking the walk, `CubicV2` vs `Cubic`,
  the backwards `In`/`Out` easing enums, and root translation for jumps, crouches
  and deaths.

**Cutscene half**

- Shot lists with lens, height, movement and dialogue.
- The 180° line, the 30° rule, jump cuts, eyeline, pacing and coverage.
- A camera player: `RenderStepped`, per-shot easing, FOV, letterbox, subtitles,
  skip on Space/A, and a clean restore of camera type, CFrame and FOV.
- Mobile-safe framing, because FOV is vertical.

## Quick start

```bash
py scripts/anim.py lint examples/punch.json
py scripts/anim.py build examples/punch.json --out out
py scripts/fk.py examples/punch.json --out out/fk.report.json
py scripts/preview.py examples/punch.json --out out/sheet.png
py scripts/cutscene.py examples/cutscene.json --out out
py scripts/verify.py --dir out
```

`verify.py` prints a gate table and exits non-zero on any red gate.

## Requirements

- **Python 3.11+** and **Pillow** — the only third-party dependency, used for the
  contact sheet. Every other script is stdlib.
- **Roblox Studio** for playback, the marker check and publishing.
- No Blender, no local rig, no config file, no API key.

## The scripts

| Script | Job |
|---|---|
| `animlib.py` | shared core: enums, rigs, easing, quaternions, validation |
| `anim.py` | lint a spec; build `.rbxmx` + Luau builder + report |
| `fk.py` | forward kinematics: sole contact, slip, stride, root height |
| `preview.py` | contact sheet, side and front, Pillow only |
| `cutscene.py` | validate a shot list; emit `CutsceneData` + `CutscenePlayer` |
| `verify.py` | the gate table |

## What was checked in this build

- `anim.py lint` and `build` on the shipped punch and run: 6 keys × 16 joints =
  96 poses, priority 2, loop flags correct, XML parses.
- The cross: hand travels 1.77 studs from wind-up to contact, reach 1.40; soles
  stay within 0.01–0.04 studs and planted feet move 0.00.
- The run: lowest sole 0.00, five ground contacts, 0.15 studs of stride.
- Deliberate failures all exit 1: a key not at `t=0`, a 34° loop seam, a camera
  that crosses the 180° line, and an empty gate (10/10 red).
- `verify.py` passes all ten gates on the example project.
- The root channel is exercised separately: a 0.2-stud drop moves both soles by
  0.2 and trips the floor gate, which is the correct failure.

**Not checked:** the emitted Luau has not been played in Studio from this machine,
and no `.rbxmx` has been imported into the Animation Editor here. Those are the
last mile, and the skill says so rather than pretending otherwise.

## Licence

Free to use and change, including in commercial Roblox games. Not for resale.
Full text in `LICENSE.txt`.
