---
name: roblox-animation
description: Author Roblox character animation and cutscenes as data, then verify them before shipping. Use when the user wants to animate a Roblox character (attack, punch, kick, emote, idle, walk or run cycle, hit react, death, tool action), build a cutscene or cinematic (intro, boss reveal, dialogue, camera move, trailer beat), fix an animation that pops, clips, floats, slides, or loses to the default walk, or get an animation into Studio with no asset upload; Blender is optional for IK-driven, custom-rig or mocap work.
---

# Roblox animation and cutscenes, as data

> **Nothing to set up.** Python 3.11+ with Pillow renders the contact sheet; every
> other script is stdlib. Roblox Studio — with its MCP connected if an agent is
> building in place — for the last mile. Blender is optional (IK, custom rigs,
> props); the core path needs no `.blend`, no rig file, no upload, no account, no key.

A Roblox animation is not a video and not a Blender action. It is **a tree of
per-joint rotations**, sampled by the Animator every frame. So author it as data:
poses over time, built into a real `KeyframeSequence`, checked with forward
kinematics and a contact sheet, then played from Studio.

**The rule: measure it, then look at it.** Every pose claim is a number (degrees,
studs, degrees per second) and every clip gets a contact sheet before it is called
done. A clip can pass every number and still read wrong — that means the spec was
wrong, and the sheet is how you find out.

## Three commands

```bash
py scripts/anim.py lint examples/punch.json          # errors, seam, snap speeds
py scripts/anim.py build examples/punch.json --out out
py scripts/fk.py examples/punch.json --out out/fk.report.json
py scripts/preview.py examples/punch.json --out out/sheet.png
py scripts/cutscene.py examples/cutscene.json --out out
py scripts/verify.py --dir out                        # the gate table
```

`build` writes `<Name>.rbxmx` (Animation Editor), `<Name>.luau` (no-upload
builder) and `anim.report.json`. `cutscene.py` writes `CutsceneData.luau` and
`CutscenePlayer.luau`. `verify.py` refuses to pass if any gate is red.

## The model

- **16 R15 joints, one pose each, every key.** A partial pose tree is the import
  bug that looks like a broken rig.
- **30 fps.** Combat 0.3–0.7 s. An emote 0.8–2 s. Death 0.8–1.2 s.
- **Five poses per action:** idle, anticipation, contact, follow-through,
  recovery. Four is a pose-to-pose cut; six is usually mush.
- **Angles in degrees**, in the joint's rest frame: `+X` swings a hanging limb
  forward, `+Z` swings it toward `+X`, `+Y` twists. Both arms hang down, so the
  same `+Z` is outward on one side and inward on the other. **Never mirror by
  copying a sign.**
- **Twist direction matters.** `+Y` sends the LEFT shoulder forward and the RIGHT
  shoulder back. A right cross therefore drives with **negative Y**; getting this
  backwards extends the arm while the torso rotates away, and the punch dies.
  (This exact bug shipped in the first draft of `examples/punch.json`; the sheet
  caught it, the numbers did not.)

## Phases, and what ends each one

| # | Phase | Exit gate |
|---|---|---|
| 0 | Brief | One sentence of intent, action class, camera side. "Right cross, 0.5 s, seen from the character's left" |
| 1 | Rig audit | Rig known; a 10° test on one joint moves the expected part; priority chosen |
| 2 | Block | Five poses on the timeline, stepped, feet on the ground |
| 3 | Spline | Ease per segment; contact is the fastest segment, not a smoothstop |
| 4 | Polish | Overlap, arcs, exaggeration, ankle counter-rotation |
| 5 | Bind | `Length` equals duration; plays on a character; legs still walk |
| 6 | Cutscene | Shot list passes 180°/30°; camera has no dead frames |
| 7 | Prove | `fk` clean, sheet looked at, `verify.py` all green |

Do not skip 2 and 3 to get to pretty. Blocked poses that read at 8 fps will read
at 30; pretty curves over a wrong pose never will.

## The spec

