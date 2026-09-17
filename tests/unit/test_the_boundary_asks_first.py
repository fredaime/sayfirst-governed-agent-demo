# SPDX-License-Identifier: Apache-2.0
"""What the wrapper does with each answer, with no socket and no daemon anywhere.

Only the ANSWER is scripted. The wrapper, the published boundary, the published digest and
LangGraph's own suspension are the real ones, which is what makes these claims about this
repository rather than about a mock.
"""

from __future__ import annotations

import sys
from pathlib import Path

# The order is the point: this call raises the runner's module-level skip where the open
# distributions are absent, so the imports under it are never executed there. They are
# written after it rather than moved into nine test bodies because every case names a
# published exception, and a module that imported its own vocabulary nine times would be
# harder to read than the rule is to state.
from open_packages import require_the_open_packages

require_the_open_packages(
    __file__, "it drives the published boundary and the published digest directly"
)

import pytest  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.types import Command  # noqa: E402
from plane_double import (  # noqa: E402
    ScriptedPlane,
    allowed,
    could_not_ask,
    denied,
    refused,
    suspended,
)
from sayfirst_boundary import AskRefused, CouldNotAsk, Denied, OutcomeLog, Record  # noqa: E402
from sayfirst_boundary.boundary import Boundary  # noqa: E402
from sayfirst_contract.decisions import Reason  # noqa: E402

CAPABILITY = "communications.send.external"


@pytest.fixture
def module(monkeypatch, tmp_path: Path):
    """The boundary module, imported fresh, with an address nothing listens at.

    Composing the client does not dial, so an address that is not there is enough for
    every case here — and it is the honest one: a unit tier that pointed at a live daemon
    would be an end-to-end tier with a shorter name.
    """
    monkeypatch.setenv("SAYFIRST_SOCKET", str(tmp_path / "absent.sock"))
    monkeypatch.setenv("SAYFIRST_SCOPE", "local")
    monkeypatch.setenv("SAYFIRST_PRINCIPAL", "user:somebody")
    for name in [m for m in list(sys.modules) if m.startswith("sayfirst_governed_agent_demo")]:
        del sys.modules[name]
    from sayfirst_governed_agent_demo import boundary_setup, governance_stamp

    governance_stamp.forget()
    yield boundary_setup
    for name in [m for m in list(sys.modules) if m.startswith("sayfirst_governed_agent_demo")]:
        del sys.modules[name]


def _plane(module, answers, monkeypatch) -> ScriptedPlane:
    """Replace the module's boundary with one that answers from a script.

    **The replacement log's sink is the module's own `_fan_out`**, which is the one the
    module composed at import. Giving it a list of this helper's own instead would be
    quietly fatal to the case that matters: `RECORDS` and anything added through
    `also_record_into` are fed BY `_fan_out`, so a replacement boundary wired to a local
    list leaves both empty for ever, and a test asserting on them cannot pass — while a
    test asserting on the local list would pass and prove nothing about the mechanism this
    repository owns. So the records are read where the module keeps them: `module.RECORDS`.
    """
    plane = ScriptedPlane(answers)
    log = OutcomeLog(capacity=8, sink=module._fan_out, clock=module.boundary._clock)
    monkeypatch.setattr(
        module,
        "boundary",
        Boundary(client=plane, principal_reference="user:somebody", log=log),
    )
    return plane


def test_an_allowed_capability_enters_the_body_and_records_an_outcome(module, monkeypatch):
    plane = _plane(module, [allowed()], monkeypatch)
    entered: list[bool] = []

    def body(state):
        entered.append(True)
        return "sent"

    node = module.governed_node(CAPABILITY, body, select=lambda state: {"to": state["to"]})
    assert node({"to": "partner@example.test"}) == "sent"
    assert entered == [True]
    assert len(plane.asks) == 1
    assert plane.asks[0].capability == CAPABILITY
    assert plane.asks[0].scope == "local"
    assert plane.asks[0].arguments_digest.startswith("sha256:")
    module.boundary.flush()
    assert [record.capability for record in module.RECORDS] == [CAPABILITY]
    assert module.RECORDS[0].decision_ref == "decision-1"
    assert module.RECORDS[0].outcome_digest is not None
    assert module.RECORDS[0].dropped_before == 0


