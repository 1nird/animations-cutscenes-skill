"""Validate a shot list and emit a camera player.

    py scripts/cutscene.py examples/cutscene.json --out out/

The rules are the ones a cut gets wrong: the 180-degree line, jump cuts under
30 degrees, degenerate look targets, absurd FOVs, whip speeds, subtitles that
outrun the eye. Nothing here renders; it proves the plan is shootable before
anyone builds it.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

EPS = 1e-6
MIN_DUR, MAX_DUR = 0.3, 20.0
FOV_MIN, FOV_MAX = 20.0, 90.0
WHIP = 20.0          # studs per second before a move reads as a whip pan
CPS = 22.0           # subtitle characters per second the eye keeps up with


def vec(value, name, shot_id, errors):
    try:
        out = tuple(float(v) for v in value)
        if len(out) != 3:
            raise ValueError
        return out
    except (TypeError, ValueError):
        errors.append(f"E204 {shot_id}: {name} must be three numbers")
        return (0.0, 0.0, 0.0)


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def side(a, b, c):
    """Sign of the camera's side of the line a-b, seen from above."""
    return (b[0] - a[0]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[0] - a[0])


def angle(a, b):
    na = math.sqrt(sum(v * v for v in a)) or 1.0
    nb = math.sqrt(sum(v * v for v in b)) or 1.0
    dot = sum(a[i] * b[i] for i in range(3)) / (na * nb)
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


def normalize(spec):
    spec = dict(spec)
    spec.setdefault("fps", 30)
    spec.setdefault("shots", [])
    shots = []
    for raw in spec["shots"]:
        shot = dict(raw)
        shot["id"] = str(shot.get("id", f"s{len(shots) + 1}"))
        shot["kind"] = str(shot.get("kind", "cut"))
        shot["dur"] = float(shot.get("dur", 1.0))
        shot["ease"] = str(shot.get("ease", "inout"))
        shot["from"] = dict(shot.get("from", {}))
        shot["to"] = dict(shot.get("to", shot["from"]))
        shot["from"]["pos"] = shot["from"].get("pos", (0, 2, 10))
        shot["from"]["look"] = shot["from"].get("look", (0, 2, 0))
        shot["from"]["fov"] = float(shot["from"].get("fov", 40))
        shot["to"]["pos"] = shot["to"].get("pos", shot["from"]["pos"])
        shot["to"]["look"] = shot["to"].get("look", shot["from"]["look"])
        shot["to"]["fov"] = float(shot["to"].get("fov", shot["from"]["fov"]))
        shots.append(shot)
    spec["shots"] = shots
    return spec


