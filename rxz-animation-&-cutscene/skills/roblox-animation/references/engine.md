# KeyframeSequence, registration, upload

## What an animation asset is

A `KeyframeSequence` holds `Keyframe`s, each with a `Time` and a `Pose` per
joint. A `Pose` is a `CFrame` relative to the joint's rest transform, plus an
easing style, direction and weight.

```
KeyframeSequence
  Loop        bool
  Priority    Enum.AnimationPriority
  Keyframe
    Time      float (seconds)
    Pose      (one per joint, named after the child part)
      CFrame
      EasingStyle / EasingDirection / Weight
```

The scripts write **every joint on every key**, including identity poses. A
partial tree imports and then plays wrong; the missing joints are not simply "at
rest", because the sequence replaces the whole pose.

## The .rbxmx

`anim.py build` writes a standard Roblox XML model:

```xml
<roblox version="4">
  <Item class="KeyframeSequence" referent="RBX0">
    <Properties>
      <string name="Name">CrossPunch</string>
      <bool name="Loop">false</bool>
      <token name="Priority">2</token>
    </Properties>
    <Item class="Keyframe" referent="RBX1">
      <Properties><float name="Time">0.14</float></Properties>
      <Item class="Pose" referent="RBX2">
        <Properties>
          <string name="Name">UpperTorso</string>
          <CoordinateFrame name="CFrame">...</CoordinateFrame>
          <token name="EasingStyle">5</token>
          <token name="EasingDirection">1</token>
          <float name="Weight">1</float>
        </Properties>
      </Item>
    </Item>
  </Item>
</roblox>
```

Insert it into the rig's `AnimSaves` folder where the Animation Editor lists saved
clips, or drag it into the viewport to inspect it. Save to Roblox from the editor
to get a real asset id.

## Easing enums, exactly

`PoseEasingStyle`:

| Item | Value |
|---|---|
| `Linear` | 0 |
| `Constant` | 1 |
| `Elastic` | 2 |
| `Cubic` | 3 — **deprecated**, direction-reversal bug |
| `Bounce` | 4 |
| `CubicV2` | 5 — use this |

`PoseEasingDirection`: `In` 0, `Out` 1, `InOut` 2.

**`In` and `Out` are backwards.** Roblox's own docs: for legacy compatibility,
their use is reversed from every other tool and from `TweenService`. `Out`
accelerates; `In` decelerates. The spec's `"ease": "in"` (accelerate) is emitted
as `CubicV2` + `Out` for exactly this reason.

`AnimationPriority`: `Idle` 0, `Movement` 1, `Action` 2, `Action2` 3, `Action3` 4,
`Action4` 5, `Core` 1000.

## Register instead of upload

For testing and iteration, no asset upload is needed:

```lua
local KeyframeSequenceProvider = game:GetService("KeyframeSequenceProvider")
local sequence = require(script.Parent.CrossPunch)   -- the generated builder
local id = KeyframeSequenceProvider:RegisterKeyframeSequence(sequence)

local anim = Instance.new("Animation")
anim.AnimationId = id        -- the BARE string; hash:// and rbxasset:// fail
local track = humanoid:FindFirstChildOfClass("Animator"):LoadAnimation(anim)
track:Play()
```

- Register on the client (it needs only the Animation capability) or the server;
  the id is **session-local**.
- `Length` reads 0 until the asset loads. Wait for it, then compare with the
  authored duration; anything else is a failure, not a rounding issue.
- The sequence must stay alive (parented) for the track to resolve.

## Verifying a pose in Studio without playing

In edit mode, the Animator can pose a rig:

```lua
local track = animator:LoadAnimation(anim)
track:Play()
track:AdjustSpeed(0)
track.TimePosition = t
animator:StepAnimations(0)
```

Writing `Part.Transform` by hand does **nothing** in edit mode — `Transform` is
the animation channel and only the Animator applies it. Use `StepAnimations`.

To compare against the preview, compute world CFrames through the joint chain:
`world[child] = world[parent] * C0 * pose.CFrame * C1:Inverse()`.

## Upload

Publishing needs a real asset id. The supported route is the Open Cloud Assets
API: create an `Animation` asset from a model containing the `KeyframeSequence`,
poll the operation, then store the returned id. Uploads are moderated and take
time; keep a table of clip name → id in the place, and set
`Animation.AnimationId = "rbxassetid://<id>"`.

Do not upload on every iteration. Register locally while authoring; upload the
clips that survived the gate.

## Markers

`KeyframeMarker` children of a `Keyframe` become `AnimationTrack` signals:

```lua
track:GetMarkerReachedSignal("Contact"):Connect(function() ... end)
```

Markers are how gameplay agrees with the animation on when a hitbox opens. Put
them on the contact frame, and test that they fire on the frame you authored —
`GetTimeOfKeyframe(name)` returns the time if you need to compare.

## Common engine errors

| Error / symptom | Cause |
|---|---|
| `AnimationId is not a valid member` / nothing plays | id prefixed with `hash://` or `rbxasset://` |
| Track length is 0 | asset still loading, or the sequence was garbage-collected |
| Character T-poses | no `Animator`, or `LoadAnimation` called on the Humanoid instead |
| Poses snap instead of blending | easing on the wrong keyframe, or `Stop(0)` |
| The clip plays at the wrong speed | `Play` speed argument, or `AdjustSpeed` left at 0 |
| Limbs in the wrong place after import | partial pose tree, or joint names from R6 used on R15 |
| Animation works in Studio, not live | asset not published, or id is session-local |
