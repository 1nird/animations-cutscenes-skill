# Animation craft, in Roblox numbers

Everything here is a starting number to adjust, not a law. The laws are the ones
that make a clip read: anticipation before the action, a fast contact, a settle,
and a silhouette that changes.

## Frame budget at 30 fps

| Beat | Frames | Time |
|---|---|---|
| Anticipation | 2–4 | 0.07–0.13 s |
| Contact / impact | 2–3 | 0.07–0.10 s |
| Follow-through | 3–5 | 0.10–0.17 s |
| Recovery | 4–8 | 0.13–0.27 s |

A 0.5 s cross is 15 frames, not 30. If a clip feels "slow", count keys, not
frames: extra keys that don't change the silhouette are what make a move feel
soft.

## Timing by action

| Action | Length | Notes |
|---|---|---|
| Jab | 0.25–0.35 s | lead arm, no hip commit |
| Cross | 0.4–0.55 s | rear hip and shoulder drive |
| Hook | 0.45–0.6 s | elbow stays ~90°, the arc is the attack |
| Uppercut | 0.45–0.6 s | dip, then drive up through the legs |
| Heavy / overhead | 0.6–0.9 s | long anticipation, late contact |
| Kick | 0.5–0.8 s | support ankle counter-rotates |
| Hit react | 0.2–0.35 s | one direction, no return to guard |
| Death | 0.8–1.2 s | collapse, then a settle |
| Emote / wave | 0.8–2.0 s | loopable if held |
| Walk cycle | 0.9–1.1 s | 2 contacts |
| Run cycle | 0.6–0.8 s | 2 contacts, airborne phase |

## The five poses

1. **Idle / guard** — the pose the clip starts and usually ends on. It must read
   as a stance, not a T-pose with bent elbows.
2. **Anticipation** — the opposite of the action. Pull back, coil, look. This is
   where most of the perceived power comes from; skip it and the strike is a
   gesture.
3. **Contact** — the extreme. Fastest segment in the clip. The silhouette should
   be unmistakable in one frame.
4. **Follow-through** — the body continues past the contact, then stops. The fist
   does not stop at the target; the shoulder and torso keep going.
5. **Recovery** — settle back to guard, usually slower than the strike.

Four poses (no separate follow-through) is a pose-to-pose cut and is fine for
stylised or R6 work. Six or more usually means the extra keys are compensating
for a weak contact pose.

## Easing per segment

Ease describes the *motion into the next key*:

- **Anticipation → contact: accelerate (`in`).** The strike must not decelerate
  into its own impact; that is the single most common reason a punch reads mushy.
- **Contact → follow-through: decelerate (`out`).** The body has spent its energy.
- **Recovery: `inout`.** Nothing dramatic should happen here.
- **Holds: `constant`.** Use it deliberately, for a snap or a hit-stop.

A global smoothstep on every key is not easing; it is a signature that says
"this was authored by a curve preset". Vary it.

## Spacing and arcs

- **Spacing** is the distance the end effector travels between keys. A cross
  travels 1.2–1.8 studs in ~0.12 s; a jab 0.9–1.2 in 0.08 s.
- **Arcs**: rotations slerp, so a hand travels an arc around the shoulder. Check
  the path on the sheet — a hand that goes *through* the torso is a pose problem,
  not an interpolation problem.
- **Overlap**: the head and any weapon lag the torso by 1–2 frames. Author it as
  a key offset, not as a separate system.
- **Follow-through on props**: the weapon's mass arrives last. Rotate the wrist
  and the prop tip 2–3 frames after the arm stops.

## Weight

Rigid Roblox parts have no squash and stretch, so weight has to come from three
places:

1. **Hip and shoulder rotation.** A punch with no hip is an arm wave. Rotate
   `LowerTorso` a few degrees and `UpperTorso` more; the shoulders carry it.
2. **Knee bend and a dip before the drive**, or a root dip of 0.1–0.25 studs. A
   0.05–0.1 stud dip reads as a load; the root channel makes it explicit.
3. **A settle after contact.** Two frames of overshoot, then a stop.

## Feet

The most common visible defect is a foot that slides or tilts.

- **Ankle counter-rotation:** `foot.X ≈ -(hip.X + knee.X)`, or the sole tilts with
  the leg and the character looks like it is standing on a slope.
- **Planted feet** in a non-locomotion clip should travel under 0.25 studs. Hip
  twist drags them; reduce the twist or counter-rotate the hip.
- **Locomotion** is different: an in-place run *should* slide the contact foot
  backward — that is stride. Set `"locomotion": true` so the gate doesn't flag it.
- **Ground contact** is not optional: the lowest sole should be within 0.06 studs
  of the floor in a grounded clip. The sheet draws a green dot on a planted foot;
  a clip with no green dots is floating.

## Exaggeration

Roblox reads at a distance and on blocky silhouettes. Push past human range:

- Torso twist: 20–35° for a committed strike, not 5°.
- Shoulder swing: 80–100° forward at contact.
- Lean: 8–15° for a drive; more reads as falling.
- Head: counter-rotate so the character keeps facing the target.

Then check the sheet. Exaggeration that breaks the silhouette is not
exaggeration; it is noise.

## Reading a contact sheet

- **Silhouette first.** Squint: can you tell what the action is from the shape?
- **Contact frame.** Does the extreme pose land on the beat you named? If the
  contact is at 0.14 s, frame 4 at 30 fps.
- **Feet.** Green dots on the floor, no foot below the line, no tilt.
- **Hands.** In front of the body, not inside it; the guard hand stays up.
- **Return.** The last frame should match the first in a one-shot that loops back
  to guard, or the seam is a pop when the clip is replayed.

Numbers can prove the pose matches the spec. Only the sheet can suggest the spec
is the wrong move.
