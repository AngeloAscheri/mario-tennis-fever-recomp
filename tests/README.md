# tests

Run with `uv run pytest -q` (seconds). None needs the game: they run in CI on every pull request.

| File | What it checks |
| --- | --- |
| `conftest.py` | Puts `recomp/`, `tools/` and `tools/cpu/` on the import path |
| `test_check_content.py` | The content guard refuses Switch files, the game's archive, the generated-code marker and key lines |
| `test_versions.py` | `recomp/versions.py` finds the known builds by build id and names an unknown one |
| `test_unpack_engine.py` | The engine unpacker on synthetic chunks from an inverse encoder (all six threads, MT19937 against the C++ reference) |
| `test_make_shared_fonts.py` | The stand-in fonts' BFTTF container reads back as the runtime reads it |
| `test_boot_explain.py` | `tools/run/boot.py` finds the SDK call to replace in a stop's stack |
| `test_lifter.py` | Plain instructions lift; the ARMv8.1-8.3 classes agree with Unicorn (`tools/cpu/lift_diff.py`) |
| `test_glsl_images.py` | Only images a shader stores into are reflected as written (`sm86/translate/glsl`) |
| `test_glsl_pred.py` | A BRA's or EXIT's own predicate holds together with its guard (`sm86/translate/glsl`) |
| `test_glsl_tess.py` | Tessellation programs' layouts from SET_TESSELLATION_PARAMETERS (`sm86/translate/glsl`) |
| `test_docs_check.py` | `tools/docs/check.py` finds the files a folder's README does not name |
