### What

### Why / issue
<!-- Closes #... -->

### Tested
<!-- OS, GPU, what you checked. For a runtime change, the stop tools/run/boot.py reported before and after. "Not tested" is a valid answer. -->

### Checklist
<!-- Rules behind each item: CONTRIBUTING.md -->
- [ ] Based on current `main`; one topic per PR
- [ ] Nothing of the game: no code, assets, bytes or anything generated from them (`python tools/check_content.py` passes)
- [ ] Recompilation, not emulation: no CPU interpreter or JIT, no GPU emulation below NVN2 at run time
- [ ] Code taken from another project is MIT-compatible and named in the code and in `THIRD_PARTY_NOTICES.md`
- [ ] `uv run pytest -q` and `uv run ruff check` pass (CI runs them too)
- [ ] Docs updated (folder READMEs, `docs/research.md` for findings)
- [ ] AI-assisted: <!-- yes / no -->
