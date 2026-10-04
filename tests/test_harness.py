"""Tests for the harness"""
import json
import os
import pathlib
import random
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
GENERATE = ROOT / "workloads" / "generate.py"
MATRIX = ROOT / "tools" / "trace_matrix.py"

sys.path.insert(0, str(ROOT / "workloads"))
import generate  # noqa: E402

ALL_WORKLOADS = [(n, v) for n in generate.WORKLOADS for v in generate.variants_of(n)]


def stats_for(run_sim, trace, *flags):
    code, out, err = run_sim(trace, "--json", *flags)
    assert code == 0, err
    return json.loads(out)

def mixed_trace(count=600, seed=7):
    rng = random.Random(seed)
    return "".join(f"{rng.choice('RW')} {rng.randrange(1 << 16):x}\n" for _ in range(count))


@pytest.mark.req("CL-009")
@pytest.mark.parametrize("flags", [
    [],
    ["--json"],
    ["--window", "7"],
    ["--sets", "8", "--ways", "2", "--writeback-cycles", "5", "--json"],
])
def test_identical_runs_are_byte_identical(run_sim, flags):
    trace = mixed_trace()
    first = run_sim(trace, *flags)
    second = run_sim(trace, *flags)
    assert first[0] == 0 and first[1]
    assert first == second


@pytest.mark.req("CL-009")
def test_output_does_not_depend_on_timezone_or_locale(run_sim, tmp_path):
    trace = tmp_path / "mixed.trc"
    trace.write_text(mixed_trace())
    outputs = set()
    for tz, locale in [("UTC", "C"), ("Asia/Tokyo", "de_DE.UTF-8"), ("America/Los_Angeles", "fr_FR.UTF-8")]:
        env = {**os.environ, "TZ": tz, "LC_ALL": locale}
        done = subprocess.run([run_sim.binary, "--json", str(trace)],
                              capture_output=True, text=True, env=env)
        assert done.returncode == 0, done.stderr
        outputs.add(done.stdout)
    assert len(outputs) == 1


# seeded workload generators

def run_generate(*args):
    return subprocess.run([sys.executable, str(GENERATE), *args], capture_output=True, text=True)


@pytest.mark.req("CL-013")
@pytest.mark.parametrize("name, variant", ALL_WORKLOADS)
def test_same_seed_gives_identical_file(tmp_path, name, variant):
    extra = ["--variant", variant] if variant else []
    paths = []
    for i in range(2):
        out = tmp_path / f"run{i}.trc"
        done = run_generate(name, "--seed", "42", *extra, "--out", str(out))
        assert done.returncode == 0, done.stderr
        paths.append(out)
    assert paths[0].read_bytes() == paths[1].read_bytes()
    assert paths[0].stat().st_size > 0


@pytest.mark.req("CL-013")
def test_different_seed_gives_different_placement():
    assert generate.generate("ring", seed=1) != generate.generate("ring", seed=2)


@pytest.mark.req("CL-013")
def test_all_flag_writes_every_workload(tmp_path):
    done = run_generate("--all", "--seed", "3", "--outdir", str(tmp_path))
    assert done.returncode == 0, done.stderr
    assert len(list(tmp_path.glob("*.trc"))) == len(ALL_WORKLOADS)


@pytest.mark.req("CL-013")
@pytest.mark.parametrize("args", [["nosuch"], ["ring", "--variant", "x"], ["structs", "--variant", "zzz"], []])
def test_bad_generator_arguments_exit_nonzero(args):
    assert run_generate(*args).returncode != 0


@pytest.mark.req("CL-013")
@pytest.mark.parametrize("name, variant", ALL_WORKLOADS)
def test_every_workload_is_a_valid_trace(run_sim, name, variant):
    s = stats_for(run_sim, generate.generate(name, seed=5, variant=variant))
    assert s["accesses"] > 0