def validate(spec):
    errors, warnings = [], []
    shots = spec["shots"]
    if not shots:
        errors.append("E201 no shots")
        return errors, warnings, {"shots": 0, "duration": 0.0, "asl": 0.0}
    if not (1 <= spec["fps"] <= 240):
        errors.append("E202 fps must be between 1 and 240")

    seen = set()
    total = 0.0
    timeline = []
    lines = {}
    for i, shot in enumerate(shots):
        sid = shot["id"]
        if sid in seen:
            errors.append(f"E203 duplicate shot id '{sid}'")
        seen.add(sid)
        if shot["kind"] not in ("cut", "move"):
            errors.append(f"E205 {sid}: kind must be 'cut' or 'move'")
        if not (MIN_DUR <= shot["dur"] <= MAX_DUR):
            errors.append(f"E206 {sid}: {shot['dur']:g}s is outside {MIN_DUR:g}-{MAX_DUR:g}s")
        if shot["ease"] not in ("linear", "constant", "in", "out", "inout", "elastic", "bounce"):
            errors.append(f"E207 {sid}: unknown ease '{shot['ease']}'")
        if shot["dur"] <= EPS:
            continue

        f, t = shot["from"], shot["to"]
        fp = vec(f["pos"], "from.pos", sid, errors)
        fl = vec(f["look"], "from.look", sid, errors)
        tp = vec(t["pos"], "to.pos", sid, errors)
        tl = vec(t["look"], "to.look", sid, errors)
        for point, label in ((fp, "camera"), (tp, "camera")):
            if point[1] < 0.0:
                errors.append(f"E208 {sid}: camera is below the floor")
        if dist(fp, fl) < 0.5 or dist(tp, tl) < 0.5:
            errors.append(f"E209 {sid}: look target is on the camera (degenerate CFrame.lookAt)")
        for fov, label in ((f["fov"], "from"), (t["fov"], "to")):
            if not (FOV_MIN <= fov <= FOV_MAX):
                errors.append(f"E210 {sid}: {label}.fov {fov:g} outside {FOV_MIN:g}-{FOV_MAX:g}")
            elif fov < 25 or fov > 75:
                warnings.append(f"W201 {sid}: {label}.fov {fov:g} is at the edge of useful")

        travel = dist(fp, tp)
        if shot["kind"] == "cut" and travel > 0.01:
            warnings.append(f"W202 {sid}: static shot has different from/to; call it a move")
        if shot["kind"] == "move":
            if travel < 0.25:
                warnings.append(f"W203 {sid}: move travels only {travel:.2f} studs")
            speed = travel / shot["dur"]
            if speed > 60:
                errors.append(f"E211 {sid}: camera moves at {speed:.0f} studs/s")
            elif speed > WHIP:
                warnings.append(f"W204 {sid}: {speed:.1f} studs/s reads as a whip pan")

        dialogue = shot.get("dialogue")
        if dialogue:
            text = str(dialogue.get("text", ""))
            if not text:
                errors.append(f"E212 {sid}: dialogue has no text")
            else:
                cps = len(text) / shot["dur"]
                if cps > CPS:
                    warnings.append(f"W205 {sid}: {cps:.0f} chars/s is faster than the eye ({CPS:.0f})")
            start = float(dialogue.get("start", 0.0))
            if start >= shot["dur"]:
                errors.append(f"E213 {sid}: dialogue starts after the shot ends")

        line = shot.get("line")
        scene = shot.get("scene")
        if line and scene:
            a = vec(line[0], "line[0]", sid, errors)
            b = vec(line[1], "line[1]", sid, errors)
            sign = side(a, b, fp)
            if abs(sign) < 1e-3:
                warnings.append(f"W206 {sid}: camera sits on the line itself")
            lines.setdefault(scene, []).append((sid, sign))

        timeline.append({
            "id": sid,
            "start": round(total, 2),
            "dur": round(shot["dur"], 2),
            "kind": shot["kind"],
            "subject": shot.get("subject", ""),
            "fov": [round(f["fov"], 1), round(t["fov"], 1)],
        })
        total += shot["dur"]

    for scene, entries in lines.items():
        signs = {1 if s > 0 else -1 for _, s in entries if abs(s) > 1e-3}
        if len(signs) > 1:
            ids = ", ".join(sid for sid, _ in entries)
            errors.append(f"E214 scene '{scene}' crosses the 180-degree line ({ids})")

    for i in range(1, len(shots)):
        a, b = shots[i - 1], shots[i]
        if a.get("subject") and a.get("subject") == b.get("subject"):
            va = tuple(a["to"]["look"][j] - a["to"]["pos"][j] for j in range(3))
            vb = tuple(b["from"]["look"][j] - b["from"]["pos"][j] for j in range(3))
            delta = angle(va, vb)
            ratio = max(a["to"]["fov"], b["from"]["fov"]) / max(1e-3, min(a["to"]["fov"], b["from"]["fov"]))
            if delta < 30 and ratio < 1.25:
                warnings.append(f"W207 {a['id']}->{b['id']}: same subject, {delta:.0f} deg apart "
                                f"and same size reads as a jump cut")

    asl = total / len(shots)
    if asl < 1.0:
        warnings.append(f"W208 average shot length {asl:.1f}s is frantic")
    if asl > 6.0:
        warnings.append(f"W209 average shot length {asl:.1f}s is sleepy")

    subjects = {s.get("subject") for s in shots if s.get("subject")}
    fovs = [s["from"]["fov"] for s in shots]
    if len(subjects) == 1 and max(fovs) - min(fovs) <= 2:
        warnings.append("W210 one subject, one lens: the scene has no coverage")

    letterbox = {bool(s.get("letterbox", True)) for s in shots}
    if len(letterbox) > 1:
        warnings.append("W211 letterbox is on for some shots and off for others")

    stats = {
        "shots": len(shots),
        "duration": round(total, 2),
        "asl": round(asl, 2),
        "timeline": timeline,
    }
    return errors, warnings, stats


