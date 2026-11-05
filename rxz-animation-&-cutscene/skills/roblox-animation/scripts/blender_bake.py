"""Inside Blender: bake an armature's evaluated pose into an rxz spec.

Run through the host, not directly:

    py scripts/blender.py bake rig.blend mapping.json --out clip.json

Reads the final pose matrices, so IK, constraints, drivers and NLA all count -
no need to bake actions first. Writes the same JSON spec the engine-native path
uses, so lint, fk, preview, build and verify apply unchanged.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix


LIMBS = ("UpperArm", "LowerArm", "Hand", "UpperLeg", "LowerLeg", "Foot")


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--mapping", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--start", type=int)
    p.add_argument("--end", type=int)
    p.add_argument("--name")
    p.add_argument("--loop", action="store_true")
    p.add_argument("--locomotion", action="store_true")
    p.add_argument("--priority")
    return p.parse_args(argv)


def axis_for(part, overrides):
    if part in overrides:
        return [float(v) for v in overrides[part]]
    # A Blender limb bone points down its own Y; Roblox's joint frame is that
    # frame turned 180 degrees about Z. Bodies and heads share Roblox's frame.
    return [-1.0, -1.0, 1.0] if part.endswith(LIMBS) else [1.0, 1.0, 1.0]


def main():
    a = parse_args()
    mapping = json.loads(Path(a.mapping).read_text(encoding="utf-8"))
    bones = mapping.get("bones") or {}
    if not bones:
        raise SystemExit("mapping has no bones")

    obj = bpy.data.objects.get(mapping.get("armature", ""))
    if obj is None:
        armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
        if not armatures:
            raise SystemExit("no armature in this .blend")
        obj = armatures[0]
    if obj.type != "ARMATURE":
        raise SystemExit(f"{obj.name} is not an armature")

    mapped = set(bones.values())
    for part, name in bones.items():
        if name not in obj.data.bones:
            raise SystemExit(f"bone '{name}' (for {part}) is not in {obj.name}")
        parent = obj.data.bones[name].parent
        if parent is not None and parent.name not in mapped:
            raise SystemExit(
                f"bone '{name}' has unmapped parent '{parent.name}': map every bone in the chain"
            )

    scene = bpy.context.scene
    start = a.start if a.start is not None else scene.frame_start
    end = a.end if a.end is not None else scene.frame_end
    if end <= start:
        raise SystemExit(f"bad frame range {start}-{end}")
    fps = int(round(scene.render.fps / max(scene.render.fps_base, 1e-6)))
    if fps <= 0:
        raise SystemExit("the scene has no fps")

    # Rest frames, armature space, relative to each bone's parent.
    rest_local = {}
    for part, name in bones.items():
        bone = obj.data.bones[name]
        rot = bone.matrix_local.to_3x3()
        if bone.parent:
            rot = bone.parent.matrix_local.to_3x3().transposed() @ rot
        rest_local[part] = rot

    axes = {part: axis_for(part, mapping.get("axis") or {}) for part in bones}
    flips = {
        part: Matrix(((axes[part][0], 0, 0), (0, axes[part][1], 0), (0, 0, axes[part][2])))
        for part in bones
    }
    # Conjugate the delta into the Roblox joint frame: F * D * F^-1.
    flips_t = {part: flips[part].transposed() for part in bones}

    root_part = "HumanoidRootPart" if "HumanoidRootPart" in bones else None
    root_bone = obj.data.bones[bones[root_part]] if root_part else None
    root_pose = obj.pose.bones[bones[root_part]] if root_part else None
    scale = float(mapping.get("studs_per_unit", 1.0))
    world = obj.matrix_world.copy()

    keys = []
    seen = set()
    gimbal_parts = set()
    print(f"baking {obj.name}: frames {start}-{end} at {fps} fps, {len(bones)} joints")

    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {}
        for part, name in bones.items():
            pb = obj.pose.bones[name]
            posed = pb.matrix.to_3x3()
            if pb.parent:
                posed = pb.parent.matrix.to_3x3().transposed() @ posed
            delta = rest_local[part].transposed() @ posed
            local = flips[part] @ delta @ flips_t[part]
            e = local.to_euler("XYZ")
            if abs(math.degrees(e.y)) > 85.0:
                gimbal_parts.add(part)
            pose[part] = [round(math.degrees(e.x), 2),
                          round(math.degrees(e.y), 2),
                          round(math.degrees(e.z), 2)]

        root = [0.0, 0.0, 0.0]
        if root_bone is not None:
            offset = (world @ root_pose.head) - (world @ root_bone.head_local)
            # Blender world is Z up, -Y forward; Roblox is Y up, -Z forward.
            root = [round(offset.x * scale, 3), round(offset.z * scale, 3),
                    round(-offset.y * scale, 3)]

        key = {"t": round((frame - start) / fps, 4), "ease": "linear", "pose": pose}
        if any(abs(v) > 1e-6 for v in root):
            key["root"] = root
        keys.append(key)
        seen.add(tuple(tuple(pose[p]) for p in sorted(pose)))

    if len(seen) == 1:
        print("WARNING: every frame is identical. The armature's action is probably "
              "empty, or the keys went into a new action instead of the existing one.")
    if gimbal_parts:
        print("NOTE: near-gimbal lock on " + ", ".join(sorted(gimbal_parts)) +
              "; check those frames on the contact sheet.")

    name = a.name or Path(bpy.data.filepath).stem or "BlenderClip"
    spec = {
        "name": name,
        "rig": mapping.get("rig", "r15"),
        "fps": fps,
        "duration": round((end - start) / fps, 4),
        "loop": bool(a.loop or mapping.get("loop", False)),
        "locomotion": bool(a.locomotion or mapping.get("locomotion", False)),
        "priority": a.priority or mapping.get("priority", "Action"),
        "keys": keys,
    }
    Path(a.out).write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {a.out}: {len(keys)} keys, {len(bones)} joints, {spec['duration']}s, "
          f"priority {spec['priority']}, loop {spec['loop']}")


main()
