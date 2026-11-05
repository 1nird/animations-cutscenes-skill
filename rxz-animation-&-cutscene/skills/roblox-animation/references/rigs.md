# Rigs and pose names

## R15: the tree the spec addresses

A `Pose` is named after the **child part** of a joint, not the Motor6D. The tree
is rooted at `HumanoidRootPart`.

| Pose name | Parent | Motor6D |
|---|---|---|
| `HumanoidRootPart` | — | `Root` (root → LowerTorso) |
| `LowerTorso` | `HumanoidRootPart` | `Root` |
| `UpperTorso` | `LowerTorso` | `Waist` |
| `Head` | `UpperTorso` | `Neck` |
| `LeftUpperArm` | `UpperTorso` | `LeftShoulder` |
| `LeftLowerArm` | `LeftUpperArm` | `LeftElbow` |
| `LeftHand` | `LeftLowerArm` | `LeftWrist` |
| `RightUpperArm` | `UpperTorso` | `RightShoulder` |
| `RightLowerArm` | `RightUpperArm` | `RightElbow` |
| `RightHand` | `RightLowerArm` | `RightWrist` |
| `LeftUpperLeg` | `LowerTorso` | `LeftHip` |
| `LeftLowerLeg` | `LeftUpperLeg` | `LeftKnee` |
| `LeftFoot` | `LeftLowerLeg` | `LeftAnkle` |
| `RightUpperLeg` | `LowerTorso` | `RightHip` |
| `RightLowerLeg` | `RightUpperLeg` | `RightKnee` |
| `RightFoot` | `RightLowerLeg` | `RightAnkle` |

Missing joints are identity, but **write every joint on every key**. A partial
pose tree is what produces the "my rig exploded" import bug.

## Axes

In the joint's rest frame:

- `+X` swings a hanging limb **forward** (`-Z` world). On the torso, `+X` leans
  **back**, because the torso points up.
- `+Z` swings a hanging limb toward `+X`. On the torso, `+Z` leans sideways.
- `+Y` twists. On the torso, `+Y` sends the **left** shoulder forward and the
  right shoulder back.

Because both arms hang down, `+Z` is outward on one side and inward on the other.
A pose authored by copying the right arm's numbers onto the left will splay the
left arm out. Solve each side.

**Verify the map on an unfamiliar rig:** build a clip with a single joint at
`[10, 0, 0]`, step it in Studio, and watch which way the part goes. Ten seconds
beats an hour of debugging a mirrored export.

## Motor6D, or AnimationConstraint

Modern Avatar Evolution dummies carry **no Motor6D** — instead 15
`AnimationConstraint`s plus `BallSocketConstraint`s. That is not a broken rig.
The Animator binds poses **by part name**, so a `KeyframeSequence` authored
against the table above plays unchanged.

To find the joints on such a rig, use `Attachment1.Parent.Name`; the constraint's
rest transform is `Attachment0.CFrame * Attachment1.CFrame:Inverse()`.

## R6

Six joints, all rigid:

| Pose | Parent | Joint |
|---|---|---|
| `Torso` | `HumanoidRootPart` | `Root` |
| `Head` | `Torso` | `Neck` |
| `Left Arm` | `Torso` | `Left Shoulder` |
| `Right Arm` | `Torso` | `Right Shoulder` |
| `Left Leg` | `Torso` | `Left Hip` |
| `Right Leg` | `Torso` | `Right Hip` |

R6 has no elbows or knees. A folded guard is not a pose it can hold; asking for
one raises the whole arm. Use R6 only when the game requires it, and expect the
stiff pose-to-pose look — that is R6's native style, not a defect.

The scripts support `"rig": "R6"`; the built-in skeleton is nominal.

## Custom rigs

`--rig rig.json` replaces the built-in skeleton for validation, FK and preview.
Dump it from the place rather than guessing proportions:

```lua
-- execute_luau, edit mode. Select the rig first.
local model = game:GetService("Selection"):Get()[1]
local out = { name = model.Name, joints = {} }
for _, j in ipairs(model:GetDescendants()) do
    if j:IsA("Motor6D") and j.Part1 then
        local offset = (j.C0 * j.C1:Inverse()).Position
        out.joints[j.Part1.Name] = {
            parent = j.Part0.Name,
            offset = { offset.X, offset.Y, offset.Z },
        }
    elseif j:IsA("AnimationConstraint") and j.Attachment1 then
        local offset = (j.Attachment0.CFrame * j.Attachment1.CFrame:Inverse()).Position
        out.joints[j.Attachment1.Parent.Name] = {
            parent = j.Attachment0.Parent.Name,
            offset = { offset.X, offset.Y, offset.Z },
        }
    end
end
print(game:GetService("HttpService"):JSONEncode(out))
```

`examples/rig-r15.json` is the nominal R15 shape, 5 studs tall, feet at y=0.
Scale every offset by `height / 5` for a taller or shorter character; joint
angles do not scale, which is why poses transfer and positions do not.

## Facing and handedness

A rig's local axes are fixed by its rest orientation, not by its name. Check the
rig you have:

1. Put the dummy at the origin facing `-Z`.
2. Author `RightUpperArm [0, 0, 20]` and step it.
3. If the arm goes toward `+X`, `+Z` is that character's right; if it goes
   toward `-X`, it is the left.

The examples here assume `+X` is the side the `Left*` parts sit on and that `+Z`
moves a limb toward `+X`. If your rig mirrors that, the numbers still work — the
*sides* swap, and a right cross becomes a left cross. That is a spec change, not
an export bug.

## Proportions

R15 is ~5 studs tall with a 1.4-stud arm reach and a 1.8-stud leg. A human is
~7.5 heads tall and a real arm hangs near the knee; R15's arm ends near the hip.
That is why copying human joint angles produces a shorter, stockier action — the
angles are right, the reach is not. Judge the reach against the intent, not
against the reference's silhouette.
