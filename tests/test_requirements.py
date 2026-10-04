import json
import subprocess

import pytest

GOOD_TRACE = "R 10\nW 0x20\n"


@pytest.mark.req("CL-001")
def test_valid_config_is_accepted(run_sim):
    code, _, err = run_sim(
        GOOD_TRACE, "--sets", "128", "--ways", "8", "--line-size", "64",
        "--hit-cycles", "2", "--miss-cycles", "50", "--writeback-cycles", "10",
    )
    assert code == 0, err


@pytest.mark.req("CL-001")
@pytest.mark.parametrize("flags, message", [
    (["--sets", "48"], "sets must be a power of two"),
    (["--line-size", "24"], "line size must be a power of two"),
    (["--ways", "0"], "ways must be at least 1"),
    (["--ways", "abc"], "invalid value for --ways"),
    (["--bogus", "1"], "unknown option"),
])
def test_invalid_config_exits_2_with_message(run_sim, flags, message):
    code, _, err = run_sim(GOOD_TRACE, *flags)
    assert code == 2
    assert message in err


@pytest.mark.req("CL-003")
def test_blank_and_comment_lines_are_skipped(run_sim):
    code, _, err = run_sim("# header\n\nR 10\n   \n# more\nW 20\n")
    assert code == 0, err


@pytest.mark.req("CL-003")
@pytest.mark.parametrize("trace, line", [
    ("R 10\nX 20\n", 2),
    ("# c\n\nR zz\n", 3),
    ("R\n", 1),
    ("R 10 20\n", 1),
    ("R 1ffffffff\n", 1),
])
def test_malformed_line_reports_line_number_and_exits_2(run_sim, trace, line):
    code, _, err = run_sim(trace)
    assert code == 2
    assert f"line {line}:" in err


@pytest.mark.req("CL-012")
def test_missing_trace_file_exits_1(run_sim, tmp_path):
    done = subprocess.run([run_sim.binary, str(tmp_path / "nope.trc")],
                          capture_output=True, text=True)
    assert done.returncode == 1
    assert "cannot open trace file" in done.stderr


@pytest.mark.req("CL-012")
def test_empty_trace_reports_zero_accesses_and_exits_0(run_sim):
    code, out, err = run_sim("")
    assert code == 0, err
    stats = json.loads(run_sim("", "--json")[1])
    assert stats["accesses"] == 0
    assert stats["total_cycles"] == 0
    assert "accesses: 0" in out


# ---- helpers -------------------------------------------------------------

# One set, two ways, 16-byte lines: easy to reason about by hand.
TINY = ["--sets", "1", "--ways", "2", "--line-size", "16"]
# One set, one way: every different line conflicts.
DIRECT = ["--sets", "1", "--ways", "1", "--line-size", "16"]


def stats_for(run_sim, trace, *flags):
    code, out, err = run_sim(trace, "--json", *flags)
    assert code == 0, err
    return json.loads(out)


def trace_of(*entries):
    return "".join(f"{e}\n" for e in entries)


# ---- CL-002: address decode ------------------------------------------------

@pytest.mark.req("CL-002")
@pytest.mark.parametrize("flags, addr, tag, set_, offset", [
    # default: 64 sets, 32-byte lines -> 5 offset bits, 6 index bits
    ([], "0x0", 0x0, 0, 0),
    ([], "1f", 0x0, 0, 31),
    ([], "20", 0x0, 1, 0),
    ([], "800", 0x1, 0, 0),
    ([], "0x12345678", 0x2468A, 51, 24),   # hand-computed
    ([], "ffffffff", 0x1FFFFF, 63, 31),
    # 4 sets, 16-byte lines -> 4 offset bits, 2 index bits
    (["--sets", "4", "--line-size", "16"], "ab", 2, 2, 11),
    # direct-mapped single set: no index bits at all
    (DIRECT, "35", 3, 0, 5),
])
def test_address_decode(run_sim, flags, addr, tag, set_, offset):
    code, out, err = run_sim("", "--decode", addr, *flags)
    assert code == 0, err
    assert out.strip() == f"tag=0x{tag:x} set=0x{set_:x} offset=0x{offset:x}"


