"""Collect and translate the shaders a run needs, in one command: run, translate what was missing, run again.

Why: the game builds some programs in play from templates in main, so no extraction lists them; a run with
MKW_SPIRV_DUMP saves the ones it had no SPIR-V for. Done by hand that was three steps (docs/first-steps.md, "Shaders")
and newcomers had to know them. Each translated program lets the run get further and meet new ones, so this repeats
until a run finds nothing missing, the same programs keep failing to translate, or --rounds runs out.

Needs build/game.json (tools/setup.py) and build/sm86/instructions.json (sm86/spec/README.md); the runs go through
tools/run/boot.py, so its toolchain or --box applies.

Usage: uv run tools/shaders/collect.py [--rounds 5] [--seconds 20] [--box NAME]
Writes build/shader-dump/ (the dumped programs), build/spirv/ (their SPIR-V), build/run/shaders.log (the last run).
"""

import argparse
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "build/sm86/instructions.json"
DUMP = ROOT / "build/shader-dump"
SPIRV = ROOT / "build/spirv"
INDEX = ROOT / "build/shader-dump-index"  # translate.py reads an index.csv; --dumped-only needs just its header
LOG = ROOT / "build/run/shaders.log"


def missing(dump: Path, spirv: Path) -> set[str]:
    """Keys of the programs a run dumped that have no SPIR-V yet (the dump's file names are the runtime's keys)."""
    return {code.stem for code in dump.glob("*.code") if not (spirv / f"{code.stem}.spv").exists()}


def collect(run_game: Callable[[int], bool], translate: Callable[[], None], dump: Path, spirv: Path,
            rounds: int) -> int:
    """The loop: run_game(round) -> whether the run happened; translate() turns the dump into SPIR-V."""
    tried: set[str] = set()
    for n in range(1, rounds + 1):
        print(f"round {n}: running the game with MKW_SPIRV_DUMP={dump}", flush=True)
        if not run_game(n):
            print(f"the run did not happen (build or setup): see {LOG} and build/run/build.log")
            return 1
        todo = missing(dump, spirv)
        if not todo:
            print("no missing shader programs")
            return 0
        new = todo - tried
        if not new:
            print(f"{len(todo)} programs are still missing and the translator could not make them: their reasons are "
                  f"in {spirv / 'failed.tsv'} (the translator's work list)")
            return 1
        print(f"round {n}: {len(new)} new programs without SPIR-V, translating", flush=True)
        translate()
        tried |= todo
    left = missing(dump, spirv)
    print(f"stopped after {rounds} rounds with {len(left)} programs still missing: run again or raise --rounds")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rounds", type=int, default=5, help="at most this many runs (default 5)")
    ap.add_argument("--seconds", type=float, default=20, help="each run, that long past boot (default 20)")
    ap.add_argument("--box", default=os.environ.get("MTF_BOX"), help="distrobox/toolbox with the toolchain")
    ap.add_argument("--jobs", type=int, help="translate.py --jobs")
    args = ap.parse_args()
    if not SPEC.is_file():
        print(f"no {SPEC.relative_to(ROOT)}: the translator needs the SM86 spec, built on this machine from NVIDIA's "
              "nvdisasm. How: sm86/spec/README.md (`python sm86/spec/spec.py`). Then run this again.")
        return 1
    if not (ROOT / "build/game.json").is_file():
        print("no build/game.json: run `uv run tools/setup.py <your dump folder>` first")
        return 1
    INDEX.mkdir(parents=True, exist_ok=True)
    (INDEX / "index.csv").write_text("sha1,stage,code_bytes,source,program\n")

    def run_game(n: int) -> bool:
        cmd = [sys.executable, str(ROOT / "tools/run/boot.py"), "--name", LOG.stem, "--seconds", f"{args.seconds:g}",
               "--spirv-dump", str(DUMP)]
        if n > 1:
            cmd.append("--no-build")  # the runtime did not change between rounds, only build/spirv/
        if args.box:
            cmd += ["--box", args.box]
        start = time.time()
        subprocess.run(cmd, cwd=ROOT)  # exits 1 at the game's stop too: whether the run happened is the log's age
        return LOG.is_file() and LOG.stat().st_mtime >= start

    def translate() -> None:
        cmd = [sys.executable, str(ROOT / "tools/shaders/translate.py"), "--shaders", str(INDEX), "--out", str(SPIRV),
               "--dumped", str(DUMP), "--dumped-only"]
        if args.jobs:
            cmd += ["--jobs", str(args.jobs)]
        subprocess.run(cmd, cwd=ROOT, check=True)

    return collect(run_game, translate, DUMP, SPIRV, args.rounds)


if __name__ == "__main__":
    sys.exit(main())
