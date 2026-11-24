# Guide for coding agents

Read this before changing mtf-recomp with an AI agent. The rules are those of [CONTRIBUTING.md](CONTRIBUTING.md);
this file says how to work by them.

## What this is

A static recompilation of *Mario Tennis Fever* (Switch 2, AArch64, Camelot's engine) to a native PC program. The
lifter in `recomp/` comes from mkw-recomp (which took it from TotK Recomp and LAS Recomp): AArch64 → C, one C
function per guest function. The runtime will come from mkw-recomp's `runtime/` (Horizon host, SDK replaced by
function name, NVN2 over Vulkan). Plan: [docs/roadmap.md](docs/roadmap.md). Findings: [docs/research.md](docs/research.md).

## Skills

Step-by-step procedures live in `.claude/skills/` (Claude Code loads them; other agents: read the `SKILL.md` that fits):

| Skill | For |
| --- | --- |
| `getting-started` | Setting up from zero: toolchain or container, the dump, `tools/setup.py`, the first run |
| `fix-sdk-call` | The run stopped at an SDK call the runtime does not answer: write its replacement, check the stop moved |
| `reverse-engineer` | What a function or a file format does, written up without the game's bytes |
| `open-pr` | Checks, commit, pull request |

Many contributors are new to this and work through an assistant: explain what you do in their language, show the plan
before large changes, and never push or open a pull request without their go-ahead.

## Hard rules

- **No emulation at run time.** No CPU interpreter or JIT, no GPU emulation below NVN2.
- **Nothing of the game in git.** Game code, assets, keys and anything generated from them (C, SPIR-V, dumps, unpacked
  modules) live in `build/` or `game/`, both ignored. Every file `recomp/gen.py` emits carries `GENERATED_MARKER`;
  `tools/check_content.py --staged` refuses it. Do not paste game bytes (hex dumps, disassembly listings with
  encodings) into issues, pull requests or docs: addresses, sizes, build ids and descriptions are fine.
- **No console keys.** Only decrypted ExeFS/RomFS folders as input. No code that asks for keys or runs hactool/NSTool.
- **Licenses.** MIT-compatible code only, with source and commit cited. GPL projects (DKB Recomp, Eden, Eglantine):
  ideas only.

## Where things are

- `uv run tools/setup.py <dump>` once: rebuilds the engine, lifts the code, writes `build/game.json` (the dump's
  paths). Never assume a path outside the repo: read it from there.
- `uv run tools/run/boot.py [--box NAME]`: builds `build/mkw`, runs to the current stop and explains it.
  `--explain LOG` reads an old log. `uv run tools/analysis/missing_overrides.py`: SDK imports without a replacement.
- `uv run tools/inspect_dump.py <exefs>`: version, modules, segments, entropy, NintendoSDK version.
- `uv run recomp/versions.py <exefs>`: which known build a dump is.
- `uv run tools/unpack_engine.py <exefs>`: rebuilds the engine (`basic`, an NRO) and `build/modules-<version>/`.
- `uv run python recomp/gen.py --exefs build/modules-<version>`: lifts `main`, `basic`, `sdk` in seconds.
- `uv run tools/analysis/plt.py <module> --calls REGEX`: who calls an import.
- mkw-recomp is the reference for everything Switch 2: read how it solved a point before inventing.

## Test without the game first

The runtime build needs the toolchain of `tools/build/README.md`; on this kind of setup it often lives in a
distrobox (`--box NAME`, `MTF_BOX`).


- `uv run pytest -q`: content guard, versions, lifter (seconds).
- `uv run tools/cpu/lift_diff.py`: every lifter change keeps all cases agreeing with Unicorn.

## Working

- Write down what you expect before a run, and what each outcome would mean.
- Keep `recomp/` close to mkw-recomp's; a Tennis-specific change says why in a comment.
- Code, comments, docs and commit messages are in English; Conventional Commits.
