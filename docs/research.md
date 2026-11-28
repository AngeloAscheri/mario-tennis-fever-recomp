# Research notes

What we know about *Mario Tennis Fever*'s executable and data, how we found it, and what is still open. Add to it in
the same pull request as the code that relies on a finding. Facts only, with how they were measured; never bytes of
the game.

## The dump

| | Base game | Update 327680 |
| --- | --- | --- |
| `main` build id | `aaf8a6ef6b7e3c78` | `104bce6874603701` |
| `sdk` build id | `32a9ac1480a6f0e9` | same file |
| NintendoSDK | 20.5.17 | 20.5.17 |
| ExeFS modules | `main`, `sdk`, `rtld`, `main.npdm` | same |
| RomFS | one file, `42`, 7.84 GB | one file, `42`, 8.17 GB |

For comparison: Donkey Kong Bananza 1.0.0 is built on NintendoSDK 19.3.2 and Mario Kart World 1.8.0 on 21.4.0. Tennis
sits between the two, so mkw-recomp's SDK replacements (by function name) should mostly apply. Measured with
`tools/inspect_dump.py` on 23/11/2026.

## `main` is a bootstrap, not the game

`tools/inspect_dump.py` on update 327680:

| Segment | Size | LZ4 in the NSO | Entropy |
| --- | --- | --- | --- |
| `.text` | 0.60 MiB | yes | 6.97 bits/byte |
| `.rodata` | 0.19 MiB | yes | 6.49 |
| `.data` | 12.89 MiB | **no** | **8.00** |

- A whole game in 0.6 MiB of code is impossible: Mario Kart World's `main` is tens of MiB of `.text`.
- From about `main+0xd0000` to the end of `.data`, every 256 KiB window has an entropy of 8.00 bits/byte: the
  payload is compressed or encrypted. The tool that built the NSO compressed `.text` and `.rodata` with LZ4 but left
  `.data` raw (flags `0x1b`, bit 2 clear), which is what it does with incompressible data.
- No `NSO0`, `NRO0`, `MOD0`, ELF or zstd frame magic appears in `.data`.
- The dynamic section's `DT_NEEDED` lists `nnSdk.nss` and **`C:/Subverted/nxe/nxapp/Ounce64/LibMASTER/basic.nrs`**,
  and `.rodata` names the module itself `nxapp/nxboot/MASTER/nxboot.nss`. So `main` is `nxboot`, and the game engine
  (`nxe`, "basic") is a separate module that `nxboot` makes at run time from its payload.
- `main` **exports** (not imports) `ZSTD_decompress`, `LZ4_decompress_safe`, Enlighten (global illumination), the
  `movie` decoders and Geo helpers: nxboot carries middleware the engine links against.
- The RomFS has a `.nrr` (the registration of modules `nn::ro` may load), one 4 KiB file.

## The engine payload (solved, 24/11/2026)

`nxboot`'s boot function (`main+0x660`, the same address in both builds) rebuilds the engine and loads it:

1. Six threads, one per core (`nn::os::CreateThread` with cores 0 to 5), each decoding one chunk of the payload. Their
   entry points are `main+0xdd8`, `+0x10e8`, `+0x13e8`, `+0x16e8`, `+0x1a08` and `+0x1d64`.
2. Each thread reads its chunk's output size, waits on a barrier, thread 0 sums the six sizes and allocates one
   buffer (4 KiB aligned), a second barrier, then each thread unpacks into its place (after the chunks before it).
3. `nn::fs::MountRom`, then the file at an obfuscated path (each character XOR `(int)(sinf(2i) * 255)`, built at
   run time, so no path shows in `strings`) is read whole and given to `nn::ro::RegisterModuleInfo`: the `.nrr`.
4. `nn::ro::GetBufferSize` and `nn::ro::LoadModule` on the unpacked buffer: the engine is an ordinary NRO.

The chunk format, read from the six decoders (all the details and constants are in `tools/unpack_engine.py`):

