#!/usr/bin/env python3
"""Generate the database ERD as a PNG from the live schema.

Renders ``backend/docs/erd.png`` straight from the database (``DATABASE_URL_SYNC``)
so the diagram is always an accurate reflection of the real schema — no
hand-drawing, no drift. Re-run it after a migration.

Requirements:
  - system graphviz:   brew install graphviz   (macOS)  /  apt install graphviz (Linux)
  - the optional extra: uv sync --extra erd

Usage:
  uv run python scripts/generate_erd.py
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any

from src.config.settings import get_settings

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

# Ensure the brew/apt graphviz `dot` is discoverable (pygraphviz shells out to it).
for _prefix in ("/opt/homebrew", "/usr/local", "/usr"):
    _bin = Path(_prefix) / "bin"
    if (_bin / "dot").exists():
        os.environ["PATH"] = f"{_bin}{os.pathsep}{os.environ.get('PATH', '')}"
        break

# eralchemy2 is an optional extra (`uv sync --extra erd`) and ships no type stubs.
# Load it dynamically so the import stays at module scope and the call site
# type-checks whether or not the package is installed.
try:
    render_er: Any = importlib.import_module("eralchemy2").render_er
except ImportError:
    render_er = None


def main() -> int:
    if render_er is None:
        print("eralchemy2 is not installed. Run:  uv sync --extra erd", file=sys.stderr)
        return 1

    out = ROOT / "docs" / "erd.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    url = get_settings().database_url_sync
    try:
        render_er(url, str(out))
    except Exception as exc:
        hint = str(exc).lower()
        if any(k in hint for k in ("graphviz", "dot", "cgraph", "pygraphviz")):
            print(
                "Could not render — is system graphviz installed?  "
                "brew install graphviz  (macOS)  /  apt install graphviz  (Linux)",
                file=sys.stderr,
            )
        print(f"ERD generation failed: {exc}", file=sys.stderr)
        return 1

    print(f"ERD written to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
