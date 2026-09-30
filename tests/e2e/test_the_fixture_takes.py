# SPDX-License-Identifier: Apache-2.0
"""What a reader with no model sees: each take of the application, end to end.

The application itself — `python -m sayfirst_governed_agent_demo.app TAKE` — against a
daemon of this case's own, in the default mode. The exit status and the outbox are the
assertions, as everywhere here.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading

import pytest

# The open imports this module depends on live in the conftest's fixtures, so without this
# line a machine without the open distributions would fail it case by case instead of
# standing it down by name.
from open_packages import require_the_open_packages

require_the_open_packages(
    __file__, "it runs each take of the application against a real control plane"
)

pytestmark = pytest.mark.e2e


def _start(take: str) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "sayfirst_governed_agent_demo.app",
            take,
            "--approval-timeout",
            "60",
        ],
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


@pytest.mark.parametrize(
    ("take", "status", "sent"), [("allow", 0, 0), ("deny", 1, 0), ("pending", 5, 0)]
)
def test_a_take_ends_with_its_verdict(governed, outbox, take: str, status: int, sent: int) -> None:
    with _start(take) as process:
        try:
            output, _ = process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise
    assert process.returncode == status, output
    assert len(outbox()) == sent, output
    assert "scripted transcript" in output


def test_the_hitl_take_suspends_and_a_person_s_approval_sends_one_message(
    governed, outbox, approve
) -> None:
    seen = []
    reference = None
    with _start("hitl") as process:
        assert process.stdout is not None
        # A deadline for the whole read: nothing else bounds a wait for a notice that
        # never comes.
        deadline = threading.Timer(120, process.kill)
        deadline.start()
        try:
            # Read while the application waits for a person: the notice arrives line by
            # line, and the answer is given from here, the way a second terminal would.
            for line in process.stdout:
                seen.append(line)
                found = re.search(r"Approval reference\s+([0-9a-f-]{36})", line)
                if found and reference is None:
                    reference = found.group(1)
                    assert outbox() == [], "the send ran before a person answered"
                    approve(reference)
            process.wait(timeout=120)
        finally:
            deadline.cancel()
            if process.poll() is None:
                process.kill()
                process.wait(timeout=20)
    assert reference is not None, "".join(seen)
    assert process.returncode == 0, "".join(seen)
    assert len(outbox()) == 1
    assert "scripted transcript" in "".join(seen)


def test_the_suspension_notice_prints_the_three_answers(governed) -> None:
    with _start("pending") as process:
        try:
            output, _ = process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise
    for verb in ("show", "approve", "reject"):
        assert re.search(
            rf"sayfirst approvals {verb} --approval [0-9a-f-]{{36}} --scope local --socket ",
            output,
        ), verb
    assert "Nothing will resume in this process" in output
