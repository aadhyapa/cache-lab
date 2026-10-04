# cache-lab

This is a set-associative cache simulator written in C++. It comes with a pytest test suite and six workloads that I use to run experiments.

## Why I built this

I did a project with a cache in it for CSE 325. I wanted to learn more about how caches work after that. I built my own simulator so I could change the settings and see what happens. Then I wrote some access patterns to test it on.

## The question

I wanted to know how much the memory access pattern changes how long a loop takes. I also wanted to know how bad the worst case can get. A cache hit and a miss differ in cost by about 100 times. Safety-critical software is judged on its worst case, so the average is not enough.

## Status

The first pass is done. The simulator works and has 15 requirements with tests. The workload generators, the experiments and the write-up in [notebooks/results.ipynb](notebooks/results.ipynb) are finished too. I have not started the stretch goals, which are a two-level cache, a prefetch toggle and a viewer.

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
| `--sets N` | This sets the number of sets, which must be a power of two. | 64 |
| `--ways N` | This sets how many lines are in each set. | 4 |
| `--line-size N` | This sets the bytes per line, which must be a power of two. | 32 |
| `--hit-cycles N` | This sets the cost of a hit. | 1 |
| `--miss-cycles N` | This sets the cost of a miss. | 100 |
| `--writeback-cycles N` | This sets the cost of writing back a dirty line. | 0 |
| `--window N` | This sets the window size for the worst total cost over N accesses in a row. | 100 |
| `--json` | This prints the report as JSON. | off |
| `--decode ADDR` | This prints the tag, set and offset of a hex address and then exits. | |

A trace file has one access on each line. Each line is either `R <hex address>` or `W <hex address>`. Blank lines and lines starting with `#` are ignored.

The program exits with 0 on success. It exits with 1 if the trace file is missing. It exits with 2 if an option is bad or the trace is malformed.

The cache uses LRU replacement with write-back and write-allocate. The total cycles are hits x hit cycles + misses x miss cycles + writebacks x writeback cycles.

## Requirements and tests

There are fifteen requirements, CL-001 to CL-015, and they are listed in [docs/requirements.md](docs/requirements.md). Every test is tagged with the requirement it checks, like `@pytest.mark.req("CL-005")`. The script `tools/trace_matrix.py` reads those tags and builds [docs/traceability.md](docs/traceability.md). The build fails if any requirement has no test. CI runs the tests with warnings as errors, and then runs them again under the sanitizers.

I followed the style of requirements-driven verification used in safety-critical work. This does not claim compliance with DO-178C or any other standard.

## Workloads

The script `workloads/generate.py` writes each trace from a seed. The access pattern never changes. The seed only picks where the buffers live, which is a base address aligned to 64 KB. The same workload, seed and variant always give the exact same file.

```
python workloads/generate.py ring --seed 1 --out ring.trc
python workloads/generate.py structs --variant soa --out soa.trc
python workloads/generate.py --all --outdir traces/
```

The patterns assume the default 32-byte lines and 64 sets. The hypotheses below are my predictions, not results.

| # | Name | Access pattern | Hypothesis |
|---|---|---|---|
| 1 | `ring` | It writes 1,024 4-byte slots in order and reads them back, for 4 laps over a 4 KB circular buffer. | I expect a high hit rate after warm-up. |
| 2 | `movavg` | For each of 1,000 samples, it writes one into a 64-sample window and reads the whole window. | I expect nearly perfect hits once the window is loaded. |
| 3 | `structs` | It reads one 4-byte field from each of 1,000 records. The `aos` variant uses 32-byte records and the `soa` variant packs the fields together. | I expect the struct of arrays to have far fewer misses. |
| 4 | `traversal` | It reads a 64 x 64 table of 4-byte values in either `row` or `col` order. | I expect column order to miss much more. |
| 5 | `conflict` | It reads two 64-byte regions that are 8 KB apart, one after the other, for 4,096 accesses. | I expect almost every access to miss with 1 way, and a second way should fix it. |
| 6 | `coldstart` | It makes five passes in order over a 6 KB table. | I expect the first pass to be much slower than the later ones. |

## Results

I ran eight traces through the simulator, which are six workloads with two of them having two variants. I used the default cache, which has 64 sets, 4 ways and 32-byte lines for 8 KB in total. A hit costs 1 cycle and a miss costs 100. The worst window is the largest total cost over any 100 accesses in a row, and it can be at most 10,000 cycles.

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

The runs showed a few things.

- Data layout alone changes the cost of the same work from 13 to 100 cycles per access. The struct of arrays and row order have 8 times fewer misses than the array of structs and column order.
- Where the buffers sit in memory can make a big difference. Two buffers that are a multiple of (sets x line size) apart miss on every access with 1 way. That gives a 0% hit rate and a 10,000-cycle window. With 2 ways the hit rate is 99.9% and the window is 496.
- The first run is the worst one. The worst window for coldstart is 1,387 cycles, and it is 100 once the cache is warm. With 16-byte lines the cache is 4 KB, which is smaller than the 6 KB table, so it never warms up and the hit rate stays at 75%.
- Averages hide the worst case. Ring, movavg, conflict and coldstart all have a worst window that is 4 to 9 times their mean cost per access.

The plots for each workload are in [results/plots/](results/plots/) and the raw numbers are in [results/results.csv](results/results.csv). Each sweep changes one parameter at a time and keeps 64 sets fixed. That means changing the ways or the line size also changes the total capacity. The seed does not change the results, because the base address is aligned to 64 KB and so it maps to the same sets.

## Limitations

The cost model is simple, because every hit costs the same and every miss costs the same. Real hardware also has prefetching, multiple cache levels and bus contention, and my model ignores all three. The numbers show how layout changes the hits and misses in this model. They are not timing predictions for any real processor. I left out multi-level caches, a prefetch toggle and a GUI for now.
