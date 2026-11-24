"""The content guard refuses what never belongs in the repository and lets ordinary files through."""

from pathlib import Path

import check_content as cc


def problems(name: str, data: bytes = b"") -> list[str]:
    return cc.problems_for(Path(name), data)


def test_ordinary_files_pass():
    assert problems("README.md", b"# hello\n") == []
    assert problems("recomp/lifter.py", b"import struct\n") == []


def test_switch_files_by_extension_and_name():
    for name in ("game.nsp", "x.xci", "a.nca", "prod.keys", "basic.nrs", "nxboot.nss", "m.nro", "dump.nup"):
        assert problems(name), name
    for name in ("main", "sdk", "rtld", "subsdk0", "main.npdm", "romfs/42"):
        assert problems(name), name


def test_switch_files_by_magic():
    assert problems("blob.bin", b"NSO0" + bytes(60))
    assert problems("blob.bin", b"CRA." + bytes(60))
    assert problems("blob.bin", bytes(16) + b"NRO0" + bytes(16))


def test_generated_code_marker():
    marker = ("MTF_RECOMP_" + "GENERATED_FROM_GAME_CODE").encode()
    assert problems("x.c", b"// " + marker + b"\nvoid f(void) {}\n") == ["generated from game code"]


def test_key_lines():
    assert problems("notes.txt", b"header_key = " + b"0" * 64 + b"\n")
    assert problems("notes.txt", b"the key is not here\n") == []


def test_size_limit():
    assert problems("big.txt", b"a" * (cc.MAX_BYTES + 1))
