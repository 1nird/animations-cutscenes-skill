"""Shared core for the rxz animation tools.

Stdlib only. Authoring, forward kinematics and preview all import this module,
so a number printed by one script means the same thing in the others: one
definition of a pose, one easing curve, one skeleton.

Axis convention, in the joint's rest frame:
    +X  swings a hanging limb FORWARD      (-Z world)
    +Z  swings it toward +X
    +Y  twists it about its own length
Both arms hang down, so the same +Z is outward on one side and inward on the
other. Never mirror a pose by copying a sign; check each side.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

EPS = 1e-6

IDENT = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

# Engine values. AnimationPriority.Core is 1000, not 6 - do not guess this one.
PRIORITIES = {
    "Idle": 0,
    "Movement": 1,
    "Action": 2,
    "Action2": 3,
    "Action3": 4,
    "Action4": 5,
    "Core": 1000,
}

# PoseEasingStyle. Cubic is a deprecated alias with a direction bug; CubicV2 is
# the one new work should use.
POSE_EASING = {
    "Linear": 0,
    "Constant": 1,
    "Elastic": 2,
    "Cubic": 3,
    "Bounce": 4,
    "CubicV2": 5,
}
POSE_DIRECTION = {"In": 0, "Out": 1, "InOut": 2}

EASE_INTENTS = ("linear", "constant", "in", "out", "inout", "elastic", "bounce")

# Spec intent -> engine enums. In and Out are backwards in Roblox for legacy
# reasons: Out accelerates, In decelerates. "in" here means accelerate.
EASE_MAP = {
    "linear": ("Linear", "Out"),
    "constant": ("Constant", "Out"),
    "in": ("CubicV2", "Out"),
    "out": ("CubicV2", "In"),
    "inout": ("CubicV2", "InOut"),
    "elastic": ("Elastic", "Out"),
    "bounce": ("Bounce", "Out"),
}

# Nominal R15, feet on y=0, character 5 studs tall. Joint offsets are in the
# parent's space, in studs. This is a preview skeleton, not a measurement of a
# particular avatar: dump rig.json from the place for exact numbers.
R15 = {
    "HumanoidRootPart": (None, (0.0, 2.20, 0.0)),
    "LowerTorso": ("HumanoidRootPart", (0.0, 0.00, 0.0)),
    "UpperTorso": ("LowerTorso", (0.0, 0.45, 0.0)),
    "Head": ("UpperTorso", (0.0, 0.95, 0.0)),
    "LeftUpperArm": ("UpperTorso", (0.55, 0.65, 0.0)),
    "LeftLowerArm": ("LeftUpperArm", (0.0, -0.70, 0.0)),
    "LeftHand": ("LeftLowerArm", (0.0, -0.70, 0.0)),
    "RightUpperArm": ("UpperTorso", (-0.55, 0.65, 0.0)),
    "RightLowerArm": ("RightUpperArm", (0.0, -0.70, 0.0)),
    "RightHand": ("RightLowerArm", (0.0, -0.70, 0.0)),
    "LeftUpperLeg": ("LowerTorso", (0.25, -0.15, 0.0)),
    "LeftLowerLeg": ("LeftUpperLeg", (0.0, -0.90, 0.0)),
    "LeftFoot": ("LeftLowerLeg", (0.0, -0.90, 0.0)),
    "RightUpperLeg": ("LowerTorso", (-0.25, -0.15, 0.0)),
    "RightLowerLeg": ("RightUpperLeg", (0.0, -0.90, 0.0)),
    "RightFoot": ("RightLowerLeg", (0.0, -0.90, 0.0)),
}

R6 = {
    "HumanoidRootPart": (None, (0.0, 2.00, 0.0)),
    "Torso": ("HumanoidRootPart", (0.0, 0.00, 0.0)),
    "Head": ("Torso", (0.0, 0.90, 0.0)),
    "Left Arm": ("Torso", (0.90, 0.40, 0.0)),
    "Right Arm": ("Torso", (-0.90, 0.40, 0.0)),
    "Left Leg": ("Torso", (0.35, -0.75, 0.0)),
    "Right Leg": ("Torso", (-0.35, -0.75, 0.0)),
}

RIGS = {"R15": R15, "R6": R6}
SOLE_DROP = {"R15": 0.25, "R6": 1.00}
FOOT_PARTS = {
    "R15": ("LeftFoot", "RightFoot"),
    "R6": ("Left Leg", "Right Leg"),
}


# --------------------------------------------------------------------- matrices

def matmul(a, b):
    return tuple(
        tuple(a[i][0] * b[0][j] + a[i][1] * b[1][j] + a[i][2] * b[2][j] for j in range(3))
        for i in range(3)
    )


def matvec(m, v):
    return (
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    )


def matadd(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def euler_matrix(rx, ry, rz):
    """Degrees, applied Z then Y then X: R = Rz * Ry * Rx.

    This is what CFrame.Angles(rx, ry, rz) builds, and the explicit product the
    engine-side exporter writes, so preview and Studio agree.
    """
    rx, ry, rz = math.radians(rx), math.radians(ry), math.radians(rz)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    mx = ((1.0, 0.0, 0.0), (0.0, cx, -sx), (0.0, sx, cx))
    my = ((cy, 0.0, sy), (0.0, 1.0, 0.0), (-sy, 0.0, cy))
    mz = ((cz, -sz, 0.0), (sz, cz, 0.0), (0.0, 0.0, 1.0))
    return matmul(matmul(mz, my), mx)


def quat_from_matrix(m):
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0.0:
        s = math.sqrt(tr + 1.0) * 2.0
        w = 0.25 * s
        x = (m[2][1] - m[1][2]) / s
        y = (m[0][2] - m[2][0]) / s
        z = (m[1][0] - m[0][1]) / s
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2.0
        w = (m[2][1] - m[1][2]) / s
        x = 0.25 * s
        y = (m[0][1] + m[1][0]) / s
        z = (m[0][2] + m[2][0]) / s
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2.0
        w = (m[0][2] - m[2][0]) / s
        x = (m[0][1] + m[1][0]) / s
        y = 0.25 * s
        z = (m[1][2] + m[2][1]) / s
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2.0
        w = (m[1][0] - m[0][1]) / s
        x = (m[0][2] + m[2][0]) / s
        y = (m[1][2] + m[2][1]) / s
        z = 0.25 * s
    n = math.sqrt(w * w + x * x + y * y + z * z) or 1.0
    return (w / n, x / n, y / n, z / n)


def matrix_from_quat(q):
    w, x, y, z = q
    return (
        (1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)),
        (2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)),
        (2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)),
    )


def slerp(a, b, t):
    """Shortest-arc slerp between two rotation matrices, as the engine does."""
    qa, qb = quat_from_matrix(a), quat_from_matrix(b)
    dot = sum(qa[i] * qb[i] for i in range(4))
    if dot < 0.0:
        qb = tuple(-v for v in qb)
        dot = -dot
    if dot > 0.9995:
        out = tuple(qa[i] + (qb[i] - qa[i]) * t for i in range(4))
        n = math.sqrt(sum(v * v for v in out)) or 1.0
        return matrix_from_quat(tuple(v / n for v in out))
    theta = math.acos(max(-1.0, min(1.0, dot)))
    sin_theta = math.sin(theta) or 1.0
    wa = math.sin((1.0 - t) * theta) / sin_theta
    wb = math.sin(t * theta) / sin_theta
    q = tuple(qa[i] * wa + qb[i] * wb for i in range(4))
    n = math.sqrt(sum(v * v for v in q)) or 1.0
    return matrix_from_quat(tuple(v / n for v in q))


def angle_between(a, b):
    """Degrees between two rotations, short way round."""
    qa, qb = quat_from_matrix(a), quat_from_matrix(b)
    dot = abs(sum(qa[i] * qb[i] for i in range(4)))
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


# ----------------------------------------------------------------------- easing

def ease(kind, t):
    """Spec-side easing. 'in' means accelerate, whatever the engine calls it."""
    t = max(0.0, min(1.0, t))
    if kind == "linear":
        return t
    if kind == "constant":
        return 0.0 if t < 1.0 else 1.0
    if kind == "in":
        return t * t * t
    if kind == "out":
        return 1.0 - (1.0 - t) ** 3
    if kind == "inout":
        return 4.0 * t ** 3 if t < 0.5 else 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0
    if kind == "elastic":
        if t in (0.0, 1.0):
            return t
        return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1.0
    if kind == "bounce":
        n1, d1 = 7.5625, 2.75
        if t < 1 / d1:
            return n1 * t * t
        if t < 2 / d1:
            t -= 1.5 / d1
            return n1 * t * t + 0.75
        if t < 2.5 / d1:
            t -= 2.25 / d1
            return n1 * t * t + 0.9375
        t -= 2.625 / d1
        return n1 * t * t + 0.984375
    return t


# ------------------------------------------------------------------------- specs

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize(spec):
    spec = dict(spec)
    spec.setdefault("rig", "R15")
    spec.setdefault("fps", 30)
    spec.setdefault("loop", False)
    spec.setdefault("priority", "Action")
    spec.setdefault("grounded", True)
    spec.setdefault("locomotion", False)
    keys = []
    for raw in spec.get("keys", []):
        keys.append({
            "t": float(raw.get("t", 0.0)),
            "ease": str(raw.get("ease", "inout")),
            "pose": dict(raw.get("pose", {})),
            "root": tuple(float(v) for v in raw.get("root", (0.0, 0.0, 0.0))),
        })
    keys.sort(key=lambda k: k["t"])
    spec["keys"] = keys
    if "duration" not in spec and keys:
        spec["duration"] = keys[-1]["t"]
    spec["duration"] = float(spec.get("duration", 1.0))
    return spec


def load_rig(path, default_name="R15"):
    if not path:
        return default_name, RIGS.get(default_name, R15)
    data = load_json(path)
    name = data.get("name", Path(path).stem)
    joints = {}
    for part, value in data["joints"].items():
        if isinstance(value, dict):
            joints[part] = (value.get("parent"), tuple(float(v) for v in value.get("offset", (0, 0, 0))))
        else:
            joints[part] = (value[0], tuple(float(v) for v in value[1]))
    return name, joints


def key_rotations(spec, rig=None):
    """Every key as {joint: rotation matrix}; missing joints are identity."""
    rig = rig or RIGS.get(spec.get("rig", "R15"), R15)
    out = []
    for key in spec["keys"]:
        rots = {}
        for joint in rig:
            value = key["pose"].get(joint, (0.0, 0.0, 0.0))
            if isinstance(value, dict):
                value = (value.get("x", 0.0), value.get("y", 0.0), value.get("z", 0.0))
            rots[joint] = euler_matrix(float(value[0]), float(value[1]), float(value[2]))
        out.append(rots)
    return out


def sample_rotations(spec, t, rig=None):
    """Rotations at an arbitrary time, slerped with the destination key's ease."""
    rig = rig or RIGS.get(spec.get("rig", "R15"), R15)
    keys = spec["keys"]
    if not keys:
        return {joint: IDENT for joint in rig}
    if t <= keys[0]["t"]:
        return key_rotations({**spec, "keys": [keys[0]]}, rig)[0]
    if t >= keys[-1]["t"]:
        return key_rotations({**spec, "keys": [keys[-1]]}, rig)[0]
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        if k0["t"] <= t <= k1["t"]:
            span = k1["t"] - k0["t"]
            u = 0.0 if span <= EPS else (t - k0["t"]) / span
            e = ease(k1["ease"], u)
            a = key_rotations({**spec, "keys": [k0]}, rig)[0]
            b = key_rotations({**spec, "keys": [k1]}, rig)[0]
            return {joint: slerp(a[joint], b[joint], e) for joint in a}
    return key_rotations({**spec, "keys": [keys[-1]]}, rig)[0]


