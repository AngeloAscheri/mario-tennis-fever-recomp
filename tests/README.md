# tests

Run with `uv run pytest -q` (seconds). None needs the game: they run in CI on every pull request.

| File | What it checks |
| --- | --- |
| `conftest.py` | Puts `recomp/`, `tools/` and `tools/cpu/` on the import path |
| `test_check_content.py` | The content guard refuses Switch files, the game's archive, the generated-code marker and key lines |
| `test_versions.py` | `recomp/versions.py` finds the known builds by build id and names an unknown one |
| `test_unpack_engine.py` | The engine unpacker on synthetic chunks from an inverse encoder (all six threads, MT19937 against the C++ reference) |
| `test_make_shared_fonts.py` | The stand-in fonts' BFTTF container reads back as the runtime reads it |
| `test_lifter.py` | Plain instructions lift; the ARMv8.1-8.3 classes agree with Unicorn (`tools/cpu/lift_diff.py`) |
