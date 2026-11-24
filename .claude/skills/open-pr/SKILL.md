---
name: open-pr
description: Turn a finished change in mtf-recomp into a pull request the maintainers can merge - the checks (tests, lint, content guard, a warning-free build), a branch and Conventional Commit message, and a description with what was tested and that it was AI-assisted. Use for "open a PR", "send it", "subir los cambios", "hacer un pull request", "preparar el PR", or when a fix is done.
---

# Open a pull request

The person may never have opened one. Explain what each step does as you go, and do not push or open anything
without their go-ahead: it publishes under their name.

## 1. The checks (all must pass)

```
uv run pytest -q
uv run ruff check
python3 tools/check_content.py          # nothing of the game, no keys, no generated code
grep -c warning build/run/build.log     # after a runtime change: no new warnings (compare with main)
```

If the change touched the runtime or the lifter, `uv run tools/run/boot.py` reached at least as far as before.
If it touched `recomp/`, `uv run tools/cpu/lift_diff.py` agrees on every case.

## 2. Branch and commit

They work on their fork (`gh repo fork --remote` once, if they have the GitHub CLI; otherwise the Fork button on
GitHub and `git remote add`).

```
git switch -c <short-topic>              # from an up-to-date main
git add <only the files of this change>
git commit                               # Conventional Commits, in English
```

Message: `type(scope): what changes`, then a body saying why, with the before/after (the stop `boot.py` reported).
Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`. Scopes: `sdk`, `runtime`, `recomp`, `engine`, `tools`,
`docs`. One topic per pull request; unrelated fixes go in their own.

## 3. The pull request

```
git push -u origin <short-topic>
gh pr create --fill                      # then edit the description from the template
```

The template ([.github/pull_request_template.md](../../../.github/pull_request_template.md)) is the checklist. Fill
"Tested" with the real commands and results, tick "AI-assisted: yes", and link the issue (`Closes #N` only if it
finishes it). Issues and pull requests may be written in Spanish or English.

Then tell the person: a maintainer will review it; answer the comments with new commits on the same branch (no force
push needed); CI must be green.
