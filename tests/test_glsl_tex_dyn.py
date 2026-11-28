"""TEX by a handle in a uniform register (sm86/translate/glsl/tex.py tex_dyn) and ULEA's carry out (alu.py ulea).

Mario Tennis Fever's crowd: a compute program samples, in each workgroup, the texture of its packed table's slot
gl_WorkGroupID.x, whose handle a ULDC read from c0 at a dynamic address. The texture becomes an element of an array of
the table's textures, indexed from that address. Stub instructions stand for decoded ones.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "sm86/translate"), str(ROOT / "sm86/translate/frontend")]

from glsl.alu import AluOps  # noqa: E402
from glsl.common import PT, Unsupported  # noqa: E402
from glsl.tex import TexOps  # noqa: E402


class Insn:
    def __init__(self, op: str, syms=None, **f) -> None:
        self.op, self.f, self.s = op, f, syms or {}

    def v(self, name: str, default=None):
        return self.f.get(name, default)

    def has(self, name: str) -> bool:
        return name in self.f

    def sym(self, name: str) -> str:
        return self.s.get(name, "")


class Tex(TexOps):
    def __init__(self, stage="cs", table=(1, 1, 32, 0, 4), handles=(4,)) -> None:
        self.stage, self.cs_table, self.ur_handle, self.dyn_tex = stage, table, set(handles), None


def test_table_slot_indexes_the_array():
    b = Tex()
    # 4 push-constant words, then one uniform and one storage buffer (16 bytes each): handles from byte 0x40
    assert b.tex_dyn(Insn("TEX", URc=4), "sampler2D") == "tdyn[min((uaddr4 - 0x40u) >> 3u, 31u)]"
    assert b.dyn_tex == ("sampler2D", 32, 0x40)


def test_handle_of_unknown_origin_refused():
    with pytest.raises(Unsupported):
        Tex(handles=()).tex_dyn(Insn("TEX", URc=4), "sampler2D")
    with pytest.raises(Unsupported):
        Tex(stage="ps").tex_dyn(Insn("TEX", URc=4), "sampler2D")
    with pytest.raises(Unsupported):
        Tex(table=None).tex_dyn(Insn("TEX", URc=4), "sampler2D")


def test_one_sampler_type_per_array():
    b = Tex()
    b.tex_dyn(Insn("TEX", URc=4), "sampler2D")
    with pytest.raises(Unsupported):
        b.tex_dyn(Insn("TEX", URc=4), "sampler2DShadow")


class Alu(AluOps):
    def __init__(self) -> None:
        self.uregs = set()

    def neg_u(self, i, slot):
        return f"ur{i.v('UR' + slot)}"

    def dst(self, i, expr):
        return f"ur{i.v('URd')} = {expr};"


def test_ulea_carry_out():
    out = Alu().ulea(Insn("ULEA", {"hilo": "LO"}, UPu=1, URa=5, URb=6, URd=7, scaleU5=4))
    assert out == "{ uint64_t s3 = uint64_t(ur5 << 4u) + uint64_t(ur6); ur7 = uint(s3); up1 = (s3 >> 32) != 0ul; }"


def test_ulea_hi_carry_refused():
    with pytest.raises(Unsupported):
        Alu().ulea(Insn("ULEA", {"hilo": "HI"}, UPu=1, URa=5, URb=6, URd=7, scaleU5=4))


def test_ulea_without_carry_is_lea(monkeypatch):
    monkeypatch.setattr(Alu, "lea", lambda self, i: "lea", raising=False)
    assert Alu().ulea(Insn("ULEA", UPu=PT)) == "lea"
