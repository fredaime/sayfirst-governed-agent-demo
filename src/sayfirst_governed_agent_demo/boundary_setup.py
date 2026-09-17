# SPDX-License-Identifier: Apache-2.0
"""This demonstration's own boundary: ask the control plane, then act, or do not act.

Two lines compose it, and they are the two the product command-line interface's launcher
composes for somebody else's program — a socket client whose peer it verifies, and a
boundary holding one principal reference:

    client = SocketClient(socket_path=..., expected_uid=expected_principal_uid(profile))
    boundary = Boundary(client=client, principal_reference=...)

Using the boundary by hand is a supported way to use it rather than a workaround, and it
is the only way to govern a graph NODE: the instrumentation command's convenience packs
wrap library calls — a database connection, an outbound request, a subprocess — and no
pack point can name a node of a graph.

`governed_node(capability, fn, select=)` wraps the callable a node is registered with, so
the decision lands after the framework has committed to the act and before the body that
causes it. On a suspension the published boundary RAISES rather than waiting: article 10
refuses a thread parked until a person answers, and its own documentation says the caller
decides how to suspend — "a graph checkpoints". This wrapper is that caller, and what it
does is call LangGraph's `interrupt()`.

**Resuming grants nothing, and the caller carries nothing.** On resume LangGraph
re-executes the suspended node from the top, so the wrapper asks again with the same
capability, the same scope and the same arguments digest. The control plane recognises the
question it already has a wait for — the scope, the principal reference, the capability
and the arguments digest are what make a re-ask the same ask — and answers it: still
pending, the same approval reference comes back and the graph suspends again; approved and
unspent, one allow, which is the one execution the person's act authorised; rejected, a
deny carrying the reason for it. The value passed to `Command(resume=...)` authorises
nothing; it only tells the framework to continue.

**One ask per execution, and the framework does the asking again.** The wrapper puts the
question once and then either enters the body or suspends; it never asks a second time
inside one execution. So a person who resumes a wait that is still pending costs the
control plane exactly one question, however many times they resume: each resume is a fresh
execution with one ask in it. An earlier shape looped back from the suspension to the ask,
on the reading that a resumed caller deserved a fresh question — which was already the
framework's job, and which made the Nth resume put N questions to the daemon for one act.

**What is digested must be describable.** The control plane pins the arguments digest as a
grant condition and compares it exactly, so `binding_arguments` refuses a value the wire
cannot carry where it was written rather than letting a repr be digested.

Three things this module deliberately does not have, each because the open surface has no
counterpart and the behaviour is better without one: no wait strategy to choose (raising is
the only behaviour), no tracer (evidence carries a sequence and a declared gap, which is
the property article 10 offers), and no file journal (the boundary's outcome log is bounded
in memory with a sink this repository owns, and the durable chain is the daemon's).
"""

from __future__ import annotations

import functools
import os
import pwd
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from sayfirst_boundary import Boundary, OutcomeLog, Record
from sayfirst_boundary.digest import arguments_digest
from sayfirst_boundary.errors import Suspended
from sayfirst_contract.binding.http_unix_socket.client import SocketClient
from sayfirst_contract.transport.socket_client import SocketProfile, expected_principal_uid

from sayfirst_governed_agent_demo import governance_stamp
from sayfirst_governed_agent_demo.settings import ConfigurationError

#: How long one question may take. A governed act waits for a decision with nobody
#: watching the terminal, which is why it is longer than a read's.
ASK_TIMEOUT: Final[float] = 10.0

#: How many outcome records are held before the oldest is dropped. A drop is declared
#: rather than hidden: every record carries how many were lost before it.
RECORD_CAPACITY: Final[int] = 1024

#: Every outcome record this process made, in order. The first sink, so a run always has
#: its own copy whatever else is listening.
RECORDS: list[Record] = []

_SINKS: list[Callable[[Record], None]] = [RECORDS.append]


def also_record_into(sink: Callable[[Record], None]) -> None:
    """Send every outcome record to `sink` as well, from the next flush onward.

    This is how the demonstration's event stream becomes the outcome log's sink: the log
    is composed at import, before there is an event stream to hand it.
    """
    _SINKS.append(sink)


def _fan_out(record: Record) -> None:
    """Hand one record to each sink in turn, and let a sink that raises be counted.

    **A sink that raises ends this record's fan-out**, so the sinks after it do not see
    that record — and nothing here catches the exception, deliberately: the published log
    counts a sink that raised as a drop and declares the gap to the records behind it,
    which is a truer account than a record this function had discarded quietly. What the
    order buys is which copy survives a refusing sink: `RECORDS.append` is registered
    first, at import, so this process keeps its own copy of a record even when a sink
    added later refuses it.
    """
    for sink in tuple(_SINKS):
        sink(record)


def _required(name: str, what: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"{name} is not set, and it has no default: {what}. "
            f"`scripts/start-control-plane.sh` prints the address it bound."
        )
    return value


