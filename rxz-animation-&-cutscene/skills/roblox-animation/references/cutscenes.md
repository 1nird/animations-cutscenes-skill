# Cutscenes: shot grammar and camera

A cutscene is not a long camera move. It is a sequence of shots, each with a
reason, cut together so the eye never has to ask where to look.

## Shot sizes, in studs

Camera FOV is **vertical** in Roblox. At 16:9, a 40° lens sees
`2 · d · tan(20°) ≈ 0.73 · d` studs of height at distance `d`. For a 5-stud
character:

| Shot | Height in frame | FOV 30 | FOV 40 | FOV 50 |
|---|---|---|---|---|
| Wide / establishing | 10+ studs | 19+ | 14+ | 10+ |
| Full body | 5 studs | 9.3 | 6.9 | 5.3 |
| Medium (waist up) | 3 studs | 5.6 | 4.1 | 3.2 |
| Close | 1.2 studs | 2.2 | 1.6 | 1.3 |

Longer lenses (lower FOV) compress the background and flatter a face; wider
lenses exaggerate depth and distort edges. Pick one lens per scene and change it
for a reason.

## The rules the validator enforces

**180° rule.** Two characters in conversation define a line between them. Every
camera in that scene stays on one side of it. Cross the line and the audience
believes the characters swapped places. `cutscene.py` computes the sign of the
camera against the line for every shot sharing a `scene` and fails if it flips.

**30° rule.** Consecutive shots of the same subject need at least 30° of camera
change, or a clear change of lens, or they read as a jump cut. Two shots from
almost the same place are a mistake, not a cut.

**Eyeline.** A character looking at another should look slightly off-camera, not
into the lens, unless the shot is deliberately confrontational. Keep the camera
near the listener's eye height for over-the-shoulder coverage.

**Lead room.** Leave space in the direction a character looks or moves. A subject
pinned to the frame edge reads as an accident.

**Cut on action.** Cut while something is moving, not after it stops. The motion
carries the cut and the eye forgives the change.

## Pacing

| Scene | Average shot length |
|---|---|
| Action | 1.0–2.0 s |
| Dialogue | 2.5–4.0 s |
| Establishing / mood | 3.0–6.0 s |

The validator warns under 1.0 s (frantic) and over 6.0 s (sleepy). A 13-second
intro at 2.6 s average is five shots — reasonable. Twelve shots in the same time
is a trailer, not an intro.

## Movement

Every shot should carry motion. A frame that does not move is a slide.

- **Push-in**: 0.5–1.5 studs over the shot. Use it when the character realises
  something.
- **Pull-out**: reveal the space; end wide.
- **Drift**: 0.2–0.5 studs sideways, slow. Keeps a dialogue shot alive.
- **Crane**: vertical move; use sparingly, it announces itself.
- **Handheld**: 0.5–1° of low-frequency noise, not a shake. Shake is impact, not
  style.
- **Whip**: 20+ studs/s. The validator warns; it is a transition, not a shot.

A camera move should have a reason in the sentence: "push in as he decides",
"pull out to show the army". If the reason is "it looked static", the shot is
wrong, not the camera.

## FOV

- 20–28: long lens, close-ups, compression. Rare in gameplay.
- 30–40: portrait and dialogue. The default for cutscenes.
- 45–55: full body and action.
- 60–75: wide, environment, speed.
- Above 80: distortion; use for a effect, not coverage.

`Camera.FieldOfView` clamps at 1–120 and defaults to 70. Because it is vertical,
a 16:9 phone and a 4:3 tablet see the same height and different widths — frame
vertically and keep the subject centred, and no one loses the action.

## Sound

- **Diegetic** sound (a door, a step) belongs at the frame it happens; put a
  marker on the keyframe.
- **Score** starts on a cut, not before it, or the cut feels late.
- Duck the music under dialogue by 6–10 dB rather than raising the voice.
- An L-cut (sound from the next shot arriving early) hides a hard cut better than
  any transition.

## Subtitles and UI

- 22 characters per second maximum; the validator warns above it.
- Two lines, 80% width, bottom safe area. On mobile, keep 12% margins.
- Letterbox: 11% top and bottom, `IgnoreGuiInset = true`, `DisplayOrder` above
  the game UI.
- Hide the core GUI (`StarterGui:SetCoreGuiEnabled(All, false)`) and disable the
  player's controls during the scene; restore both on exit and on skip.
- Skip on Space / gamepad A / Start, always. A cutscene that cannot be skipped is
  a retention problem.

## Camera collision

A camera move inside a room will go through a wall. Before the shot, raycast from
the subject to the camera position and pull the camera in front of the first hit,
or keep the move inside the room's bounds. Do the test in Studio; the validator
cannot see geometry.

## Post

- `DepthOfFieldEffect`: `FocusDistance` = distance to the subject,
  `InFocusRadius` 4–8 studs, `FarIntensity` 0.2–0.4. Focus on the eyes.
- `ColorCorrectionEffect`: one look per scene, not per shot.
- `BlurEffect` only for a transition or a flashback.
- Grade and letterbox should be consistent across the scene; the validator warns
  if letterbox flickers.

## Testing

1. Screenshot the **midpoint of every shot** and look at the framing.
2. Check the subject is inside the middle third on both 16:9 and a 4:3 crop.
3. Play it end to end, skip it, and play it again: the camera must return to the
   player exactly as it was.
4. Check there is no frame where the camera is inside geometry or the subject is
   off-screen.
