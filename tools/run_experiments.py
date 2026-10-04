#!/usr/bin/env python3
"""Run the six workloads through the simulator and save results/results.csv.

For every workload (and variant) it sweeps ONE parameter, keeping everything
else at the defaults (64 sets, 4 ways, 32-byte lines, hit 1 cycle, miss 100,
writeback 0, window 100):

  ring, movavg, structs, coldstart   line size 16, 32, 64
  traversal, conflict                ways 1 to 8

Sets stay at 64, so changing ways or line size also changes capacity; the
capacity_bytes column records it. The cost model is never changed.

    python tools/run_experiments.py [--binary build/cache_lab] [--seed 1]
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "workloads"))
import generate  # noqa: E402

LINE_SIZES = [16, 32, 64]
WAYS = list(range(1, 9))
SWEEPS = {
    "ring": ("line_size", LINE_SIZES),
    "movavg": ("line_size", LINE_SIZES),
    "structs": ("line_size", LINE_SIZES),
    "traversal": ("ways", WAYS),
    "conflict": ("ways", WAYS),
    "coldstart": ("line_size", LINE_SIZES),
}
DEFAULTS = {"sets": 64, "ways": 4, "line_size": 32}
FLAGS = {"sets": "--sets", "ways": "--ways", "line_size": "--line-size"}
COLUMNS = ["workload", "variant", "sweep_param", "sweep_value", "sets", "ways", "line_size",
           "capacity_bytes", "accesses", "hits", "misses", "hit_rate", "writebacks",
           "total_cycles", "cost_min", "cost_mean", "cost_max", "window",
           "worst_window_cycles", "seed"]


def simulate(binary, trace_path, config):
    flags = []
    for key, value in config.items():
        flags += [FLAGS[key], str(value)]
    done = subprocess.run([str(binary), "--json", *flags, str(trace_path)],
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"simulator failed ({done.returncode}): {done.stderr.strip()}")
    return json.loads(done.stdout)


def run(binary, seed):
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, (param, values) in SWEEPS.items():
            for variant in generate.variants_of(name):
                trace = pathlib.Path(tmp) / "trace.trc"
                trace.write_text(generate.generate(name, seed, variant), newline="\n")
                for value in values:
                    config = {**DEFAULTS, param: value}
                    report = simulate(binary, trace, config)
                    rows.append({
                        "workload": name, "variant": variant or "", "sweep_param": param,
                        "sweep_value": value, **config,
                        "capacity_bytes": config["sets"] * config["ways"] * config["line_size"],
                        **report, "seed": seed,
                    })
    return pd.DataFrame(rows, columns=COLUMNS)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--binary", type=pathlib.Path,
                        default=pathlib.Path(os.environ.get("CACHE_LAB", ROOT / "build" / "cache_lab")))
    parser.add_argument("--seed", type=int, default=generate.DEFAULT_SEED)
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "results" / "results.csv")
    args = parser.parse_args(argv)

    if not args.binary.exists():
        print(f"error: simulator not found at {args.binary} (run make first)", file=sys.stderr)
        return 2
    df = run(args.binary, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, lineterminator="\n")

    default = df[(df.ways == DEFAULTS["ways"]) & (df.line_size == DEFAULTS["line_size"])]
    print(default[["workload", "variant", "accesses", "hit_rate", "total_cycles",
                   "worst_window_cycles"]].to_string(index=False))
    print(f"\nwrote {len(df)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
