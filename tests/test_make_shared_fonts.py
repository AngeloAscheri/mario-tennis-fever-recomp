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
