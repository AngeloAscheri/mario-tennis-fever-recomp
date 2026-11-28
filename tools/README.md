# tools

| File | What it does |
| --- | --- |
| `check_content.py` | Refuses game content, keys and generated game code (CI and the pre-commit hook) |
| `cpu/` | The lifter's differential test against Unicorn ([cpu/README.md](cpu/README.md)) |
| `setup.py` | One command from the user's dump: finds ExeFS/RomFS, rebuilds the engine, lifts the code, makes the fonts, writes `build/game.json` |
| `run/boot.py` | Builds `build/mkw`, runs to the current stop and explains it (`--explain LOG` for an old log) |
| `analysis/missing_overrides.py` | The SDK imports of `main` and the engine that no `HOST_OVERRIDE` replaces, by namespace |
| `unpack_engine.py` | Rebuilds the engine `basic.nrs` from the dump's `main` into `build/engine-<version>/`, and the modules folder `recomp/gen.py` lifts |
| `analysis/plt.py` | Names a module's PLT stubs and lists the call sites of chosen imports |
| `make_shared_fonts.py` | Stand-in system shared fonts (BFTTF) from a free font, with button icons of our own, into `build/shared-fonts/`, for nn::pl; `--ext` takes the console's Nintendo extension font |
| `build/`, `i18n/` | mkw-recomp's build (`build/build.py`) and text catalog tools, unchanged |
| `inspect_dump.py` | Prints a dump's version, modules, segments, entropy and SDK version, safe to paste in an issue |
| `git/pre-commit` | The hook: `git config core.hooksPath tools/git` |
