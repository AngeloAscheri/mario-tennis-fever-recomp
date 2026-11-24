# tools/analysis

| Script | What it does |
| --- | --- |
| `missing_overrides.py` | The SDK imports of `main` and the engine without a `HOST_OVERRIDE`, by `nn::` namespace (`--ns hid` lists them) |
| `plt.py` | Names a module's PLT stubs (JUMP_SLOT relocations) and lists the call sites of chosen imports. Prints addresses and names only |
