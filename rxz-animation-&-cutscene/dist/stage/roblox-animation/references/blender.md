# Optional: author in Blender

The engine-native spec is the default: it needs no Blender, no rig file and no
install, and every gate still applies. Blender is for the jobs the spec cannot
do well:

- **IK feet.** Plant a foot with an IK target, let the knees solve, bake the
  result. The contact check then proves it.
- **Custom rigs and props.** A rig with extra bones (coat, tail, weapon) bakes
  to the same 16 joints; anything beyond those joints is not shipped.
- **Long, layered motion.** Constraints, drivers, NLA and curve editing, then
  one bake.
- **Retargeting.** Constrain a humanoid rig to Mixamo or mocap, bake to the
  deform bones, and the result is an ordinary spec.
- **Mesh previews.** Judge a silhouette on the real character, not the stick
  figure, before committing to the clip.

Blender is *not* faster for a five-pose punch. Use it when the motion needs a
solver or a real mesh.

## Requirements

Blender 3.6 or newer, tested on 5.2 LTS. The host finds it through `$BLENDER`,
`PATH`, or the default install folder; override with `--blender`.

```bash
py scripts/blender.py check
```

Exit 2 with instructions means Blender was not found. Nothing else in the skill
needs it.

## Workflow

```bash
# 1. what is in this .blend? writes bones + a draft mapping
py scripts/blender.py probe rig.blend --out rig-info.json

# 2. copy the draft out, fix the names, save it
#    (the draft is at .armatures[0].mapping in rig-info.json)

# 3. animate, then bake the evaluated result
py scripts/blender.py bake rig.blend mapping.json --out clip.json --name Cross

# 4. the engine-native checks take over
py scripts/anim.py lint clip.json
py scripts/anim.py build clip.json --out out
py scripts/fk.py clip.json --out out/fk.report.json
py scripts/preview.py clip.json --out out/sheet.png
py scripts/verify.py --dir out
```

The bake reads `pose_bone.matrix` at every frame, so **constraints, IK, drivers
and NLA are already applied**. You do not need to bake the action to FK first.

## The mapping

```json
{
  "rig": "r15",
  "armature": "Armature",
  "studs_per_unit": 1.0,
  "priority": "Action",
  "bones": {
    "HumanoidRootPart": "HumanoidRootPart",
    "LowerTorso": "LowerTorso",
    "UpperTorso": "UpperTorso",
    "Head": "Head",
    "RightUpperArm": "RightUpperArm",
    "RightLowerArm": "RightLowerArm",
    "RightHand": "RightHand"
  },
  "axis": { "RightUpperArm": [-1, -1, 1] }
}
```

- **One bone per Roblox joint.** Every mapped bone's parent must also be mapped
  (the bake refuses otherwise), so the hierarchy it reads is the hierarchy
  Roblox will pose.
- **Deform bones, not controls.** IK controls usually sit outside the chain;
  the deform bones are the ones that carry the pose.
- **`axis`** is the frame change between the bone's local axes and the Roblox
  joint's. Limbs default to `[-1, -1, 1]` and bodies to `[1, 1, 1]`, which is
  correct for a rig built like the R15 one: limb bones pointing down, torso and
  head up. Check one 30° pose on the contact sheet; if a limb leans the wrong
  way, flip its entry.
- **`studs_per_unit`** scales root translation only. Rotations are scale-free.
  A rig authored in studs uses 1.0.
- **Root motion** comes from the bone mapped to `HumanoidRootPart`: its head
  offset, converted from Blender's Z-up frame to Roblox's Y-up frame. The clip
  root is in studs.

## Traps this path was built around

- **The empty Action.** Blender's animation editor can create a *new* action
  while the old one stays on the armature; every frame then bakes identical.
  The baker prints a warning when all frames match. Key into the action that is
  assigned to the armature.
- **Scene fps.** The bake uses the scene's fps. Set it to 30 to match Roblox
  playback; a 24 fps clip still plays, but every engine-side timing number moves.
- **Gimbal lock.** Euler extraction warns above 85° on Y. Fix the pose or add a
  key to carry it through cleanly; check the sheet.
- **Armature object transform.** Rotations are read in armature space, root
  translation in world space. Do not animate the armature object itself: the
  root channel only sees the bone.
- **Scale and shape keys.** Neither is a joint rotation. Non-uniform object
  scale breaks the rest frames; apply scale before baking.
- **Props and extra bones** do not survive: the spec is 16 humanoid joints.
  Animate a prop as a separate model, or attach it in Studio.

## What Blender buys, honestly

An IK-planted foot still has to pass `fk.py`; a beautiful curve still has to
pass the seam and speed gates. Blender changes how the pose is authored, not
what counts as a finished clip. The bake is the handoff, and the engine-native
checks remain the judge.
