---
name: getting-started
description: Set up mtf-recomp from zero on the person's machine and get to their first run of Mario Tennis Fever's port - the Python environment, the build toolchain (or a distrobox/toolbox container), their own dump, tools/setup.py and tools/run/boot.py. Use when someone is new to the project, says "how do I start", "empezar", "primeros pasos", "no sé por dónde empezar", "set up", "install", or when build/game.json is missing.
---

# Getting started

The person may know little about recompilation, C or the Switch. Explain each step in their language (many
contributors write in Spanish), say what it is for in one sentence, and run the commands for them where you can.
Never ask them for game files, keys or a download link, and never offer one: they use their own dump.

## 1. What they need

- Linux (Windows works for mkw-recomp's runtime but this port has only been run on Linux so far).
- `git`, and [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- Their own decrypted dump of Mario Tennis Fever: a folder with `exefs/` (holding `main`, `sdk`, `main.npdm`) and
  `romfs/` (holding `42` and `.nrr/`), for the base game and/or update 327680. Formats that need console keys (NSP,
  XCI, NCA) are not supported, and helping to decrypt them is out of scope: say so and stop there.
- The build toolchain of mkw-recomp: `clang`, `lld`, `ninja`, `ccache` (optional), SDL3, Opus, libvpx, zstd,
  xxHash, the Vulkan headers ([tools/build/README.md](../../../tools/build/README.md)). On an immutable system
  (Bazzite, Silverblue, SteamOS) put them in a container instead:

  ```
  distrobox create -n mtf-dev -i registry.fedoraproject.org/fedora:45
  distrobox enter mtf-dev -- sudo dnf install -y clang lld llvm ninja-build ccache SDL3-devel opus-devel libvpx-devel \
      libzstd-devel xxhash-devel vulkan-headers vulkan-loader-devel python3
  ```

  Then every run takes `--box mtf-dev` (or `export MTF_BOX=mtf-dev` once).
- The VMA header in `scratchpad/vma/` (tools/build/README.md has the curl line and its sha256; check the hash).

## 2. Set up from the dump

```
git config core.hooksPath tools/git          # the hook that keeps game files out of commits
uv sync                                      # Python environment
uv run tools/setup.py "<their dump folder>"  # finds exefs/romfs, rebuilds the engine, lifts the code, makes fonts
```

`setup.py` prints the versions it found and writes `build/game.json`. If it finds no known version, run
`uv run tools/inspect_dump.py <their exefs>` and help them open a "Dump report" issue with that output (it holds no
game bytes).

## 3. First run

```
uv run tools/run/boot.py            # builds build/mkw (~5-10 min the first time) and runs it to its first stop
```

It ends with "reached:" (how far the game got) and "stopped:" (why it stopped), in plain words. That stop is the
current frontier of the port: compare it with the roadmap ([docs/roadmap.md](../../../docs/roadmap.md)) and the open
issues. If it is a call to a console service, the `fix-sdk-call` skill turns it into a pull request.

## 4. Before they change anything

- `uv run pytest -q` passes (seconds, no game needed).
- Read [CONTRIBUTING.md](../../../CONTRIBUTING.md) "Rules of the project" with them, briefly: nothing of the game in
  the repository, issues or pull requests; MIT-compatible code only; console behaviour by default.
- Suggest a `good first issue`, or the stop `boot.py` reports, as the first task.
