"""Refuse files that look like game content, console keys or C generated from the game's code.

Why: this repository is public and holds no part of Mario Tennis Fever. Everything taken from or generated from a
dump lives in ignored folders (build/, game/). This check is the guard: CI runs it on every push and pull request,
and tools/git/pre-commit runs it on the staged files.

Usage: python tools/check_content.py            every tracked or committable file
       python tools/check_content.py --staged   the files staged for the next commit
Standard library only, so it runs before any environment is set up.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

MAX_BYTES = 1024 * 1024

# Switch containers, executables, registrations and the game's data formats.
BLOCKED_SUFFIXES = {
    ".xci", ".xcz", ".nsp", ".nsz", ".nca", ".ncz", ".nup", ".nx", ".tik", ".cert", ".keys",
    ".nso", ".nro", ".nrs", ".nss", ".nrr", ".npdm",
    ".bfres", ".bntx", ".bnsh", ".sarc", ".szs", ".zs", ".byml", ".msbt", ".bars", ".bwav", ".bfstm",
}

# ExeFS modules carry no extension; "42" is the name of the game's single RomFS archive.
BLOCKED_NAMES = {"main", "sdk", "rtld", "main.npdm", "42"} | {f"subsdk{i}" for i in range(10)}

# Magic numbers at offset 0 of files that never belong here (NSO, NRO at 0x10, NRR, the game's CRA archive).
BLOCKED_MAGIC = (b"NSO0", b"NRR0", b"CRA.")

# Written by recomp/gen.py into every file it emits (split so this file does not carry it).
GENERATED_MARKER = "MTF_RECOMP_" + "GENERATED_FROM_GAME_CODE"

# A prod.keys / title.keys line: a name with key, kek or seed in it, then 32+ hex digits.
KEY_LINE = re.compile(r"^\s*[A-Za-z0-9_]*(key|kek|seed)[A-Za-z0-9_]*\s*=\s*[0-9A-Fa-f]{32,}\s*$", re.MULTILINE)


def list_files(staged: bool) -> list[Path]:
    if staged:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]
    else:
        cmd = ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
    out = subprocess.run(cmd, check=True, capture_output=True).stdout
    return [Path(p) for p in out.decode("utf-8").split("\0") if p]


def read(path: Path, staged: bool) -> bytes | None:
    if staged:
        return subprocess.run(["git", "cat-file", "blob", f":{path.as_posix()}"], check=True,
                              capture_output=True).stdout
    return path.read_bytes() if path.is_file() else None


def problems_for(path: Path, data: bytes) -> list[str]:
    found = []
    if path.suffix.lower() in BLOCKED_SUFFIXES:
        found.append(f"blocked file type {path.suffix}")
    if path.name.lower() in BLOCKED_NAMES:
        found.append("name of a Switch executable module or of the game's archive")
    if len(data) > MAX_BYTES:
        found.append(f"{len(data) // 1024} KiB, over the {MAX_BYTES // 1024} KiB limit")
    if data[:4] in BLOCKED_MAGIC or data[0x10:0x14] == b"NRO0":
        found.append("starts like a Switch module or the game's archive")
    if GENERATED_MARKER.encode() in data:
        found.append("generated from game code")
    if KEY_LINE.search(data[:MAX_BYTES].decode("utf-8", errors="ignore")):
        found.append("contains a key in prod.keys format")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--staged", action="store_true", help="check staged files only")
    args = parser.parse_args()
    failed = False
    for path in list_files(args.staged):
        data = read(path, args.staged)
        if data is None:
            continue
        for problem in problems_for(path, data):
            print(f"{path}: {problem}")
            failed = True
    if failed:
        print("\nGame content, keys and code generated from the game never go into the repository. See CONTRIBUTING.md.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
