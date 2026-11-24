"""Write stand-in system shared fonts (nn::pl) from a free font, so the game can start without the console's firmware.

Why: Mario Tennis Fever's engine asks nn::pl for the standard shared font at boot whatever the language (Mario Kart
World only for Chinese and Korean), and the runtime serves the files in build/shared-fonts/ (runtime/sdk/ov/ov_system.c
ov_shared_font_dir). The console's own fonts come from its firmware; this writes the same container, BFTTF, around a
free font instead (Noto Sans, SIL Open Font License, from the system by default). Latin text renders with it; the
Nintendo extension font's button icons and the CJK glyphs are missing until the console's fonts are used instead.

BFTTF: big-endian 32-bit words XORed with a key; word 0 is 0x7f9a0218 ^ key, word 1 the font size ^ key, then the
font, padded to a word, every word XORed with the key (ov_bfttf_size reads it back).

Usage: uv run tools/make_shared_fonts.py [--font /usr/share/fonts/google-noto/NotoSans-Regular.ttf] [--out build/shared-fonts]
"""

import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAGIC = 0x7F9A0218
KEY = 0x49621806  # any key decodes; this is the one the console's files use
FILES = ("0-standard.bfttf", "1-chinese-simplified.bfttf", "2-chinese-simplified-extension.bfttf",
         "3-chinese-traditional.bfttf", "4-korean.bfttf", "5-nintendo-extension.bfttf")
DEFAULT_FONT = Path("/usr/share/fonts/google-noto/NotoSans-Regular.ttf")


def bfttf(font: bytes, key: int = KEY) -> bytes:
    if font[:4] not in (b"\x00\x01\x00\x00", b"OTTO"):
        raise ValueError("not a TrueType or OpenType font")
    font += bytes(-len(font) % 4)
    words = struct.unpack(f">{len(font) // 4}I", font)
    head = (MAGIC ^ key, len(font) ^ key)
    return struct.pack(f">{2 + len(words)}I", *head, *(w ^ key for w in words))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--font", type=Path, default=DEFAULT_FONT)
    ap.add_argument("--out", type=Path, default=ROOT / "build/shared-fonts")
    args = ap.parse_args()
    data = bfttf(args.font.read_bytes())
    args.out.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        (args.out / name).write_bytes(data)
    print(f"{len(FILES)} shared fonts from {args.font.name} ({len(data):,} bytes each) in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
