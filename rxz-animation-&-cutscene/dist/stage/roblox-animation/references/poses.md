# Pose recipes

Degrees in the joint's rest frame. `+X` swings a hanging limb forward, `+Z` toward
`+X`, `+Y` twists. These are starting points: render, look, adjust. They are
consistent with each other, so a guard from here and a contact from here will
blend without a re-author.

Format: `Joint [x, y, z]`.

## Stance and guard (orthodox, left lead)

```
LowerTorso  [0, 6, 0]      UpperTorso [-5, 10, 0]     Head [3, -14, 0]
LUpperArm   [20, 0, 16]    LLowerArm  [98, 0, 0]      LHand [0, 0, 0]
RUpperArm   [24, 0, -14]   RLowerArm  [102, 0, 0]     RHand [0, 0, 0]
LUpperLeg   [14, 0, 0]     LLowerLeg  [-12, 0, 0]     LFoot [-2, 0, 0]
RUpperLeg   [-8, 0, 0]     RLowerLeg  [6, 0, 0]       RFoot [2, 0, 0]
```

The lead (left) shoulder is forward because `+Y` sends the left shoulder forward.
Hands sit near the chin, elbows down — an upper arm at 20–25° is a guard; 45° is
already half a punch.

## Cross (rear hand)

| Pose | UpperTorso | RUpperArm | RLowerArm | Notes |
|---|---|---|---|---|
| Guard | `[-5, 10, 0]` | `[24, 0, -14]` | `[102, 0, 0]` | hand by the chin |
| Anticipation | `[-2, 20, 0]` | `[-8, 0, -24]` | `[112, 0, 0]` | torso winds **+Y**, fist by the ear |
| Contact | `[-10, -14, 0]` | `[86, 0, 6]` | `[6, 0, 0]` | torso unwinds to **−Y** |
| Follow | `[-12, -20, 0]` | `[92, 0, -2]` | `[10, 0, 0]` | shoulder past the fist |
| Recovery | `[-8, -6, 0]` | `[50, 0, -8]` | `[66, 0, 0]` | back to guard |

Head counter-rotates to keep the face on target: guard `[3, -14, 0]`, contact
`[4, 18, 0]`. Feet stay planted; the rear heel can lift 2–3° at contact.

## Jab (lead hand)

0.3 s. No hip commit, so the torso barely changes.

```
Guard       LUpperArm [20, 0, 16]   LLowerArm [98, 0, 0]
Extend      LUpperArm [84, 0, 8]    LLowerArm [10, 0, 0]
Recover     LUpperArm [24, 0, 15]   LLowerArm [96, 0, 0]
```

The rear hand stays at the chin the whole time. A jab that drops the other hand
is a tell, and it reads as sloppy at any speed.

## Hook

0.55 s. The elbow stays near 90°; the punch is the arc, not the extension.

```
Wind-up     UpperTorso [-2, 24, 0]   RUpperArm [-10, 0, -30]   RLowerArm [95, 0, 0]
Contact     UpperTorso [-8, -18, 0]  RUpperArm [55, 0, 20]     RLowerArm [88, 0, 0]
Follow      UpperTorso [-10, -26, 0] RUpperArm [62, 0, 26]     RLowerArm [92, 0, 0]
```

`+Z` on the right upper arm swings it outward; for a hook the elbow travels
around, not forward. Check the sheet: the fist should cross the centreline.

## Roundhouse kick (rear leg)

0.7 s. Support foot stays flat; the kicking hip passes 90°.

| Pose | Support (L) | Kick (R) | Torso |
|---|---|---|---|
| Chamber | `LUpperLeg [8]`, `LFoot [-8]` | `RUpperLeg [70, 0, 0]`, `RLowerLeg [-95]` | `UpperTorso [-4, 18]` |
| Contact | `LUpperLeg [10]`, `LFoot [-10]` | `RUpperLeg [105, 0, 0]`, `RLowerLeg [-25]` | `UpperTorso [-8, -12]` |
| Rechamber | `LUpperLeg [8]`, `LFoot [-8]` | `RUpperLeg [75]`, `RLowerLeg [-80]` | `UpperTorso [-4, 4]` |

