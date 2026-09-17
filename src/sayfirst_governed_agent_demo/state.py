# SPDX-License-Identifier: Apache-2.0
"""The binding projections that tie a governed act to its approval, and the
members of the state they read.

The state the GRAPH runs is `GraphState`, declared in `graph.py` beside the
`StateGraph` it is given to. `AgentState` below is the shape these projections
and `resolve_act` read -- the members they touch, and no others -- declared here
so that this module needs no import of the graph it is read from. It is a
reader's view rather than the framework's schema: LangGraph never sees it.

Everything here is JSON-serializable, and that is a requirement rather than a
style: LangGraph checkpoints the state and may resume it in another process,
and the boundary refuses a binding it cannot digest reproducibly.
"""

from __future__ import annotations

import hashlib
from typing import Any, TypedDict


class PendingAct(TypedDict):
    """The act the model has proposed and the graph has committed to attempting.

    `sequence` makes two identical acts in one run two distinct acts -- reading
    the same file twice is two reads, and the authority should see two asks. It
    is set by the reasoning node and never by the tool node, so a resumed tool
    node re-reads the same value and re-requests identically.
    """

    call_id: str
    tool: str
    arguments: dict[str, Any]
    sequence: int


class AgentState(TypedDict, total=False):
    """What the functions in this module read of the state, and nothing more.

    Not the graph's schema -- that is `GraphState` in `graph.py`, which carries
    these members and the three the reasoning node needs for its own loop. This
    is the annotation of the six functions below, so a reader of a binding can
    see which members it is entitled to touch without opening the graph.
    """

    task: str
    #: The model's own latest written prose -- the report it composed.
    draft: str
    #: The report text as actually saved, so the external send delivers what the
    #: internal write recorded rather than a later draft.
    report_text: str
    messages: list[dict[str, Any]]
    pending: PendingAct | None
    sequence: int
    answer: str


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def _pending(state: AgentState) -> PendingAct:
    pending = state.get("pending")
    if not pending:
        raise RuntimeError("a governed node ran with no pending act -- graph wiring bug")
    return pending


# -- the binding projections ---------------------------------------------------
#
# One per governed node. Each names EVERY field that constitutes the act, which is the
# whole rule: what is not projected here is not bound, and LangGraph lets a caller merge
# state on resume -- so an unprojected field could be substituted after a human
# approved. Payloads travel as digests: the authority binds what was approved
# without the demo shipping message bodies into governance records.


def bind_read(state: AgentState) -> dict[str, Any]:
    """The corpus this act will read, named document by document.

    The names rather than a count: an approver reading the record should see
    WHICH documents were read, and a corpus that changed between the ask and the
    act is a different act.
    """
    act = _pending(state)
    resolved = resolve_act(state)
    return {
        "act": act["sequence"],
        "capability": "documents.read",
        "documents": resolved.get("documents", []),
    }


def bind_write_internal(state: AgentState) -> dict[str, Any]:
    """The filename and the digest of the exact text about to be written.

    The text arrives through `resolve_act` rather than as a model argument, and
    the digest is taken of the RESOLVED value -- so the binding names what will
    actually land on disk, not what was proposed.
    """
    act = _pending(state)
    resolved = resolve_act(state)
    return {
        "act": act["sequence"],
        "capability": "report.write.internal",
        "filename": str(resolved.get("filename", "")),
        "content_digest": _digest(str(resolved.get("content", ""))),
    }


def bind_send_external(state: AgentState) -> dict[str, Any]:
    """Recipient, destination domain, subject and payload digest -- the whole act.

    This is the projection the argument-mutation test attacks. Changing any of
    these after approval yields a different digest, therefore a different ask,
    therefore no execution under the earlier approval.
    """
    act = _pending(state)
    resolved = resolve_act(state)
    recipient = str(resolved.get("recipient", ""))
    return {
        "act": act["sequence"],
        "capability": "communications.send.external",
        "recipient": recipient,
        "destination_domain": recipient.rpartition("@")[2],
        "subject": str(resolved.get("subject", "")),
        "body_digest": _digest(str(resolved.get("body", ""))),
    }


def bind_upload_external(state: AgentState) -> dict[str, Any]:
    act = _pending(state)
    resolved = resolve_act(state)
    return {
        "act": act["sequence"],
        "capability": "data.upload.external",
        "destination": str(resolved.get("destination", "")),
        "filename": str(resolved.get("filename", "")),
    }


def resolve_act(state: AgentState) -> dict[str, Any]:
    """The complete arguments of the pending act: what the model chose, plus what
    the application supplies.

    ONE function, called by both the binding projection and the node body, so
    the value the authority digests and the value the side effect uses cannot
    diverge. That identity is the whole reason this is not two code paths: a
    binding computed from proposed arguments while the body ran on resolved ones
    would let an approved act execute with something else.

    What the MODEL contributes: which act, and every security-relevant choice --
    the document to read, the recipient of an external message, the upload
    destination. What the APPLICATION contributes: the report text the model
    wrote in its own prose (carried in `draft`, because small instruct models
    cannot emit long tool arguments) and fixed product naming. Nothing here
    invents a recipient, a destination or a path.
    """
    from sayfirst_governed_agent_demo.tools import (
        EXTERNAL_SUBJECT,
        REPORT_FILENAME,
        UPLOAD_FILENAME,
    )

    act = _pending(state)
    arguments = dict(act["arguments"])
    tool = act["tool"]
    if tool == "read_documents":
        from sayfirst_governed_agent_demo.settings import load_settings
        from sayfirst_governed_agent_demo.tools import corpus

        return {"documents": [p.name for p in corpus(load_settings())]}
    if tool == "write_internal_report":
        return {
            "filename": str(arguments.get("filename") or REPORT_FILENAME),
            "content": str(state.get("draft") or ""),
        }
    if tool == "send_external_email":
        return {
            "recipient": str(arguments.get("recipient", "")),
            "subject": str(arguments.get("subject") or EXTERNAL_SUBJECT),
            "body": str(state.get("report_text") or state.get("draft") or ""),
        }
    if tool == "upload_external":
        return {
            "destination": str(arguments.get("destination", "")),
            "filename": str(arguments.get("filename") or UPLOAD_FILENAME),
        }
    return arguments
