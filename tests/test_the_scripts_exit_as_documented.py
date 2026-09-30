# SPDX-License-Identifier: Apache-2.0
"""The scripts' refusals exit with the statuses the README's table gives.

A precondition nothing here can satisfy is 7, the configuration status the application
already uses; « nothing is listening » when a take starts is 4, could not ask — the same
status a take reports when a node cannot reach the control plane as it asks. A take already
waiting for a person keeps waiting if the control plane stops, then ends suspended (5) with
nothing sent. 1 stays denied or rejected, and only that.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]


def _run(script: str, cwd: Path, **env: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(REPOSITORY / "scripts" / script)],
        cwd=cwd,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
    )


def test_a_precondition_refusal_exits_7(tmp_path: Path) -> None:
    # The principal is checked before anything asks for the environment, a distribution or
    # a daemon, so this refusal is reachable on a machine that holds only this repository.
    done = _run(
        "start-control-plane.sh",
        REPOSITORY,
        SAYFIRST_PRINCIPAL="bad",
        SAYFIRST_DEMO_RUN=str(tmp_path / "run"),
    )
    assert done.returncode == 7, done.stderr
    assert "SAYFIRST_PRINCIPAL=bad is not a reference" in done.stderr
    assert not (tmp_path / "run").exists(), "a refused start wrote its run directory"


def test_nothing_listening_exits_4_and_names_the_script_that_starts_one(tmp_path: Path) -> None:
    done = _run(
        "run-demo.sh",
        REPOSITORY,
        SAYFIRST_SOCKET=str(tmp_path / "absent.sock"),
    )
    if "is not installed here" in done.stderr or "no environment at" in done.stderr:
        # The open distributions are not in this environment (a reduced run): the
        # refusal that comes first is the precondition's, which is 7.
        assert done.returncode == 7, done.stderr
        return
    assert done.returncode == 4, done.stderr
    assert "start-control-plane.sh" in done.stderr
