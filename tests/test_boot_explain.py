"""tools/run/boot.py explains a run's stop from its log: the SDK call to replace, or the crash's stack."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/run"))

import boot  # noqa: E402

IPC_LOG = """[host] ENTER nnMain
FATAL: svc #0x1f unknown at sdk+0x180cb0: IPC to a console service: replace its SDK call by name
  lr sdk+0x161cd4 (_ZN2nn2sm10InitializeEv+0x54)
  guest frame  0: sdk+0x161a74 (_ZN2nn2sf4hipc31InitializeHipcServiceResolutionEv+0x14)
  guest frame  1: sdk+0x63eb34 (_ZN2nn3hid6detail29SetNpadHandheldActivationModeENS0_26NpadHandheldActivationModeE+0x24)
  guest frame  2: sdk+0x64dab4 (_ZN2nn3hid29SetNpadHandheldActivationModeENS0_26NpadHandheldActivationModeE+0x14)
  guest frame  3: basic+0x123c724
  guest frame  4: basic+0x11fa820 (_Z6Abort_v+0x10)
"""


def test_finds_the_sdk_call_the_game_made():
    fr = boot.frames(IPC_LOG.splitlines())
    assert boot.sdk_call_from_game(fr) == (
        "_ZN2nn3hid29SetNpadHandheldActivationModeENS0_26NpadHandheldActivationModeE", "basic+0x123c724")


def test_explain_ipc(tmp_path, capsys):
    log = tmp_path / "boot.log"
    log.write_text(IPC_LOG)
    assert boot.explain(log) == 1
    out = capsys.readouterr().out
    assert "_ZN2nn3hid29SetNpadHandheldActivationMode" in out and "ov_mtf.c" in out


def test_explain_nvn(tmp_path, capsys):
    log = tmp_path / "boot.log"
    log.write_text("FATAL: NVN nvnCommandBufferSetCopyImageStride is not implemented\n")
    assert boot.explain(log) == 1
    assert "runtime/gfx/nvn/api/" in capsys.readouterr().out


def test_explain_clean_run(tmp_path, capsys):
    log = tmp_path / "boot.log"
    log.write_text("boot: first NVN call nvnBootstrapLoader(\"x\") from basic+0x2895c\nboot: passed (1 SVCs)\n")
    assert boot.explain(log) == 0
    assert "reached" in capsys.readouterr().out