# ---- CL-004: cold miss, immediate repeat hits -------------------------------

@pytest.mark.req("CL-004")
def test_first_access_misses_and_repeat_hits(run_sim):
    s = stats_for(run_sim, trace_of("R 0", "R 0"))
    assert (s["accesses"], s["misses"], s["hits"]) == (2, 1, 1)


@pytest.mark.req("CL-004")
def test_cold_cache_every_new_line_misses(run_sim):
    s = stats_for(run_sim, trace_of("R 0", "R 20", "R 40"))
    assert (s["misses"], s["hits"]) == (3, 0)


# ---- CL-005: LRU ------------------------------------------------------------

@pytest.mark.req("CL-005")
def test_lru_eviction_order(run_sim):
    # A=0x00 B=0x10 C=0x20 in a 2-way set. Hand trace:
    #  A miss [A]; B miss [A,B]; A hit (B now LRU); C miss evicts B -> [A,C];
    #  B miss evicts A (LRU) -> [C,B]; A miss.
    # FIFO would instead hit on the second B, so this separates LRU from FIFO.
    s = stats_for(run_sim, trace_of("R 0", "R 10", "R 0", "R 20", "R 10", "R 0"), *TINY)
    assert (s["hits"], s["misses"]) == (1, 5)


@pytest.mark.req("CL-005")
def test_hit_refreshes_recency(run_sim):
    # After A B A, B is LRU, so C evicts B and A stays resident.
    s = stats_for(run_sim, trace_of("R 0", "R 10", "R 0", "R 20", "R 0"), *TINY)
    assert (s["hits"], s["misses"]) == (2, 3)


# ---- CL-006: write-back, write-allocate -------------------------------------

@pytest.mark.req("CL-006")
def test_write_then_evict_counts_one_writeback(run_sim):
    s = stats_for(run_sim, trace_of("W 0", "R 10"), *DIRECT, "--writeback-cycles", "10")
    assert (s["misses"], s["writebacks"], s["total_cycles"]) == (2, 1, 210)


@pytest.mark.req("CL-006")
def test_read_then_evict_counts_no_writeback(run_sim):
    s = stats_for(run_sim, trace_of("R 0", "R 10"), *DIRECT, "--writeback-cycles", "10")
    assert (s["misses"], s["writebacks"], s["total_cycles"]) == (2, 0, 200)


@pytest.mark.req("CL-006")
def test_write_hit_sets_dirty_without_memory_write(run_sim):
    # R miss, W hit (dirty, no writeback yet), R conflicting miss -> 1 writeback.
    s = stats_for(run_sim, trace_of("R 0", "W 0", "R 10"), *DIRECT, "--writeback-cycles", "10")
    assert (s["hits"], s["misses"], s["writebacks"]) == (1, 2, 1)
    assert s["total_cycles"] == 1 + 200 + 10


@pytest.mark.req("CL-006")
def test_write_miss_allocates_line(run_sim):
    s = stats_for(run_sim, trace_of("W 0", "R 0"), *DIRECT)
    assert (s["hits"], s["misses"]) == (1, 1)


@pytest.mark.req("CL-006")
def test_replaced_line_starts_clean(run_sim):
    # W 0 dirty -> evicted by R 10 (1 writeback). R 10 is clean, so R 20 adds none.
    s = stats_for(run_sim, trace_of("W 0", "R 10", "R 20"), *DIRECT, "--writeback-cycles", "10")
    assert (s["writebacks"], s["total_cycles"]) == (1, 310)


# ---- CL-007: same-line accesses ---------------------------------------------

@pytest.mark.req("CL-007")
def test_sequential_bytes_in_one_line_hit_after_first(run_sim):
    trace = trace_of(*(f"R {b:x}" for b in range(32)))   # all of one 32-byte line
    s = stats_for(run_sim, trace)
    assert (s["misses"], s["hits"]) == (1, 31)


