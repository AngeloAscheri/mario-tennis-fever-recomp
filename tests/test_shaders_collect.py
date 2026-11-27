"""tools/shaders/collect.py repeats run and translate until nothing is missing, with fake runs and translations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/shaders"))

import collect  # noqa: E402


class FakeGame:
    """Each run dumps the programs of its round; translate writes .spv for all of them except the broken ones."""

    def __init__(self, tmp: Path, rounds: list[list[str]], broken: set[str] = frozenset(), runs: bool = True):
        self.dump, self.spirv = tmp / "dump", tmp / "spirv"
        self.dump.mkdir()
        self.spirv.mkdir()
        self.rounds, self.broken, self.runs = rounds, broken, runs
        self.translations = 0

    def run(self, n: int) -> bool:
        for key in self.rounds[min(n, len(self.rounds)) - 1]:
            (self.dump / f"{key}.code").write_bytes(b"")
        return self.runs

    def translate(self) -> None:
        self.translations += 1
        for code in self.dump.glob("*.code"):
            if code.stem not in self.broken:
                (self.spirv / f"{code.stem}.spv").write_bytes(b"")

    def collect(self, rounds: int = 5) -> int:
        return collect.collect(self.run, self.translate, self.dump, self.spirv, rounds)


def test_repeats_until_a_run_finds_nothing_missing(tmp_path, capsys):
    game = FakeGame(tmp_path, [["a", "b"], ["c"], []])
    assert game.collect() == 0
    assert game.translations == 2
    assert "no missing shader programs" in capsys.readouterr().out
    assert collect.missing(game.dump, game.spirv) == set()


def test_stops_when_the_same_programs_keep_failing(tmp_path, capsys):
    game = FakeGame(tmp_path, [["a", "bad"], []], broken={"bad"})
    assert game.collect() == 1
    assert game.translations == 1
    assert "failed.tsv" in capsys.readouterr().out


def test_stops_after_the_rounds(tmp_path, capsys):
    game = FakeGame(tmp_path, [["a"], ["b"], ["c"], ["d"]])
    assert game.collect(rounds=2) == 1
    assert game.translations == 2
    assert "stopped after 2 rounds" in capsys.readouterr().out


def test_a_run_that_did_not_happen_is_not_success(tmp_path, capsys):
    game = FakeGame(tmp_path, [[]], runs=False)
    assert game.collect() == 1
    assert "did not happen" in capsys.readouterr().out