```json
{
  "name": "CrossPunch", "rig": "R15", "fps": 30, "duration": 0.5,
  "loop": false, "priority": "Action", "grounded": true, "locomotion": false,
  "keys": [
    {"t": 0.0, "ease": "linear", "pose": {"UpperTorso": [-5, 10, 0], "RightUpperArm": [24, 0, -14]}},
    {"t": 0.14, "ease": "in", "pose": {"UpperTorso": [-10, -14, 0], "RightUpperArm": [86, 0, 6]}}
  ]
}
```

- `ease` is the **intent**: `in` accelerates, `out` decelerates, `inout` both.
  The exporter maps it to the engine's enums, which are backwards (see below).
- `"root": [x, y, z]` on a key translates the whole character, lerped with the
  same ease. Use it for jumps, crouches and deaths; 1–2 studs is a lot.
- `locomotion: true` tells `fk.py` that planted-foot travel is stride, not slip.
- `grounded: false` skips the "something must touch the floor" gate.

## Getting it into Studio — no upload

1. `anim.py build` → `<Name>.luau`.
2. Paste it into a Script or ModuleScript; it returns a `KeyframeSequence`.
3. Register it: `KeyframeSequenceProvider:RegisterKeyframeSequence(sequence)`
   returns a ContentId. Assign that **bare** string to `Animation.AnimationId` —
   `hash://` and `rbxasset://` both fail.
4. `Animator:LoadAnimation(anim):Play()`. Those ids are **session-local**: perfect
   for testing, not for publishing. Publishing needs a real uploaded asset id.

The `.rbxmx` is for the Animation Editor: insert it into the rig's `AnimSaves`
folder, where the editor lists saved clips, and save to Roblox from there.

**Verify before believing:** `AnimationTrack.Length` reads **0 until the asset
loads**; wait for it and compare against the spec duration. In edit mode,
`Animator:StepAnimations(0)` with `AdjustSpeed(0)` and a `TimePosition` poses the
rig — writing `Part.Transform` by hand does not.

## Optional: Blender

The data path above needs nothing. When the motion needs a solver, a real mesh or
a rig the spec cannot describe, author in Blender and bake the evaluated pose back
into the same spec:

```bash
py scripts/blender.py check                            # finds 3.6+, or exits 2
py scripts/blender.py probe rig.blend --out rig-info.json
py scripts/blender.py bake rig.blend mapping.json --out clip.json
```

The bake reads `pose_bone.matrix`, so IK, constraints, drivers and NLA are already
solved; no pre-bake is needed. It writes ordinary spec JSON, so `lint`, `fk`,
`preview`, `build` and `verify` still apply. Map one deform bone per Roblox joint
and map every parent in the chain. Read `references/blender.md` before the first
bake.

## Priorities — and the masking trap

| Priority | Value | Use |
|---|---|---|
| `Idle` | 0 | breathing, stance |
| `Movement` | 1 | walk, run, swim, climb |
| `Action` | 2 | attacks, emotes that override locomotion |
| `Action2`–`Action4` | 3–5 | rarer overrides |
| `Core` | **1000** | Roblox's default animations; lowest priority |

Higher priority wins **per joint**, and once the weight sum reaches 1.0 for a
joint, lower tracks stop being evaluated for it. Roblox's own `Animate` script
plays at `Core`. So a full-body idle authored at `Action` masks the default walk
on every joint it poses: the character glides with still legs, and it looks like
the walk cycle vanished. Either author the idle at `Core`, pose only the upper
body, or author the locomotion set too.

## Easing: two engine traps

- **`Cubic` is deprecated** with a direction-reversal bug between editor and
  runtime. New work uses **`CubicV2` (5)**. All scripts here do.
- **`PoseEasingDirection.In` and `.Out` are backwards** — for legacy reasons
  `Out` accelerates and `In` decelerates. The spec's `in` maps to `Out`; the
  exporter does it, so never hand-write the enum from the spec word.

## Cutscenes

A cutscene is a shot list, a camera rule set, and one player script.

