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
- `main` imports `ZSTD_decompress`, `LZ4_decompress_safe` and `LZ4_compress_default` from the SDK, and
  `nndetailRoGetRoDataStart/End` (the `nn::ro` machinery for modules loaded at run time).
- The RomFS has a `.nrr` (the registration of modules `nn::ro` may load), one 4 KiB file.
- The lifter takes the visible code without trouble: `main` 1,589 functions and `sdk` 47,907, 0 unsupported
  instructions (`recomp/gen.py`, 5 s on 24 jobs).

### Why it matters

A static recompiler translates the code it can see when it runs. The engine is not visible in the shipped `main`, so
the plan grows a step before everything else: **rebuild `basic.nrs` offline, on the user's machine, from the user's
own `main`**, then lift it like any other module (the layout in `recomp/layout.py` already takes extra modules).

### Open questions

1. Which function in `main` reads the payload, and in what order does it call zstd, LZ4 and anything else? Start
   from the callers of the `ZSTD_decompress` and `LZ4_decompress_safe` import stubs.
2. Is there a cipher in front of the compression? An entropy of exactly 8.00 points that way (zstd and LZ4 output
   usually stays a little below), but a strong compressor alone can reach it.
3. What comes out: an NRO, an NSO-like image, or raw segments that `nxboot` maps itself? Does `nxboot` call
   `nn::ro::LoadModule`, or map code memory directly with SVCs?
4. Does the `.nrr` list the hash of the result? Then the rebuilt module can be checked against it.
5. Is the payload the same scheme in the base game and in the update (they differ in size: 12.60 vs 12.89 MiB)?

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
