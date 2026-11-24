---
name: reverse-engineer
description: Find out what a part of Mario Tennis Fever's code or data does (a crash in the game's own code, a file format such as the CRA archive "42", where a value lives) with the repo's analysis tools, and write the finding up without publishing any of the game's bytes. Use for "what does this function do", "investigar", "ingeniería inversa", "formato del archivo", "crash in basic+", "research", or work on issues labelled research.
---

# Reverse engineering, safely

Findings are welcome as much as code, but this repository and its issues are public: **describe, never copy.**
Addresses, sizes, build ids, constants that are parameters of an algorithm, field layouts and plain-language
explanations are fine. Hex dumps, disassembly listings with the instruction encodings, extracted files, screenshots of
the game's data and text are not. Keep raw output in `build/` or `scratchpad/` (both ignored) and summarise it.

## Tools in the repo

| Question | Tool |
| --- | --- |
| What is in this dump? | `uv run tools/inspect_dump.py <exefs>` |
| Which import is this `bl`, who calls an import? | `uv run tools/analysis/plt.py build/modules-<v>/<module> [--calls REGEX]` |
| What does this function do? | The lifted C: `grep -n "f_<address>" build/generated-<v>/<module>/*.c` (address = module base + offset, from `build/generated-<v>/layout.json`), or disassemble with capstone (`uv run python -c ...` using `recomp/nso.py` `Nso(path).image`) |
| Which SDK calls have no replacement? | `uv run tools/analysis/missing_overrides.py` |
| Where did the run stop? | `uv run tools/run/boot.py --explain build/run/<name>.log` |
| What happens at run time? | `uv run tools/run/boot.py --trace svc,fs` (`MKW_TRACE`: svc, host, fs, gfx, sched) |

Module bases: `main` 0x7000000000, `basic` 0x7000e00000, `sdk` after them (`layout.json` is the truth). The engine
`basic` exports almost nothing, so its functions have no names: name them by what they do in your notes.

## Method

1. Write down the question and what each possible answer would change in the port.
2. Start from what is named: the SDK imports a function calls, the strings it reads, its callers. `plt.py` turns
   `bl` targets into SDK names.
3. Check a hypothesis against the game, not against intuition: a hash the game itself stores (as the engine's NRO
   was checked against the `.nrr`), a size the header declares, a run that now goes further.
4. Prefer a tool over a description: a decoder that rebuilds something from the user's own dump into `build/`, with a
   test on synthetic data (`tests/test_unpack_engine.py` is the model).

## Writing it up

Add a section to [docs/research.md](../../../docs/research.md): what was found, how it was measured, the open
questions. Link it from the issue. Code that reads a format goes in `tools/` with a docstring saying where the format
was learned (addresses of the game's own reader).
