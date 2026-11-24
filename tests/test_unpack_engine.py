"""tools/unpack_engine.py decodes nxboot's chunk format, checked on synthetic chunks built by an inverse encoder here.

The encoder writes the same stream the game's decoder reads (flag bytes, literals, matches of each length form, the
end mark) and scrambles it the inverse way, so no byte of the game is needed.
"""

import random

import pytest

import unpack_engine as ue


def test_mt19937_matches_the_reference():
    # std::mt19937 default seed 5489: the 10000th output is 4123659995 (C++ standard, [rand.predef]).
    mt = ue.MT19937(5489)
    first = mt.next()
    for _ in range(9998):
        mt.next()
    assert first == 3499211612
    assert mt.next() == 4123659995


def tokens_for(payload: bytes, rng: random.Random) -> list:
    """Literals and matches (dist, length) that rebuild payload, exercising every length form."""
    out, i, toks = bytearray(), 0, []
    while i < len(payload):
        best = None
        for dist in (1, 2, 3, 7, 64, 300, 4000):
            if dist > len(out):
                continue
            n = 0
            while i + n < len(payload) and n < 1000 and payload[i + n] == (out + payload[i:i + n])[len(out) - dist + n]:
                n += 1
            if n >= 2 and (best is None or n > best[1]):
                best = (dist, n)
        if best and rng.random() < 0.9:
            toks.append(best)
            out += payload[i:i + best[1]]
            i += best[1]
        else:
            toks.append(payload[i])
            out.append(payload[i])
            i += 1
    return toks


def stream_for(tokens: list) -> list[int]:
    """The unscrambled byte stream: groups of 8 tokens behind a negated flag byte, then the end mark."""
    s = []
    for g in range(0, len(tokens), 8):
        group = tokens[g:g + 8]
        bits = 0
        body = []
        for j, t in enumerate(group):
            if isinstance(t, int):
                body.append(t)
                continue
            bits |= 0x80 >> j
            dist, n = t
            if n <= 15:
                nib, extra = n, []
            elif n < 0x110:
                nib, extra = 0, [n - 0x10]
            else:
                m = n - 0x110
                nib, extra = 1, [m & 0xFF, m >> 8]
            body += [(dist & 0xF) << 4 | nib, dist >> 4, *extra]
        if len(group) < 8:
            bits |= 0x80 >> len(group)  # the next token is the end mark: a match flag
            body += [0, 0]
        s += [(-bits) & 0xFF, *body]
    if len(tokens) % 8 == 0:
        s += [(-0x80) & 0xFF, 0, 0]
    return s


def encode(payload: bytes, k: int, rng: random.Random) -> tuple[bytes, int]:
    """A chunk for thread k decoding to payload; returns (buffer, end offset)."""
    stream = stream_for(tokens_for(payload, rng))
    mt = None
    if k == ue.MT_CHUNK:
        mt = ue.MT19937(ue.MT_SEED)
        for _ in range(ue.MT_SKIP):
            mt.next()
    size = len(payload) ^ ue.SIZE_XOR[k]
    tail = [rng.randrange(256) for _ in range(4)]  # end-1 .. end-4: not read but for chaining
    raws = list(tail)
    prev = tail[-1]
    for shift in (24, 16, 8, 0):
        b = size >> shift & 0xFF
        if mt is not None:
            b ^= mt.next() & 0xFF
        prev = b ^ ue.ror8(prev)
        raws.append(prev)
    key, step = ue.key_start(k), ue.key_step(k)
    for v in stream:
        if mt is not None:
            v ^= mt.next() & 0xFF
        prev = v ^ ue.ror8(prev) ^ key
        key = (key + step) & 0xFF
        raws.append(prev)
    pad = bytes(rng.randrange(256) for _ in range(16))
    buf = pad + bytes(reversed(raws))
    return buf, len(buf)


@pytest.mark.parametrize("k", range(ue.CHUNKS))
def test_round_trip(k):
    rng = random.Random(k)
    payload = bytes(rng.choice(b"ABCD\0\xff") for _ in range(3000)) + bytes(600) + bytes(range(256)) * 3
    buf, end = encode(payload, k, rng)
    assert ue.decode_chunk(buf, end, k) == payload


def test_wrong_thread_parameters_fail_loudly():
    rng = random.Random(9)
    payload = bytes(rng.randrange(4) for _ in range(500))
    buf, end = encode(payload, 0, rng)
    with pytest.raises((ValueError, IndexError)):
        ue.decode_chunk(buf, end, 1)
