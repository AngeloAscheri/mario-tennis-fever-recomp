# First steps

For anyone who wants to help and is not a recompilation expert, with or without an AI assistant.
[Español](i18n/primeros-pasos.es.md).

## What the work looks like

The game's code already translates to C (the hard part, solved). What is left is mostly **the runtime answering
everything the game asks of the console**: files, controllers, sound, graphics, system services. The game runs until
it asks something the runtime does not answer yet, and stops there. Each stop fixed moves it further. Most stops are a
small, self-contained change, which is why this project suits newcomers and AI-assisted work.

## Set up (once)

You need Linux, `git`, [uv](https://docs.astral.sh/uv/) and **your own** decrypted dump of Mario Tennis Fever
(`exefs/` and `romfs/` folders). The build needs clang and a few libraries; on Bazzite, Silverblue or SteamOS put them
in a distrobox. The exact commands are in the `getting-started` skill
([.claude/skills/getting-started/SKILL.md](../.claude/skills/getting-started/SKILL.md)); with Claude Code, just say
"help me get started" and it follows it.

```
git clone <your fork of this repository> && cd mario-tennis-fever-recomp
git config core.hooksPath tools/git
uv sync
uv run tools/setup.py "<your dump folder>"
uv run tools/run/boot.py [--box <your distrobox>]
```

The last command builds the port and runs the game until its current stop, then says in plain words where and why.

## Pick something

- **The current stop.** `tools/run/boot.py` names it. If it says "the game called nn::... talks to a console service",
  that is a `fix-sdk-call` task: one replacement function, then run again. See the skill for the steps.
- **Issues labelled [`good first issue`](../../../issues?q=is%3Aopen+label%3A%22good+first+issue%22).** Each has
  what to do, how to check it and a ready prompt for your AI assistant.
- **Research** (labelled `research`): file formats, what a function does. The `reverse-engineer` skill.
- **No code**: run `tools/inspect_dump.py` on a dump of another region or update and post it (issue #4); test on your
  GPU and report how far it gets.

Say in the issue that you take it, so nobody else starts the same thing.

## Working with an AI assistant

The repository is set up for it:

- [AGENTS.md](../AGENTS.md) is the guide every coding agent reads (Claude Code reads it through `CLAUDE.md`).
- `.claude/skills/` holds step-by-step skills Claude Code loads by itself: `getting-started`, `fix-sdk-call`,
  `reverse-engineer`, `open-pr`. Other assistants: point them at the `SKILL.md` that fits.
- The tools print plain explanations instead of raw logs, so an assistant (and you) can act on them.

What stays your job: read what it changed before you send it, run the checks, and say in the pull request that it was
AI-assisted. The maintainers review the code, not who wrote it.

Prompts that work well:

- "Run tools/run/boot.py and fix the next stop following the fix-sdk-call skill."
- "Take issue #N. Read it, tell me your plan before changing anything."
- "Explain what this change does in simple terms before we commit it."

## When it crashes

`boot.py` tells three kinds of stop apart:

1. **A call to a console service** ("talks to a console service"): a missing replacement. `fix-sdk-call`.
2. **A crash inside an SDK function** (`nn::...` in the stack): usually an earlier replacement left out something a
   service would have set up (an object, an event). Look at the innermost SDK call the game made; `fix-sdk-call`
   covers it too.
3. **A crash inside the game's own code** (`basic+0x...` only): needs reading the code. Post `boot.py`'s output in
   an issue (it holds no game bytes); the `reverse-engineer` skill is the way in.

Never paste game files, hex dumps or disassembly listings in issues: addresses and descriptions are enough.

## The rules, in short

Nothing of the game goes into the repository, issues or pull requests. Code from other projects only if
MIT-compatible, credited. The console's behaviour is the default. The full list: [CONTRIBUTING.md](../CONTRIBUTING.md).
