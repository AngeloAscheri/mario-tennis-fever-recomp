"""Rebuild the game engine module (basic.nrs, an NRO) from the user's own exefs/main.

Why: Mario Tennis Fever's exefs/main is a loader, nxboot. Its code is 0.6 MiB; the engine is carried in main's
.data as six compressed and scrambled chunks that six threads unpack into one buffer at boot, which nxboot then
hands to nn::ro::LoadModule. A static recompiler only lifts code it can see, so the engine is rebuilt here, offline,
from the user's dump, into build/ (never into the repository). How it was found: docs/research.md, "The engine
payload". No key is involved: every constant below is a parameter of the game's own decoder, read from its code.

The format of one chunk, as nxboot's thread k decodes it (main+0xdd8, +0x10e8, +0x13e8, +0x16e8, +0x1a08, +0x1d64 in
both known builds):
- A chunk is read backwards, from its end (a pointer in main's .data, CHUNK_END_SLOTS) towards lower addresses.
- Every byte is unscrambled as ror8(the raw byte just above it) ^ key ^ raw, key starting at 0x68 + 8k and growing by
  0xd + k (mod 256) per byte. The last chunk also XORs each byte with the low 8 bits of the next std::mt19937 output
  (seeded 0x76, first four outputs discarded).
- The 4 bytes at end-5 .. end-8 (chained the same way, without the key) are the chunk's output size, XOR SIZE_XOR[k].
- Then an LZ77 stream: a flag byte (negated; its bits from the top: 0 a literal, 1 a match), literals, and matches of
  two bytes, a 12-bit distance (0 ends the chunk) and a 4-bit length (0: one more byte + 16; 1: two more bytes,
  + 272; else the length itself).
Chunk k's output follows chunk k-1's; the whole is the NRO.

It also writes build/modules-<version>/: the ExeFS modules (links to the dump) with `basic` beside them, the folder
recomp/gen.py lifts: uv run python recomp/gen.py --exefs build/modules-<version>

Usage: uv run tools/unpack_engine.py <exefs> [--out build/engine-<version>/basic.nro]
"""

import argparse
import hashlib
import struct
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "recomp"))

from nso import R_AARCH64_RELATIVE, Nso  # noqa: E402
from versions import detect  # noqa: E402

CHUNKS = 6
# main's .data slots holding each chunk's end address (RELATIVE relocations), read by thread k. Same in both builds.
CHUNK_END_SLOTS = (0xCD6E0, 0xCD6E8, 0xCD6F0, 0xCD6F8, 0xCD700, 0xCD708)
SIZE_XOR = tuple((0x34 + 4 * k) << 24 | (0x41 + 5 * k) << 16 | (0x4E + 6 * k) << 8 | (0x5B + 7 * k) for k in range(6))
MT_CHUNK, MT_SEED, MT_SKIP = 5, 0x76, 4


def key_start(k: int) -> int:
    return 0x68 + 8 * k


def key_step(k: int) -> int:
    return 0xD + k


class MT19937:
    """std::mt19937 (the 32-bit Mersenne Twister), seeded as std::mt19937(seed) does."""

    def __init__(self, seed: int):
        self.mt = [0] * 624
        self.mt[0] = seed & 0xFFFFFFFF
        for i in range(1, 624):
            self.mt[i] = (0x6C078965 * (self.mt[i - 1] ^ self.mt[i - 1] >> 30) + i) & 0xFFFFFFFF
        self.i = 624

    def next(self) -> int:
        if self.i >= 624:
            mt = self.mt
            for j in range(624):
                y = (mt[j] & 0x80000000) | (mt[(j + 1) % 624] & 0x7FFFFFFF)
                mt[j] = mt[(j + 397) % 624] ^ (y >> 1) ^ (0x9908B0DF if y & 1 else 0)
            self.i = 0
        y = self.mt[self.i]
        self.i += 1
        y ^= y >> 11
        y ^= (y << 7) & 0x9D2C5680
        y ^= (y << 15) & 0xEFC60000
        return (y ^ y >> 18) & 0xFFFFFFFF


def ror8(b: int) -> int:
    return (b >> 1 | b << 7) & 0xFF


