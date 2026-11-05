# Changelog

## 1.1.0

- **Optional Blender path.** `blender.py` finds Blender 3.6+, probes an armature
  and drafts a joint-to-bone mapping, then bakes the evaluated pose into the same
  spec. IK, constraints, drivers and NLA are read after evaluation, so no
  pre-bake is needed; the engine-native checks and exporter are unchanged.
- **Root channel.** A key may carry `"root": [x, y, z]` to translate the whole
  character, using the same ease. This is what makes jumps, crouches and full
  deaths possible; the Blender bake derives it from the `HumanoidRootPart` bone.
- Baked specs carry per-frame linear keys and the scene's fps.

## 1.0.0

First release, as a standalone one-folder skill.

- **Engine-native, no Blender.** Poses are authored in Roblox joint space and
  built into a real `KeyframeSequence`; nothing depends on a `.blend` rig, a
  `LOCAL.md` or a machine-specific path.
- **Two halves in one skill:** character animation and cutscene camera work.
- **Six scripts:** `animlib.py`, `anim.py` (lint/build), `fk.py` (contact, slip,
  stride), `preview.py` (contact sheet), `cutscene.py` (shot list + camera player),
  `verify.py` (gate table).
- **Seven references:** animation craft, pose recipes, rigs, priorities and
  blending, cutscene grammar, engine integration, QA.
- **Four examples:** a 0.5 s cross, a 0.8 s run cycle, a nominal R15 rig, and a
  five-shot intro with dialogue.
- **Engine corrections carried into the code:** `AnimationPriority.Core` is 1000
  (not 6); `Cubic` is deprecated with a direction bug, so the exporter uses
  `CubicV2` (5); `PoseEasingDirection.In` and `.Out` are backwards, so the spec's
  `in` (accelerate) is emitted as `Out`.
- **Measured example:** the cross travels 1.77 studs into contact with reach 1.40
  and zero planted-foot travel; the run has five ground contacts and 0.15 studs
  of stride.
- **Failure paths proven:** missing `t=0`, a 34° loop seam, a line-crossing shot
  list and an empty gate all exit non-zero.

Known gap: the emitted Luau and `.rbxmx` were not played or imported in Studio in
this build. The pipeline is verified up to the artifacts, not through the engine.
The Blender bridge was verified on 5.2 with a generated rig, not with a real
character mesh.
