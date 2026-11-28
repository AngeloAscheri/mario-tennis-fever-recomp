"""tools/make_shared_fonts.py writes BFTTF files that the runtime's reader (ov_system.c ov_bfttf_size) accepts."""

import struct

import pytest

import make_shared_fonts as msf


def bfttf_size(p: bytes) -> int:
    """ov_bfttf_size, in Python: 0 when p is not a BFTTF image."""
    key = struct.unpack(">I", p[:4])[0] ^ msf.MAGIC
    size = struct.unpack(">I", p[4:8])[0] ^ key
    first = struct.unpack(">I", p[8:12])[0] ^ key
    return size if size + 8 == len(p) and first in (0x00010000, 0x4F54544F) else 0


def test_round_trip():
    font = b"\x00\x01\x00\x00" + bytes(range(37))   # an sfnt header and an odd length, padded to a word
    out = msf.bfttf(font)
    assert bfttf_size(out) == 44
    key = msf.KEY
    words = struct.unpack(f">{(len(out) - 8) // 4}I", out[8:])
    assert struct.pack(f">{len(words)}I", *(w ^ key for w in words))[:len(font)] == font


def test_refuses_other_files():
    with pytest.raises(ValueError):
        msf.bfttf(b"wOFF" + bytes(32))


def tiny_font():
    """A TrueType font with a square for each label character the icons use, and U+E0A0 already mapped."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    chars = "ABXYLRZS+-"
    names = [".notdef"] + [f"g{ord(c):02X}" for c in chars] + ["mine"]
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap({**{ord(c): f"g{ord(c):02X}" for c in chars}, 0xE0A0: "mine"})
    glyphs = {}
    for n in names:
        pen = TTGlyphPen(None)
        pen.moveTo((50, 0)), pen.lineTo((50, 700)), pen.lineTo((550, 700)), pen.lineTo((550, 0)), pen.closePath()
        glyphs[n] = pen.glyph()
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (600, 50) for n in names})
    fb.setupHorizontalHeader(ascent=900, descent=-200)
    fb.setupOS2(sCapHeight=700)
    fb.setupPost()
    fb.setupNameTable({"familyName": "Tiny", "styleName": "Regular"})
    return fb.font


def test_button_icons_added():
    font = tiny_font()
    added = msf.add_buttons(font)
    cmap = font.getBestCmap()
    assert added == len(msf.BUTTONS) - 1 and cmap[0xE0A0] == "mine"   # a code point the font has is kept
    glyf = font["glyf"]
    for cp in msf.BUTTONS:
        g = glyf[cmap[cp]]
        assert g.numberOfContours > 0 and font["hmtx"][cmap[cp]][0] > 0
    assert glyf[cmap[0xE0E5]].numberOfContours == 2   # filled R: the shape and the letter's hole
    assert glyf[cmap[0xE0A5]].numberOfContours == 3   # outlined R: two rings and the letter
    assert glyf[cmap[0xE0AB]].numberOfContours == 2   # a blank button: a ring


def test_stand_in_is_a_bfttf(tmp_path):
    p = tmp_path / "tiny.ttf"
    tiny_font().save(p)
    out = msf.bfttf(msf.stand_in(p))
    assert bfttf_size(out) and msf.is_bfttf(out) and not msf.is_bfttf(b"\x00\x01\x00\x00" + bytes(16))
