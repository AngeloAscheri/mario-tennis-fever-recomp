"""Check that every folder README names the files in its folder.

Why: CONTRIBUTING.md asks for a README.md in every folder that names its files, but nothing checked it, so the
READMEs drifted. The idea comes from mkw-recomp's tools/docs/check.py (MIT); this is a smaller rewrite, no code copied.

For every folder with a README.md under recomp/, tools/, tests/ and docs/, each tracked file directly in that folder
must appear in the README by name (a path ending in it, like `run/boot.py`, counts). runtime/ keeps mkw-recomp's
READMEs and is left out for now.

Usage: uv run tools/docs/check.py     prints the unnamed files and exits 1 when there are any
Standard library only, like tools/check_content.py.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKED = ("recomp", "tools", "tests", "docs")


def named(readme: str, name: str) -> bool:
    """Whether the README text names the file: the name not glued to a longer word or file name."""
    return re.search(rf"(?<![\w.-]){re.escape(name)}(?![\w-])", readme) is not None


def tracked_files(root: Path) -> list[Path]:
    """Files git tracks under the checked folders (build/ and other ignored output never count)."""
    out = subprocess.run(["git", "ls-files", "-z", "--", *CHECKED], cwd=root, capture_output=True, check=True)
    return [Path(p) for p in out.stdout.decode().split("\0") if p]


def unnamed(root: Path, files: list[Path]) -> dict[Path, list[str]]:
    """README path -> names of the files in its folder that it does not mention."""
    by_folder: dict[Path, list[str]] = {}
    for f in files:
        by_folder.setdefault(f.parent, []).append(f.name)
    report = {}
    for folder, names in sorted(by_folder.items()):
        if "README.md" not in names:
            continue
        readme = (root / folder / "README.md").read_text(encoding="utf-8", errors="replace")
        missing = sorted(n for n in names if n != "README.md" and not named(readme, n))
        if missing:
            report[folder / "README.md"] = missing
    return report


def main() -> int:
    report = unnamed(ROOT, tracked_files(ROOT))
    for readme, missing in report.items():
        print(f"{readme.as_posix()}: not named: {', '.join(missing)}")
    if report:
        print("Name each file in its folder's README.md (CONTRIBUTING.md, Code).")
        return 1
    print("docs check: every README names its files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
