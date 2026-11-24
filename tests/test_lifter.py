"""The lifter translates ordinary AArch64 words, and its ARMv8.1-8.3 classes agree with Unicorn.

The Unicorn comparison builds C with clang (or Zig's clang from the dev group), so it is skipped where neither runs.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from lifter import Lifter

ROOT = Path(__file__).resolve().parents[1]

WORDS = {
    "add x0, x1, x2": 0x8B020020,
    "sub w3, w4, #1": 0x51000483,
    "ldr x0, [x1, #8]": 0xF9400420,
    "str w2, [sp, #4]": 0xB90007E2,
    "movz x5, #0x1234": 0xD2824685,
    "fadd s0, s1, s2": 0x1E222820,
}


@pytest.mark.parametrize("name", WORDS)
def test_plain_instructions_lift(name):
    ins = Lifter(0, simd="c").lift(WORDS[name], 0x1000)
    assert ins.kind == "op", name
    assert ins.code.strip(), name


def test_ret_lifts_as_ret():
    assert Lifter(0, simd="c").lift(0xD65F03C0, 0x1000).kind == "ret"


def have_compiler() -> bool:
    if shutil.which("clang"):
        return True
    try:
        import ziglang  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.skipif(not have_compiler(), reason="needs clang or the ziglang package")
def test_new_classes_agree_with_unicorn():
    pytest.importorskip("unicorn")
    run = subprocess.run([sys.executable, str(ROOT / "tools/cpu/lift_diff.py"), "--n", "400", "--seed", "7"],
                         capture_output=True, text=True, timeout=600)
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
    assert "400 of 400 agree" in run.stdout