def lua_num(value):
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def lua_str(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def lua_point(point):
    return f"Vector3.new({lua_num(point[0])}, {lua_num(point[1])}, {lua_num(point[2])})"


def emit_data(spec):
    lines = ["-- Generated by rxz animation. Shot list for CutscenePlayer.", "return {",
             f"\tname = {lua_str(spec.get('name', 'Cutscene'))},",
             f"\tfps = {spec['fps']},",
             "\tshots = {"]
    for shot in spec["shots"]:
        f, t = shot["from"], shot["to"]
        lines.append("\t\t{")
        lines.append(f"\t\t\tid = {lua_str(shot['id'])}, kind = {lua_str(shot['kind'])}, "
                     f"dur = {lua_num(shot['dur'])}, ease = {lua_str(shot['ease'])},")
        if shot.get("subject"):
            lines.append(f"\t\t\tsubject = {lua_str(shot['subject'])},")
        lines.append(f"\t\t\tfrom = {{ pos = {lua_point(f['pos'])}, look = {lua_point(f['look'])}, "
                     f"fov = {lua_num(f['fov'])} }},")
        lines.append(f"\t\t\tto   = {{ pos = {lua_point(t['pos'])}, look = {lua_point(t['look'])}, "
                     f"fov = {lua_num(t['fov'])} }},")
        if shot.get("dialogue"):
            d = shot["dialogue"]
            lines.append(f"\t\t\tdialogue = {{ speaker = {lua_str(d.get('speaker', ''))}, "
                         f"text = {lua_str(d.get('text', ''))}, start = {lua_num(float(d.get('start', 0)))} }},")
        if shot.get("sfx"):
            lines.append(f"\t\t\tsfx = {lua_str(shot['sfx'])}, ")
        lines.append(f"\t\t\tletterbox = {'true' if shot.get('letterbox', True) else 'false'},")
        lines.append("\t\t},")
    lines += ["\t},", "}", ""]
    return "\n".join(lines)


PLAYER = r'''-- rxz cutscene player. LocalScript in StarterPlayerScripts, next to the
-- CutsceneData ModuleScript. It owns the camera only while playing and
-- restores it afterwards. Play it in Studio before shipping it.
-- It plays on start; to trigger it yourself, make it a ModuleScript and
-- replace the final play() with: return play
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ContextActionService = game:GetService("ContextActionService")
local StarterGui = game:GetService("StarterGui")
local SoundService = game:GetService("SoundService")

local data = require(script.Parent:WaitForChild("CutsceneData"))
local player = Players.LocalPlayer
local camera = workspace.CurrentCamera
local skipped = false

local function ease(kind, t)
	t = math.clamp(t, 0, 1)
	if kind == "linear" then
		return t
	elseif kind == "constant" then
		return t < 1 and 0 or 1
	elseif kind == "in" then
		return t * t * t
	elseif kind == "out" then
		return 1 - (1 - t) ^ 3
	elseif kind == "inout" then
		return t < 0.5 and 4 * t ^ 3 or 1 - ((-2 * t + 2) ^ 3) / 2
	elseif kind == "elastic" then
		if t == 0 or t == 1 then return t end
		return 2 ^ (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1
	elseif kind == "bounce" then
		local n, d = 7.5625, 2.75
		if t < 1 / d then return n * t * t end
		if t < 2 / d then t = t - 1.5 / d return n * t * t + 0.75 end
		if t < 2.5 / d then t = t - 2.25 / d return n * t * t + 0.9375 end
		t = t - 2.625 / d
		return n * t * t + 0.984375
	end
	return t
end

local function makeUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "CutsceneUi"
	gui.IgnoreGuiInset = true
	gui.ResetOnSpawn = false
	gui.DisplayOrder = 50
	gui.Parent = player:WaitForChild("PlayerGui")

	local top = Instance.new("Frame")
	top.Name = "Top"
	top.BackgroundColor3 = Color3.new(0, 0, 0)
	top.BorderSizePixel = 0
	top.Size = UDim2.new(1, 0, 0.11, 0)
	top.Position = UDim2.new(0, 0, 0, 0)
	top.Parent = gui

	local bottom = top:Clone()
	bottom.Name = "Bottom"
	bottom.Position = UDim2.new(0, 0, 0.89, 0)
	bottom.Parent = gui

	local sub = Instance.new("TextLabel")
	sub.Name = "Subtitle"
	sub.BackgroundTransparency = 1
	sub.AnchorPoint = Vector2.new(0.5, 1)
	sub.Position = UDim2.new(0.5, 0, 0.86, 0)
	sub.Size = UDim2.new(0.8, 0, 0.12, 0)
	sub.Font = Enum.Font.GothamMedium
	sub.TextScaled = true
	sub.TextColor3 = Color3.new(1, 1, 1)
	sub.TextStrokeTransparency = 0.4
	sub.TextWrapped = true
	sub.Text = ""
	sub.Parent = gui
	return gui, top, bottom, sub
end

local function bindSkip()
	ContextActionService:BindAction("SkipCutscene", function(_, state)
		if state == Enum.UserInputState.Begin then
			skipped = true
		end
		return Enum.ContextActionResult.Sink
	end, true, Enum.KeyCode.Space, Enum.KeyCode.ButtonA, Enum.KeyCode.ButtonStart)
end

local function play()
	local gui, top, bottom, sub = makeUi()
	local savedType = camera.CameraType
	local savedCFrame = camera.CFrame
	local savedFov = camera.FieldOfView
	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	local savedWalk, savedJump, savedJumpHeight
	if humanoid then
		savedWalk, savedJump, savedJumpHeight = humanoid.WalkSpeed, humanoid.JumpPower, humanoid.JumpHeight
		humanoid.WalkSpeed = 0
		humanoid.JumpPower = 0
		humanoid.JumpHeight = 0
	end
	camera.CameraType = Enum.CameraType.Scriptable
	StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.All, false)
	bindSkip()

	for _, shot in ipairs(data.shots) do
		if skipped then break end
		top.Visible = shot.letterbox ~= false
		bottom.Visible = shot.letterbox ~= false
		sub.Text = ""
		if shot.sfx then
			local sound = Instance.new("Sound")
			sound.SoundId = shot.sfx
			sound.Parent = SoundService
			sound:Play()
			sound.Ended:Once(function() sound:Destroy() end)
		end

		local start = os.clock()
		local connection
		connection = RunService.RenderStepped:Connect(function()
			local u = math.clamp((os.clock() - start) / shot.dur, 0, 1)
			local e = ease(shot.ease, u)
			local pos = shot.from.pos:Lerp(shot.to.pos, e)
			local look = shot.from.look:Lerp(shot.to.look, e)
			camera.CFrame = CFrame.lookAt(pos, look)
			camera.FieldOfView = shot.from.fov + (shot.to.fov - shot.from.fov) * e
			if shot.dialogue then
				local at = math.max(0, shot.dialogue.start or 0)
				sub.Text = u * shot.dur >= at and (shot.dialogue.speaker .. ": " .. shot.dialogue.text) or ""
			end
		end)

		while os.clock() - start < shot.dur and not skipped do
			task.wait()
		end
		connection:Disconnect()
	end

	ContextActionService:UnbindAction("SkipCutscene")
	gui:Destroy()
	camera.CameraType = savedType
	camera.CFrame = savedCFrame
	camera.FieldOfView = savedFov
	if humanoid and humanoid.Parent then
		humanoid.WalkSpeed = savedWalk
		humanoid.JumpPower = savedJump
		humanoid.JumpHeight = savedJumpHeight
	end
	StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.All, true)
end

-- Plays on start. To trigger it yourself, make this a ModuleScript and
-- replace the next line with: return play
play()
'''


def cmd(args):
    spec = normalize(json.loads(Path(args.spec).read_text(encoding="utf-8")))
    errors, warnings, stats = validate(spec)
    report = {
        "name": spec.get("name", ""),
        "fps": spec["fps"],
        "errors": errors,
        "warnings": warnings,
        "stats": {k: v for k, v in stats.items() if k != "timeline"},
        "timeline": stats["timeline"],
    }
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "CutsceneData.luau").write_text(emit_data(spec), encoding="utf-8")
        (out / "CutscenePlayer.luau").write_text(PLAYER, encoding="utf-8")
        (out / "cutscene.report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{spec.get('name', 'Cutscene')}  {stats['shots']} shots  "
              f"{stats['duration']:.1f}s  ASL {stats['asl']:.1f}s")
        print(f"{'start':>6} {'dur':>5}  {'id':<5} {'kind':<5} {'subject':<12} fov")
        for row in stats["timeline"]:
            print(f"{row['start']:>6.1f} {row['dur']:>5.1f}  {row['id']:<5} "
                  f"{row['kind']:<5} {row['subject'][:12]:<12} {row['fov'][0]:g}-{row['fov'][1]:g}")
        for w in warnings:
            print(f"WARN  {w}")
        for e in errors:
            print(f"FAIL  {e}")
        print("OK" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a cutscene shot list and emit Luau.")
    parser.add_argument("spec")
    parser.add_argument("--out", help="write CutsceneData.luau, CutscenePlayer.luau and a report")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    return cmd(args)


if __name__ == "__main__":
    raise SystemExit(main())
