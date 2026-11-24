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

**Day 0: research.** Nothing runs yet. Updated 23 November 2026.

| Phase | | State |
| --- | --- | --- |
| F0 CPU: lift the code | 🚧 | The lifter (from mkw-recomp) translates `sdk` (47,907 functions) and the visible part of `main` with **no unsupported instruction**. But `main` turns out to be a loader: see below. |
| F0b Unpack the engine | 🔍 | **The first open problem.** The game engine is not in `main` as shipped. |
| F1 OS | ⏳ | Boot on mkw-recomp's Horizon host. |
| F2 NVN2 | ⏳ | mkw-recomp's NVN2 front end. |
| F3 Shaders | ⏳ | Ampere SM86 → SPIR-V, as in mkw-recomp. |
| F4 Vulkan | ⏳ | First picture. |
| F5 Playable | ⏳ | Input, audio, movies, saves. |

### The first finding: `main` is a bootstrap

`exefs/main` is a small loader the game calls `nxboot`: **0.6 MiB of code** and a **12.9 MiB `.data` segment with an
entropy of 8.00 bits per byte** (compressed or encrypted; the console's own packer did not even try to LZ4 it). Its
dynamic section asks for a second module, `basic.nrs`, from a build path `nxe/nxapp/Ounce64/LibMASTER`. The real game
engine lives in that payload and is loaded at run time, which a static recompiler cannot see. Details and the open
questions: [docs/research.md](docs/research.md).

Your dump's facts (no game bytes) in one command:

```
uv run tools/inspect_dump.py <dump>/exefs
```

## How to help

This is the best moment to join: the problems are well bounded and nothing is decided yet. Each open problem has its
own issue; say in it that you are on it, and keep a pull request to one topic.

**Reverse engineering** (the most useful right now):

- [#1](../../issues/1) **How `nxboot` loads `basic.nrs`.** Find the code in `main` that reads the payload in `.data`, and what it does to it
  (zstd and LZ4 are imported; is there a cipher in front?). Output wanted: a description of the format and a tool that
  rebuilds `basic.nrs` from the user's own `main`.
- [#2](../../issues/2) **The RomFS archive.** The whole RomFS is one 7.8 GB file, `42`, starting with the magic `CRA.`. Its index format
  matters for the file system host and for modding later.

**Porting** (once `basic.nrs` lifts):

- [#3](../../issues/3) Bring mkw-recomp's `runtime/` over, make it build, and boot to the first SVC.
- [#5](../../issues/5) Port mkw-recomp's spin-wait finder and fill the patch tables (good first issue).
- Lift `basic.nrs` and count what the lifter does not support.

**No code needed:** run `tools/inspect_dump.py` on your dump and post the output in [#4](../../issues/4). Other
regions or updates show up as other build ids; every one helps.

Read [CONTRIBUTING.md](CONTRIBUTING.md) first. Its hard rule: nothing that came out of the game goes into the
repository, issues or pull requests. Questions go to [Discussions](../../discussions).

## Building (what exists today)

Linux, Python 3.12+ and [uv](https://docs.astral.sh/uv/). With a decrypted ExeFS from your own dump:

```
git config core.hooksPath tools/git          # the content guard, once
uv sync
uv run recomp/versions.py <exefs>            # which version you have
uv run python recomp/gen.py --exefs <exefs>  # lifts main + sdk to C in build/generated-<version>/ (seconds)
```

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