def _this_account() -> str:
    """Who this process is, in the one spelling the boundary uses for a person.

    Never sent as a credential: the control plane establishes identity from the peer of the
    connection. This is the reference a grant's own condition is compared against, locally.
    """
    return f"user:{pwd.getpwuid(os.geteuid()).pw_name}"


SOCKET_PATH: Final[Path] = Path(
    _required("SAYFIRST_SOCKET", "it is the address the control plane is listening at")
)
SCOPE: Final[str] = os.environ.get("SAYFIRST_SCOPE", "").strip() or "local"
PRINCIPAL: Final[str] = os.environ.get("SAYFIRST_PRINCIPAL", "").strip() or _this_account()

_profile = SocketProfile(str(SOCKET_PATH), scope=SCOPE)

client = SocketClient(
    socket_path=SOCKET_PATH,
    expected_uid=expected_principal_uid(_profile),
    timeout=ASK_TIMEOUT,
)

boundary = Boundary(
    client=client,
    principal_reference=PRINCIPAL,
    log=OutcomeLog(capacity=RECORD_CAPACITY, sink=_fan_out, clock=lambda: datetime.now(UTC)),
)


def read_approval(approval_ref: str) -> Any:
    """Read where one wait stands, on a connection of its own.

    A connection of its own on purpose: the boundary's client holds the channel a grant
    rides, and a read that borrowed it would be a second request on a connection the
    control plane closes after an answer it writes itself.
    """
    reader = SocketClient(
        socket_path=SOCKET_PATH,
        expected_uid=expected_principal_uid(_profile),
        timeout=ASK_TIMEOUT,
    )
    return reader.read_approval(SCOPE, approval_ref)


def binding_arguments(
    state: Any, select: Callable[[Any], Any] | None = None
) -> Mapping[str, object]:
    """The mapping whose digest binds a suspension to its resume.

    Refuses anything the wire cannot carry, before any question is put. The control plane
    pins this digest as a grant condition and compares it exactly, and a graph may resume
    in another process, so a value digested through a repr would not reproduce and the
    resume would be refused after a person had already approved it.
    """
    value = state if select is None else select(state)
    if not isinstance(value, Mapping):
        raise TypeError(
            f"a governed node binds a mapping of the act's arguments, not "
            f"{type(value).__name__}. Pass select=lambda state: {{...}} naming the "
            f"arguments that constitute the act."
        )
    # Computed here and discarded: the boundary computes it again for the ask, and what
    # this call buys is the refusal arriving where the binding was written.
    try:
        arguments_digest(value)
    except TypeError as refused:
        raise TypeError(
            f"a governed node binds arguments the wire can carry ({refused}). The control "
            f"plane pins this digest and compares it exactly, so a value it cannot "
            f"describe must not be sent as though it had been. Pass "
            f"select=lambda state: {{...}} naming the arguments that constitute the act."
        ) from refused
    return value


def flush() -> None:
    """Hand what the boundary has recorded to the sinks. Never on the hot path."""
    boundary.flush()


def close() -> None:
    """Give up every held grant and flush what is recorded."""
    boundary.close()


def governed_node(
    capability: str,
    fn: Callable[..., Any],
    *,
    select: Callable[[Any], Any] | None = None,
) -> Callable[..., Any]:
    """Wrap a node so its side effect happens only under a decision that allowed it.

    `select` projects the arguments that constitute the act out of the node's state.
    Whatever is not projected is not bound — and the framework lets a caller merge state on
    resume, so an unprojected field could be substituted after a person approved.
    """

    @functools.wraps(fn)
    def node(state: Any, *args: Any, **kwargs: Any) -> Any:
        # Local import, never at module level: this module must import in a process that
        # has no graph framework at all, and only this helper needs one.
        from langgraph.types import interrupt

        arguments = binding_arguments(state, select)
        entered = False
        try:
            with boundary.request(capability, arguments, scope=SCOPE) as grant:
                entered = True
                # What the body may stamp on its artefact: the decision that opened this
                # block, read off the handle the boundary gave rather than off a value this
                # process invented.
                governance_stamp.record(capability=capability, decision_ref=grant.decision_ref)
                result = fn(state, *args, **kwargs)
                grant.record_outcome(arguments_digest({"result": result}))
                return result
        except Suspended as waiting:
            if entered:
                raise  # raised by the body, not by the boundary's gate
            # Suspend the graph itself, and go on suspending it. ONE ask per execution: the
            # question has been put once, above, and the re-ask is the framework
            # re-executing this node from the top rather than anything this block does.
            #
            # First pass: the call below raises the framework's interruption, the graph
            # checkpoints, nothing has executed. Resumed pass: the ask above has already
            # put the question again and the answer was still « suspend », so the value the
            # caller resumed with is not an authorisation and this block treats it as what
            # it is — a request to continue, which is refused by suspending again. The
            # framework hands that value to the first call here and has none for the next,
            # so the next one raises and the graph re-suspends. The loop terminates because
            # a caller can only have resumed a finite number of times, and it is there so
            # that a second resume cannot reach the body either.
            while True:
                interrupt({"approval": waiting.approval_ref, "capability": capability})

    return node
