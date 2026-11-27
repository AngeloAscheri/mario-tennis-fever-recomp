"""Build build/mkw, run Mario Tennis Fever until it stops, and say in plain words where and why it stopped.

Why: the port moves forward one stop at a time: the game calls something the runtime does not answer yet, the run ends
with a FATAL and a stack. Reading that stack is the part newcomers (and their AI assistants) find hardest, so this
prints the one line that matters and what to do about it: for a call to a console service, the SDK function the game
called, demangled, and where its replacement goes (the fix-sdk-call skill, .claude/skills/fix-sdk-call/SKILL.md).

Needs build/game.json from tools/setup.py. The build needs clang, lld, ninja and mkw-recomp's libraries
(tools/build/README.md); without clang on the host, --box NAME (or MTF_BOX=NAME) builds and runs inside that
distrobox or toolbox container.

Usage: uv run tools/run/boot.py [--name boot] [--seconds 20 | --boot] [--no-build] [--box NAME] [--trace svc,fs]
                                [--spirv-dump DIR]
       uv run tools/run/boot.py --explain build/run/boot.log     # only read a log written before
"""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRAME = re.compile(r"guest frame\s+(\d+): (\w+)\+(0x[0-9a-f]+)(?: \((\S+?)\+0x[0-9a-f]+\))?")
GAME_MODULES = ("main", "basic")


def demangle(names: list[str]) -> list[str]:
    tool = shutil.which("c++filt") or shutil.which("llvm-cxxfilt")
    if not tool or not names:
        return names
    out = subprocess.run([tool], input="\n".join(names), capture_output=True, text=True).stdout.splitlines()
    return out if len(out) == len(names) else names


def frames(lines: list[str]) -> list[tuple[str, int, str | None]]:
    out = []
    for line in lines:
        m = FRAME.search(line)
        if m:
            out.append((m.group(2), int(m.group(3), 16), m.group(4)))
    return out


def sdk_call_from_game(fr: list[tuple[str, int, str | None]]) -> tuple[str, str] | None:
    """(SDK symbol, game caller) of the innermost SDK function the game itself called, from the guest frames."""
    for i in range(len(fr) - 1):
        mod, _, sym = fr[i]
        caller_mod, caller_off, _ = fr[i + 1]
        if mod == "sdk" and sym and caller_mod in GAME_MODULES:
            return sym, f"{caller_mod}+{caller_off:#x}"
    return None


def explain(log: Path) -> int:
    lines = log.read_text(errors="replace").splitlines()
    passed = [ln for ln in lines if "boot: passed" in ln or "first NVN call" in ln]
    fatal = next((i for i, ln in enumerate(lines) if ln.startswith("FATAL:")), None)
    for ln in passed:
        print("reached:", ln.split("] ")[-1])
    if fatal is None:
        print("no FATAL in the log: the run ended by itself (time limit or window closed)." if passed else
              f"no FATAL and no boot checkpoint: read the end of {log}")
        return 0
    head = lines[fatal]
    print(f"stopped: {head[len('FATAL: '):]}")
    fr = frames(lines[fatal:fatal + 60])
    call = sdk_call_from_game(fr)
    if "IPC to a console service" in head and call:
        sym, at = call
        print(f"\nThe game called {demangle([sym])[0]}\n  (symbol {sym}) from {at}.\n"
              "That SDK function talks to a console service, which the runtime does not have: it needs a\n"
              "replacement by name. Add a HOST_OVERRIDE for that symbol in runtime/sdk/ov/ov_mtf.c (or next to its\n"
              "family in runtime/sdk/ov/), returning what the console would. Step by step: the fix-sdk-call skill,\n"
              ".claude/skills/fix-sdk-call/SKILL.md.")
        return 1
    nvn = re.match(r"FATAL: NVN (nvn\w+) is not implemented", head)
    if nvn:
        print(f"\nThe game called the graphics API function {nvn.group(1)}, which the NVN2 front end does not have yet.\n"
              "It goes in runtime/gfx/nvn/api/ (grep its neighbours: a Get/Set pair, the same object), recorded as an op\n"
              "when it is a command buffer call and replayed in runtime/gfx/vk/exec/. Look at how mkw-recomp did the\n"
              "nearest function first; this is a bigger task than an SDK replacement: say so in the issue.")
        return 1
    m = next((re.search(r"in lifted function (\S+) = (\S+)(?: \((\S+?)\+)?", ln) for ln in lines[fatal:fatal + 4]
              if "in lifted function" in ln), None)
    if m:
        where = m.group(2) + (f" ({demangle([m.group(3)])[0]})" if m.group(3) else "")
        print(f"\nA crash inside lifted code ({'the SDK' if where.startswith('sdk') else 'the game'}), at {where}.")
        # the crashing SDK function itself, called straight from the game: the usual missing replacement
        if where.startswith("sdk") and m.group(3) and fr and fr[0][0] in GAME_MODULES and not call:
            call = (m.group(3), f"{fr[0][0]}+{fr[0][1]:#x}")
    if fr:
        names = demangle([s or "" for _, _, s in fr])
        print("guest stack, innermost first:")
        for (mod, off, _), name in zip(fr, names):
            print(f"  {mod}+{off:#x}  {name}")
    if call:
        print(f"\nThe innermost SDK call the game made: {demangle([call[0]])[0]} from {call[1]}.\n"
              "When the crash is inside the SDK below it, that call often needs a replacement too: it reached\n"
              "state a console service would have set up (the fix-sdk-call skill says how to tell).")
    print("\nA crash needs reading, not a replacement: see docs/first-steps.md, \"When it crashes\".")
    return 1


