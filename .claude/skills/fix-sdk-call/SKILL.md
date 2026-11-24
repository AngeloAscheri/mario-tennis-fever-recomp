---
name: fix-sdk-call
description: Move Mario Tennis Fever's port one stop further when the run ends at an SDK call the runtime does not answer - read tools/run/boot.py's report, write the HOST_OVERRIDE replacement the console's behaviour calls for, rebuild, check the stop moved, and prepare the change. Use for "IPC to a console service", "replace its SDK call by name", "svc #0x1f", "the next crash", "siguiente parada", "arreglar el siguiente error", "avanzar el arranque", or a crash inside an nn:: SDK function.
---

# Fix the next SDK call

On the console, much of the SDK talks to system services over IPC. The runtime has no services: it replaces those SDK
functions by name (`HOST_OVERRIDE` in `runtime/sdk/ov/`). Mario Kart World's port already replaces ~300; Mario Tennis
Fever calls some it never did, and each one stops the run. This skill is the loop that moves the frontier.

## 1. Find the stop

```
uv run tools/run/boot.py [--box NAME]
```

Its last lines say what to do. Two cases:

- **"The game called nn::X::Y ... talks to a console service"**: the case for this skill. Note the mangled symbol it
  prints.
- **A crash ("access violation") inside an `nn::` function**: often the same thing one step removed: an earlier SDK
  call was answered so that the state a service would have set up is missing (an object, an event, a handle). Look
  at the innermost SDK call the game made (`boot.py` names it) and at its siblings in the same class.
- **A crash inside the game's own code (`basic+...`) with no SDK frame**: not this skill. Report it in the issue with
  `boot.py`'s output and use the `reverse-engineer` skill.

`uv run tools/analysis/missing_overrides.py --ns <namespace>` lists the namespace's other imports without a
replacement: do the whole small family at once when they are obviously alike (all the setters of one service).

## 2. Decide what the console would answer

Read before writing:

1. `grep -rn "<namespace>" runtime/sdk/ov/` - mkw-recomp may replace the same family already: follow its style, its
   helpers (`ret_x`, `arg_x`, `arg_p`, `ST32`, `ST64`, `kern_bind_system_event`) and its result codes.
2. The function's signature, from the demangled name: arguments arrive in `x0..x7` (`arg_x(c, i)`), the return value
   goes in `x0` (`ret_x`). `Result` is 0 for success. An output pointer argument must be written.
3. What the call means on a console with no network and no special hardware. The defaults that keep the game on its
   offline path: settings calls do nothing; "initialize" succeeds; queries return "nothing" (0 entries, false); online
   calls fail with that service's module number (`ov_net.c`, `ov_mtf.c` have examples). Never invent game addresses.
4. If the function returns an object the game will wait on (a `SystemEvent`, a handle), it must be a real one:
   `kern_bind_system_event` creates an `nn::os` system event in runtime memory (see `ov_mtf.c` `bound_event`).

If you cannot tell what the console returns, say so in the code comment and choose the answer that keeps the game
offline and quiet; mention the doubt in the pull request.

## 3. Write it

- Tennis-only calls go in `runtime/sdk/ov/ov_mtf.c`; a call of a family mkw-recomp already has (hid in `ov_input.c`,
  time, account in `ov_system.c`...) goes next to it, under a `// mtf-recomp` comment.
- One comment per function: its signature as the SDK declares it and what the replacement answers, and why.
- `HOST_OVERRIDE("<mangled name exactly as boot.py printed it>", <your function>);`
- A new file or a new kind of change: add its row to `runtime/MTF.md`.

## 4. Check it

```
uv run tools/run/boot.py [--box NAME]
```

The stop must have moved past that call. The build must show no new warning (`grep warning build/run/build.log`).
Write down the old stop and the new one: they go in the pull request. If the same call stops it again, the replacement
is not linked (a typo in the mangled name) or another overload is being called.

## 5. Hand it in

Use the `open-pr` skill. Title like `feat(sdk): answer nn::hid::SetNpadHandheldActivationMode`, and the before/after
stops in the description.
