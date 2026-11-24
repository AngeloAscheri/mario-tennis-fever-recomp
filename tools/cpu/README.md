# tools/cpu

| Script | What it does | Usage |
| --- | --- | --- |
| `lift_diff.py` | Differential test of the lifter's newer classes (LSE atomics, CAS/CASP, LDAPR, XPAC, RETAA/RETAB) against Unicorn: equal registers and memory. From mkw-recomp @ c38933e (MIT); builds its harness with clang or Zig's clang (`ziglang`, in the dev group) | `uv run tools/cpu/lift_diff.py [--n 2000]` (~9 s; 2000 of 2000 on 24/11/2026) |
