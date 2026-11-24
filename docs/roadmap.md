# Roadmap

The open work, in order. Each item becomes one or more issues; the issue says who is on it. Findings go in
[research.md](research.md).

## F0 — CPU: lift the code

- [x] Lifter from mkw-recomp, adapted (`MTF_` marker and switches, `recomp/versions.py` with both known builds).
- [x] `main`, `basic` and `sdk` lift with 0 unsupported instructions (both versions).
- [x] Differential test of the lifter's ARMv8.1-8.3 classes against Unicorn (`tools/cpu/lift_diff.py`, 2000 of 2000, in CI).
- [x] The same over every instruction shape of the game's code (`tools/cpu/lift_game_diff.py`, local, needs the dump): 1,541 of 1,542 agree, the last is `stg`, which Unicorn does not run.
- [ ] [#5](../../../issues/5) Spin waits: find them with mkw-recomp's `tools/cpu/spin_waits.py` and fill `recomp/patches-mtf-*.txt`.

## F0b — Unpack the engine (the first blocker)

- [x] [#1](../../../issues/1) How `nxboot` turns its payload into `basic.nrs` ([research.md](research.md#the-engine-payload-solved-24112026)).
- [x] `tools/unpack_engine.py`: rebuilds it from the user's own `main`; the SHA-256 matches the game's `.nrr`.
- [x] `basic` is a module of `recomp/layout.py` and lifts.

## F1 — OS: boot on the Horizon host

- [ ] [#3](../../../issues/3) Bring mkw-recomp's `runtime/` over (core, cpu, sdk, platform), strip what is Mario Kart World's own.
- [ ] Load `nxboot` + `basic` + `sdk` as the console would; `nn::ro::LoadModule` answers with the lifted `basic`
      (the 14 imports neither module exports are weak and stay null).
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