- A chunk is read **backwards** from its end; the six end addresses sit in `main`'s `.data` (`main+0xcd6e0` ..
  `+0xcd708`).
- Each byte is unscrambled as `ror8(raw byte above it) ^ key ^ raw`; thread `k` starts its key at `0x68 + 8k` and adds
  `0xd + k` per byte. The last chunk also XORs every byte with the low 8 bits of a `std::mt19937` seeded `0x76`
  (first four outputs discarded; a first seeding with `0x1571` is overwritten before use).
- The output size is the 4 bytes below the last 4, chained the same way without the key, XOR a per-thread constant.
- Then LZ77: negated flag bytes (top bit first; 0 a literal, 1 a match), 12-bit distances (0 ends the chunk), 4-bit
  lengths with one- and two-byte extensions.

This is obfuscation, not a console key: everything needed is in the game's own code. The result is checked against the
game itself: **the SHA-256 of the rebuilt NRO is the one the game's `.nrr` registers** (at `.nrr+0x4d0`), for both the
base game and update 327680. `tools/unpack_engine.py` does it in about 1.5 s; `tests/test_unpack_engine.py` checks the
format on synthetic chunks.

## The engine module, `basic`

| | Base game | Update 327680 |
| --- | --- | --- |
| NRO size | 24,211,456 bytes | 24,764,416 bytes |
| NRO build id | `74f247340419ccde` | `250a510a934129cb` |
| `.text` | 18.3 MiB | 18.9 MiB |
| `.rodata` / `.data` / `.bss` | 3.6 / 1.0 / 45.4 MiB | 3.7 / 1.0 / 45.4 MiB |

Lifted with `recomp/gen.py` (update 327680, 8 s on 24 jobs for all three modules):

| Module | Functions | C | Unsupported |
| --- | --- | --- | --- |
| `main` | 1,589 | 11 MB | 0 |
| `basic` | 60,966 | 338 MB | 1, a false one: `basic+0x48` is inside the NRO header (the build id), not code |

The base game's `basic`: 59,286 functions, 329 MB of C, 3 false ones at `basic+0x44..0x4c`, the same header.
| `sdk` | 47,907 | 139 MB | 0 |

`tools/cpu/lift_game_diff.py` runs every instruction shape of the three modules through the lifter's C and Unicorn:
1,541 of 1,542 shapes agree (11,667 words, 8 random states each). The one left is `stg` (an MTE tag store) that
Unicorn does not run; mkw-recomp sees the same on Mario Kart World.

### What the engine links against

`basic`'s 1,203 imports: 1,101 come from `sdk`, 88 from `main` (the middleware above), 14 from neither. Those 14 are
all **weak** and never called directly: the `glslc*` runtime shader compiler (8), gRPC thread-local wrappers (2) and
`nn::pia` zstd trace hooks (4). They resolve to null, as on the console.

Of the `nn::*` imports from `sdk`, mkw-recomp's runtime already replaces 124 by name (most of `nn::ldn`, `nn::socket`,
`nn::oe`, `nn::time`, `nn::account`). The rest run as lifted SDK code over the Horizon host, as in mkw-recomp. The
biggest namespaces: `nn::audio` 151, `nn::os` 93, `nn::hid` 55, `nn::util` 45, `nn::async` 44, `nn::movie` 34.

### The engine's cache of recorded commands (26/11/2026)

The engine records draw commands once per material and replays them each frame (`basic+0x11a5fe0`): each material has
a pair of 16-byte entries `{recorder, handle}`, the main pass and a variant. Its own `CallCommands` (`basic+0x1257338`)
reads the handle at `entry+8` and falls back to `nvnCommandBufferCallCommands`. When a recording ends
(`basic+0x1257224`), it adds how much `nvnCommandBufferGetCommandMemoryUsed` and `GetControlMemoryUsed` grew since its
start; under 9 bytes it takes the recording as empty and stores a null handle. The variant's call path checks the
recorder, not the handle. The recorders start with 256 bytes of control memory and their memory callback
(`basic+0x231c0`) doubles it each time it runs out (256, 512, 1024, 2048).

