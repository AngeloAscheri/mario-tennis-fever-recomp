# recomp

Generator: translates the AArch64 code of the game's NSOs to C, one C function per game function.

Copied from [mkw-recomp](https://github.com/adriadam10/mkw-recomp) `recomp/` @ c38933e (MIT, `LICENSE.mkw-recomp`),
which took it from TotK Recomp (`LICENSE.totk-pc-recomp`) and LAS Recomp. Kept close to it so fixes can travel both
ways; ruff does not check it.

Changes against mkw-recomp:

- `gen.py`: the marker is `MTF_RECOMP_…`; the defaults name Tennis's versions.
- `patches.py`: run-time switches take the `MTF_` prefix.
- `versions.py`: new, Tennis's builds (base and update 327680).
- Left out: MKW's patch tables and HUD layout tables (`hud_layouts.py`).

Usage: `uv run python recomp/gen.py --exefs <exefs> --jobs 8` (seconds; writes `build/generated-<version>/`).

| File | What it does |
| --- | --- |
| `nso.py` | Loads an NSO: LZ4 segments, image, MOD0, symbols and relocations |
| `module.py` | A module loaded at a base: `.text` words, function seeds |
| `lifter.py` | AArch64 decoder → C statements per instruction |
| `simd_c.py` | NEON/FP → C |
| `flags.py`, `regs.py` | NZCV and the most used registers in local variables |
| `jumptables.py` | Jump tables resolved symbolically |
| `gen.py` | Generates the C by function, in parallel processes |
| `layout.py` | Load addresses of the modules |
| `patches.py` | Instruction patches by address and spin loops |
| `versions.py` | The game versions the port knows, by `exefs/main`'s build id |
| `patches-mtf-base.txt`, `patches-mtf-327680.txt` | Patch tables per version (empty for now) |
