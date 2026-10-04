#!/usr/bin/env python3
"""Seeded trace generators for the six CacheLab workloads.

    python workloads/generate.py ring --seed 1 --out ring.trc
    python workloads/generate.py structs --variant soa
    python workloads/generate.py --all --outdir traces/
"""
import argparse
import pathlib
import random
import sys

DEFAULT_SEED = 1


def _base(rng):
    """64 KB-aligned base address; every pattern stays inside 64 KB of it."""
    return rng.randrange(0x8000) * 0x10000


def ring(rng):
    """1. Sensor ring buffer: 4 KB circular buffer of 4-byte samples, written
    sequentially and then read back sequentially, over 4 laps."""
    base, slots = _base(rng), 4096 // 4
    for _ in range(4):
        for i in range(slots):
            yield "W", base + 4 * i
        for i in range(slots):
            yield "R", base + 4 * i


def movavg(rng):
    """2. Moving-average filter: for each of 1,000 new samples, write it into
    a 64-sample window (256 bytes) and read the whole window."""
    base, window = _base(rng), 64
    for n in range(1000):
        yield "W", base + 4 * (n % window)
        for k in range(window):
            yield "R", base + 4 * k


def structs(rng, variant="aos"):
    """3. Array of structs vs struct of arrays: read one 4-byte field of each
    of 1,000 records. aos: 32-byte records, field read at a 32-byte stride.
    soa: the field stored contiguously, 4-byte stride."""
    base = _base(rng)
    stride = 32 if variant == "aos" else 4
    for i in range(1000):
        yield "R", base + stride * i


def traversal(rng, variant="row"):
    """4. Row vs column traversal: read a 64 x 64 table of 4-byte values
    (16 KB) in row-major (row) or column-major (col) order."""
    base, n = _base(rng), 64
    for a in range(n):
        for b in range(n):
            i, j = (a, b) if variant == "row" else (b, a)
            yield "R", base + 4 * (i * n + j)


def conflict(rng):
    """5. Conflict thrash: two buffers 8 KB apart (a multiple of sets x line
    size), read alternately, 64 bytes (two lines) of each, 4,096 accesses."""
    a = _base(rng)
    b = a + 8192
    for i in range(2048):
        off = 4 * (i % 16)
        yield "R", a + off
        yield "R", b + off


def coldstart(rng):
    """6. Cold start vs steady state: five sequential passes over a 6 KB
    table of 4-byte values (fits the default 8 KB cache)."""
    base = _base(rng)
    for _ in range(5):
        for i in range(6144 // 4):
            yield "R", base + 4 * i


# name -> (function, allowed variants or None)
WORKLOADS = {
    "ring": (ring, None),
    "movavg": (movavg, None),
    "structs": (structs, ("aos", "soa")),
    "traversal": (traversal, ("row", "col")),
    "conflict": (conflict, None),
    "coldstart": (coldstart, None),
}


def variants_of(name):
    """The variants to generate for --all: [None] when a workload has none."""
    allowed = WORKLOADS[name][1]
    return list(allowed) if allowed else [None]


def generate(name, seed=DEFAULT_SEED, variant=None):
    """Return the trace as text. Same arguments, same bytes."""
    if name not in WORKLOADS:
        raise ValueError(f"unknown workload: {name} (choose from {', '.join(WORKLOADS)})")
    func, allowed = WORKLOADS[name]
    if allowed is None and variant is not None:
        raise ValueError(f"workload {name} has no variants")
    if allowed is not None:
        variant = variant or allowed[0]
        if variant not in allowed:
            raise ValueError(f"variant for {name} must be one of {', '.join(allowed)}")

    rng = random.Random(seed)
    entries = func(rng, variant) if allowed else func(rng)
    header = f"# cachelab workload={name} seed={seed}" + (f" variant={variant}" if variant else "")
    lines = [header] + [f"{op} {addr:x}" for op, addr in entries]
    return "\n".join(lines) + "\n"


def _write(path, text):
    # newline="\n" keeps the bytes identical on every platform
    with open(path, "w", newline="\n") as f:
        f.write(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("workload", nargs="?", choices=sorted(WORKLOADS))
    parser.add_argument("--variant")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", type=pathlib.Path, help="output file (default: stdout)")
    parser.add_argument("--all", action="store_true", help="write every workload and variant")
    parser.add_argument("--outdir", type=pathlib.Path, default=pathlib.Path("traces"))
    args = parser.parse_args(argv)

    try:
        if args.all:
            args.outdir.mkdir(parents=True, exist_ok=True)
            for name in WORKLOADS:
                for variant in variants_of(name):
                    stem = f"{name}-{variant}" if variant else name
                    text = generate(name, args.seed, variant)
                    _write(args.outdir / f"{stem}.trc", text)
            return 0
        if not args.workload:
            parser.error("give a workload name or --all")
        text = generate(args.workload, args.seed, args.variant)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.out:
        _write(args.out, text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
