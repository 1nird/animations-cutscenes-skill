"""Zip a staging folder with forward-slash paths.

PowerShell's Compress-Archive writes backslashes, which extract as literal
backslash filenames on macOS and Linux. zipfile always uses forward slashes,
and keeps the executable bit on the macOS installer.
"""
import sys
import zipfile
from pathlib import Path

stage = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()

if not stage.is_dir():
    raise SystemExit(f"no staging folder at {stage}")

files = sorted(path for path in stage.rglob("*") if path.is_file())
if not files:
    raise SystemExit(f"nothing to zip in {stage}")

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in files:
        info = zipfile.ZipInfo(path.relative_to(stage).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        mode = 0o755 if path.suffix in (".command", ".sh") else 0o644
        info.external_attr = mode << 16
        archive.writestr(info, path.read_bytes())

print(f"zipped {len(files)} files -> {out.name}")
