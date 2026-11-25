#!/usr/bin/env python3
"""Draws the icon of mkw.exe by code (our own: a tennis ball on a court-green rounded square, no art of the game;
mtf-recomp's, in place of mkw-recomp's checkered flag) and writes it as
an .ico with PNG images of 256, 48, 32 and 16 pixels. tools/build/build.py --target windows calls it before the
resource (runtime/platform/mkw.rc names "mkw.ico"); the file is made in build/, never committed. With an .svg name it
writes the same drawing as vector shapes instead (text, so it can be versioned); with a
.png name, one 256-pixel image (the Linux AppImage's icon, tools/build/release.py); with a .c name, the C source of
app_icon_set(SDL_Window *), which gives the window a 128-pixel copy (build.py, every target): Wayland compositors with
xdg_toplevel_icon (KWin) show it in the taskbar instead of a generic icon when no desktop file matches the app id.

Usage: uv run tools/build/icon.py OUT.ico | OUT.svg | OUT.png | OUT.c
"""

import math
import struct
import sys
import zlib
from pathlib import Path

BG_TOP, BG_BOTTOM = (46, 150, 84), (20, 86, 48)   # court green, lighter at the top
BALL, BALL_DARK = (214, 232, 52), (150, 176, 20)   # the ball's felt, lit from the top left
SEAM = (250, 250, 245)
BALL_C, BALL_R = (0.5, 0.5), 0.33                  # the ball in the unit square
SEAM_DX, SEAM_R, SEAM_W = 0.45, 0.30, 0.028        # each seam: an arc of a circle centred beside the ball


def coverage(x: float, y: float) -> tuple[int, int, int, int]:
    """Colour at (x, y) in a unit square, (0, 0) top left; alpha 0 outside the rounded square."""
    r = 0.18   # corner radius
    cx, cy = min(max(x, r), 1 - r), min(max(y, r), 1 - r)
    if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
        return (0, 0, 0, 0)
    bx, by = x - BALL_C[0], y - BALL_C[1]
    d = math.hypot(bx, by)
    if d <= BALL_R:
        for side in (-1, 1):   # the two seams
            if abs(math.hypot(bx - side * SEAM_DX, by) - SEAM_R) <= SEAM_W / 2:
                return (*SEAM, 255)
        t = min(1.0, max(0.0, 0.5 + (bx + by) / (2.4 * BALL_R)))   # 0 at the lit top left, 1 at the far side
        return (*[int(a + (b - a) * t) for a, b in zip(BALL, BALL_DARK)], 255)
    t = y
    return (*[int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)], 255)


def render(size: int, ss: int = 4) -> bytes:
    """RGBA rows, each pixel the mean of ss x ss samples (antialiasing)."""
    rows = bytearray()
    for py in range(size):
        rows.append(0)   # PNG filter: none
        for px in range(size):
            acc = [0, 0, 0, 0]
            for sy in range(ss):
                for sx in range(ss):
                    c = coverage((px + (sx + 0.5) / ss) / size, (py + (sy + 0.5) / ss) / size)
                    a = c[3]
                    acc[0] += c[0] * a
                    acc[1] += c[1] * a
                    acc[2] += c[2] * a
                    acc[3] += a
            a = acc[3]
            rows += bytes([acc[0] // a, acc[1] // a, acc[2] // a, a // (ss * ss)] if a else [0, 0, 0, 0])
    return bytes(rows)


def png(size: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    head = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)   # 8-bit RGBA
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head) + chunk(b"IDAT", zlib.compress(render(size), 9)) + chunk(b"IEND", b"")


def svg() -> str:
    """The icon as SVG in a 256-unit square: the ball a circle, its seams two circles clipped to it."""
    s = 256
    hexc = lambda c: "#%02x%02x%02x" % c   # noqa: E731
    cx, cy, br = BALL_C[0] * s, BALL_C[1] * s, BALL_R * s
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s} {s}" width="{s}" height="{s}">',
        f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{hexc(BG_TOP)}"/>'
        f'<stop offset="1" stop-color="{hexc(BG_BOTTOM)}"/></linearGradient>'
        f'<linearGradient id="ball" x1="0" y1="0" x2="1" y2="1"><stop offset="0.2" stop-color="{hexc(BALL)}"/>'
        f'<stop offset="1" stop-color="{hexc(BALL_DARK)}"/></linearGradient>'
        f'<clipPath id="in"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="{br:.1f}"/></clipPath></defs>',
        f'<rect width="{s}" height="{s}" rx="{0.18 * s:.1f}" fill="url(#bg)"/>',
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{br:.1f}" fill="url(#ball)"/>',
    ]
    for side in (-1, 1):
        out.append(f'<circle cx="{cx + side * SEAM_DX * s:.1f}" cy="{cy:.1f}" r="{SEAM_R * s:.1f}" fill="none" '
                   f'stroke="{hexc(SEAM)}" stroke-width="{SEAM_W * s:.1f}" clip-path="url(#in)"/>')
    return "\n".join([*out, "</svg>", ""])


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    if sys.argv[1].endswith(".svg"):
        Path(sys.argv[1]).write_text(svg())
        return
    if sys.argv[1].endswith(".png"):
        Path(sys.argv[1]).write_bytes(png(256))
        return
    if sys.argv[1].endswith(".c"):
        n = 128
        rows = render(n)
        px = b"".join(rows[y * (n * 4 + 1) + 1 : (y + 1) * (n * 4 + 1)] for y in range(n))   # without the filter bytes
        body = ",".join(str(b) for b in px)
        Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
        Path(sys.argv[1]).write_text(
            "// Drawn by tools/build/icon.py: the window's icon, RGBA rows. Generated, never committed.\n"
            "#include <SDL3/SDL.h>\n"
            f"static const unsigned char px[{len(px)}] = {{{body}}};\n"
            "void app_icon_set(SDL_Window *w) {\n"
            f"    SDL_Surface *s = SDL_CreateSurfaceFrom({n}, {n}, SDL_PIXELFORMAT_RGBA32, (void *)px, {n * 4});\n"
            "    if (s) SDL_SetWindowIcon(w, s), SDL_DestroySurface(s);   // SDL keeps a copy\n"
            "}\n"
        )
        return
    sizes = (256, 48, 32, 16)
    images = [png(s) for s in sizes]
    out = struct.pack("<HHH", 0, 1, len(images))
    off = 6 + 16 * len(images)
    for s, data in zip(sizes, images):
        out += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(data), off)
        off += len(data)
    Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
    Path(sys.argv[1]).write_bytes(out + b"".join(images))


if __name__ == "__main__":
    main()
