"""Map a module's PLT stubs to the symbols they call, and list the call sites of chosen imports.

Why: an NSO calls its imports through PLT stubs (adrp x16; ldr x17, [x16, #slot]; add x16; br x17) whose GOT slot
carries a JUMP_SLOT relocation naming the symbol. Knowing which stub is which turns "bl 0x7a0c0" into
"bl nn::ro::LoadModule", the first step of reading any function. Prints addresses and names only.

Usage: uv run tools/analysis/plt.py <exefs>/main [--calls REGEX]
"""

import argparse
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "recomp"))

from nso import R_AARCH64_GLOB_DAT, R_AARCH64_JUMP_SLOT, Nso  # noqa: E402


def adrp_target(word: int, pc: int) -> int | None:
    if word & 0x9F000000 != 0x90000000:
        return None
    imm = ((word >> 5) & 0x7FFFF) << 2 | (word >> 29) & 3
    if imm & (1 << 20):
        imm -= 1 << 21
    return (pc & ~0xFFF) + (imm << 12)


def stubs(nso: Nso) -> dict[int, str]:
    """{stub address: symbol} for every adrp x16 / ldr x17, [x16, #imm] pair whose slot has a symbol relocation."""
    slot_sym = {}
    for addr, kind, sym, _ in nso.relocs:
        if kind in (R_AARCH64_JUMP_SLOT, R_AARCH64_GLOB_DAT) and sym:
            slot_sym[addr] = nso.syms[sym][0]
    out = {}
    text_lo, text_size = nso.text
    for pc in range(text_lo, text_lo + text_size - 4, 4):
        w0, w1 = struct.unpack_from("<II", nso.image, pc)
        page = adrp_target(w0, pc)
        if page is None or w0 & 0x1F != 16:
            continue
        if w1 & 0xFFC003FF != 0xF9400211:  # ldr x17, [x16, #imm12*8]
            continue
        slot = page + ((w1 >> 10) & 0xFFF) * 8
        if slot in slot_sym:
            out[pc] = slot_sym[slot]
    return out


def calls(nso: Nso, targets: dict[int, str]) -> list[tuple[int, str]]:
    """[(call site, symbol)] for every bl or b to one of the targets."""
    out = []
    text_lo, text_size = nso.text
    for pc in range(text_lo, text_lo + text_size, 4):
        w = struct.unpack_from("<I", nso.image, pc)[0]
        if w & 0x7C000000 == 0x14000000:  # b / bl
            imm = w & 0x3FFFFFF
            if imm & (1 << 25):
                imm -= 1 << 26
            dest = pc + imm * 4
            if dest in targets:
                out.append((pc, targets[dest]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("nso", type=Path)
    ap.add_argument("--calls", help="regex over symbol names: list the call sites of those imports")
    args = ap.parse_args()
    nso = Nso(str(args.nso))
    table = stubs(nso)
    if not args.calls:
        for pc, name in sorted(table.items()):
            print(f"{pc:#09x}  {name}")
        return 0
    want = {pc: n for pc, n in table.items() if re.search(args.calls, n)}
    for pc, name in calls(nso, want):
        print(f"{pc:#09x}  -> {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
