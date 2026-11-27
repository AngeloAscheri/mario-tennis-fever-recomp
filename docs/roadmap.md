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

- [x] mkw-recomp's `sm86/` translator and `tools/shaders/` imported unchanged; the programs a run meets
      (`MKW_SPIRV_DUMP=build/shader-dump`) translate with `tools/shaders/translate.py --dumped build/shader-dump`:
      27 of 27 valid SPIR-V. The first text is drawn. Through the tutorial's court: 438 of 438 (a shadow sampler with a
      bias needed `GL_EXT_texture_shadow_lod`, as textureLod already did).
- [ ] [#11](../../../issues/11) Every program of the game, not only the ones a run met: where Tennis keeps them (`42`, #2).
- [ ] The controller button icons come out as "?": the stand-in fonts lack the Nintendo extension font's glyphs.

## F4 — First picture

- [x] The intro movie plays (VP9 through main's `movie::` library and the SDK's `nn::movie` extractor, decoded with
      libvpx) and the title screen draws on Vulkan.
- [x] The title screen's text samples its font (it read the movie's texture: two texture pools shared one slot table).
- [x] Only some characters of the title screen's text are drawn: the glyph staging texture was taken as written by
      the GPU ([research.md](research.md#the-texts-glyph-cache-27112026)). The button icons stay "?" (the stand-in
      fonts).
- [ ] Some movie frames show blocks of an older picture (the VP9 decode or its frame order).
- [x] After the title screen (A): `CallCommands with a null handle` from `basic+0x11a6b38`. The control memory's usage
      saturated, so the engine took recordings as empty ([research.md](research.md#the-engines-cache-of-recorded-commands-26112026)).
      The run now reaches the court of the first-run tutorial in 3D (60 s, no stop).
- [x] The court's lighting drew a grid of dark triangles: indexed quads were drawn as a triangle list.
- [x] The court is covered by a blue haze: the fog volume's 64 slices were all drawn into its first one, which a
      passthrough geometry program selects per draw. Passthrough geometry programs are translated and drawn
      ([research.md](research.md#geometry-programs-27112026)), with every viewport and scissor; the shadow cascades
      come out with them.
- [ ] The shadow cascades' viewports exceed `maxViewportDimensions` (Vulkan validation): fine on RADV, check other
      drivers; a fix would scale the transform in the geometry stage.
- [ ] Tessellation: 128 programs with tessellation and geometry stages are registered, none drawn up to the
      tutorial's court. The free match (`tools/run/scripts/match.txt`) draws one, indirect, a frame: VS, TCS, TES,
      a full geometry program and FS, most likely the grass's blades
      ([research.md](research.md#past-the-tutorial-a-free-match-27112026)). Translating it needs TCS, TES and
      geometry programs that emit their own vertices.
- [ ] A compute program whose texture handle comes from a uniform register (`tex_scr_urc_`) does not translate.
- [ ] One frame of the main menu's transition into Historia is solid blue.
- [ ] A cutscene of Historia's intro stayed half-way through a cross-fade between two shots for 20 s in one run.
- [x] The grass is speckled with black: an EXIT's own predicate operand was dropped, so the lanes under the
      court's alpha threshold that were not killed exited with 0 as albedo and normal
      ([research.md](research.md#exits-predicate-operand-27112026)).
- [x] The tutorial's message boxes show no text: the same glyph cache ([research.md](research.md#the-texts-glyph-cache-27112026)).
- [ ] Some runs skip the movie and show a black screen with a few glyphs instead: find what decides it.

## F5 — Playable

- [ ] Controllers, audio, movies, saves; a match from start to end. Reached: the tutorial ends and saves, the
      menus, a free match starts and plays (`tools/run/scripts/match.txt`).

## F6 and later

- Stability on more GPUs, performance, Windows build, a setup/launcher, translations of the start screen.