def chunk_size(data: bytes, end: int, k: int, mt: MT19937 | None) -> int:
    """The output size stored at end-5 .. end-8 of chunk k (big end first)."""
    size = 0
    for at in (end - 4, end - 5, end - 6, end - 7):
        b = ror8(data[at]) ^ data[at - 1]
        if mt is not None:
            b ^= mt.next() & 0xFF
        size = size << 8 | b
    return size ^ SIZE_XOR[k]


def decode_chunk(data: bytes, end: int, k: int) -> bytes:
    """Chunk k ending at `end` (an offset into data), unpacked."""
    mt = None
    if k == MT_CHUNK:
        mt = MT19937(MT_SEED)
        for _ in range(MT_SKIP):
            mt.next()
    size = chunk_size(data, end, k, mt)
    out = bytearray()
    p, prev, key, step = end - 8, data[end - 8], key_start(k), key_step(k)
    mtn = mt.next if mt is not None else None

    def byte() -> int:
        nonlocal p, prev, key
        p -= 1
        raw = data[p]
        v = ror8(prev) ^ key ^ raw
        if mtn is not None:
            v ^= mtn() & 0xFF
        key = (key + step) & 0xFF
        prev = raw
        return v

    while True:
        flags = ((-byte()) & 0xFF) << 24 | 0x800000
        while True:
            if not flags & 0x80000000:
                out.append(byte())
                flags = flags << 1 & 0xFFFFFFFF
                continue
            flags = flags << 1 & 0xFFFFFFFF
            if not flags:
                break  # the sentinel: next flag byte
            b0, b1 = byte(), byte()
            dist = b0 >> 4 | b1 << 4
            if dist == 0:
                if len(out) != size:
                    raise ValueError(f"chunk {k}: {len(out)} bytes out, the header says {size}")
                return bytes(out)
            n = b0 & 0xF
            if n == 0:
                n = byte() + 0x10
            elif n == 1:
                lo = byte()
                n = lo + (byte() << 8) + 0x110
            src = len(out) - dist
            if src < 0:
                raise ValueError(f"chunk {k}: distance {dist} before the start at {len(out)}")
            for i in range(n):
                out.append(out[src + i])


def chunk_ends(nso: Nso) -> list[int]:
    rel = {addr: target for addr, kind, _, target in nso.relocs if kind == R_AARCH64_RELATIVE}
    return [rel[slot] for slot in CHUNK_END_SLOTS]


def unpack(exefs: Path, jobs: int = CHUNKS) -> bytes:
    nso = Nso(str(exefs / "main"))
    ends = chunk_ends(nso)
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        parts = list(pool.map(decode_chunk, [nso.image] * CHUNKS, ends, range(CHUNKS)))
    return b"".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("exefs", type=Path)
    ap.add_argument("--out", type=Path, help="default: build/engine-<version>/basic.nro")
    ap.add_argument("--jobs", type=int, default=CHUNKS)
    args = ap.parse_args()
    version = detect(args.exefs)
    out = args.out or ROOT / f"build/engine-{version.name}/basic.nro"
    t = time.perf_counter()
    nro = unpack(args.exefs, args.jobs)
    magic = nro[0x10:0x14]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(nro)
    print(f"{version.name}: {len(nro):,} bytes, magic {magic!r} at 0x10, sha256 {hashlib.sha256(nro).hexdigest()[:16]}, "
          f"{time.perf_counter() - t:.1f} s -> {out}")
    if magic != b"NRO0":
        print("warning: the result does not start like an NRO", file=sys.stderr)
        return 1
    size = struct.unpack_from("<I", nro, 0x18)[0]
    print(f"NRO header size {size:,} bytes ({'matches' if size == len(nro) else 'DIFFERS from'} the unpacked size)")
    mods = write_modules_dir(args.exefs, out, ROOT / f"build/modules-{version.name}")
    print(f"modules for recomp/gen.py: {mods}")
    return 0


def write_modules_dir(exefs: Path, nro: Path, mods: Path) -> Path:
    """mods/ with links to the ExeFS files and to the rebuilt engine as `basic` (recomp/layout.py ORDER)."""
    mods.mkdir(parents=True, exist_ok=True)
    links = {f.name: f.resolve() for f in Path(exefs).iterdir() if f.is_file() and not f.name.startswith(".")}
    links["basic"] = nro.resolve()
    for name, target in links.items():
        link = mods / name
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(target)
    return mods


if __name__ == "__main__":
    sys.exit(main())
