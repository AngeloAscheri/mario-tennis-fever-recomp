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
