# tools

| File | What it does |
| --- | --- |
| `check_content.py` | Refuses game content, keys and generated game code (CI and the pre-commit hook) |
| `cpu/` | The lifter's differential test against Unicorn ([cpu/README.md](cpu/README.md)) |
| `inspect_dump.py` | Prints a dump's version, modules, segments, entropy and SDK version, safe to paste in an issue |
| `git/pre-commit` | The hook: `git config core.hooksPath tools/git` |
