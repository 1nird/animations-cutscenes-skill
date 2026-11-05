"""Render a contact sheet from a pose spec, so the clip can be looked at.

    py scripts/preview.py examples/punch.json --out out/punch-sheet.png

Two views per tile: side (forward is right) and front. Nothing here decides
whether the animation is good; it decides whether the pose data is what it
claims to be. Judge the sheet against the intent sentence, not itself.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import animlib as A  # noqa: E402
import fk  # noqa: E402

BG = (20, 16, 28)
TILE = (30, 24, 40)
GRID = (48, 40, 60)
GROUND = (110, 231, 160)
INK = (236, 230, 245)
DIM = (150, 140, 165)
LEFT = (255, 107, 157)
RIGHT = (89, 194, 255)
HEAD = (245, 240, 252)

BONES = [
    ("HumanoidRootPart", "LowerTorso", 0.26),
    ("LowerTorso", "UpperTorso", 0.26),
    ("UpperTorso", "Head", 0.18),
    ("UpperTorso", "RightUpperArm", 0.17),
    ("RightUpperArm", "RightLowerArm", 0.16),
    ("RightLowerArm", "RightHand", 0.15),
    ("UpperTorso", "LeftUpperArm", 0.17),
    ("LeftUpperArm", "LeftLowerArm", 0.16),
    ("LeftLowerArm", "LeftHand", 0.15),
    ("LowerTorso", "RightUpperLeg", 0.19),
    ("RightUpperLeg", "RightLowerLeg", 0.18),
    ("RightLowerLeg", "RightFoot", 0.16),
    ("LowerTorso", "LeftUpperLeg", 0.19),
    ("LeftUpperLeg", "LeftLowerLeg", 0.18),
    ("LeftLowerLeg", "LeftFoot", 0.16),
]


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def project(point, view):
    if view == "side":
        return (-point[2], point[1])
    return (point[0], point[1])


def bounds(frames, view):
    xs, ys = [], []
    for frame in frames:
        for _, (_, pos) in frame["world"].items():
            u, v = project(pos, view)
            xs.append(u)
            ys.append(v)
        for pos in frame["soles"].values():
            u, v = project(pos, view)
            xs.append(u)
            ys.append(v)
    return min(xs), max(xs), min(ys), max(ys)


def draw_frame(draw, frame, view, box, data_bounds, scale):
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    u0, u1, v0, v1 = data_bounds
    uc = (u0 + u1) / 2
    vc = (v0 + v1) / 2

    def at(point):
        u, v = project(point, view)
        return (cx + (u - uc) * scale, cy - (v - vc) * scale)

    # ground line and one-stud grid
    gy = at((0, 0, 0))[1]
    for stud in range(-2, 3):
        u = at((stud, 0, 0))[0] if view == "front" else at((0, 0, -stud))[0]
        draw.line((u, y0 + 6, u, y1 - 6), fill=GRID, width=1)
    draw.line((x0 + 4, gy, x1 - 4, gy), fill=GROUND, width=2)

    world = frame["world"]

    def segment(a, b, color, width):
        pa, pb = at(world[a][1]), at(world[b][1])
        draw.line((*pa, *pb), fill=color, width=max(2, int(width * scale)), joint="curve")

    for a, b, width in BONES:
        color = RIGHT if a.startswith("Right") or b.startswith("Right") else (
            LEFT if a.startswith("Left") or b.startswith("Left") else INK)
        if a in world and b in world:
            segment(a, b, color, width)

    head = at(world["Head"][1])
    radius = max(4, int(0.42 * scale))
    draw.ellipse((head[0] - radius, head[1] - radius * 1.15,
                  head[0] + radius, head[1] + radius * 1.15), outline=HEAD, width=2)

    for foot, pos in frame["soles"].items():
        px, py = at(pos)
        if pos[1] <= fk.CONTACT:
            draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=GROUND)
        else:
            draw.ellipse((px - 2, py - 2, px + 2, py + 2), outline=DIM)

    label = f"f{frame['frame']:02d}  {frame['t']:.2f}s"
    draw.text((x0 + 8, y0 + 8), label, fill=DIM, font=font(13))


def render(spec, rig, out, cols=6, count=24, tile=240, view="both"):
    frames = fk.sample(spec, rig)
    total = len(frames)
    if total > count:
        step = (total - 1) / (count - 1)
        frames = [frames[int(round(i * step))] for i in range(count)]
    views = ["side", "front"] if view == "both" else [view]
    rows = math.ceil(len(frames) / cols)
    header = 58
    sheet = Image.new("RGB", (cols * tile, header + rows * tile * len(views)), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((16, 12), f"{spec['name']}  {spec['duration']:.2f}s  {spec['fps']}fps  "
                        f"{len(spec['keys'])} keys  {spec.get('priority', 'Action')}",
              fill=INK, font=font(20))
    draw.text((16, 34), "side view (forward right) / front view - judge against the intent",
              fill=DIM, font=font(13))

    for vi, name in enumerate(views):
        data_bounds = bounds(frames, name)
        u0, u1, v0, v1 = data_bounds
        pad = 0.55
        span_u = max(0.5, u1 - u0 + pad * 2)
        span_v = max(0.5, v1 - v0 + pad * 2)
        scale = min((tile - 28) / span_u, (tile - 30) / span_v)
        data_bounds = (u0 - pad, u1 + pad, v0 - pad, v1 + pad)
        for i, frame in enumerate(frames):
            col, row = i % cols, i // cols
            x0 = col * tile
            y0 = header + vi * rows * tile + row * tile
            draw.rectangle((x0, y0, x0 + tile - 1, y0 + tile - 1), fill=TILE, outline=GRID)
            draw_frame(draw, frame, name, (x0, y0, x0 + tile, y0 + tile), data_bounds, scale)
            if vi == 0:
                draw.text((x0 + 8, y0 + tile - 20), name, fill=GRID, font=font(11))

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out, sheet.size, len(frames) * len(views)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Contact sheet for a pose spec.")
    parser.add_argument("spec")
    parser.add_argument("--out", default="sheet.png")
    parser.add_argument("--rig")
    parser.add_argument("--cols", type=int, default=6)
    parser.add_argument("--frames", type=int, default=24)
    parser.add_argument("--tile", type=int, default=240)
    parser.add_argument("--view", choices=("both", "side", "front"), default="both")
    args = parser.parse_args(argv)

    spec = A.normalize(A.load_json(args.spec))
    rig_name, rig = A.load_rig(args.rig, spec.get("rig", "R15"))
    errors, _, _ = A.validate(spec, rig_name=rig_name, rig=rig)
    if errors:
        for e in errors:
            print(f"FAIL  {e}", file=sys.stderr)
        return 1
    out, size, frames = render(spec, rig, args.out, args.cols, args.frames, args.tile, args.view)
    print(f"{out}  {size[0]}x{size[1]}  {frames} views from {spec['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
