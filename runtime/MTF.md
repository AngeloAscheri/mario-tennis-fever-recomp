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
| `sdk/ov/ov_system.c` | Shared fonts decoded as the pl service keeps them (plain sfnt after the 8-byte header); oe's non-blocking message queue, its event, the default display resolution and its change event; no profile image | The engine passes the font's address straight to nn::fontll, which refused the encoded words (error 0x193). **Worth checking in mkw-recomp too**: its Chinese and Korean text reads the same fonts |
| `gfx/nvn/api/nvn_api_state.c`, `nvn_obj.h`, `nvn_api_cmd.c`, `gfx/vk/exec/vk_exec*.c`, `vk_exec_xfer.c` | `nvnCommandBufferSetCopyImageStride`: a new op (appended, so older captures keep their numbers) and the buffer side's layer stride | Tennis sets it |
| `sdk/ov/ov_input.c` | GetNpadState (one state), controller colours, hid settings that change nothing on the host | Same |
| `sdk/ov/ov_codec.c` | The VP9 decoder's submission-ready event is manual clear and first signaled at `StartVp9Decoder` (then after each accepted Submit and each Acquire); an event pool per clear mode | The engine takes the same event as `movie::VideoDecoder`'s input-ready event and counts one input credit per signal once its decoder is started: the intro movie waited forever. **Worth checking in mkw-recomp too** (1.8.0's movie library) |
| `gfx/nvn/api/nvn_api_obj.c`, `nvn_api.h`, `gfx/vk/exec/vk_exec_ops.c`, `vk_exec_par.c`, `vk_exec_view.c`, `gfx/vk/tex/vk_tex_slots.c` | Each texture and sampler pool takes its own range of the slot table (the first pool base 0); bound handles are read in the pools bound at that point of the replay; sampler slots 16 bits | The movie library's pool registers ids 256 and 257, which replaced the engine's font textures: the title screen's text sampled the video. **Worth checking in mkw-recomp too** if a game there uses a second pool |
| `gfx/nvn/api/nvn_api_cmd.c` | A null handle in Call/CopyCommands names its caller and entry | The next stop, after the title screen |
| `core/diag/impcensus.c` | `MKW_IMPORT_CENSUS` counts the engine's (`basic`) calls into the SDK too | The game's own code is main and the engine |
| `gfx/nvn/host/gfx_window_sdl.c`, `tools/build/icon.py` | Window title "Mario Tennis Fever Recomp", Wayland app id `mtf-recomp`, a tennis-ball icon | With mkw-recomp installed the desktop showed the window as Mario Kart World |

Names stay mkw-recomp's (`MKW_*` switches, `build/mkw`), so fixes can still travel both ways.
