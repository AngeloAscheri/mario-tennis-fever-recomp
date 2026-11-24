# tools

| File | What it does |
| --- | --- |
| `check_content.py` | Refuses game content, keys and generated game code (CI and the pre-commit hook) |
| `cpu/` | The lifter's differential test against Unicorn ([cpu/README.md](cpu/README.md)) |
| `unpack_engine.py` | Rebuilds the engine `basic.nrs` from the dump's `main` into `build/engine-<version>/`, and the modules folder `recomp/gen.py` lifts |
| `analysis/plt.py` | Names a module's PLT stubs and lists the call sites of chosen imports |
| `inspect_dump.py` | Prints a dump's version, modules, segments, entropy and SDK version, safe to paste in an issue |
| `git/pre-commit` | The hook: `git config core.hooksPath tools/git` |
