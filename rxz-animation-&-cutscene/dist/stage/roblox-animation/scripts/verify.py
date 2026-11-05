"""The gate. Reads what the other scripts wrote and refuses to call it done.

    py scripts/verify.py --dir out/

Gates are numbers, not opinions; each one failed at least once in a real build.
A red gate is fixed in the spec, never by relaxing the gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

LIMITS = {
    "seam": 15.0,
    "floor": -0.06,
    "travel": 0.25,
    "asl_min": 1.0,
    "asl_max": 6.0,
}


def read(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gate a generated animation + cutscene.")
    parser.add_argument("--dir", default="out")
    parser.add_argument("--skip-cutscene", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.dir)

    anim = read(root / "anim.report.json")
    fk = read(root / "fk.report.json")
    cut = read(root / "cutscene.report.json")
    rbxmx = list(root.glob("*.rbxmx"))
    luau = list(root.glob("*.luau"))
    sheets = list(root.glob("*.png"))

    gates = []

    def gate(name, ok, detail):
        gates.append({"gate": name, "ok": bool(ok), "detail": detail})

    gate("spec valid", anim and not anim.get("errors"),
         f"{len(anim.get('errors', []))} error(s)" if anim else "no anim.report.json")
    if anim:
        stats = anim.get("stats", {})
        gate("clip length", stats.get("duration", 0) >= 0.1 and stats.get("keys", 0) >= 2,
             f"{stats.get('duration', 0):g}s, {stats.get('keys', 0)} keys")
        seam = stats.get("loop_seam_deg", 0.0)
        gate("loop seam", (not anim.get("loop")) or seam <= LIMITS["seam"],
             f"{seam:g} deg" + (" (loop)" if anim.get("loop") else " (one-shot)"))
    else:
        gate("clip length", False, "no report")
        gate("loop seam", False, "no report")

    if fk:
        low = fk.get("lowest_sole", 0.0)
        gate("foot contact", low >= LIMITS["floor"] and (low <= 0.10 or not fk.get("grounded", True)),
             f"lowest sole {low:+.2f}")
        travel = fk.get("max_travel", 0.0)
        gate("planted foot", fk.get("locomotion") or travel <= LIMITS["travel"],
             f"{travel:.2f} studs" + (" (stride)" if fk.get("locomotion") else ""))
        runs = sum(v.get("runs", 0) for v in fk.get("contact", {}).values())
        gate("ground evidence", (not fk.get("grounded", True)) or runs >= 1,
             f"{runs} contact run(s)")
    else:
        for name in ("foot contact", "planted foot", "ground evidence"):
            gate(name, False, "no fk.report.json (run fk.py)")

    if not args.skip_cutscene:
        gate("cutscene valid", cut and not cut.get("errors"),
             f"{len(cut.get('errors', []))} error(s)" if cut else "no cutscene.report.json")
        asl = (cut or {}).get("stats", {}).get("asl", 0.0)
        gate("cutscene pacing", bool(cut) and LIMITS["asl_min"] <= asl <= LIMITS["asl_max"],
             f"ASL {asl:.1f}s" if cut else "no report")

    gate("artifacts", bool(rbxmx) and bool(luau),
         f"{len(rbxmx)} rbxmx, {len(luau)} luau, {len(sheets)} png")
    gate("contact sheet", bool(sheets), ", ".join(p.name for p in sheets) or "none")

    failed = [g for g in gates if not g["ok"]]
    if args.json:
        print(json.dumps({"gates": gates, "ok": not failed}, indent=2))
    else:
        for g in gates:
            print(f"{'PASS' if g['ok'] else 'FAIL'}  {g['gate']:<16} {g['detail']}")
        print("ALL GATES PASS" if not failed else f"{len(failed)} gate(s) failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
