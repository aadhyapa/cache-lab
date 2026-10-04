# CacheLab requirements

Fifteen requirements, each testable. Verification is by automated test (T),
inspection (I), or the CI pipeline (CI).

Defaults: 64 sets, 4 ways, 32-byte lines (8 KB), hit cost 1 cycle, miss cost
100 cycles, writeback cost 0.

`tools/trace_matrix.py` reads this table. A requirement whose "Verified by"
cell contains `T:` must have at least one test tagged
`@pytest.mark.req("CL-nnn")`, or the build fails. The result is written to
[traceability.md](traceability.md).

| ID | The simulator shall | Verified by |
|---|---|---|
| CL-001 | Accept sets, ways, line size, hit cycles, miss cycles, and writeback cycles as command-line options. Sets and line size must be powers of two; an invalid configuration prints a message and exits with code 2. | T: valid and invalid configs |
| CL-002 | Split a 32-bit address into tag, set index, and byte offset according to the configuration. | T: table of addresses with hand-computed fields |
| CL-003 | Read a trace of lines `R <hex address>` or `W <hex address>`, skip blank lines and lines starting with `#`, and on a malformed line report its line number and exit with code 2. | T: good, blank, comment, and malformed traces |
| CL-004 | Treat the first access to any line in a cold cache as a miss, and an immediate repeat of the same address as a hit. | T: two-line trace |
| CL-005 | When a set is full, evict the least recently used line. | T: 2-way set with a hand-traced eviction order |
| CL-006 | Use write-back with write-allocate: a write hit sets the dirty bit without a memory write; evicting a dirty line counts one writeback; evicting a clean line counts none. | T: write then evict, read then evict |
| CL-007 | Treat accesses within the same line as hits after the first access to that line. | T: sequential bytes in one line |
| CL-008 | Compute total cycles as hits x hit cycles + misses x miss cycles + writebacks x writeback cycles. | T: expected totals for three small traces |
| CL-009 | Produce byte-identical output for identical configuration and trace, with no dependence on time or randomness. | T: run twice and compare |
| CL-010 | Report accesses, hits, misses, hit rate, writebacks, and total cycles, and emit the same data as JSON with `--json`. | T: parse JSON and compare to text |
| CL-011 | Report per-access cost (min, mean, max) and the worst total cost over any window of N consecutive accesses (`--window N`). | T: trace with a known worst window |
| CL-012 | Exit with code 1 and a message when the trace file is missing; on an empty trace report zero accesses and exit 0. | T: missing and empty files |
| CL-013 | Generate each workload trace reproducibly from a fixed seed, and document each workload's access pattern. | T: same seed gives identical file; I: README |
| CL-014 | Generate a requirement-to-test traceability table from test markers, and fail the build when any requirement has no test. | T: meta-test with a removed marker; CI |
| CL-015 | Build with warnings as errors (`-Wall -Wextra -Werror`) and pass the full test suite under AddressSanitizer and UndefinedBehaviorSanitizer. | CI |