def world_of(rig, rots, root=(0.0, 0.0, 0.0)):
    """{joint: (rotation, world position)} from rest offsets, rotations and root."""
    out = {}
    for part, (parent, offset) in rig.items():
        local = rots.get(part, IDENT)
        if parent is None:
            out[part] = (local, tuple(float(offset[i]) + float(root[i]) for i in range(3)))
        else:
            pr, pt = out.get(parent, (IDENT, (0.0, 0.0, 0.0)))
            out[part] = (matmul(pr, local), matadd(matvec(pr, offset), pt))
    return out


def sample_root(spec, t):
    """Root translation at an arbitrary time, lerped with the destination ease."""
    keys = spec["keys"]
    if not keys:
        return (0.0, 0.0, 0.0)
    if t <= keys[0]["t"]:
        return keys[0].get("root", (0.0, 0.0, 0.0))
    if t >= keys[-1]["t"]:
        return keys[-1].get("root", (0.0, 0.0, 0.0))
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        if k0["t"] <= t <= k1["t"]:
            span = k1["t"] - k0["t"]
            u = 0.0 if span <= EPS else (t - k0["t"]) / span
            e = ease(k1["ease"], u)
            a, b = k0.get("root", (0.0, 0.0, 0.0)), k1.get("root", (0.0, 0.0, 0.0))
            return tuple(a[j] + (b[j] - a[j]) * e for j in range(3))
    return keys[-1].get("root", (0.0, 0.0, 0.0))