### Geometry programs (27/11/2026)

143 programs the game registers by the tutorial's court (nvnProgramSetShaders) have a geometry stage (NVN stage 2).
128 of them also have tessellation stages (VS, TCS, TES, GS, FS), but none of those is drawn there: in a 60 s run to
the court (10 764 frames) no draw's program had a tessellation stage and no draw was skipped (corrected 27/11/2026;
this said 141 programs that draw patches). Of the 15 without tessellation, two are drawn, both passthrough programs
(SPH word 0 bit 24):
they set per-primitive outputs and pass the vertices on, ending with NVIDIA's exit handler (`LEPC`, `BMOV` into a
barrier register, `EXIT`, `OUT.FINAL`, `EXIT`):

- the fog volume's: `layer = int(c4[0x20])`, one slice of an 8x8x64 `r11g11b10f` volume per draw (64 draws into a
  64-layer target). The fog pass reads it by distance, `(d - 50) / 1950`; with every slice in layer 0 the whole court
  read the horizon's haze.
- the shadow casters': a viewport mask (`a[0x3a0]`, NV_viewport_array2) read from c10 at an index in c5. The shadow
  map is a 1024x1024 depth array of 4 layers; a first pass binds all 4 with four viewports (one transform per cascade)
  and draws the shared casters once, the next three bind one layer each. The program writes no layer, yet each cascade
  must land in its own layer: viewport-relative layer, read here from SPH byte 0x4f bit 0, which only this program sets
  (eden's header calls the byte OmapReserved). The cascade viewports exceed Vulkan's `maxViewportDimensions` (54391
  wide); RADV draws them right, validation reports it.

SPH output map, VTG layout (byte offsets): 0x35 bit 1 marks a layer output, bits 4-7 the position.

### EXIT's predicate operand (27/11/2026)

The court's grass came out with black specks, 46 % of its pixels at albedo (0, 0, 0) and normal (0, 0, 0), with no
gradient at their edges. The court is one draw (program 4624 on this run, 2048x2048 BC1/BC5/BC4 textures) whose
fragment program tests the albedo texel against a threshold: `FSETP.GEU P0` on it, `FSETP.GT P1` on an attribute
(`> 0`, with `!P0`), `@P1 KILL`, then `@!P0 EXIT` with `P1` as EXIT's own predicate operand. As BRA's (01/11/2026),
that operand must hold together with the guard: the EXIT ends only the lanes the KILL removed. The translator took
the guard alone, so every lane under the threshold exited early with its output registers still 0. Six of the 440
programs met so far carry such an EXIT; none of RET, CALL or BRX does. mkw-recomp's translator has the same gap.

### The text's glyph cache (27/11/2026)

The text is drawn from an 8192x2048 `r8` glyph cache (a block-linear texture in a GPU-only pool, NVN pool flags 0x21).
nn::font rasterises each new glyph with nn::fontll on the CPU into a pitch-linear 8192x2048 `r8` staging texture of
the same size (texture flags IMAGE and LINEAR, a CPU-cached pool), and a compute program loads from that staging image
to fill the cache. The translator reflected every storage image as written by the shader (flag 4), as it once did
every storage buffer: the replay took the staging texture as GPU-written and copied its image (still the first glyphs
it was uploaded with, the `?` of the button icons) back over the CPU's new glyphs after each submission. The text was
laid out (the button icons moved with each language's string widths) but every glyph drew blank. With flag 4 only on
images a SUST, SURED or SUATOM writes, the staging texture is uploaded again each time the CPU writes it, and the
tutorial's messages and the title screen's text draw. Three of the six images in the 440 programs met are load-only.
mkw-recomp's translator marks every image the same way.

nn::fontll answered every lookup the text made; the only misses were the Nintendo extension font's private-use codes
(0xE0xx, the button icons), which the stand-in fonts lack.

### Past the tutorial: a free match (27/11/2026)

`tools/run/scripts/match.txt` ends the tutorial with PLUS and goes through the main menu to Libre, Mario against
Donkey Kong (the CPU picked in the grid: "Al azar" changes the opponent, and so the programs, each run) on the
stadium's grass court. Three stops on the way, now answered: `nn::fs::CommitSaveData` when the tutorial ends; an
abort in `nn::os::CreateThread` (the engine gives a thread a static stack in its .bss, and the kernel's MapMemory only
took heap or alias memory as source, so the SDK's 64 random tries all failed); `nn::nfp::Initialize` (amiibo).

The stadium first drew as white fog and sky only: 701 of 1701 draws a frame had no prepared SPIR-V. With the match's
programs dumped and translated (845 programs, 843 valid), 1840 of 1841 draws run. The one left is the first draw met
with tessellation: an indirect draw of patches into the G-buffer, VS, TCS (quad patches of 4 control points, 7
per-patch attributes, two texture samples), TES, a full geometry program (528 instructions, 11 texture samples, a
4-vertex triangle strip out) and FS: a quad per tessellated point, most likely the grass's blades. The two programs
that do not translate are that geometry program and a compute program whose texture handle comes from a uniform
register (`tex_scr_urc_`; translated now, see "The crowd in the stands").

### Tessellation (27/11/2026)

The free match's grass draws, once a frame, an indirect draw of 4-point patches through VS, TCS, TES, a geometry
program and FS into the G-buffer: tufts of grass blades around the players' feet (with it the grass rises over
Mario's soles; without it it is flat). The TCS reads vertices 0 and 2, samples two array textures for a level and
writes it to all six tessellation levels and to per-patch word 0x18; the TES interpolates the four corners with
gl_TessCoord and passes 0x18 on; the geometry program turns each triangle into a 4-vertex strip.

What the translation rests on (sm86/translate/glsl mem.py vtg_attr, head.py vtg_head):

- ISBERD gives the input vertex's ISBE offset, which ALD's Rb then indexes gl_in[] and in_attr<L>[] by; with the
  primitive index taken as 0 (SR_INVOCATION_INFO's low byte) that is the vertex index (Ryujinx, MIT). The info word's
  bits 16-23 are the vertices of a patch (TCS, TES) or input primitive (GS).
- ALD/AST.P reach the per-patch words: 0x00-0x0c outer levels, 0x10-0x14 inner, 0x18 up the user's vec4s. They take
  Locations from 31 down, since per-patch and per-vertex variables may not share one in Vulkan and the translator sees
  one program at a time. A TCS writes gl_out[gl_InvocationID] and reads outputs back with ALD.O.
- A TES's domain, spacing and winding are not in its code: the driver loads SET_TESSELLATION_PARAMETERS from the
  control section's +0x5c (0x202 here: quads, integer spacing, triangles CW, per NVIDIA's clb197.h, MIT). Vulkan's
  `cw` with the default upper-left domain origin is the hardware's TRIANGLES_CW (Mesa NVK, MIT).
- A 128-bit ALD may name its vertex register among its destinations (`ALD.128 R4, a[0x70], R4`): every word is read
  before any is written, as LDG already did.

The runtime (vk_pipeline.c create_graphics) builds such pipelines whole, one descriptor set, bindings in pipeline
order; NVN's patch size is recorded (OP_PATCH_SIZE). Each stage's gl_in block is fitted to the stage before's output
block (vk_spirv_patch.c spirv_gs_adapt, inputs only): the vertex stage's ClipDistance and CullDistance for the TCS, none
for the TES and the geometry stage, whose blocks the translator writes without them. Vulkan validation passes on the
match (2044 of 2044 draws).

### The crowd in the stands (27/11/2026)

The match's upper stands were empty: only the low stand beside the court, a mesh, had spectators. The rest are
billboards, 35 instanced draws of quads a frame (vertex program reading a 16-byte record per instance and a camera
block at c13). Two faults hid them, one after the other.

**The rectangles.** Each billboard's quad is the visible rectangle of its impostor (u,v min and max), which a compute
program writes before the draws: one workgroup per impostor samples the impostor's texture at mip 1 and reduces the
texels with alpha to a rectangle. Its texture handle is not at a fixed c-bank offset but in a uniform register
(`TEX.URC`), read by a ULDC from c0 at a dynamic address: the program's packed table of bound handles (runtime
gfx_shader_refl.c cs_res), slot gl_WorkGroupID.x. The translator now keeps where such a word came from (mem.py uldc,
`uaddr<n>`) and turns the TEX into an element of an array of the table's textures, reflected as one binding of that
many (tex.py tex_dyn). The same program needed ULEA with a carry out (alu.py ulea), the low word of the record's
64-bit address. Without them the records stayed zero and every quad collapsed to a point.

**The camera.** With sane rectangles (0.30, 0.05 to 0.70, 0.70) the billboards still drew a few hundred pixels in one
corner: their c13 block held a 512x512 orthographic matrix and an identity view, and its contents changed between
submissions and within one (2D at 1280x720, 64x64 icons, the impostors' atlas). Every pass bound the same address for
c13. The engine binds that block from a view of a 1 MiB uniform ring (basic f_70020562d0 asks nvnBufferGetAddress for
it), and it makes the views without the API: it copies the ring's NVNbuffer and adds the view's offset to the field at
+0x18. The NVN2 driver's own procs (the sdk shared by the base game and update 327680, build id 32a9ac14:
BufferBuilderSetStorage sdk+0x5c2c90, BufferInitialize sdk+0x5c2ce0, BufferGetAddress sdk+0x5c2da0; found through its
proc table, the name pool at sdk+0xb9a5aa and the pointers at sdk+0xe056e0) keep the device at +0x8, the pool at +0x10,
the offset at +0x18 and the size at +0x20. The runtime had pool, offset and size at +0x8, +0x10 and +0x18, so the copies
grew in size and kept the ring's base address. With the driver's layout (runtime nvn_api.h buf_t, buf_builder_t) every
view has its own block and the stands fill. mkw-recomp shares the old layout; whether MKW makes views the same way is
not checked.

### Open questions

1. Where does the engine keep its shaders? `nvnProgramSetShaders` is imported; the `sysCustomShader*` names suggest a
   shader library in the RomFS archive.
2. The engine imports `nn::pia` and gRPC: what does it use them for offline, and what must answer for a local match?

## The RomFS archive `42`

The RomFS holds one file, `42`, of 7.84 GB (base) or 8.17 GB (update). It starts with the magic `CRA.`, then a
version-like `u16 2, u16 1` and what look like `(offset, size)` entries. Nothing is known yet beyond that.
Questions: the index format, whether entries are compressed (and with what), and whether the update's `42` is a full
replacement or a patch over the base one.

## Sources

Projects we read or take code from. Code only from MIT-compatible ones (CONTRIBUTING.md, "Licenses").

| Project | License | Good for |
| --- | --- | --- |
| [mkw-recomp](https://github.com/adriadam10/mkw-recomp) | MIT | Everything Switch 2: lifter, Horizon host, SDK by name, NVN2 over Vulkan, SM86 shaders. Our base. |
| [TotK Recomp](https://github.com/valentderah/totk-pc-recomp) | MIT | Where mkw-recomp's lifter and runtime come from. |
| [LAS Recomp](https://github.com/peiikai/LASRecomp) | MIT | The original lifter. |
| [DKB Recomp](https://github.com/Lucas-blip-png/dkb-pc-recomp) | GPL-3.0 (as a whole) | Switch 2 research and notes. Ideas only. |
| [Switchbrew](https://switchbrew.org) | wiki | NSO/NRO/NRR formats, SVCs, services. |
