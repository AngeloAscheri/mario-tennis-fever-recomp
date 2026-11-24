"""Puts recomp/ and tools/ on the import path, as the scripts do for themselves."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("recomp", "tools", "tools/cpu"):
    sys.path.insert(0, str(ROOT / sub))
