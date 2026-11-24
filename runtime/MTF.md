# What mtf-recomp changes in mkw-recomp's runtime

`runtime/` came from mkw-recomp @ c38933e unchanged (commit dd30104); `git diff dd30104 -- runtime` shows every change.
Each one says `mtf-recomp` in a comment where it is.

| File | Change | Why |
| --- | --- | --- |
| `core/boot/loader.c` | NROs; `R_AARCH64_TLSDESC` | The engine `basic` is an NRO with ten thread-local variables |
| `core/boot/tlsdesc.c` | New: the TLSDESC resolver, a zero-filled block per guest thread | Same |
| `core/boot/version.c`, `version.h` | Rows for the base game and update 327680; `ro_module`, `nvn_module` | Tennis's init_array counts, the engine loaded by nn::ro, its first NVN call |
| `core/boot/boot.c` | The `ro_module`'s DT_INIT runs at nn::ro::LoadModule (`rt_boot_ro_init`); the NVN checkpoint in any module | As ro does on the console |
| `core/kernel/kernel.c`, `core/base/host.h` | `kern_settle`: a replaced service call lets started threads run first | nxboot's unpacking threads read their arguments from its stack, which it reuses after three service calls |
| `sdk/fs/romfs.c` | Only the dump tool's `.listing` files are skipped, not every dot name | The RomFS's `.nrr/nrr.nrr` |
| `sdk/ov/ov_mtf.c` | New: nxboot's nn::fs and nn::ro calls, offline nn::friends | Calls Mario Kart World never makes |
| `sdk/ov/ov_input.c` | GetNpadState (one state), controller colours, hid settings that change nothing on the host | Same |

Names stay mkw-recomp's (`MKW_*` switches, `build/mkw`), so fixes can still travel both ways.
