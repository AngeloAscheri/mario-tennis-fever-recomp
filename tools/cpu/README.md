# tools/cpu

| Script | What it does | Usage |
| --- | --- | --- |
| `lift_game_diff.py` | Every instruction shape of the game's modules through the lifter's C and Unicorn: registers, flags, vectors and memory. From mkw-recomp @ c38933e (MIT). Needs the dump | `uv run tools/cpu/lift_game_diff.py --exefs build/modules-327680 --modules main,basic,sdk --per 10 --runs 8` (~12 s; 1,541 of 1,542 shapes on 24/11/2026, the last is `stg`) |
| `lift_diff.py` | Differential test of the lifter's newer classes (LSE atomics, CAS/CASP, LDAPR, XPAC, RETAA/RETAB) against Unicorn: equal registers and memory. From mkw-recomp @ c38933e (MIT); builds its harness with clang or Zig's clang (`ziglang`, in the dev group) | `uv run tools/cpu/lift_diff.py [--n 2000]` (~9 s; 2000 of 2000 on 24/11/2026) |
