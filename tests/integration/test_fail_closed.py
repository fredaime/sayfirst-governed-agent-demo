# SPDX-License-Identifier: Apache-2.0
"""A control plane that cannot be reached does not become permission.

No daemon runs in this module. That is the point: the boundary is pointed at an address
nothing is listening at, and the protected act must not happen. No model, no network beyond
a socket file that is not there.

The published client answers an unreachable address with a problem classed « could not
ask » rather than raising, and the boundary raises that as its own refusal — so this tier
also pins the one thing a caller must never get wrong: the absence of a refusal is not a
refusal, and it is not an allowance either.

**This module needs the open packages, and its first statement says so.** Its imports are
inside `_run`, which is how a module can collect on a machine that does not have them and
then fail at run time — counted as a failure rather than as a check that could not run. The
declaration below stands the module down instead, with a reason the gate counts and names.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

# The open imports of this module are inside `_run`, so without this line it collects on a
# machine that has none of them and then errors case by case.
from open_packages import require_the_open_packages

require_the_open_packages(
    __file__, "it points the published boundary at an address nothing is listening at"
)

REPOSITORY = Path(__file__).resolve().parents[2]


@pytest.fixture
def unreachable(tmp_path: Path, monkeypatch):
    for name in ("outbox", "reports", "events"):
        (tmp_path / name).mkdir()
    monkeypatch.setenv("SAYFIRST_SOCKET", str(tmp_path / "nothing-is-here.sock"))
    monkeypatch.setenv("SAYFIRST_SCOPE", "local")
    monkeypatch.setenv("DEMO_OUTBOX", str(tmp_path / "outbox"))
    monkeypatch.setenv("DEMO_REPORTS", str(tmp_path / "reports"))
    monkeypatch.setenv("DEMO_EVENTS", str(tmp_path / "events"))
    monkeypatch.setenv("DEMO_DATA", str(REPOSITORY / "demo_data"))
    monkeypatch.setenv("MODEL_MODE", "fixture")
    for module in [m for m in list(sys.modules) if m.startswith("sayfirst_governed_agent_demo")]:
        del sys.modules[module]
    yield tmp_path
    for module in [m for m in list(sys.modules) if m.startswith("sayfirst_governed_agent_demo")]:
        del sys.modules[module]


def _run(*calls):
    from langgraph.checkpoint.memory import InMemorySaver

    from sayfirst_governed_agent_demo.agent import GovernedRun
    from sayfirst_governed_agent_demo.demo_events import EventLog
    from sayfirst_governed_agent_demo.graph import build_graph
    from sayfirst_governed_agent_demo.model import ModelReply, ScriptedModel, ToolCall
    from sayfirst_governed_agent_demo.settings import load_settings

    replies = []
    for index, entry in enumerate(calls):
        if isinstance(entry, str):
            replies.append(ModelReply(content=entry))
        else:
            name, arguments = entry
            replies.append(
                ModelReply(
                    content="",
                    tool_calls=(ToolCall(id=f"c{index}", name=name, arguments=arguments),),
                )
            )
    settings = load_settings()
    events = EventLog(colour=False)
    graph = build_graph(
        settings, ScriptedModel(replies=replies), events, checkpointer=InMemorySaver()
    )
    run = GovernedRun(app=graph, settings=settings, events=events, thread_id=uuid.uuid4().hex)
    return run.start("Send the report to the external partner.")


def test_a_control_plane_that_cannot_be_reached_executes_nothing(unreachable):
    result = _run(("send_external_email", {"recipient": "partner@example.test"}), "Sent.")

    assert result.verdict == "unobservable", "an unreachable control plane is neither yes nor no"
    assert list((unreachable / "outbox").glob("*.json")) == [], "fail closed: nothing was sent"


def test_a_control_plane_that_cannot_be_reached_blocks_an_allowed_capability_too(unreachable):
    """Failing closed is not a property of the strict capabilities.

    Reading the corpus is `allow` under the policy this demonstration ships — and it still
    does not happen. A boundary that could not ask has no answer to act on, whatever the
    answer would have been.
    """
    result = _run(("read_documents", {}), "Read.")

    assert result.verdict == "unobservable"
    assert list((unreachable / "reports").glob("*")) == []
