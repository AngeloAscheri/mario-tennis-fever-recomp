"""Set up mtf-recomp from your own dump in one command: find its ExeFS and RomFS, rebuild the engine, lift the code.

Why: before the first build there are four steps (which folder is which, tools/unpack_engine.py, recomp/gen.py,
tools/make_shared_fonts.py) and a newcomer should not have to know them. This runs them all and writes
build/game.json, which tools/run/boot.py reads, so later commands need no paths.

The dump is the folder your dump tool wrote: it holds an `exefs/` with `main` and a `romfs/` somewhere below it (for
example base/exefs and updates/327680/exefs). The newest version found is used, unless --version names one.

Usage: uv run tools/setup.py <dump folder> [--version base|327680] [--jobs N]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "recomp"))

from versions import VERSIONS, detect  # noqa: E402


def find_dumps(top: Path) -> dict[str, tuple[Path, Path | None]]:
    """{version name: (exefs, romfs or None)} for every exefs/main below top whose build this port knows."""
    found = {}
    for main in sorted(top.rglob("exefs/main")):
        exefs = main.parent
        try:
            v = detect(exefs)
        except ValueError as e:
            print(f"  skipped {exefs}: {e}")
            continue
        romfs = exefs.parent / "romfs"
        found[v.name] = (exefs, romfs if romfs.is_dir() else None)
    return found


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dump", type=Path)
    ap.add_argument("--version", choices=[v.name for v in VERSIONS])
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()
    if not args.dump.is_dir():
        sys.exit(f"{args.dump} is not a folder")
    print(f"looking for exefs/main below {args.dump} ...")
    found = find_dumps(args.dump)
    if not found:
        sys.exit("no known version found: the dump needs a decrypted exefs/ (with main) and romfs/. "
                 "Run `uv run tools/inspect_dump.py <exefs>` on it and open a dump report issue.")
    for name, (exefs, romfs) in found.items():
        print(f"  {name}: exefs {exefs}, romfs {romfs or 'MISSING'}")
    order = [v.name for v in VERSIONS]
    name = args.version or max(found, key=order.index)
    if name not in found:
        sys.exit(f"version {name} is not in the dump")
    exefs, romfs = found[name]
    if romfs is None:
        sys.exit(f"{exefs.parent} has no romfs/ folder beside exefs/")
    py = sys.executable
    run([py, "tools/unpack_engine.py", str(exefs)])
    run([py, "recomp/gen.py", "--exefs", f"build/modules-{name}", "--jobs", str(args.jobs)])
    run([py, "tools/make_shared_fonts.py"])
    game = {"version": name, "exefs": str(exefs.resolve()), "romfs": str(romfs.resolve()),
            "modules": str((ROOT / f"build/modules-{name}").resolve())}
    (ROOT / "build/game.json").write_text(json.dumps(game, indent=1) + "\n")
    print(f"\nready: {name}. Next: uv run tools/run/boot.py   (builds build/mkw and runs it to its first stop)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
