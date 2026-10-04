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
def test_empty_trace_exits_0(run_sim):
    # The "reports zero accesses" half needs the report (CL-010).
    code, _, err = run_sim("")
    assert code == 0, err
