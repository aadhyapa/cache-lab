import os
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def pytest_configure(config):
    config.addinivalue_line("markers", "req(id): the requirement (CL-nnn) this test verifies")


@pytest.fixture
def run_sim(tmp_path):
    """Run the simulator on trace text; returns (exit code, stdout, stderr)."""
    binary = os.environ.get("CACHE_LAB", str(ROOT / "build" / "cache_lab"))

    def run(trace_text, *flags):
        trace = tmp_path / "t.trc"
        trace.write_text(trace_text)
        done = subprocess.run([binary, *flags, str(trace)], capture_output=True, text=True)
        return done.returncode, done.stdout, done.stderr

    run.binary = binary
    return run
