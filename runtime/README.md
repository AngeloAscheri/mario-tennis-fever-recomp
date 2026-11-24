# runtime

What will play the console for the generated code. For now only the headers the lifted C includes, from
[mkw-recomp](https://github.com/adriadam10/mkw-recomp) `runtime/cpu/` @ c38933e (MIT; they come in turn from TotK
Recomp, `LICENSE.totk-pc-recomp`, and LAS Recomp). The rest of mkw-recomp's runtime comes over in issue #3.

| Folder | Contents |
| --- | --- |
| `cpu/` | `cpu.h` (guest CPU state and helpers for the generated C), `simd.h` and `simd_fp.h` (NEON/FP in portable C) |
