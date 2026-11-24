# Roadmap

The open work, in order. Each item becomes one or more issues; the issue says who is on it. Findings go in
[research.md](research.md).

## F0 — CPU: lift the code

- [x] Lifter from mkw-recomp, adapted (`MTF_` marker and switches, `recomp/versions.py` with both known builds).
- [x] `main` (the visible part) and `sdk` lift with 0 unsupported instructions.
- [x] Differential test of the lifter's ARMv8.1-8.3 classes against Unicorn (`tools/cpu/lift_diff.py`, 2000 of 2000, in CI).
- [ ] The same over every instruction shape of Tennis's own code (mkw-recomp's `tools/cpu/lift_game_diff.py`; runs locally, needs the dump).
- [ ] [#5](../../../issues/5) Spin waits: find them with mkw-recomp's `tools/cpu/spin_waits.py` and fill `recomp/patches-mtf-*.txt`.

## F0b — Unpack the engine (the first blocker)

- [ ] [#1](../../../issues/1) Find how `nxboot` (`main`) turns its 12.9 MiB payload into `basic.nrs` ([research.md](research.md#open-questions)).
- [ ] A tool, `tools/unpack_engine.py`, that rebuilds `basic.nrs` from the user's own `main` into `build/`, checked
      against the `.nrr` hash if it is listed there.
- [ ] Lift `basic.nrs` (an extra module in `recomp/layout.py`) and count unsupported instructions.

## F1 — OS: boot on the Horizon host

- [ ] [#3](../../../issues/3) Bring mkw-recomp's `runtime/` over (core, cpu, sdk, platform), strip what is Mario Kart World's own.
- [ ] Load `nxboot` + `basic` + `sdk` as the console would; `nn::ro` answers for the engine module.
- [ ] RomFS host serving `42`; save data; reach `nnMain` of the engine.

## F2 — NVN2

- [ ] mkw-recomp's NVN2 front end; list the NVN2 entry points Tennis asks for that MKW never did.

## F3 — Shaders

- [ ] Find where the game keeps its shaders (inside `42`?), translate SM86 → SPIR-V with mkw-recomp's `sm86/`.

## F4 — First picture

- [ ] Title screen on Vulkan.

## F5 — Playable

- [ ] Controllers, audio, movies, saves; a match from start to end.

## F6 and later

- Stability on more GPUs, performance, Windows build, a setup/launcher, translations of the start screen.
