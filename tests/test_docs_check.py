"""tools/docs/check.py finds the files a folder's README does not name, and the repository's READMEs name theirs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "docs"))

import check  # noqa: E402


def test_names_need_a_boundary():
    assert check.named("| `boot.py` | runs |", "boot.py")
    assert check.named("see run/boot.py.", "boot.py")
    assert not check.named("| `reboot.py` |", "boot.py")
    assert not check.named("| `boot.py.bak` |", "boot.py")
    assert not check.named("| `boot-old.py` |", "boot")


def test_reports_unnamed_files(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "README.md").write_text("| `a.py` | does a |\n")
    files = [Path("tools/README.md"), Path("tools/a.py"), Path("tools/b.py"), Path("tools/x/c.py")]
    assert check.unnamed(tmp_path, files) == {Path("tools/README.md"): ["b.py"]}


def test_folder_without_readme_is_skipped(tmp_path):
    assert check.unnamed(tmp_path, [Path("docs/notes.md")]) == {}


def test_repository_readmes_name_their_files():
    assert check.unnamed(check.ROOT, check.tracked_files(check.ROOT)) == {}
