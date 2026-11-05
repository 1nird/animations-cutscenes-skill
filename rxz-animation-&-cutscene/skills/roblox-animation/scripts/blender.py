"""Optional Blender bridge: probe a rig, bake its motion into a spec.

    py scripts/blender.py check
    py scripts/blender.py probe rig.blend --out rig-info.json
    py scripts/blender.py bake rig.blend mapping.json --out clip.json

Blender is optional. Nothing here runs unless asked; when it is missing the
command exits 2 with install instructions instead of failing deep inside bpy.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "blender_probe.py"
BAKE = HERE / "blender_bake.py"


def find_blender(explicit=None):
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.exists() else None
    env = os.environ.get("BLENDER")
    if env:
        path = Path(env)
        if path.exists():
            return path
    found = shutil.which("blender")
    if found:
        return Path(found)
    candidates = []
    if os.name == "nt":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                     os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
            root = Path(base) / "Blender Foundation"
            if root.is_dir():
                for folder in sorted(root.iterdir(), reverse=True):
                    candidates.append(folder / "blender.exe")
    elif sys.platform == "darwin":
        candidates.append(Path("/Applications/Blender.app/Contents/MacOS/Blender"))
    else:
        candidates += [Path("/usr/bin/blender"), Path("/usr/local/bin/blender"),
                       Path("/snap/bin/blender")]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def require_blender(args):
    blender = find_blender(args.blender)
    if blender is None:
        print("Blender not found. Install 3.6+ and either put it on PATH, set "
              "BLENDER to the executable, or pass --blender <path>.\n"
              "The engine-native path does not need Blender: anim.py, fk.py, "
              "preview.py, cutscene.py and verify.py all run on plain Python.",
              file=sys.stderr)
        raise SystemExit(2)
    return blender


def version(blender):
    proc = subprocess.run([str(blender), "--version"], capture_output=True, text=True)
    first = (proc.stdout or proc.stderr).strip().splitlines()
    return first[0] if first else "unknown"


def run_blender(blender, blend, script, extra):
    cmd = [str(blender), "--background", str(blend), "--python-exit-code", "1",
           "--python", str(script), "--", *extra]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stdout + "\n" + proc.stderr).strip().splitlines()[-25:]
        raise SystemExit("Blender failed:\n" + "\n".join(tail))
    return proc


def cmd_check(args):
    blender = require_blender(args)
    print(f"Blender {version(blender)}")
    print(f"  {blender}")
    print("optional path ready (engine-native scripts need only Python)")


def cmd_probe(args):
    blend = Path(args.blend)
    if not blend.exists():
        raise SystemExit(f"no such .blend: {blend}")
    blender = require_blender(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    run_blender(blender, blend, PROBE, ["--out", str(out.resolve())])
    info = json.loads(out.read_text(encoding="utf-8"))
    for arm in info["armatures"]:
        print(f"  {arm['name']}: {len(arm['bones'])} bones, action={arm['action']}, "
              f"mapped {len(arm['mapping']['bones'])}/{16}")
        if arm["missing"]:
            print(f"    missing: {', '.join(arm['missing'])}")
        for review in arm["review"]:
            print(f"    check {review['part']}: chose {review['chose']}, also {review['also']}")
    print(f"draft mapping: {out} -> armatures[0].mapping (copy it out and fix names)")


def cmd_bake(args):
    blend, mapping = Path(args.blend), Path(args.mapping)
    if not blend.exists():
        raise SystemExit(f"no such .blend: {blend}")
    if not mapping.exists():
        raise SystemExit(f"no such mapping: {mapping}")
    blender = require_blender(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    extra = ["--mapping", str(mapping.resolve()), "--out", str(out.resolve())]
    for flag, value in (("--start", args.start), ("--end", args.end),
                        ("--name", args.name), ("--priority", args.priority)):
        if value is not None:
            extra += [flag, str(value)]
    if args.loop:
        extra.append("--loop")
    if args.locomotion:
        extra.append("--locomotion")
    run_blender(blender, blend, BAKE, extra)

    lint = subprocess.run([sys.executable, str(HERE / "anim.py"), "lint", str(out)],
                          capture_output=True, text=True)
    print(lint.stdout.strip())
    if lint.returncode != 0:
        print((lint.stderr or "").strip(), file=sys.stderr)
        raise SystemExit("baked spec failed lint")


def main():
    parser = argparse.ArgumentParser(description="Optional Blender path for rxz animation")
    parser.add_argument("--blender", help="path to the Blender executable")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="find Blender and print its version")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("probe", help="list armatures/bones and draft a mapping")
    p.add_argument("blend")
    p.add_argument("--out", default="rig-info.json")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("bake", help="bake evaluated bones into an rxz spec")
    p.add_argument("blend")
    p.add_argument("mapping")
    p.add_argument("--out", required=True)
    p.add_argument("--start", type=int)
    p.add_argument("--end", type=int)
    p.add_argument("--name")
    p.add_argument("--loop", action="store_true")
    p.add_argument("--locomotion", action="store_true")
    p.add_argument("--priority")
    p.set_defaults(func=cmd_bake)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
