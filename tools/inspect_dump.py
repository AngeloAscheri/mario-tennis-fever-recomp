"""Describe a Mario Tennis Fever dump without writing anything from it: version, modules, segments, payload.

Why: most early reports and research start from "what does your dump look like". This prints the facts that are
safe to paste in an issue (build ids, sizes, SDK version, entropy), never bytes of the game.

Usage: uv run tools/inspect_dump.py <exefs folder>
       uv run tools/inspect_dump.py "<dump>/updates/327680/exefs"
"""

import argparse
import collections
import math
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "recomp"))

from layout import ORDER  # noqa: E402
from nso import Nso  # noqa: E402
from versions import detect  # noqa: E402

SEGMENTS = ("text", "rodata", "data")


def entropy(buf: bytes) -> float:
    if not buf:
        return 0.0
    counts = collections.Counter(buf)
    return -sum(n / len(buf) * math.log2(n / len(buf)) for n in counts.values())


def describe(path: Path) -> None:
    raw = path.read_bytes()
    nso = Nso(str(path))
    flags = struct.unpack_from("<I", raw, 0xC)[0]
    print(f"{path.name}: build id {raw[0x40:0x60].hex()[:16]}, image {nso.size / 2**20:.1f} MiB, flags {flags:#x}")
    for i, name in enumerate(SEGMENTS):
        _, mem_off, size, _ = struct.unpack_from("<IIII", raw, 0x10 + i * 0x10)
        seg = nso.image[mem_off:mem_off + size]
        compressed = bool(flags & (1 << i))
        print(f"  .{name:<6} at {mem_off:#9x}, {size / 2**20:6.2f} MiB, lz4 {'yes' if compressed else 'no '}, "
              f"entropy {entropy(seg[:4 << 20]):.2f} bits/byte")
    needed = [n for n in nso.needed]
    if needed:
        print(f"  needs: {', '.join(needed)}")
    text = nso.image.decode("latin-1")
    sdk = sorted(set(re.findall(r"sdk_version: ([0-9.]+)", text)))
    if sdk:
        print(f"  NintendoSDK {', '.join(sdk)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("exefs", type=Path)
    args = ap.parse_args()
    try:
        v = detect(args.exefs)
        print(f"Mario Tennis Fever {v.name} (title version {v.number})")
    except (FileNotFoundError, ValueError) as e:
        print(f"unknown version: {e}")
    for name in ORDER:
        if (args.exefs / name).is_file():
            describe(args.exefs / name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