def test_a_denied_capability_never_enters_the_body(module, monkeypatch):
    _plane(module, [denied()], monkeypatch)
    entered: list[bool] = []
    node = module.governed_node(CAPABILITY, lambda state: entered.append(True))

    with pytest.raises(Denied) as raised:
        node({"to": "partner@example.test"})

    assert entered == []
    assert raised.value.reason == str(Reason.POLICY_DENIES)


def test_a_rejected_approval_arrives_as_a_denial_that_names_the_rejection(module, monkeypatch):
    """The demo's terminal `rejected` verdict is a READ of the denial's reason.

    There is no rejection exception in the published boundary, and there does not need to
    be: a re-ask of a rejected wait is a deny carrying the reason the contract publishes.
    """
    _plane(module, [denied(Reason.APPROVAL_REJECTED)], monkeypatch)
    node = module.governed_node(CAPABILITY, lambda state: "sent")

    with pytest.raises(Denied) as raised:
        node({"to": "partner@example.test"})

    assert raised.value.reason == str(Reason.APPROVAL_REJECTED)


def test_a_question_that_could_not_be_asked_is_not_permission(module, monkeypatch):
    _plane(module, [could_not_ask()], monkeypatch)
    entered: list[bool] = []
    node = module.governed_node(CAPABILITY, lambda state: entered.append(True))

    with pytest.raises(CouldNotAsk):
        node({"to": "partner@example.test"})
    assert entered == []


def test_a_refused_question_is_not_a_denial(module, monkeypatch):
    _plane(module, [refused()], monkeypatch)
    entered: list[bool] = []
    node = module.governed_node(CAPABILITY, lambda state: entered.append(True))

    with pytest.raises(AskRefused):
        node({"to": "partner@example.test"})

    assert entered == []


def test_a_suspension_checkpoints_the_graph_and_a_resume_asks_the_same_question(
    module, monkeypatch
):
    """The demo's strongest claim, in one process: resuming grants nothing.

    The graph is compiled with a checkpointer, as the demo compiles it. The first pass
    suspends with the body not entered; the resume re-executes the node from the top and
    the wrapper puts the SAME question — same capability, same scope, same digest — so the
    authority answers the wait it already has rather than a new one.
    """
    plane = _plane(module, [suspended("approval-1"), suspended("approval-1")], monkeypatch)
    entered: list[bool] = []

    def body(state):
        entered.append(True)
        return {"answer": "sent"}

    builder = StateGraph(dict)
    builder.add_node(
        "send",
        module.governed_node(CAPABILITY, body, select=lambda state: {"to": state["to"]}),
    )
    builder.add_edge(START, "send")
    builder.add_edge("send", END)
    graph = builder.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "one"}}

    first = graph.invoke({"to": "partner@example.test"}, config)
    assert "__interrupt__" in first
    assert first["__interrupt__"][0].value["approval"] == "approval-1"
    assert entered == []

    again = graph.invoke(Command(resume="continue"), config)

    assert "__interrupt__" in again
    assert again["__interrupt__"][0].value["approval"] == "approval-1"
    assert entered == []
    assert len(plane.asks) == 2
    assert plane.asks[0] == plane.asks[1], "a resumed node asks the same question"