def soles(rig_name, rig, world):
    drop = SOLE_DROP.get(rig_name, 0.25)
    out = {}
    for foot in FOOT_PARTS.get(rig_name, ("LeftFoot", "RightFoot")):
        rot, pos = world[foot]
        out[foot] = matadd(pos, matvec(rot, (0.0, -drop, 0.0)))
    return out


def validate(spec, rig_name=None, rig=None):
    """Return (errors, warnings, stats). Codes are stable so a gate can cite them."""
    errors, warnings = [], []
    rig_name = rig_name or spec.get("rig", "R15")
    rig = rig or RIGS.get(rig_name)
    keys = spec.get("keys", [])

    if not str(spec.get("name", "")).strip():
        errors.append("E001 name is empty")
    if rig is None:
        errors.append(f"E002 unknown rig '{rig_name}' (known: {', '.join(RIGS)})")
        rig = R15
    if not keys:
        errors.append("E003 no keys")
        return errors, warnings, {"duration": 0.0, "frames": 0, "keys": 0}
    if spec["fps"] <= 0 or spec["fps"] > 240:
        errors.append("E004 fps must be between 1 and 240")
    if spec["duration"] <= 0:
        errors.append("E005 duration must be greater than 0")
    if spec["priority"] not in PRIORITIES:
        errors.append(f"E006 unknown priority '{spec['priority']}'")
    if abs(keys[0]["t"]) > EPS:
        errors.append(f"E007 first key must be at t=0 (it is {keys[0]['t']:g})")
    for i in range(1, len(keys)):
        if keys[i]["t"] <= keys[i - 1]["t"] + EPS:
            errors.append(f"E008 key times must strictly increase (index {i})")
    last = keys[-1]["t"]
    if last > spec["duration"] + EPS:
        errors.append(f"E009 last key {last:g}s is past duration {spec['duration']:g}s")
    elif last < spec["duration"] - 0.05:
        warnings.append(f"W001 last key {last:g}s holds for {spec['duration'] - last:.2f}s")

    joints_used = set()
    for i, key in enumerate(keys):
        if key["ease"] not in EASE_INTENTS:
            errors.append(f"E010 key {i} has unknown ease '{key['ease']}'")
        root = key.get("root", (0.0, 0.0, 0.0))
        if len(root) != 3:
            errors.append(f"E017 key {i} root must be three numbers")
        elif max(abs(v) for v in root) > 5.0:
            warnings.append(f"W005 key {i} moves the root {max(abs(v) for v in root):.1f} studs")
        for joint, value in key["pose"].items():
            if joint not in rig:
                errors.append(f"E011 unknown joint '{joint}' for {rig_name}")
                continue
            try:
                xyz = [float(v) for v in value] if not isinstance(value, dict) else [
                    float(value.get("x", 0.0)), float(value.get("y", 0.0)), float(value.get("z", 0.0))
                ]
            except (TypeError, ValueError):
                errors.append(f"E012 joint '{joint}' needs three numbers")
                continue
            if len(xyz) != 3:
                errors.append(f"E013 joint '{joint}' needs three numbers")
                continue
            if max(abs(v) for v in xyz) > 180.0:
                warnings.append(f"W002 {joint} exceeds 180 deg ({max(abs(v) for v in xyz):.0f})")
            if any(abs(v) > 1e-9 for v in xyz):
                joints_used.add(joint)

    markers = spec.get("markers", [])
    seen = set()
    for m in markers:
        name = str(m.get("name", ""))
        if not name or name in seen:
            errors.append(f"E014 marker names must be unique and non-empty ('{name}')")
        seen.add(name)
        if not (0.0 <= float(m.get("t", -1)) <= spec["duration"] + EPS):
            errors.append(f"E015 marker '{name}' is outside the clip")

    rotations = key_rotations(spec)
    seam = 0.0
    if spec["loop"]:
        for joint in rig:
            seam = max(seam, angle_between(rotations[0][joint], rotations[-1][joint]))
        if seam > 15.0:
            errors.append(f"E016 loop seam is {seam:.1f} deg (limit 15)")
        elif seam > 8.0:
            warnings.append(f"W003 loop seam is {seam:.1f} deg")

    max_speed = 0.0
    worst = ""
    for i in range(1, len(keys)):
        dt = keys[i]["t"] - keys[i - 1]["t"]
        if dt <= EPS:
            continue
        for joint in rig:
            deg = angle_between(rotations[i - 1][joint], rotations[i][joint])
            speed = deg / dt
            if speed > max_speed:
                max_speed, worst = speed, joint
    if max_speed > 2000.0:
        warnings.append(f"W004 {worst} snaps at {max_speed:.0f} deg/s")

    frames = int(round(spec["duration"] * spec["fps"])) + 1
    stats = {
        "duration": spec["duration"],
        "frames": frames,
        "fps": spec["fps"],
        "keys": len(keys),
        "joints_used": len(joints_used),
        "max_speed_dps": round(max_speed, 1),
        "fastest_joint": worst,
        "loop_seam_deg": round(seam, 2),
        "markers": len(markers),
        "root_travel": round(max((max(abs(v) for v in k.get("root", (0, 0, 0))) for k in keys), default=0.0), 3),
    }
    return errors, warnings, stats


def report(spec, errors, warnings, stats):
    return {
        "name": spec.get("name", ""),
        "rig": spec.get("rig", "R15"),
        "priority": spec.get("priority", "Action"),
        "loop": bool(spec.get("loop")),
        "grounded": bool(spec.get("grounded", True)),
        "locomotion": bool(spec.get("locomotion", False)),
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
    }
