"""Tessellation programs' layouts (sm86/translate/glsl/head.py tes_layout, vtg_head).

SET_TESSELLATION_PARAMETERS as NVIDIA's clb197.h (MIT) lays it out: domain 1:0, spacing 5:4, output primitives 9:8;
the hardware's TRIANGLES_CW is Vulkan's cw with the default domain origin (Mesa NVK).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "sm86/translate"), str(ROOT / "sm86/translate/frontend")]

from glsl.common import Unsupported  # noqa: E402
from glsl.head import tes_layout, vtg_head  # noqa: E402
from glsl.mem import MemOps  # noqa: E402


def test_court_grass_quads():
    # Mario Tennis Fever's court: control +0x5c = 0x202
    assert tes_layout(0x202) == "layout(quads, equal_spacing, cw) in;"


def test_triangles_ccw_fractional():
    assert tes_layout(0x311) == "layout(triangles, fractional_odd_spacing, ccw) in;"
    assert tes_layout(0x321) == "layout(triangles, fractional_even_spacing, ccw) in;"


def test_points_and_isolines():
    assert tes_layout(0x002) == "layout(quads, equal_spacing, point_mode) in;"
    assert tes_layout(0x100) == "layout(isolines, equal_spacing) in;"


def test_unknown_parameters_refused():
    with pytest.raises(Unsupported):
        tes_layout(0x003)  # domain 3
    with pytest.raises(Unsupported):
        tes_layout(0x232)  # spacing 3


def test_patch_locations_from_the_top():
    assert MemOps.patch_location(0) == 31
    assert MemOps.patch_location(3) == 28


class Builder:
    def __init__(self, stage: str, in_attrs=(), out_attrs=(), patch_attrs=()) -> None:
        self.stage, self.vtg, self.tess_mode, self.sph = stage, True, 0x202, None
        self.in_attrs, self.out_attrs, self.patch_attrs = set(in_attrs), set(out_attrs), set(patch_attrs)


def test_tes_declarations():
    head = vtg_head(Builder("tes", out_attrs={0}, patch_attrs={0}))
    assert head[0] == "layout(quads, equal_spacing, cw) in;"
    assert "layout(location = 31) patch in vec4 patch_attr0;" in head
    assert "layout(location = 0) out vec4 out_attr0;" in head
    assert "out gl_PerVertex { vec4 gl_Position; float gl_PointSize; };" in head


def test_patch_location_clash_refused():
    with pytest.raises(Unsupported):
        vtg_head(Builder("tes", in_attrs={31}, patch_attrs={0}))