def in_box(box: str | None, cmd: str) -> list[str]:
    if not box:
        return ["bash", "-lc", cmd]
    runner = "distrobox" if shutil.which("distrobox") else "toolbox"
    return [runner, "enter", box, "--", "bash", "-lc", cmd] if runner == "distrobox" else \
        [runner, "run", "-c", box, "bash", "-lc", cmd]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--name", default="boot", help="log name: build/run/NAME.log")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--seconds", type=float, default=20, help="run that long past boot (default 20)")
    mode.add_argument("--boot", action="store_true", help="stop at the first NVN call (the boot checkpoint)")
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--box", default=os.environ.get("MTF_BOX"), help="distrobox/toolbox with the toolchain")
    ap.add_argument("--trace", help="MKW_TRACE: svc, host, fs, gfx, sched... comma separated")
    ap.add_argument("--spirv-dump", type=Path, help="MKW_SPIRV_DUMP: save the programs without SPIR-V here "
                    "(tools/shaders/collect.py)")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--explain", type=Path, help="only explain this log")
    args = ap.parse_args()
    if args.explain:
        return explain(args.explain)
    game_file = ROOT / "build/game.json"
    if not game_file.is_file():
        sys.exit("no build/game.json: run `uv run tools/setup.py <your dump folder>` first")
    game = json.loads(game_file.read_text())
    if not args.box and not shutil.which("clang"):
        sys.exit("no clang on this system: install the toolchain (tools/build/README.md) or pass --box NAME "
                 "(a distrobox/toolbox container that has it; MTF_BOX=NAME remembers it)")
    (ROOT / "build/run").mkdir(parents=True, exist_ok=True)
    log = ROOT / f"build/run/{args.name}.log"
    q = shlex.quote
    steps = [f"cd {q(str(ROOT))}"]
    if not args.no_build:
        steps.append(f"uv run tools/build/build.py --exefs {q(game['modules'])} > build/run/build.log 2>&1 "
                     "|| { tail -30 build/run/build.log; exit 99; }")
    mode = "--boot" if args.boot else f"--seconds {args.seconds:g}"
    env = f"MKW_TRACE={q(args.trace)} " if args.trace else ""
    if args.spirv_dump:
        env += f"MKW_SPIRV_DUMP={q(str(args.spirv_dump.resolve()))} "
    steps.append(f"{env}timeout {args.timeout} build/mkw --exefs {q(game['modules'])} --romfs {q(game['romfs'])} "
                 f"--profile build/run/profile {mode} > {q(str(log))} 2>&1")
    print(f"building and running {game['version']}{' in ' + args.box if args.box else ''} -> {log}")
    r = subprocess.run(in_box(args.box, " && ".join(steps[:-1]) + " && " + steps[-1] if len(steps) > 2
                              else " && ".join(steps)))
    if r.returncode == 99:
        print("the build failed: the errors are above and in build/run/build.log")
        return 1
    return explain(log)


if __name__ == "__main__":
    sys.exit(main())