@pytest.mark.req("CL-007")
def test_next_line_misses_again(run_sim):
    trace = trace_of(*(f"R {b:x}" for b in range(64)))   # two 32-byte lines
    s = stats_for(run_sim, trace)
    assert (s["misses"], s["hits"]) == (2, 62)


# ---- CL-008: cycle model ----------------------------------------------------

COSTS = ["--hit-cycles", "2", "--miss-cycles", "50", "--writeback-cycles", "7"]


@pytest.mark.req("CL-008")
@pytest.mark.parametrize("trace, hits, misses, writebacks, total", [
    (["R 0", "R 0", "R 0"], 2, 1, 0, 1 * 50 + 2 * 2),
    (["W 0", "W 10", "W 0"], 0, 3, 2, 3 * 50 + 2 * 7),
    (["R 0", "W 0", "R 10", "R 10"], 2, 2, 1, 2 * 50 + 2 * 2 + 1 * 7),
])
def test_total_cycles_formula(run_sim, trace, hits, misses, writebacks, total):
    s = stats_for(run_sim, trace_of(*trace), *DIRECT, *COSTS)
    assert (s["hits"], s["misses"], s["writebacks"]) == (hits, misses, writebacks)
    assert s["total_cycles"] == total


# ---- CL-010: report and JSON ------------------------------------------------

def parse_text_report(text):
    return dict(line.split(": ", 1) for line in text.strip().splitlines())


@pytest.mark.req("CL-010")
def test_json_matches_text_report(run_sim):
    trace = trace_of("R 0", "W 0", "R 20", "R 800", "W 20", "R 0")
    code, text, err = run_sim(trace, *DIRECT)
    assert code == 0, err
    code, raw, err = run_sim(trace, "--json", *DIRECT)
    assert code == 0, err
    as_text, as_json = parse_text_report(text), json.loads(raw)
    for key in ("accesses", "hits", "misses", "writebacks", "total_cycles"):
        assert int(as_text[key]) == as_json[key], key
    assert float(as_text["hit_rate"]) == pytest.approx(as_json["hit_rate"])


@pytest.mark.req("CL-010")
def test_report_values(run_sim):
    s = stats_for(run_sim, trace_of("R 0", "R 0", "R 0", "R 20"))
    assert s["accesses"] == 4
    assert (s["hits"], s["misses"]) == (2, 2)
    assert s["hit_rate"] == pytest.approx(0.5)
    assert s["writebacks"] == 0
    assert s["total_cycles"] == 202


# ---- CL-011: per-access cost and worst window -------------------------------

# Costs under the defaults: 100, 1, 1, 100, 100, 1
WINDOW_TRACE = trace_of("R 0", "R 0", "R 0", "R 20", "R 40", "R 0")


@pytest.mark.req("CL-011")
def test_per_access_min_mean_max(run_sim):
    s = stats_for(run_sim, WINDOW_TRACE)
    assert (s["cost_min"], s["cost_max"]) == (1, 100)
    assert s["cost_mean"] == pytest.approx(303 / 6)


@pytest.mark.req("CL-011")
@pytest.mark.parametrize("window, worst", [
    (1, 100),
    (2, 200),    # the two adjacent misses
    (3, 201),
    (6, 303),
    (50, 303),   # window longer than the trace -> whole trace
])
def test_worst_window(run_sim, window, worst):
    s = stats_for(run_sim, WINDOW_TRACE, "--window", str(window))
    assert s["window"] == window
    assert s["worst_window_cycles"] == worst


@pytest.mark.req("CL-011")
def test_window_defaults_to_100_and_zero_is_rejected(run_sim):
    assert stats_for(run_sim, WINDOW_TRACE)["window"] == 100
    code, _, err = run_sim(WINDOW_TRACE, "--window", "0")
    assert code == 2
    assert "window" in err
