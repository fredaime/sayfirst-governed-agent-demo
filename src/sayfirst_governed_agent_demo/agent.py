# SPDX-License-Identifier: Apache-2.0
"""Running the governed graph, including the caller's half of the resume protocol.

This repository composes the boundary and the suspension by hand; it
deliberately does not write this loop, because resuming is the application's own
control flow. What matters is what the loop does NOT do:

    out = app.invoke(state, config)
    while "__interrupt__" in out:
        ...wait for a human to answer, out of band...
        out = app.invoke(Command(resume="continue"), config)

It carries no approval reference, passes no verdict, and the value handed to
`Command(resume=...)` authorises nothing -- it only tells LangGraph to continue.
On resume the graph re-executes the suspended node from the top, the boundary
re-requests identically, and the AUTHORITY answers whether the approval it
already has pending has resolved. A resume before a human has answered suspends
again on the same reference.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from langgraph.types import Command
from sayfirst_boundary import AskRefused, CouldNotAsk, Denied, Suspended
from sayfirst_contract.approvals import ApprovalState
from sayfirst_contract.client import Answered
from sayfirst_contract.decisions import Reason

from sayfirst_governed_agent_demo.demo_events import EventLog
from sayfirst_governed_agent_demo.settings import Settings
from sayfirst_governed_agent_demo.tools import outbox_count


class Verdict(str):
    """How a run ended, in the vocabulary this demonstration prints and its tests assert."""


COMPLETED = Verdict("completed")
SUSPENDED = Verdict("suspended")
REJECTED = Verdict("rejected")
DENIED = Verdict("denied")
REFUSED = Verdict("refused")
UNOBSERVABLE = Verdict("unobservable")

#: One process exit code per thing that can come back. The codes are this
#: demonstration's own — a library that chose a process's exit status would be deciding
#: something that is not its to decide — and they are the ones the product command-line
#: interface publishes for the same six situations, so one event reads one way whichever
#: program reported it. A rejection shares the denial's code because it IS a denial: the
#: control plane answers a rejected wait with `deny` and the reason for it.
EXIT_BY_VERDICT = {
    COMPLETED: 0,
    DENIED: 1,
    REJECTED: 1,
    REFUSED: 3,
    UNOBSERVABLE: 4,
    SUSPENDED: 5,
}


@dataclass
class RunResult:
    verdict: Verdict
    answer: str = ""
    approval_ref: str | None = None
    capability: str | None = None
    message: str = ""
    outbox: int = 0
    state: dict[str, Any] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        return EXIT_BY_VERDICT.get(self.verdict, 1)


def _interrupt_payload(out: Any) -> dict[str, Any]:
    interrupts = out.get("__interrupt__") or ()
    for item in interrupts:
        value = getattr(item, "value", None)
        if isinstance(value, dict):
            return value
    return {}


@dataclass
class GovernedRun:
    """One graph, one thread, and the loop that drives it."""

    app: Any
    settings: Settings
    events: EventLog
    thread_id: str

    @property
    def config(self) -> dict[str, Any]:
        return {"configurable": {"thread_id": self.thread_id}}

    def start(self, task: str) -> RunResult:
        return self._drive(lambda: self.app.invoke({"task": task}, self.config))

    def resume(self, *, update: dict[str, Any] | None = None) -> RunResult:
        """Continue a suspended graph.

        `update` exists so the argument-mutation test can do the attack it must
        be able to do -- merge different state on resume -- through exactly the
        API a caller has. It is never used by the demo itself.
        """
        command = (
            Command(resume="continue", update=update) if update else Command(resume="continue")
        )
        return self._drive(lambda: self.app.invoke(command, self.config))

    def _drive(self, invoke: Callable[[], Any]) -> RunResult:
        """One invocation, with the closed answer set turned into a verdict.

        Nothing here converts a refusal into a state update: a node that could not act does
        not pretend it acted. And nothing here invents an outcome — there are three, and
        « could not ask » is the fourth thing that is not one of them.
        """
        try:
            out = invoke()
        except Denied as refusal:
            if refusal.reason == str(Reason.APPROVAL_REJECTED):
                self.events.policy("the external send was rejected by a person", terminal=True)
                return self._result(REJECTED, message=str(refusal))
            self.events.policy("the capability is denied by policy", terminal=True)
            return self._result(DENIED, message=str(refusal))
        except AskRefused as refusal:
            self.events.control(f"the question was refused: {refusal.problem_code}")
            return self._result(REFUSED, message=str(refusal))
        except CouldNotAsk as refusal:
            self.events.control(
                "the control plane could not be asked -- the protected act did NOT run"
            )
            return self._result(UNOBSERVABLE, message=str(refusal))
        except Suspended as waiting:
            # Only reachable if a BODY raised it; the wrapper turns the boundary's own
            # suspension into the graph's. The capability travels with the reference because
            # the published exception carries it: a verdict that named the act it is waiting
            # on through one route and not the other would print a suspension nobody could
            # place, the day a governed node gains a governed child.
            return self._result(
                SUSPENDED, approval_ref=waiting.approval_ref, capability=waiting.capability
            )
        finally:
            # What the boundary recorded reaches the event stream at the end of every
            # invocation, whichever way the invocation ended.
            from sayfirst_governed_agent_demo import boundary_setup

            boundary_setup.flush()

        if "__interrupt__" in out:
            payload = _interrupt_payload(out)
            return self._result(
                SUSPENDED,
                approval_ref=payload.get("approval"),
                capability=payload.get("capability"),
                state=out,
            )
        return self._result(COMPLETED, answer=str(out.get("answer") or ""), state=out)

    def _result(self, verdict: Verdict, **kwargs: Any) -> RunResult:
        return RunResult(verdict=verdict, outbox=outbox_count(self.settings), **kwargs)


def wait_for_a_person(
    approval_ref: str,
    *,
    timeout_s: float = 300.0,
    poll_interval_s: float = 1.0,
    on_tick: Callable[[float], None] | None = None,
) -> str:
    """Poll the control plane until a person has answered, and return what it says.

    Polling is how this demonstration knows when to resume. It is not how the act becomes
    authorised: the resumed node asks again and the control plane answers again. Delete
    this function, resume on a timer instead, and every security property is unchanged.
    """
    from sayfirst_governed_agent_demo import boundary_setup

    deadline = time.monotonic() + timeout_s
    while True:
        answer = boundary_setup.read_approval(approval_ref)
        if isinstance(answer, Answered) and answer.value.state is not ApprovalState.PENDING:
            return str(answer.value.state)
        if time.monotonic() >= deadline:
            return str(ApprovalState.PENDING)
        if on_tick:
            on_tick(max(0.0, deadline - time.monotonic()))
        time.sleep(poll_interval_s)
