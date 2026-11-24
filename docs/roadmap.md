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

- [x] mkw-recomp's `runtime/` imported unchanged (dd30104), then adapted (the list: `runtime/MTF.md`).
- [x] Load `nxboot` + `basic` + `sdk`; `nn::ro::LoadModule` answers with the lifted `basic` and runs its constructors.
- [x] RomFS host serving `42` and `.nrr`; save data; the engine's entry runs; `build/mkw --boot` passes.
- [x] [#3](../../../issues/3) The engine's font set-up (the shared fonts are served decoded, as the console does), nn::oe's
      message queue and display resolution, the profile image: a 20 s run ends cleanly, presenting 60 fps.

## F2 — NVN2

- [ ] The NVN2 entry points Tennis asks for that MKW never did: the `nvnProgramBuilder*` family so far (null for now).
- [ ] The NVN2 driver's proc table in Tennis's `sdk` (`version.c` `sdk_name_pool` and friends, 0 for now).

## F3 — Shaders

- [ ] **Next:** every draw is skipped ("no prepared SPIR-V"). Bring mkw-recomp's `sm86/` translator and `tools/shaders/`,
      find where Tennis keeps its shaders (inside `42`, or only as NVN programs at run time).

## F4 — First picture

- [ ] Title screen on Vulkan.

## F5 — Playable

- [ ] Controllers, audio, movies, saves; a match from start to end.

## F6 and later

- Stability on more GPUs, performance, Windows build, a setup/launcher, translations of the start screen.
