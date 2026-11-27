"""A BRA's or EXIT's own predicate operand holds together with its guard (sm86/translate/glsl/common.py own_pred).

Stub instructions stand for decoded ones: only the fields the translator reads (Pg, Pp and their negations).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "sm86/translate"), str(ROOT / "sm86/translate/frontend")]

from glsl.common import PT, own_pred  # noqa: E402
from glsl.subroutines import plain  # noqa: E402


class Stub:
    def __init__(self, op: str, **f: int) -> None:
        self.op, self.f = op, f
        for p in ("Pg", "Pp"):  # the decoder gives a predicate field with its negation
            if p in f:
                f.setdefault(p + "@not", 0)

    def has(self, name: str) -> bool:
        return name in self.f

    def v(self, name: str, default: int | None = None) -> int:
        if name in self.f:
            return self.f[name]
        if default is None:
            raise KeyError(name)
        return default


def test_exit_with_pt_operand_has_no_condition():
    assert own_pred(Stub("EXIT", Pg=PT, Pp=PT)) is None
    assert plain(Stub("EXIT", Pg=PT, Pp=PT))


def test_exit_operand_is_a_condition():
    # `@!P0 EXIT P1`: the court's fragment program (docs/research.md, "EXIT's predicate operand")
    i = Stub("EXIT", Pg=0, **{"Pg@not": 1}, Pp=1)
    assert own_pred(i) == "p1"
    assert not plain(i)


def test_unguarded_exit_with_operand_is_not_plain():
    i = Stub("EXIT", Pg=PT, Pp=2, **{"Pp@not": 1})
    assert own_pred(i) == "!p2"
    assert not plain(i)


def test_bra_operand():
    assert own_pred(Stub("BRA", Pg=PT, Pp=4)) == "p4"
    assert not plain(Stub("BRA", Pg=PT, Pp=4))


def test_mov_without_operand_is_plain():
    assert plain(Stub("MOV", Pg=PT))
