# Guide for coding agents

Read this before changing mtf-recomp with an AI agent. The rules are those of [CONTRIBUTING.md](CONTRIBUTING.md);
this file says how to work by them.

## What this is

A static recompilation of *Mario Tennis Fever* (Switch 2, AArch64, Camelot's engine) to a native PC program. The
lifter in `recomp/` comes from mkw-recomp (which took it from TotK Recomp and LAS Recomp): AArch64 → C, one C
function per guest function. The runtime will come from mkw-recomp's `runtime/` (Horizon host, SDK replaced by
function name, NVN2 over Vulkan). Plan: [docs/roadmap.md](docs/roadmap.md). Findings: [docs/research.md](docs/research.md).

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

- The user's dump is linked under `game/` (ignored): `game/exefs-base`, `game/exefs-327680`. Never assume a path
  outside the repo.
- `uv run tools/inspect_dump.py <exefs>`: version, modules, segments, entropy, NintendoSDK version.
- `uv run recomp/versions.py <exefs>`: which known build a dump is.
- `uv run python recomp/gen.py --exefs <exefs>`: lifts to `build/generated-<version>/` in seconds.
- mkw-recomp is the reference for everything Switch 2: read how it solved a point before inventing.

## Test without the game first

- `uv run pytest -q`: content guard, versions, lifter (seconds).
- `uv run tools/cpu/lift_diff.py`: every lifter change keeps all cases agreeing with Unicorn.

## Working

- Write down what you expect before a run, and what each outcome would mean.
- Keep `recomp/` close to mkw-recomp's; a Tennis-specific change says why in a comment.
- Code, comments, docs and commit messages are in English; Conventional Commits.