```json
{"id": "s2", "kind": "cut", "dur": 2.2, "scene": "gate", "subject": "Kade",
 "line": [[-6, 0, 0], [6, 0, 0]],
 "from": {"pos": [2.4, 1.6, 4.2], "look": [0, 1.5, 0], "fov": 30},
 "dialogue": {"speaker": "Kade", "text": "They said the gate was sealed."}}
```

The validator enforces what a cut gets wrong: both cameras in a dialogue scene
stay on **one side of the 180° line**; consecutive shots of the same subject
differ by **30° or a lens change**, or they read as a jump cut; look targets can't
sit on the camera; FOV stays in 20–90; subtitle text stays under 22 characters a
second. `cutscene.py` then emits `CutscenePlayer.luau`, which owns the camera
only while playing, drives it with `RenderStepped`, lerps position and look, eases
per shot, animates FOV, draws letterbox and subtitles, skips on Space/A, and
restores camera type, CFrame and FOV afterwards.

**Every shot moves.** In the working shot language this skill encodes, a frame is
never static: a push-in or a drift, an entrance, and a foreground detail. A
"cut" may be still in position but should carry a slow push or a FOV drift; if it
carries neither, it is a slide, and the audience feels it.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Limbs pop between frames | Euler interpolation, or the pose tree assembled wrong | slerp per joint (this pipeline does); one full pose tree per key |
| Punch extends but reads flat | torso twists away from the strike | flip the sign: right shoulder forward is `-Y` |
| Character glides, legs frozen | authored idle at `Action` masks `Core` walk | author idle at `Core`, or upper body only |
| T-pose in game | asset not loaded, or no `Animator` | wait on `Length`, use `Humanoid:FindFirstChildOfClass("Animator")` |
| Feet slide | hip twist drags planted legs; no ankle counter | `foot.X ≈ -(hip.X + knee.X)`, reduce hip twist |
| Hands float off a prop | prop not welded at the grip point | weld to the hand, author the grip as a pose offset |
| Animation plays once and stops mid-air | `Loop` false on a locomotion clip | `loop: true` for cycles |
| Camera cuts through a wall | no occlusion test | raycast from subject to camera, or keep moves inside the room |

## Anti-patterns

- Animating at 60 fps because it feels smoother. The engine samples at 30 and the
  editor is 30; extra keys are noise.
- Copying real-life timing. A real cross is ~0.35 s of travel with a slow start;
  Roblox needs the contact inside 0.15 s.
- A pose per frame. Keys earn their place by changing the silhouette.
- Judging on one view. A right-arm action is invisible from the left.
- Calling it done because `build` exited 0. That only proves the XML is well
  formed.

## Cheat sheet

| Thing | Number |
|---|---|
| Character height | 5 studs (1 PH = 5) |
| Arm reach (R15) | ~1.4 studs from shoulder |
| Combat length | 0.3–0.7 s |
| Contact window | 0.06–0.12 s |
| Cross hand travel | ~1.2–1.8 studs |
| Lowest sole | ≥ −0.06, ideally 0.00 |
| Planted-foot travel | ≤ 0.25 studs (non-locomotion) |
| Loop seam | ≤ 15° per joint |
| Snap speed | warning above 2000 °/s |
| Camera FOV | 1–120, default 70, **vertical** |
| Default walk | 16 studs/s; jump apex 6.37 studs |
| Root channel | rigid translation; warn above 5 studs |

## References

- `references/animation.md` — timing, spacing, arcs, overlap, weight, exaggeration.
- `references/poses.md` — degree tables for guard, strikes, kicks, cycles, emotes.
- `references/rigs.md` — R15 tree, Pose names, Motor6D vs AnimationConstraint, R6, custom rigs.
- `references/priorities.md` — blending math, masking, fades, markers, track API.
- `references/cutscenes.md` — shot grammar, camera rules, audio, subtitles, mobile.
- `references/engine.md` — KeyframeSequence, registration, upload, easing enums.
- `references/blender.md` — the optional path: probe, mapping, bake, IK and the traps.
- `references/qa.md` — the gate table, the sheet method, failure diagnosis.
