# cache-lab

A configurable set-associative cache simulator in C++, with a Python/pytest
verification harness and a set of sensor-style workloads.

**Question:** how much can memory access pattern change a loop's timing, and
how bad is the worst case? Safety-critical software is judged on worst-case
timing, not average speed, and a cache hit and a miss differ in cost by roughly
100x.

**Status: first pass complete.** The simulator, 15 requirements with tests, the
workload generators, the experiments and the write-up
([notebooks/results.ipynb](notebooks/results.ipynb)) are done. Stretch goals
(two-level cache, prefetch toggle, viewer) are not started.

## Build and test

```
make test           # build with -Wall -Wextra -Werror, run the tests
make test SAN=1     # same, under AddressSanitizer and UBSan
make matrix         # regenerate docs/traceability.md
make setup          # once: install pandas, matplotlib, notebook
make experiments    # run the workloads, write results/results.csv and results/plots/
```

## Run

```
./build/cache_lab [options] trace.trc
```

| Option | Meaning | Default |
|---|---|---|
| `--sets N` | number of sets (power of two) | 64 |
| `--ways N` | lines per set | 4 |
| `--line-size N` | bytes per line (power of two) | 32 |
| `--hit-cycles N` | cost of a hit | 1 |
| `--miss-cycles N` | cost of a miss | 100 |
| `--writeback-cycles N` | cost of writing back a dirty line | 0 |
| `--window N` | worst total cost over N consecutive accesses | 100 |
| `--json` | print the report as JSON | off |
| `--decode ADDR` | print the tag, set and offset of a hex address, then exit | |

A trace has one access per line: `R <hex address>` or `W <hex address>`. Blank
lines and lines starting with `#` are ignored. Exit codes: 0 ok, 1 trace file
missing, 2 bad option or malformed trace.

The policy is LRU with write-back and write-allocate. Total cycles =
hits x hit cycles + misses x miss cycles + writebacks x writeback cycles.

## Requirements and verification

Fifteen requirements, CL-001 to CL-015, are in
[docs/requirements.md](docs/requirements.md). Every test is tagged with the
requirement it checks (`@pytest.mark.req("CL-005")`).
`tools/trace_matrix.py` builds [docs/traceability.md](docs/traceability.md)
from those tags and fails the build if a requirement has no test. CI runs the
suite with warnings as errors and again under the sanitizers.

This is requirements-driven verification in the style of safety-critical
processes. It does not claim compliance with DO-178C or any other standard.

## Workloads

`workloads/generate.py` writes each trace from a seed. The access pattern is
fixed; the seed chooses where the buffers live (a 64 KB-aligned base address).
The same workload, seed and variant always give a byte-identical file.

```
python workloads/generate.py ring --seed 1 --out ring.trc
python workloads/generate.py structs --variant soa --out soa.trc
python workloads/generate.py --all --outdir traces/
```

The patterns assume the default 32-byte lines and 64 sets. The hypotheses are
predictions to test, not results.

| # | Name | Access pattern | Hypothesis |
|---|---|---|---|
| 1 | `ring` | write 1,024 4-byte slots in order, then read them back; 4 laps over a 4 KB circular buffer | high hit rate after warm-up |
| 2 | `movavg` | for each of 1,000 samples, write one into a 64-sample window and read the whole window | near-perfect hits once the window is resident |
| 3 | `structs` | read one 4-byte field of 1,000 records; `aos`: 32-byte records, `soa`: fields packed together | struct of arrays has far fewer misses |
| 4 | `traversal` | read a 64 x 64 table of 4-byte values; `row` or `col` order | column order misses much more |
| 5 | `conflict` | read two 64-byte regions placed 8 KB apart, alternately, 4,096 accesses | with 1 way nearly every access misses; a second way removes the conflict |
| 6 | `coldstart` | five sequential passes over a 6 KB table | the first pass is far slower than later passes |

## Results

Eight traces (six workloads, two of them with two variants) run through the
simulator at the default cache (64 sets, 4 ways, 32-byte lines = 8 KB; hit 1
cycle, miss 100 cycles). The worst window is the largest total cost over any 100
consecutive accesses; the most it can be is 10,000 cycles.

| Workload | Hit rate | Total cycles | Worst 100-access window |
|---|---|---|---|
| ring | 98.4% | 20,864 | 1,387 |
| movavg | 99.99% | 65,792 | 892 |
| structs, array of structs | 0.0% | 100,000 | 10,000 |
| structs, struct of arrays | 87.5% | 13,375 | 1,387 |
| traversal, row order | 87.5% | 54,784 | 1,387 |
| traversal, column order | 0.0% | 409,600 | 10,000 |
| conflict | 99.9% | 4,492 | 496 |
| coldstart | 97.5% | 26,688 | 1,387 |

What the runs show:

- **Layout alone moves the same work from 13 to 100 cycles per access.** Struct
  of arrays and row-major order have 8x fewer misses than array of structs and
  column order.
- **Buffer placement can cause a large swing.** Two buffers a multiple of
  (sets x line size) apart miss on every access with 1 way (0% hits, 10,000-cycle
  window) and almost never with 2 ways (99.9%, 496).
- **The first run is the worst run.** Coldstart's worst window is 1,387 cycles
  against 100 once warm. With 16-byte lines the cache (4 KB) is smaller than the
  6 KB table, so it never warms up: the hit rate stays at 75%.
- **Averages hide the worst case.** Ring, movavg, conflict and coldstart have a
  worst window 4 to 9 times their mean cost per access.

Per-workload plots are in [results/plots/](results/plots/) and the raw numbers
in [results/results.csv](results/results.csv). The sweeps change one parameter
at a time with 64 sets fixed, so changing ways or line size also changes
capacity. The placement seed does not change the results: the base address is
64 KB aligned, which maps to the same sets.

## Limitations

The cost model is deliberately simple: every hit costs the same and every miss
costs the same. Real hardware also has prefetching, multiple cache levels, and
bus contention, and this model ignores all three. The numbers show how layout
changes hit and miss counts under this model; they are not timing predictions
for any real processor. Out of scope for the first pass: multi-level caches, a
prefetch toggle and a GUI.
