"""Write stand-in system shared fonts (nn::pl) from a free font, so the game can start without the console's firmware.

Why: Mario Tennis Fever's engine asks nn::pl for the standard shared font at boot whatever the language (Mario Kart
World only for Chinese and Korean), and the runtime serves the files in build/shared-fonts/ (runtime/sdk/ov/ov_system.c
ov_shared_font_dir). The console's own fonts come from its firmware; this writes the same container, BFTTF, around a
free font instead (Noto Sans, SIL Open Font License, from the system by default). Latin text renders with it; the CJK
glyphs are missing until the console's fonts are used instead.

Button icons. The console's Nintendo extension font keeps the controller's buttons in the private use area, and the
game's text names them by code point (the tutorial's "<-/+> Terminar", "Pulsa <R> para añadir más jugadores"). Noto
has none of them, so they came out as "?". The stand-in fonts get icons of our own (drawn here: circles, shoulder
shapes, the font's letters) at the code points whose button is known: A, B, X, Y, L, R, ZL, ZR, SL, SR at U+E0A0-E0A9
and +/- at U+E0B5/E0B6, outlined (libtesla's key table, facts only), and the same buttons filled from U+E0E0, with +/-
at U+E0EF/E0F0 (libtesla's "U+E0E1 Back  U+E0E0 OK"; the game: U+E0F0/U+E0EF beside "Terminar" in the tutorial that
PLUS ends, U+E0E5 in "press R to add players"). The game also asks for U+E0AB (beside "Confirmar"), U+E0AD, U+E0AE,
U+E0F1 and U+E0F2, whose buttons no source we can use names: they get a blank button, so the text reads without a "?".
--ext takes the console's own Nintendo extension font instead (TTF/OTF, or the BFTTF the console stores), for exact
icons: dump it from your own console (its system data, or a shared-font dumper's output).

BFTTF: big-endian 32-bit words XORed with a key; word 0 is 0x7f9a0218 ^ key, word 1 the font size ^ key, then the
font, padded to a word, every word XORed with the key (ov_bfttf_size reads it back).

Usage: uv run tools/make_shared_fonts.py [--font /usr/share/fonts/google-noto/NotoSans-Regular.ttf]
                                         [--ext nintendo_ext.ttf] [--out build/shared-fonts]
"""

import argparse
import io
import math
import struct
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
MAGIC = 0x7F9A0218
KEY = 0x49621806  # any key decodes; this is the one the console's files use
FILES = ("0-standard.bfttf", "1-chinese-simplified.bfttf", "2-chinese-simplified-extension.bfttf",
         "3-chinese-traditional.bfttf", "4-korean.bfttf", "5-nintendo-extension.bfttf")
DEFAULT_FONT = Path("/usr/share/fonts/google-noto/NotoSans-Regular.ttf")

FACE, SHOULDER = "face", "shoulder"
# code point -> (label, shape, filled); see the docstring for where each comes from
BUTTONS = {}
for base, filled in ((0xE0A0, False), (0xE0E0, True)):
    for k, label in enumerate(("A", "B", "X", "Y")):
        BUTTONS[base + k] = (label, FACE, filled)
    for k, label in enumerate(("L", "R", "ZL", "ZR", "SL", "SR")):
        BUTTONS[base + 4 + k] = (label, SHOULDER, filled)
BUTTONS.update({0xE0B5: ("+", FACE, False), 0xE0B6: ("-", FACE, False),
                0xE0EF: ("+", FACE, True), 0xE0F0: ("-", FACE, True)})
BLANK = (0xE0AB, 0xE0AD, 0xE0AE, 0xE0F1, 0xE0F2)  # asked for by the game, button unknown
for cp in BLANK:
    BUTTONS[cp] = ("", FACE, False)


def bfttf(font: bytes, key: int = KEY) -> bytes:
    if font[:4] not in (b"\x00\x01\x00\x00", b"OTTO"):
        raise ValueError("not a TrueType or OpenType font")
    font += bytes(-len(font) % 4)
    words = struct.unpack(f">{len(font) // 4}I", font)
    head = (MAGIC ^ key, len(font) ^ key)
    return struct.pack(f">{2 + len(words)}I", *head, *(w ^ key for w in words))


def is_bfttf(data: bytes) -> bool:
    if len(data) < 12:
        return False
    key = struct.unpack(">I", data[:4])[0] ^ MAGIC
    size = struct.unpack(">I", data[4:8])[0] ^ key
    first = struct.unpack(">I", data[8:12])[0] ^ key
    return size + 8 <= len(data) and first in (0x00010000, 0x4F54544F)


def _shape(pen, points) -> None:
    pen.moveTo(points[0])
    for p in points[1:]:
        pen.lineTo(p)
    pen.closePath()


