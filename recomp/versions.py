"""The game versions this port knows, keyed by the build id of exefs/main.

Why: each update of Mario Tennis Fever is a different executable (other addresses, maybe another sdk build), so
everything tied to one build (the patch sites, the number the runtime switches its fixed addresses on) is chosen
here, from the dump itself, in one place. Adapted from mkw-recomp recomp/versions.py @ c38933e (MIT).

The display version (1.x.y) lives in the control NCA's NACP, which a decrypted ExeFS/RomFS dump does not carry, so
versions are named by their title version until someone with the NACP names them.

Usage: from versions import detect; v = detect(exefs)  ->  Version, or ValueError for a build not listed.
       uv run recomp/versions.py [EXEFS]          prints the version of a dump.
       uv run recomp/versions.py --gen-dir EXEFS  prints the generated-C dir for the dump.
       uv run recomp/versions.py --patches EXEFS  prints the patch table for the dump.
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Version:
    name: str  # "base", or the update's title version
    number: int  # title version: 0 for the base game, 327680 for its update
    main_build_id: str  # first 8 bytes of the NSO build id of exefs/main, hex
    patches: Path  # recomp/patches-*.txt for this executable


VERSIONS = (
    # Both share the same sdk (build id 32a9ac1480a6f0e9, NintendoSDK 20.5.17). 23/11/2026.
    Version("base", 0, "aaf8a6ef6b7e3c78", ROOT / "recomp/patches-mtf-base.txt"),
    Version("327680", 327680, "104bce6874603701", ROOT / "recomp/patches-mtf-327680.txt"),
)


def build_id_of(head: bytes, where: str = "exefs/main") -> str:
    """The build id of exefs/main from its first 0x48 bytes."""
    if head[:4] != b"NSO0":
        raise ValueError(f"{where} is not an NSO: decrypted exefs needed")
    return head[0x40:0x48].hex()


def main_build_id(exefs: Path) -> str:
    return build_id_of((Path(exefs) / "main").read_bytes()[:0x48], str(Path(exefs) / "main"))


def detect(exefs: Path) -> Version:
    return detect_id(main_build_id(exefs))


def detect_id(got: str) -> Version:
    for v in VERSIONS:
        if v.main_build_id == got:
            return v
    names = ", ".join(v.name for v in VERSIONS)
    raise ValueError(
        f"exefs/main is not a known version of Mario Tennis Fever ({names}; build id {got}). "
        "If it is a newer update, open an issue with this build id."
    )


def modules(exefs: Path) -> list[str]:
    """The game modules present in the ExeFS, in load order (recomp/layout.py ORDER)."""
    sys.path.insert(0, str(ROOT / "recomp"))
    from layout import ORDER

    return [m for m in ORDER if (Path(exefs) / m).is_file()]


def gen_dir_for(v: Version) -> Path:
    """The generated-C dir for a version."""
    return ROOT / f"build/generated-{v.name}"


def default_gen(exefs: Path) -> Path:
    """The generated-C dir for the dump in exefs (from its build id)."""
    return gen_dir_for(detect(exefs))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Name the game version of a dump.")
    ap.add_argument("exefs", nargs="?", type=Path, default=Path("game/exefs"))
    ap.add_argument("--gen-dir", action="store_true", help="print only the generated-C dir for the dump")
    ap.add_argument("--patches", action="store_true", help="print only the patch table for the dump")
    ap.add_argument("--number", action="store_true", help="print only the title version of the dump")
    args = ap.parse_args()
    v = detect(args.exefs)
    if args.gen_dir:
        print(gen_dir_for(v))
    elif args.patches:
        print(v.patches)
    elif args.number:
        print(v.number)
    else:
        print(f"Mario Tennis Fever {v.name} (title version {v.number}), modules {', '.join(modules(args.exefs))}, "
              f"patches {v.patches.name}")
