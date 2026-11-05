# Priorities, blending and the track API

## The enum

| Item | Value | Recommended for |
|---|---|---|
| `Idle` | 0 | breathing, stance |
| `Movement` | 1 | walk, run, swim, climb |
| `Action` | 2 | attacks, emotes that must override locomotion |
| `Action2` | 3 | rarer overrides |
| `Action3` | 4 | rarer still |
| `Action4` | 5 | highest developer priority |
| `Core` | **1000** | Roblox's own animations; **lowest** priority |

`Core` is 1000, not 6. If you author a clip at `Core` expecting it to win, it
will lose to everything.

## How the blend works

Tracks are evaluated per joint, high priority to low, until the total weight for
that joint reaches 1.0. Then evaluation stops for that joint — lower tracks are
not blended, they are **not evaluated at all**.

- Higher priority overrides lower priority **per joint**, not per clip. That is
  why an upper-body-only idle can coexist with a walk.
- Tracks at the **same** priority blend proportional to their weights, normalized
  if the sum exceeds 1.
- A track with weight 1.0 at `Action` completely hides `Movement` on every joint
  it poses, even if its pose is nearly identical.

## The masking trap

Roblox's default `Animate` script plays idle, walk, run, jump, fall and climb at
`Core`. An authored full-body idle at `Action` masks all of them on the joints it
poses. The character stands correctly, then **glides with frozen legs** when the
player walks — and only on the character you authored the idle for. It reads as a
missing walk animation.

Pick one and say which in the brief:

1. Author the idle at `Core`; the default walk still wins.
2. Pose only arms and torso, and let locomotion drive below the hips.
3. Author the locomotion set too (`Movement`), which is the only choice if the
   carry pose has to change how the character walks.

There is no static check for this. Playtest it: stand, walk, run, jump, land, and
watch the **legs**, per character.

## Playback

```lua
local animator = humanoid:FindFirstChildOfClass("Animator")
local track = animator:LoadAnimation(animation)
track:Play(0.1, 1, 1)          -- fadeTime, weight, speed
track:AdjustWeight(0.5, 0.2)   -- weight, fadeTime
track:AdjustSpeed(0.8)
track.TimePosition = 0.3
```

| Member | Meaning |
|---|---|
| `Length` | seconds; **0 until the asset loads** |
| `Speed` | playback multiplier |
| `WeightCurrent` / `WeightTarget` | current and target blend weight |
| `TimePosition` | playhead, seconds |
| `IsPlaying` | boolean |
| `Looped` | whether the asset loops |
| `Play(fade, weight, speed)` | start or resume |
| `Stop(fade)` | fade out and stop |
| `Pause()` / `Resume()` | hold and continue |
| `GetMarkerReachedSignal(name)` | fires when a keyframe marker passes |
| `DidLoop` | fires each loop |
| `Stopped` | fires when stopped or faded out |
| `Ended` | fires when a non-looping track reaches its end |

`LoadAnimation` requires an `Animator`; a Humanoid creates one, but a custom rig
may need `Instance.new("Animator")`.

## Fades

- 0.1–0.2 s for a combat transition; 0.05 s for a snap; 0.3 s for an emote.
- A fade is a blend, not a cut: both clips are evaluated during it, so a
  full-body clip fading in will briefly mask the walk at partial weight.
- `Stop(0)` is a hard cut and pops if the pose differs; use it only when the next
  clip starts on the same pose.

## Loops and seams

`KeyframeSequence.Loop` (spec `"loop": true`) makes the track repeat. The last
pose should equal the first, or the seam is a visible jump every cycle. The
linter measures the largest per-joint seam and fails above 15°.

A one-shot that returns to guard should also end on its first pose — not because
it loops, but because gameplay will blend back into idle and a mismatch pops.

## Markers

Markers are `KeyframeMarker` instances named on a `Keyframe`. They are the
correct way to sync a hitbox, a sound or a VFX to a frame:

```lua
local track = animator:LoadAnimation(anim)
track:GetMarkerReachedSignal("Contact"):Connect(function()
    hitbox:Hit()
end)
track:Play()
```

Author them at the contact frame, not "close enough"; the marker is the contract
between animation and gameplay. In the spec, `markers: [{name, t}]` documents the
beats and the linter checks the time is inside the clip.

## Server or client?

`Animator:LoadAnimation` on the client plays locally. For combat, the server
should own the decision and replicate the animation (a RemoteEvent or a
server-played track on the character), otherwise a client can play any animation
it likes and the hitbox follows the lie. Cosmetic emotes can be client-played.

## Which priority for what

| Clip | Priority |
|---|---|
| Breathing idle, stance | `Core` (or `Idle` if you own locomotion) |
| Walk, run, swim | `Movement` |
| Punch, kick, tool swing | `Action` |
| Block, reload, channel | `Action` / `Action2` |
| Emote, dance | `Action` (cancel on movement) |
| Hit react | `Action2` (must beat the attack) |
| Death | `Action3` (must beat everything) |
| Cutscene pose overlay | `Action4` |
