"""recomp/versions.py names the known builds by the build id in exefs/main's header."""

import pytest

import versions


def header(build_id: str) -> bytes:
    return b"NSO0" + bytes(0x3C) + bytes.fromhex(build_id) + bytes(0x18)


def test_known_builds():
    for v in versions.VERSIONS:
        assert versions.detect_id(versions.build_id_of(header(v.main_build_id))) is v
        assert v.patches.is_file(), v.patches


def test_unknown_build_names_its_id():
    with pytest.raises(ValueError, match="0123456789abcdef"):
        versions.detect_id("0123456789abcdef")


def test_not_an_nso():
    with pytest.raises(ValueError, match="not an NSO"):
        versions.build_id_of(b"NCA3" + bytes(0x44))


def test_build_ids_unique_and_dirs_distinct():
    ids = [v.main_build_id for v in versions.VERSIONS]
    assert len(ids) == len(set(ids))
    assert len({versions.gen_dir_for(v) for v in versions.VERSIONS}) == len(versions.VERSIONS)