- A forward kick needs the hip **past 90°** or the leg merges with the torso.
- Counter-rotate the support ankle: `LFoot ≈ -(LUpperLeg + LLowerLeg)`. At contact
  that is `-(10 + -6) = -4`; the table's `-10` includes a heel pivot.
- The support knee stays slightly bent; a locked knee reads as a stork.

## Hit react

0.25 s, one direction only.

```
Impact    UpperTorso [8, -6, 0]    Head [10, 8, 0]     arms fly back 15°
Settle    UpperTorso [4, -2, 0]    Head [4, 4, 0]
```

Do not return to guard inside a hit react; the gameplay layer blends back. A clip
that recovers fully reads as a flinch loop.

## Death

0.9 s. Collapse is a chain: head, torso, hips, knees, then the floor.

```
Stagger   UpperTorso [-14, 0, 6]   Head [-18, 0, 8]    knees 20°
Buckle    LowerTorso [0, 0, 0]     LUpperLeg [38]      LLowerLeg [-70]
Floor     LowerTorso [0, 0, 18]    UpperTorso [6, 0, 12]   arms splayed
```

Rigid parts cannot lie flat by folding alone, so a full death uses the **root
channel**: drop and push the whole character back while the knees fold, e.g.
`"root": [0, -1.4, 0.6]` at the floor key. The root is a rigid translation of
the whole body — use it for jumps, crouches and deaths, not to fake a pose.

## Locomotion

Walk (1.0 s, two contacts) and run (0.7 s, two contacts) share the shape:

| Phase | Lead leg | Trail leg | Arms |
|---|---|---|---|
| Contact | `UpperLeg [28]`, `LowerLeg [-8]`, `Foot [-20]` | `UpperLeg [-24]`, `LowerLeg [40]`, `Foot [-16]` | opposite arm forward 35° |
| Pass | `UpperLeg [2]`, `LowerLeg [-40]`, `Foot [30]` | `UpperLeg [10]`, `LowerLeg [-55]`, `Foot [20]` | arms near neutral |
| Contact (mirror) | swap sides | swap sides | swap sides |

- Torso leans forward: walk `-4`, run `-12` (`UpperTorso.X`).
- Arms opposite the legs, elbows 60–80°.
- Run has an airborne phase; walk always has one foot down.
- Set `"locomotion": true`. The contact foot travelling backward is stride.

## Idle

2–4 s loop, subtle:

```
UpperTorso [-2, 0, 0] → [-3, 0, 0]     Head [2, 0, 0] → [1, 2, 0]
Arms: guard or relaxed, 2–4° of drift   Knees: 1–2° flex
```

A breathing idle changes the chest by 1–2° and the head by 1–2°; more looks like
a sway. Loop seam under 5°.

## Emote / wave

```
Raise    RUpperArm [70, 0, -55]   RLowerArm [20, 0, 0]   Head [2, -8, 0]
Wave 1   RLowerArm [25, 0, 20]    RHand [0, 0, 25]
Wave 2   RLowerArm [25, 0, -15]   RHand [0, 0, -20]
Lower    RUpperArm [20, 0, -10]   RLowerArm [80, 0, 0]
```

`+Z` on the right arm is outward; the wave alternates `Z` on the forearm, not the
shoulder. Keep the elbow above the wrist.

## Props

| Class | At rest | In motion |
|---|---|---|
| Polearm, spear, glaive | head **up** — shouldered, butt on the ground, or at guard with the head at chest height or above. Never hanging at the feet | head leads the arc; shaft crosses in front of the body |
| Sword | angled up and forward from a lowered hand, ~35° | edge leads; the whole arm carries the arc, the wrist is not a hinge |
| Axe, hammer | head up or shouldered | the head is the mass: it arrives last and hardest |
| Fist weapon | worn, not gripped | the hips drive it |

A weapon longer than the character is tall cannot be carried in the same plane as
the arm without clipping. Put it across the body.

## The three rules that catch people out

1. **Child angles compound.** Shoulder 50° + elbow 70° puts the forearm 120° from
   vertical — pointing up over the shoulder. Keep shoulder + elbow under ~120° for
   a guard.
2. **Twist on `LowerTorso` drags the legs.** Lean and most twist go on
   `UpperTorso`; the hips get a few degrees, not the whole rotation.
3. **Counter-rotate the ankle**, or the foot tilts with the leg and the character
   stands on a slope.
