"""Forward kinematics for a pose spec: where the feet actually are.

    py scripts/fk.py examples/run.json
    py scripts/fk.py examples/punch.json --json --out out/fk.report.json

Samples every frame, slerps the way the engine does, and reports the lowest
sole, contact runs and how far a planted foot travels. A pose that looks fine
in numbers but floats or scrapes shows up here.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import animlib as A  # noqa: E402

CONTACT = 0.06      # a sole this close to y=0 counts as planted
FLOOR = -0.06       # deeper than this is through the floor
SLIP = 0.25         # studs a planted foot may travel in a non-locomotion clip


def sample(spec, rig):
    count = int(round(spec["duration"] * spec["fps"])) + 1
    out = []
    for frame in range(count):
        t = min(frame / spec["fps"], spec["duration"])
        world = A.world_of(rig, A.sample_rotations(spec, t, rig), A.sample_root(spec, t))
        soles = A.soles(spec.get("rig", "R15"), rig, world)
        out.append({"frame": frame, "t": t, "world": world, "soles": soles})
    return out


def analyse(spec, rig):
    frames = sample(spec, rig)
    feet = list(frames[0]["soles"].keys())
    warnings = []

    lowest = min((pos[1], foot, f["frame"]) for f in frames for foot, pos in f["soles"].items())
    highest = max(pos[1] for f in frames for pos in f["soles"].values())

    runs = {foot: [] for foot in feet}
    open_runs = {foot: [] for foot in feet}
    for frame in frames:
        for foot in feet:
            pos = frame["soles"][foot]
            if pos[1] <= CONTACT:
                open_runs[foot].append((frame["frame"], pos))
            elif open_runs[foot]:
                runs[foot].append(open_runs[foot])
                open_runs[foot] = []
    for foot in feet:
        if open_runs[foot]:
            runs[foot].append(open_runs[foot])

    contact = {}
    max_travel = 0.0
    for foot in feet:
        travels = []
        for run in runs[foot]:
            a, b = run[0][1], run[-1][1]
            travels.append(math.dist((a[0], a[2]), (b[0], b[2])))
        longest = max((len(r) for r in runs[foot]), default=0) / spec["fps"]
        peak = max(travels, default=0.0)
        max_travel = max(max_travel, peak)
        contact[foot] = {
            "runs": len(runs[foot]),
            "longest_s": round(longest, 3),
            "travel": round(peak, 3),
        }

    root = [f["world"]["HumanoidRootPart"][1][1] for f in frames]

    if lowest[0] < FLOOR:
        warnings.append(f"W101 {lowest[1]} passes through the floor by {abs(lowest[0]):.2f} studs "
                        f"at frame {lowest[2]}")
    if spec.get("grounded", True) and lowest[0] > 0.10:
        warnings.append(f"W102 nothing is on the ground: lowest sole {lowest[0]:.2f} studs")
    if not spec.get("locomotion", False) and max_travel > SLIP:
        warnings.append(f"W103 a planted foot slides {max_travel:.2f} studs "
                        f"(limit {SLIP:.2f}); check hip twist and ankle counter-rotation")
    if spec.get("locomotion", False) and sum(c["runs"] for c in contact.values()) < 2:
        warnings.append("W104 locomotion clip has fewer than two ground contacts")
    if spec.get("locomotion", False):
        warnings.append("N101 in-place locomotion: foot travel is stride, not slip")

    report = {
        "name": spec["name"],
        "rig": spec.get("rig", "R15"),
        "frames": len(frames),
        "fps": spec["fps"],
        "lowest_sole": round(lowest[0], 3),
        "lowest_foot": lowest[1],
        "lowest_frame": lowest[2],
        "highest_sole": round(highest, 3),
        "root_y": [round(min(root), 3), round(max(root), 3)],
        "contact": contact,
        "max_travel": round(max_travel, 3),
        "warnings": warnings,
        "errors": [],
    }
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ground-contact check for a pose spec.")
    parser.add_argument("spec")
    parser.add_argument("--rig", help="rig.json (default: built-in R15)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", help="write the report here")
    args = parser.parse_args(argv)

    spec = A.normalize(A.load_json(args.spec))
    rig_name, rig = A.load_rig(args.rig, spec.get("rig", "R15"))
    errors, _, _ = A.validate(spec, rig_name=rig_name, rig=rig)
    if errors:
        for e in errors:
            print(f"FAIL  {e}", file=sys.stderr)
        return 1

    report = analyse(spec, rig)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{spec['name']}  {report['frames']} frames @ {spec['fps']}fps  "
              f"root y {report['root_y'][0]:.2f}-{report['root_y'][1]:.2f}")
        print(f"lowest sole {report['lowest_sole']:+.2f} ({report['lowest_foot']}, "
              f"frame {report['lowest_frame']})  highest {report['highest_sole']:.2f}")
        for foot, data in report["contact"].items():
            print(f"  {foot}: {data['runs']} contact(s), longest {data['longest_s']:.2f}s, "
                  f"travel {data['travel']:.2f}")
        for w in report["warnings"]:
            print(f"NOTE  {w}")
        print("OK" if not report["warnings"] or all(w.startswith("N") for w in report["warnings"])
              else f"{len([w for w in report['warnings'] if w.startswith('W')])} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