def test_a_second_resume_costs_one_more_question_and_not_two(module, monkeypatch):
    """One ask per execution, asserted where it can regress: N resumes, N + 1 questions.

    The wrapper suspends by interrupting and nothing more. A shape that asked again after
    the framework handed back a resume value would put two questions on the first resume
    and three on the second, growing with every resume, for one act nobody has authorised
    yet — and every one of them a real request to the daemon. Three answers are scripted
    for three passes, so a fourth ask runs the script out and fails loudly rather than
    quietly costing a question.
    """
    plane = _plane(module, [suspended("approval-1") for _ in range(3)], monkeypatch)
    entered: list[bool] = []

    def body(state):
        entered.append(True)
        return {"answer": "sent"}

    builder = StateGraph(dict)
    builder.add_node(
        "send",
        module.governed_node(CAPABILITY, body, select=lambda state: {"to": state["to"]}),
    )
    builder.add_edge(START, "send")
    builder.add_edge("send", END)
    graph = builder.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "two"}}

    graph.invoke({"to": "partner@example.test"}, config)
    assert len(plane.asks) == 1, "the first pass puts one question"
    graph.invoke(Command(resume="continue"), config)
    assert len(plane.asks) == 2, "a resume puts one more question, not two"
    again = graph.invoke(Command(resume="continue"), config)
    assert len(plane.asks) == 3, "and a second resume puts one more, not another two"

    assert "__interrupt__" in again
    assert again["__interrupt__"][0].value["approval"] == "approval-1"
    assert entered == []
    assert len(set(plane.asks)) == 1, "every pass puts the identical question"


def test_a_binding_the_wire_cannot_carry_is_refused_before_any_ask(module, monkeypatch):
    """A digest the control plane pins has to reproduce, so a value that cannot be
    described is refused where it was written rather than digested through a repr."""
    plane = _plane(module, [allowed()], monkeypatch)
    node = module.governed_node(CAPABILITY, lambda state: "sent", select=lambda state: state)

    with pytest.raises(TypeError) as raised:
        node({"recipients": {"partner@example.test"}})

    assert "select=" in str(raised.value)
    assert plane.asks == [], "nothing was asked about an act that could not be described"


def test_a_binding_that_is_not_a_mapping_is_refused_the_same_way(module, monkeypatch):
    plane = _plane(module, [allowed()], monkeypatch)
    node = module.governed_node(CAPABILITY, lambda state: "sent", select=lambda state: ["a list"])

    with pytest.raises(TypeError):
        node({"to": "partner@example.test"})
    assert plane.asks == []


def test_the_records_reach_a_sink_this_repository_owns_and_carry_no_payload(module, monkeypatch):
    """The mechanism the event stream is attached by, asserted on the sink it attaches.

    Three claims, and the middle one is the one this case exists for. The module's own
    list holds what the boundary recorded — that is the first sink, registered at import
    so that a run always has its own copy. A sink added through `also_record_into` gets
    the same records — that is how the demonstration's event stream becomes the outcome
    log's sink, and it is the only claim here about a mechanism rather than about a list.
    And neither carries the body's result.

    The added sink is asserted on DIRECTLY. An earlier draft of this case called
    `also_record_into` and then asserted on the module's list, which would have passed
    with the fan-out to the added sink deleted — a test named after a mechanism it did not
    read.
    """
    secret = "Pricing for hosted small models fell"
    plane = _plane(module, [allowed()], monkeypatch)
    seen: list[Record] = []
    module.also_record_into(seen.append)

    node = module.governed_node(
        CAPABILITY, lambda state: secret, select=lambda state: {"to": state["to"]}
    )
    node({"to": "partner@example.test"})
    module.boundary.flush()

    assert module.RECORDS, "the module's own sink holds what the boundary recorded"
    assert [record.capability for record in module.RECORDS] == [CAPABILITY]
    assert seen, "a sink added through also_record_into receives what the boundary recorded"
    assert [record.capability for record in seen] == [CAPABILITY]
    assert [record.sequence for record in seen] == [record.sequence for record in module.RECORDS], (
        "both sinks see the same records, in the same order"
    )
    assert secret not in str(module.RECORDS), "a record names the act, never its content"
    assert secret not in str(seen), "and the added sink is handed the same metadata"
    assert plane.asks[0].capability == CAPABILITY
