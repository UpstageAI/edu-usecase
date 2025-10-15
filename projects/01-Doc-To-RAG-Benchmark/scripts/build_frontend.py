#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
STATIC_DIR = ROOT / "src" / "pypi_test_app" / "static"


def run(command: list[str], cwd: Path) -> None:
    print(f"→ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    if not FRONTEND_DIR.exists():
        print("Frontend directory does not exist. Run the Vite scaffold first.", file=sys.stderr)
        return 1

    run(["npm", "install"], FRONTEND_DIR)
    run(["npm", "run", "build"], FRONTEND_DIR)

    if STATIC_DIR.exists():
        shutil.rmtree(STATIC_DIR)
    shutil.copytree(DIST_DIR, STATIC_DIR)
    print(f"Copied {DIST_DIR} → {STATIC_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