@pytest.mark.req("CL-013")
def test_ring_and_filter_only_miss_on_first_touch(run_sim):
    ring = stats_for(run_sim, generate.generate("ring"))
    assert (ring["accesses"], ring["misses"]) == (8192, 128) # 4 KB / 32 B
    avg = stats_for(run_sim, generate.generate("movavg"))
    assert (avg["accesses"], avg["misses"]) == (65000, 8) # 256 B window


@pytest.mark.req("CL-013")
def test_struct_of_arrays_misses_far_less_than_array_of_structs(run_sim):
    aos = stats_for(run_sim, generate.generate("structs", variant="aos"))
    soa = stats_for(run_sim, generate.generate("structs", variant="soa"))
    assert (aos["misses"], soa["misses"]) == (1000, 125)


@pytest.mark.req("CL-013")
def test_column_traversal_misses_more_than_row_traversal(run_sim):
    row = stats_for(run_sim, generate.generate("traversal", variant="row"))
    col = stats_for(run_sim, generate.generate("traversal", variant="col"))
    assert row["misses"] == 512 # 16 KB / 32 B
    assert col["misses"] > 4 * row["misses"]


@pytest.mark.req("CL-013")
def test_conflict_thrash_depends_on_ways(run_sim):
    trace = generate.generate("conflict")
    direct = stats_for(run_sim, trace, "--ways", "1")
    two_way = stats_for(run_sim, trace, "--ways", "2")
    assert direct["hits"] == 0 # every access misses
    assert two_way["misses"] == 4 # only the cold misses


@pytest.mark.req("CL-013")
def test_cold_start_is_the_slowest_pass(run_sim):
    trace = generate.generate("coldstart")
    s = stats_for(run_sim, trace, "--window", "1536") # one pass of 1,536 reads
    assert s["misses"] == 192 # 6 KB / 32 B, first pass only
    first_pass = 192 * 100 + (1536 - 192) * 1
    assert s["worst_window_cycles"] == first_pass


# traceability matrix
def run_matrix(*args):
    return subprocess.run([sys.executable, str(MATRIX), *args], capture_output=True, text=True)


def copy_tests(dest, transform=lambda text: text):
    dest.mkdir()
    for path in (ROOT / "tests").glob("test_*.py"):
        (dest / path.name).write_text(transform(path.read_text()))


@pytest.mark.req("CL-014")
def test_matrix_lists_every_requirement_and_passes_on_this_repo(tmp_path):
    out = tmp_path / "matrix.md"
    done = run_matrix("--out", str(out))
    assert done.returncode == 0, done.stderr
    table = out.read_text()
    for n in range(1, 16):
        assert f"| CL-{n:03d} |" in table
    assert "MISSING" not in table
    assert "15 of 15 requirements covered" in table


@pytest.mark.req("CL-014")
def test_matrix_fails_when_a_requirement_loses_its_test_marker(tmp_path):
    marker = '@pytest.mark.req("CL-011")\n'
    copy = tmp_path / "tests"
    copy_tests(copy, lambda text: text.replace(marker, ""))
    out = tmp_path / "matrix.md"
    done = run_matrix("--tests", str(copy), "--out", str(out))
    assert done.returncode == 1
    assert "CL-011 has no test" in done.stderr
    assert "MISSING TEST" in out.read_text()


@pytest.mark.req("CL-014")
def test_matrix_fails_on_a_marker_for_an_unknown_requirement(tmp_path):
    copy = tmp_path / "tests"
    copy_tests(copy)
    (copy / "test_typo.py").write_text(
        'import pytest\n\n@pytest.mark.req("CL-099")\ndef test_typo():\n    pass\n')
    done = run_matrix("--tests", str(copy), "--out", str(tmp_path / "m.md"))
    assert done.returncode == 1
    assert "CL-099" in done.stderr


@pytest.mark.req("CL-014")
def test_matrix_rejects_a_missing_requirements_file(tmp_path):
    done = run_matrix("--requirements", str(tmp_path / "nope.md"), "--out", str(tmp_path / "m.md"))
    assert done.returncode == 2
