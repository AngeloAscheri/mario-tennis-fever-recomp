"""Only images a program stores into are reflected as written (sm86/translate/glsl/tex.py image, head.py flag 4).

A load-only image marked written is copied back from the GPU over what the CPU wrote: Mario Tennis Fever's glyph
staging texture (docs/research.md, "The text's glyph cache"). Stub instructions stand for decoded ones.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "sm86/translate"), str(ROOT / "sm86/translate/frontend")]

from glsl.common import PT, RZ  # noqa: E402
from glsl.tex import TexOps  # noqa: E402


class Insn:
    def __init__(self, op: str, **f) -> None:
        self.op = op
        self.f = {"Pu": PT, "Ra": 4, "Rb": 8, "Rd": 12, "bank5": 0, "tsPtrIdx": 7, **f}
        self.s = {"dim": "2D", "clamp": "IGN", "rgba": "R"}

    def v(self, name: str, default=None):
        return self.f.get(name, default)

    def sym(self, name: str) -> str:
        return self.s.get(name, "")


class Ops(TexOps):
    def __init__(self) -> None:
        self.images, self.images_written, self.regs = {}, set(), set()


def test_load_only_image_is_not_written():
    b = Ops()
    b.suld(Insn("SULD"))
    assert b.images == {(0, 7): "image2D"}
    assert b.images_written == set()


def test_stored_image_is_written():
    b = Ops()
    b.suld(Insn("SULD", tsPtrIdx=7))
    b.sust(Insn("SUST", tsPtrIdx=9))
    assert b.images_written == {(0, 9)}


def test_rz_coordinates_still_register():
    b = Ops()
    b.sust(Insn("SUST", Ra=RZ))
    assert (0, 7) in b.images_written
