# Contributing

Thanks for wanting to help. Not sure where to start? [docs/roadmap.md](docs/roadmap.md) lists the open work in
order, and issues labelled `good first issue` are the small ones. Issues and discussions can be in English or Spanish;
code, comments and commit messages are in English.

## How work is shared

1. **Pick an issue**, or open one for what you want to do. Say in it that you are on it; a maintainer adds the
   `in progress` label so nobody else starts the same thing.
2. **Fork, branch from current `main`**, one topic per branch.
3. **Open a pull request** early as a draft if you want feedback. The template is the checklist.
4. A maintainer reviews it. Follow-up work goes in a new pull request, not in a merged one.

Findings that are not code yet (how a format works, what a function does) are just as welcome: post them in the
issue, or as a pull request to [docs/research.md](docs/research.md).

## Rules of the project

- **Recompilation, not emulation.** No CPU interpreter or JIT at run time, and no GPU emulation below NVN2. If a fix
  seems to need one, it is the wrong fix. (Tools that run offline on your machine, such as a Unicorn differential test
  of the lifter, are fine.)
- **Nothing of the game in the repository.** No game code, assets, keys, dumps, screenshots of disassembly with the
  game's bytes, or C, SPIR-V or data generated from them: not in commits, issues or pull requests. All of that is
  regenerated in `build/` from each user's own copy. Install the hook once: `git config core.hooksPath tools/git`.
  CI runs the same check (`python tools/check_content.py`). Naming an address, a build id, a size or a format is fine;
  pasting the bytes is not.
- **No console keys and no key-based decryption.** Setup reads only an already decrypted dump (ExeFS and RomFS
  folders). Formats that need the console's keys (NSP, XCI, NCA, NSZ, XCZ), and code that asks for keys or runs a tool
  that decrypts with them (hactool, NSTool), are not accepted.
- **No online services.** Nothing that talks to or stands in for Nintendo's online services. Local play stays.
- **The console's behaviour by default.** Options for weaker hardware are options; the default is what the console
  does.
- **Fix, don't switch off.** A feature that causes a bug is fixed where it breaks.

## Licenses

The project is MIT. Code may be copied only from MIT-compatible projects (MIT, BSD, ISC, zlib, Apache-2.0), keeping
its header, naming the source project and commit in the code, and adding a row to
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) in the same pull request. From GPL projects (DKB Recomp as a whole,
Eden, Eglantine, yuzu, oboromi) and from projects without a license: **ideas only, never code**. Files from
mkw-recomp keep their origin in their header.

## Code

- C for the runtime, Python for the tools, run with `uv`. `ruff check` passes (`pyproject.toml`).
- Code under `recomp/` comes from mkw-recomp and is kept close to it so fixes can travel both ways. Changes there say
  why in a comment, and fixes that are not Tennis-specific are worth sending upstream too.
- Generated C is never edited by hand: change the generator.
- Every script starts with a docstring: what it does, why it exists, how to run it.
- Comments say why, not what, and name the measurement or source behind a choice.
- Every new folder gets a `README.md` that names its files.

## Tests

`uv run pytest -q` runs in seconds and needs no game: the content guard, the version table, and the lifter against
Unicorn. CI runs it, `ruff check` and the content guard on every pull request, and a pull request is merged only
when they pass. A change to `recomp/` keeps `uv run tools/cpu/lift_diff.py` at all cases agreeing. New behaviour
comes with a test when it can be checked without the game.

## Commits and pull requests

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat(recomp): ...`,
  `docs(research): ...`), in English.
- One topic per pull request. Say what you tested ("not tested" is a valid answer).
- AI-assisted contributions are welcome. Say so in the pull request; you are responsible for having read and run what
  you send. [AGENTS.md](AGENTS.md) is the guide for coding agents.

## Conduct

Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).
