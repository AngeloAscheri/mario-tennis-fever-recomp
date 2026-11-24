"""List the SDK functions the game imports that no HOST_OVERRIDE replaces yet, grouped by nn:: namespace.

Why: every console service the game reaches stops the run (tools/run/boot.py names the one it hit). Many of those calls
can be seen coming: this lists what main and the engine import from the SDK without a replacement, so a namespace can
be taken as one task (nn::hid, nn::account...). Not every entry needs one: plain library code (containers, math,
nn::util) runs fine as lifted SDK code; only what talks to a service does. The fix-sdk-call skill says how to tell.

Usage: uv run tools/analysis/missing_overrides.py [--modules build/modules-327680] [--ns hid] [--all]
"""

import argparse
import collections
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "recomp"))

from nso import Nso  # noqa: E402

OVERRIDE = re.compile(r'HOST_OVERRIDE\(\s*"([^"]+)"')
MACRO = re.compile(r'HOST_OVERRIDE\(\s*([A-Z_][A-Z0-9_]*)\s*,')
DEFINE = re.compile(r'#define\s+([A-Z_][A-Z0-9_]*)\s+"(_Z[^"]+)"')


def overridden() -> set[str]:
    names, defines, used = set(), {}, set()
    for p in [*(ROOT / "runtime").rglob("*.c"), *(ROOT / "runtime").rglob("*.h")]:
        text = p.read_text(errors="replace")
        names.update(OVERRIDE.findall(text))
        used.update(MACRO.findall(text))   # HOST_OVERRIDE(S_OPEN_FILE, ...) with #define S_OPEN_FILE "_ZN..."
        defines.update(DEFINE.findall(text))
    return names | {defines[m] for m in used if m in defines}


def namespace(sym: str) -> str:
    s = sym.replace("_ZNK", "_ZN", 1)
    m = re.match(r"_ZN2nn(\d+)", s)
    if not m:
        return "(not nn::)"
    n = int(m.group(1))
    return "nn::" + s[m.end():m.end() + n]


def demangle(names: list[str]) -> list[str]:
    tool = shutil.which("c++filt") or shutil.which("llvm-cxxfilt")
    if not tool or not names:
        return names
    out = subprocess.run([tool], input="\n".join(names), capture_output=True, text=True).stdout.splitlines()
    return out if len(out) == len(names) else names


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--modules", type=Path, default=None, help="default: the newest build/modules-*")
    ap.add_argument("--ns", help="only this namespace, e.g. hid or account")
    ap.add_argument("--all", action="store_true", help="list every function, not only the counts")
    args = ap.parse_args()
    mods = args.modules or max((ROOT / "build").glob("modules-*"), default=None)
    if not mods or not mods.is_dir():
        sys.exit("no build/modules-*: run `uv run tools/setup.py <your dump folder>` first")
    sdk_exports = {s[0] for s in Nso(str(mods / "sdk")).exports()}
    done = overridden()
    missing: dict[str, set[str]] = collections.defaultdict(set)
    total = collections.Counter()
    for m in ("main", "basic"):
        for s in Nso(str(mods / m)).imports():
            name = s[0]
            if name not in sdk_exports:
                continue
            ns = namespace(name)
            total[ns] += 1
            if name not in done:
                missing[ns].add(name)
    for ns in sorted(missing, key=lambda k: -len(missing[k])):
        if args.ns and ns != f"nn::{args.ns}":
            continue
        print(f"{ns:24} {len(missing[ns]):4} of {total[ns]:4} imports without a replacement")
        if args.all or args.ns:
            names = sorted(missing[ns])
            for mangled, nice in zip(names, demangle(names)):
                print(f"    {nice}\n        {mangled}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
