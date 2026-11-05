# QA: the gates and the sheet

## The gates

`verify.py` reads the reports and prints PASS/FAIL. Thresholds live in one place;
change them only with a reason you can defend.

| Gate | Passes when | Why it exists |
|---|---|---|
| spec valid | no errors from `anim.py lint` | structure failures are cheaper to fix than playback failures |
| clip length | duration > 0.1 s, at least 2 keys | a one-key clip is a pose, not an animation |
| loop seam | ≤ 15° per joint (loops only) | the seam is a visible jump every cycle |
| foot contact | lowest sole ≥ −0.06 studs | through-floor feet are the most common visible defect |
| planted foot | travel ≤ 0.25 studs, or `locomotion: true` | sliding feet read as ice |
| ground evidence | at least one contact run if grounded | a clip with no contact is floating |
| cutscene valid | no shot-list errors | 180°/30°/degenerate look targets |
| cutscene pacing | ASL 1.0–6.0 s | frantic or sleepy, both are cuts that don't land |
| artifacts | at least one `.rbxmx` and `.luau` | the deliverable exists |
| contact sheet | at least one `.png` | someone can look at it |

Warnings are not failures, but a warning you did not read is a failure you chose.

## The contact sheet

`preview.py` renders two views of up to 24 evenly spaced frames:

- **Side**: forward is to the right. Best for arcs, reach, lean, foot contact.
- **Front**: best for guard symmetry, twist, arm crossing, whether a punch
  crosses the centreline.

Look for, in order:

1. **Silhouette.** Squint. Can you name the action from the shape?
2. **Contact.** The extreme pose lands where you said (0.14 s = frame 4).
3. **Feet.** Green dots on the line, no sole below it, no tilt.
4. **Hands.** In front of the torso, not inside it; the guard hand stays up.
5. **Return.** Last frame matches the first if the clip returns to guard.

The sheet proves the data matches the spec. It cannot prove the spec is the right
move — judge it against the intent sentence and, when there is one, the reference
side by side. If they disagree, the reference wins and the spec changes.

## Why numbers and pictures both

- Numbers catch what the eye forgives at 240 px: 0.3 studs of slide, a foot 0.1
  below the floor, a seam that only shows on loop.
- Pictures catch what the numbers cannot describe: a guard that reads as a shrug,
  a punch that travels but has no weight, a kick that merges with the torso.

Neither is optional. A run that only passes the numbers is unverified; a sheet
that looks fine over feet in the floor is unverified too.

## Diagnosis

| What you see | First check | Then |
|---|---|---|
| Punch weak, arm extends | torso twist sign; `+Y` sends the right shoulder back | flip torso Y at contact, add hip drive |
| Arm crosses the face | shoulder + elbow compounding past 120° | reduce upper arm X, keep elbow |
| Feet slide | hip twist; ankle counter-rotation | `foot.X ≈ -(hip.X + knee.X)` |
| Foot below the floor | leg rotation without a root dip | shorten the stance or bend the knee |
| Legs frozen during walk | authored idle at `Action` masks `Core` | idle at `Core` or upper body only |
| Loop pops | last pose differs from first | copy frame 0 to the end, re-check seam |
| Clip plays once in a loop | `loop: false` | set `loop: true` |
| Hands float off a prop | grip not authored | weld at the grip, pose the wrist |
| Everything looks stiff | keys only at extremes, linear ease | add a breakdown, vary ease |

## Before calling it done

- [ ] `anim.py lint` exits 0.
- [ ] `fk.py` shows contact within tolerance and no warning you have not explained.
- [ ] The sheet was opened and judged against the intent.
- [ ] `verify.py` all green.
- [ ] In Studio: `Length` matches, the clip plays on the character, the legs still
      walk when the character moves, and the marker fires on the contact frame.
- [ ] If it is a cutscene: every shot midpoint was looked at, skip works, and the
      camera restores exactly.
