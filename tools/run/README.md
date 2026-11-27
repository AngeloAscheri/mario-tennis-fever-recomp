# tools/run

| Script | What it does |
| --- | --- |
| `boot.py` | Builds `build/mkw` (in a container with `--box`), runs the game to its current stop and explains it: the SDK call to replace, or the crash's stack, demangled. `--explain LOG` reads an old log |
| `scripts/tutorial.txt` | `MKW_INPUT_SCRIPT`: A every second, from the intro into the tutorial's court (a steady scene for frame dumps near frame 4500) |
| `scripts/match.txt` | `MKW_INPUT_SCRIPT`: ends the tutorial, then Libre: Mario against Donkey Kong on the stadium's grass court; the match starts near frame 3100 |

Both start from a new save, which the first run then writes: run them with an empty profile (`boot.py` uses `build/run/profile`; keep a copy of a fresh one and restore it before each run). `MKW_SHOTS=lo-hi:step` saves small screenshots along the way (`MKW_SHOTS_DIR`).