def _round_rect(x0: float, y0: float, x1: float, y1: float, r: float, clockwise: bool) -> list[tuple[int, int]]:
    """A rectangle with round corners as a polygon (TrueType's outer contours run clockwise)."""
    pts = []
    corners = ((x1 - r, y1 - r, 0), (x1 - r, y0 + r, -90), (x0 + r, y0 + r, -180), (x0 + r, y1 - r, -270))
    for cx, cy, start in corners:   # clockwise: top right, bottom right, bottom left, top left
        for k in range(9):
            a = math.radians(90 + start - 90 * k / 8)
            pts.append((round(cx + r * math.cos(a)), round(cy + r * math.sin(a))))
    return pts if clockwise else pts[::-1]


def button_glyph(font: TTFont, letters: TTFont, label: str, shape: str, filled: bool):
    """One icon: a circle (face buttons, +/-) or a shoulder shape, outlined or filled, the label inside (cut out of a
    filled one). Returns the glyph and its advance width."""
    upm = font["head"].unitsPerEm
    cap = getattr(font["OS/2"], "sCapHeight", 0) or int(upm * 0.714)
    h = cap * 1.18                                   # the icon's height, centred on the capitals
    y0 = (cap - h) / 2
    w = h if shape == FACE else h * (1.15 if len(label) <= 1 else 1.6)
    side = upm * 0.06
    x0 = side
    r = h / 2 if shape == FACE else h * 0.3
    ring = h * 0.09
    pen = TTGlyphPen(None)
    _shape(pen, _round_rect(x0, y0, x0 + w, y0 + h, r, True))
    if not filled:
        _shape(pen, _round_rect(x0 + ring, y0 + ring, x0 + w - ring, y0 + h - ring, r - ring, False))
    if label:
        gs, cmap = letters.getGlyphSet(), letters.getBestCmap()
        names = [cmap[ord(c)] for c in label]
        bp = BoundsPen(gs)
        adv = 0
        for n in names:
            gs[n].draw(TransformPen(bp, (1, 0, 0, 1, adv, 0)))
            adv += gs[n].width
        bx0, by0, bx1, by1 = bp.bounds
        if label in ("+", "-"):   # the sign half as wide as the circle
            s = w * 0.5 / max(bx1 - bx0, 1)
        else:                     # capitals 58 % of the icon's height, narrower when they would not fit
            s = min(h * 0.58 / cap, (w - 2.6 * ring) / max(bx1 - bx0, 1))
        ox = x0 + w / 2 - s * (bx0 + bx1) / 2
        oy = y0 + h / 2 - s * (by0 + by1) / 2
        target = ReverseContourPen(pen) if filled else pen   # a filled icon's label is a hole
        adv = 0
        for n in names:
            gs[n].draw(TransformPen(target, (s, 0, 0, s, ox + s * adv, oy)))
            adv += gs[n].width
    return pen.glyph(), round(w + 2 * side)


def add_buttons(font: TTFont, letters: TTFont | None = None) -> int:
    """The BUTTONS icons added to a TrueType font (glyf), mapped in every Unicode cmap subtable. Code points the font
    already maps are left alone. Returns how many were added."""
    if "glyf" not in font:
        raise ValueError("button icons need a TrueType (glyf) font")
    letters = letters or font
    order = list(font.getGlyphOrder())
    have = font.getBestCmap()
    added = 0
    for cp, (label, shape, filled) in sorted(BUTTONS.items()):
        if cp in have:
            continue
        name = f"uni{cp:04X}"
        glyph, adv = button_glyph(font, letters, label, shape, filled)
        font["glyf"][name] = glyph
        glyph.recalcBounds(font["glyf"])
        font["hmtx"][name] = (adv, glyph.xMin)
        order.append(name)
        for t in font["cmap"].tables:
            if t.isUnicode():
                t.cmap[cp] = name
        added += 1
    font.setGlyphOrder(order)
    font["glyf"].setGlyphOrder(order)
    if "post" in font:
        font["post"].formatType = 3.0   # no glyph names: the new glyphs need none
    return added


def stand_in(path: Path) -> bytes:
    """The free font with the button icons, as sfnt bytes. Letters from its bold sibling when there is one."""
    font = TTFont(path)
    bold = path.with_name(path.name.replace("-Regular", "-Bold"))
    letters = TTFont(bold) if bold != path and bold.exists() else font
    add_buttons(font, letters)
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--font", type=Path, default=DEFAULT_FONT)
    ap.add_argument("--ext", type=Path, help="the console's Nintendo extension font (TTF, OTF or BFTTF), dumped by you")
    ap.add_argument("--out", type=Path, default=ROOT / "build/shared-fonts")
    args = ap.parse_args()
    data = bfttf(stand_in(args.font))
    args.out.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        (args.out / name).write_bytes(data)
    print(f"{len(FILES)} shared fonts from {args.font.name} with {len(BUTTONS)} button icons "
          f"({len(data):,} bytes each) in {args.out}")
    if args.ext:
        ext = args.ext.read_bytes()
        (args.out / FILES[5]).write_bytes(ext if is_bfttf(ext) else bfttf(ext))
        print(f"{FILES[5]}: the console's font from {args.ext.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
