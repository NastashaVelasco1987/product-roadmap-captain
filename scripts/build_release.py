#!/usr/bin/env python3
"""Build dist/product-roadmap-captain.zip, the file people upload to the Claude app.

The zip holds one folder, product-roadmap-captain/, with SKILL.md at its top level,
which is the layout the Claude app expects. Uses the Python standard library only.

    python3 scripts/build_release.py
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "product-roadmap-captain"
OUTPUT = ROOT / "dist" / "product-roadmap-captain.zip"
SKIPPED_NAMES = {".DS_Store", "Thumbs.db"}


def main() -> int:
    if not (SKILL_DIR / "SKILL.md").is_file():
        print("skills/product-roadmap-captain/SKILL.md not found", file=sys.stderr)
        return 1

    OUTPUT.parent.mkdir(exist_ok=True)
    files = sorted(p for p in SKILL_DIR.rglob("*") if p.is_file() and p.name not in SKIPPED_NAMES)

    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, Path(SKILL_DIR.name) / path.relative_to(SKILL_DIR))

    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(files)} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
