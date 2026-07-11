#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.manuals import MANUALS, build_manual_pdf  # noqa: E402


def main() -> int:
    for key in MANUALS:
        output_path = build_manual_pdf(key)
        print(output_path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
