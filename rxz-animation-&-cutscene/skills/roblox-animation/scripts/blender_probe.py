"""Inside Blender: inspect an armature and draft a mapping for the baker.

Run through the host, not directly:

    py scripts/blender.py probe rig.blend --out rig-info.json

Writes every armature's bones, its active action, and a best-guess mapping from
Roblox joint names to bone names. The guess is a starting point: check the
duplicates and the `review` flags before baking. Nothing is modified in the
.blend.
"""
import argparse
import json
import sys
from pathlib import Path

import bpy


LIMBS = ("UpperArm", "LowerArm", "Hand", "UpperLeg", "LowerLeg", "Foot")
R15_PARTS = [
    "HumanoidRootPart", "LowerTorso", "UpperTorso", "Head",
    "LeftUpperArm", "LeftLowerArm", "LeftHand",
    "RightUpperArm", "RightLowerArm", "RightHand",
    "LeftUpperLeg", "LeftLowerLeg", "LeftFoot",
    "RightUpperLeg", "RightLowerLeg", "RightFoot",
]
PREFIXES = ("mixamorig:", "mixamorig", "def-", "def_", "org-", "org_",
            "fk_", "fk-", "ik_", "ik-", "mch_", "mch-", "ctrl_", "ctrl-")
PARTS = {
    "upper_arm": "UpperArm", "upperarm": "UpperArm", "arm": "UpperArm",
    "forearm": "LowerArm", "lower_arm": "LowerArm", "lowerarm": "LowerArm",
    "hand": "Hand",
    "thigh": "UpperLeg", "upper_leg": "UpperLeg", "upperleg": "UpperLeg", "leg": "UpperLeg",
    "shin": "LowerLeg", "calf": "LowerLeg", "lower_leg": "LowerLeg", "lowerleg": "LowerLeg",
    "foot": "Foot",
    "hips": "LowerTorso", "pelvis": "LowerTorso", "spine": "LowerTorso",
    "lower_torso": "LowerTorso", "lowertorso": "LowerTorso", "torso": "LowerTorso",
    "chest": "UpperTorso", "upper_torso": "UpperTorso", "uppertorso": "UpperTorso",
    "spine1": "UpperTorso", "spine2": "UpperTorso",
    "head": "Head",
    "root": "HumanoidRootPart", "humanoidrootpart": "HumanoidRootPart",
}
SIDES = ((".l", "Left"), (".r", "Right"), ("_l", "Left"), ("_r", "Right"),
         ("left", "Left"), ("right", "Right"))


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    return p.parse_args(argv)


def suggest(name):
    s = name.lower().replace(" ", "_").replace("-", "_")
    for prefix in PREFIXES:
        if s.startswith(prefix):
            s = s[len(prefix):]
    side = ""
    for prefix, word in (("left", "Left"), ("right", "Right")):
        if s.startswith(prefix):
            side, s = word, s[len(prefix):]
            break
    if not side:
        for suffix, word in SIDES:
            if s.endswith(suffix):
                side, s = word, s[:-len(suffix)]
                break
    part = PARTS.get(s)
    if not part:
        return None
    return (side + part) if side else part


def main():
    a = parse_args()
    if not bpy.data.filepath:
        raise SystemExit("save the .blend first: probe needs a file, not an unsaved scene")
    scene = bpy.context.scene
    info = {
        "blend": bpy.data.filepath,
        "fps": round(scene.render.fps / max(scene.render.fps_base, 1e-6), 3),
        "frames": [scene.frame_start, scene.frame_end],
        "armatures": [],
    }
    for obj in [o for o in bpy.data.objects if o.type == "ARMATURE"]:
        bones = []
        candidates = {}
        for b in obj.data.bones:
            pb = obj.pose.bones[b.name]
            constraints = [c.type for c in pb.constraints]
            part = suggest(b.name)
            direction = (b.tail_local - b.head_local).normalized()
            bones.append({
                "name": b.name,
                "parent": b.parent.name if b.parent else None,
                "deform": b.use_deform,
                "head": [round(v, 4) for v in b.head_local],
                "tail": [round(v, 4) for v in b.tail_local],
                "direction": [round(v, 3) for v in direction],
                "constraints": constraints,
                "suggests": part,
            })
            if part:
                candidates.setdefault(part, []).append({
                    "bone": b.name, "deform": b.use_deform,
                    "controls": bool(constraints) or not b.use_deform,
                })
        mapping = {}
        review = []
        for part in R15_PARTS:
            found = candidates.get(part, [])
            if not found:
                continue
            found.sort(key=lambda c: (c["controls"], c["bone"]))
            mapping[part] = found[0]["bone"]
            if len(found) > 1:
                review.append({"part": part, "chose": found[0]["bone"],
                               "also": [c["bone"] for c in found[1:]]})
        action = obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else None
        nla = len(obj.animation_data.nla_tracks) if obj.animation_data else 0
        info["armatures"].append({
            "name": obj.name,
            "bones": bones,
            "action": action,
            "nla_tracks": nla,
            "mapping": {
                "rig": "r15",
                "armature": obj.name,
                "studs_per_unit": 1.0,
                "priority": "Action",
                "bones": mapping,
                "axis": {},
            },
            "missing": [p for p in R15_PARTS if p not in mapping],
            "review": review,
        })

    Path(a.out).write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    for arm in info["armatures"]:
        print(f"armature {arm['name']}: {len(arm['bones'])} bones, action={arm['action']}, nla={arm['nla_tracks']}")
        print(f"  mapped {len(arm['mapping']['bones'])}/{len(R15_PARTS)}, missing: {arm['missing'] or 'none'}")
        for r in arm["review"]:
            print(f"  check {r['part']}: chose {r['chose']}, also {r['also']}")
    if not info["armatures"]:
        raise SystemExit("no armature found in this .blend")
    print(f"wrote {a.out}")


main()
