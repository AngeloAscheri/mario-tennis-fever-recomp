<h1 align="center">mtf-recomp</h1>

<p align="center">
  <b>A static recompilation of <i>Mario Tennis Fever</i> (Nintendo Switch 2) into a native PC program.</b>
</p>

<p align="center">
  <a href="docs/roadmap.md">Roadmap</a> ·
  <a href="docs/research.md">Research notes</a> ·
  <a href="CONTRIBUTING.md">Contributing</a> ·
  <a href="../../issues">Issues</a> ·
  <a href="../../discussions">Discussions</a> ·
  <a href="docs/i18n/README.es.md">Español</a>
</p>

> [!IMPORTANT]
> **No game files are included, and none ever will be.** You need your own copy of *Mario Tennis Fever*, dumped from
> your own console. This repository holds only tools and the runtime; everything made from the game is generated on
> your machine, from your dump, into ignored folders.

## What this is

The goal is the approach of [mkw-recomp](https://github.com/adriadam10/mkw-recomp) (*Mario Kart World*) and
[DKB Recomp](https://github.com/Lucas-blip-png/dkb-pc-recomp) (*Donkey Kong Bananza*): the game's AArch64 code is
translated to C **ahead of time** and compiled for your CPU, with no emulator, interpreter or JIT at run time.
The console's OS and the NVN2 graphics API are reimplemented on top of the host (Vulkan), and the game's shaders are
translated to SPIR-V offline.

Those two projects already solved most of what a Switch 2 game needs (lifting ARMv8.3 code, NVN2 over Vulkan, Ampere
shaders, the Horizon host). *Mario Tennis Fever* is a different engine (Camelot's, not Nintendo EPD's), so what it
needs from us is mostly the game-specific part.

## Status

**It boots.** No picture yet: the engine starts, reads its data and sets up the GPU, then stops at its font set-up. Updated 24 November 2026.

| Phase | | State |
| --- | --- | --- |
| F0 CPU: lift the code | ✅ | `main`, the engine `basic` and `sdk`: 110,000 functions lift with **no unsupported instruction**; 1,541 of 1,542 instruction shapes of the game agree with Unicorn. |
| F0b Unpack the engine | ✅ | `tools/unpack_engine.py` rebuilds the engine from your `main`; its SHA-256 matches the one the game itself registers. |
| F1 OS | 🚧 | On mkw-recomp's runtime, `build/mkw --boot` passes (876 SVCs, 25 threads): nxboot unpacks the engine in the guest (byte for byte the offline copy), the engine's constructors run, it reads its archive, mounts its save, initializes controllers, rumble, motion and audio. |
| F2 NVN2 | 🚧 | The device comes up; the run stops in the engine's font set-up, before the first frame. |
| F3 Shaders | ⏳ | Ampere SM86 → SPIR-V, as in mkw-recomp. |
| F4 Vulkan | ⏳ | First picture. |
| F5 Playable | ⏳ | Input, audio, movies, saves. |

### How the engine is found

`exefs/main` is only a loader the game calls `nxboot`: 0.6 MiB of code and a 12.9 MiB payload. At boot, six threads
unscramble and decompress six chunks of it into one NRO, the engine (`basic.nrs`, 24 MB, 61,000 functions), which
`nxboot` hands to `nn::ro::LoadModule`. `tools/unpack_engine.py` does the same offline, on your machine, from your own
dump, in about a second and a half, and the result's SHA-256 is the one the game's own `.nrr` registers. The format:
[docs/research.md](docs/research.md#the-engine-payload-solved-24112026).

Your dump's facts (no game bytes) in one command:

```
uv run tools/inspect_dump.py <dump>/exefs
```

## How to help

This is the best moment to join: the problems are well bounded and nothing is decided yet. Each open problem has its
own issue; say in it that you are on it, and keep a pull request to one topic.

**New to this, or working with an AI assistant?** Start with [docs/first-steps.md](docs/first-steps.md)
([español](docs/i18n/primeros-pasos.es.md)): the tools say where the game stopped and what to do about it, and the
skills in `.claude/skills/` walk an assistant through each kind of task.

**Reverse engineering**:

- [#2](../../issues/2) **The RomFS archive.** The whole RomFS is one 7.8 GB file, `42`, starting with the magic `CRA.`. Its index format
  matters for the file system host and for modding later.

**Porting** (the engine lifts now):

- [#3](../../issues/3) From the font set-up to the first frame: the next SDK calls Tennis makes that Mario Kart World does not.
- [#5](../../issues/5) Port mkw-recomp's spin-wait finder and fill the patch tables (good first issue).
- Where the engine keeps its shaders, and how many NVN2 entry points it uses that Mario Kart World does not.

**No code needed:** run `tools/inspect_dump.py` on your dump and post the output in [#4](../../issues/4). Other
regions or updates show up as other build ids; every one helps.

Read [CONTRIBUTING.md](CONTRIBUTING.md) first. Its hard rule: nothing that came out of the game goes into the
repository, issues or pull requests. Questions go to [Discussions](../../discussions).

## Building (what exists today)

Linux, Python 3.12+ and [uv](https://docs.astral.sh/uv/). With a decrypted ExeFS from your own dump:

```
git config core.hooksPath tools/git          # the content guard, once
uv run tools/setup.py <dump folder>          # all the steps below in one, then: uv run tools/run/boot.py
uv sync
uv run recomp/versions.py <exefs>            # which version you have
uv run tools/unpack_engine.py <exefs>        # rebuilds the engine into build/, writes build/modules-<version>/
uv run python recomp/gen.py --exefs build/modules-<version>   # lifts main + basic + sdk to C (seconds)
uv run pytest -q                             # the tests, no game needed
uv run tools/make_shared_fonts.py            # stand-in system fonts from a free font, in build/shared-fonts/
uv run tools/build/build.py --exefs build/modules-<version>    # the runtime and the game code: build/mkw
build/mkw --exefs build/modules-<version> --romfs <dump>/romfs --boot
```

The runtime build needs what mkw-recomp's does: `clang`, `lld`, `ninja`, SDL3, Opus, libvpx, zstd, xxHash, the Vulkan
headers and VMA 3.4.0 in `scratchpad/vma/` ([tools/build/README.md](tools/build/README.md)); a Fedora toolbox or
distrobox with those packages works.

Only already-decrypted dumps (ExeFS and RomFS folders) are supported. Formats that need console keys (NSP, XCI, NCA)
are not, and code that asks for keys is not accepted.

## FAQ

**Can I play it?** No. Nothing runs yet; see the status table.

**Which version?** The base game and update 327680 are known (`recomp/versions.py`). Both share the same `sdk`
(NintendoSDK 20.5.17). A dump with another build id prints it: please report it.

**Windows? macOS?** The runtime will come from mkw-recomp, which already runs on Linux and Windows. Linux first.

**How is AI used?** Much of the code and documentation is written with AI coding agents (Claude Code), as in the
projects this one builds on, and checked by running it. AI-assisted pull requests are welcome; you are responsible for
having read and run them. [AGENTS.md](AGENTS.md) is the guide for agents.

## Credits

- [mkw-recomp](https://github.com/adriadam10/mkw-recomp) by adriadam10 and contributors (MIT): the lifter in
  `recomp/` and, later, the runtime.
- [TotK Recomp](https://github.com/valentderah/totk-pc-recomp) by valentderah (MIT) and
  [LAS Recomp](https://github.com/peiikai/LASRecomp) by Peiikai (MIT), where that lifter comes from.
- [DKB Recomp](https://github.com/Lucas-blip-png/dkb-pc-recomp): the Switch 2 research we read (GPL: ideas only, see
  [CONTRIBUTING.md](CONTRIBUTING.md#licenses)).
- [Switchbrew](https://switchbrew.org) and the Switch homebrew community.

The full list with licenses: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## License

[MIT](LICENSE). The license grants nothing for Nintendo's game. mtf-recomp is an independent, non-commercial fan
project, not affiliated with or endorsed by Nintendo or Camelot. *Mario Tennis Fever* and *Nintendo Switch 2* are
trademarks of Nintendo.
