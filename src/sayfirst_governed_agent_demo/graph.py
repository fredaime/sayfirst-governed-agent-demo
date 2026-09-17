# SPDX-License-Identifier: Apache-2.0
"""The LangGraph application: one reasoning node, four tool nodes, one router.

An ordinary ReAct-shaped graph, composed of governed nodes. What this module
knows about governance is exactly that: which capability key each tool node is
registered under and which projection binds its act. It asks nothing, decides
nothing and reads no answer -- the boundary around each registration does that,
and `boundary_setup.py`, this repository's own module, is where it is composed.
The diff from the plain application is recorded in `docs/INTEGRATION_DIFF.md`,
which is what makes "bring your agent, keep your workflow" demonstrable rather
than a slogan.

Two structural rules sayfirst imposes, both honoured here:

* **One node, one capability key.** A prebuilt `ToolNode` would execute whichever
  tool the model picked under a single key, which cannot express four different
  regimes. Each tool therefore gets its own node.
* **Only one governed node may suspend at a time.** The router fans to exactly
  one tool node per turn, so two branches can never suspend concurrently.
"""

from __future__ import annotations

import json
import operator
from collections.abc import Callable
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from sayfirst_governed_agent_demo.boundary_setup import governed_node
from sayfirst_governed_agent_demo.demo_events import EventLog
from sayfirst_governed_agent_demo.governance_stamp import last_authorisation
from sayfirst_governed_agent_demo.model import ChatModel, ModelReply
from sayfirst_governed_agent_demo.settings import (
    CAP_COMMUNICATIONS_SEND_EXTERNAL,
    CAP_DATA_UPLOAD_EXTERNAL,
    CAP_DOCUMENTS_READ,
    CAP_REPORT_WRITE_INTERNAL,
    Settings,
)
from sayfirst_governed_agent_demo.state import (
    PendingAct,
    bind_read,
    bind_send_external,
    bind_upload_external,
    bind_write_internal,
    resolve_act,
)
from sayfirst_governed_agent_demo.tools import (
    TOOLS_BY_NAME,
    ToolRefused,
    openai_tool_schemas,
    read_documents,
    send_external_email,
    upload_external,
    write_internal_report,
)

SYSTEM_PROMPT = """You are ResearchOps Agent.

You reason about the task you are given and use the tools available to you.

Tool availability does NOT imply authorization. An independent runtime authority
decides whether any tool call is actually permitted to execute. You do not
enforce that and must not try to.

When a tool result says the operation was refused, state plainly that the
operation could not be performed, and continue with the rest of the task.
When an operation is awaiting human approval, allow the runtime to suspend.

Follow this plan, one tool call per turn, in order:

1. read_documents          -- reads the whole corpus. No arguments.
2. Write the report as an ORDINARY MESSAGE with no tool call: four to six
   sentences covering the findings from every document you read.
3. write_internal_report   -- saves the report you just wrote. No arguments.
4. send_external_email     -- pass the recipient address named in the task.

Do not repeat a step you have already completed. When every step is done, reply
with a short plain-text summary and no tool call."""

#: Node names. The router returns one of these, so they are shared vocabulary
#: between the conditional edge and the registrations.
NODE_REASON = "reason"
NODE_READ = "read_documents"
NODE_WRITE_INTERNAL = "write_internal_report"
NODE_SEND_EXTERNAL = "send_external_email"
NODE_UPLOAD_EXTERNAL = "upload_external"

TOOL_NODES: dict[str, str] = {
    "read_documents": NODE_READ,
    "write_internal_report": NODE_WRITE_INTERNAL,
    "send_external_email": NODE_SEND_EXTERNAL,
    "upload_external": NODE_UPLOAD_EXTERNAL,
}


class GraphState(TypedDict, total=False):
    task: str
    messages: Annotated[list[dict[str, Any]], operator.add]
    pending: PendingAct | None
    sequence: int
    answer: str
    #: The model's own latest written prose: the report it composed. Carried in
    #: state because a small instruct model cannot emit it as a tool argument,
    #: and it is the model's output either way.
    draft: str
    #: The report text as actually saved, so the external send delivers what the
    #: internal write recorded.
    report_text: str
    #: Set when the graph has asked the model, in so many words, to write the
    #: report. Only the prose that ANSWERS that request is taken as the report:
    #: a model narrating its plan ("I have read the documents and will now
    #: summarise") writes prose too, and saving that as the report would put a
    #: file on disk that is not what it claims to be.
    draft_requested: bool
    #: Set when the reasoning node refused a premature "I am done" and sent the
    #: model back round. Bounded by MAX_NUDGES so a model that will not comply
    #: ends the run instead of looping.
    nudge: bool
    nudges: int


#: How much prose counts as a drafted report rather than a passing remark.
_MIN_DRAFT = 80

#: How many times the graph will tell the model that a step it claimed is not
#: actually done. Small on purpose: this corrects a slip, it does not argue.
MAX_NUDGES = 6


def _attempted(messages: list[dict[str, Any]]) -> set[str]:
    """Tools the model has actually PROPOSED, read off the transcript.

    Attempted, not succeeded: an act the authority refused was still attempted,
    and demanding success here would loop forever on a denied capability.
    """
    names: set[str] = set()
    for message in messages:
        for call in message.get("tool_calls") or ():
            name = (call.get("function") or {}).get("name")
            if name:
                names.add(str(name))
    return names


def _corpus_text(messages: list[dict[str, Any]]) -> str:
    """The corpus as the read already returned it, from the transcript."""
    for message in reversed(messages):
        if message.get("role") == "tool" and message.get("name") == "read_documents":
            return str(message.get("content") or "")
    return ""


def _next_step(tool: str, has_draft: Any, attempt: int = 1) -> str:
    """What the model still has to do, named as a STEP rather than as values.

    This is the validation loop's whole vocabulary. It says which step is
    outstanding; it never supplies an argument. The recipient of an external
    message, the destination of an upload and the content of the report all
    come from the model or from the task, never from this function -- a demo
    that fed the model its own security-relevant arguments would be
    demonstrating a script, not an agent.

    `attempt` makes the correction ESCALATE. Repeating an identical instruction
    to a model at temperature 0 gets an identical refusal: measured, this model
    ignored the same polite correction six times in a row and the run ended
    having done nothing. So a repeat drops the prose and states the call. It
    still names only the STEP -- never an argument -- so what escalates is
    insistence, not information.
    """
    insist = (
        ""
        if attempt < 2
        else f" This is attempt {attempt}. Reply with the {tool} tool call and nothing else."
    )
    if tool == "read_documents":
        return (
            "You reported that the task is complete, but you have not read the "
            "corpus yet. Call read_documents now." + insist
        )
    if tool == "write_internal_report":
        if not has_draft:
            return (
                "Write a report of four to six sentences covering the important "
                "findings from the corpus you read. Reply with the report text "
                "only, and do not call a tool."
            )
        return "Now call write_internal_report to save the report you just wrote." + insist
    if tool == "send_external_email":
        return (
            "The report is saved but not delivered. Call send_external_email with "
            "the recipient named in the task." + insist
        )
    if tool == "upload_external":
        return (
            "You have not performed the upload yet. Call upload_external with the "
            "destination named in the task." + insist
        )
    return f"You have not called {tool} yet. Do that now." + insist


def _tool_result(call_id: str, name: str, content: str) -> dict[str, Any]:
    return {"role": "tool", "tool_call_id": call_id, "name": name, "content": content}


def make_reason_node(
    settings: Settings,
    model: ChatModel,
    events: EventLog,
    required_tools: tuple[str, ...] = (),
) -> Callable[[GraphState], dict[str, Any]]:
    """One model turn: either a tool call the graph will attempt, or the answer.

    `required_tools` names the acts the task asks for. When the model declares
    itself finished without having ATTEMPTED one of them, the node says so and
    sends it round again -- a validation loop, not a script: nothing here
    fabricates a tool call, chooses arguments, or decides that an act happened.
    A model that ignores three corrections is allowed to finish, and the run
    reports what it actually did.
    """

    def reason(state: GraphState) -> dict[str, Any]:
        messages = state.get("messages") or []
        if not messages:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": state["task"]},
            ]
            added: list[dict[str, Any]] = list(messages)
        else:
            added = []

        events.model(f"{model.identity} reasoning", turn=len(messages))
        reply: ModelReply = model.complete(messages, openai_tool_schemas())
        # Prose the model writes IS the report -- but only prose written in the
        # window where a report is what it is writing: after the corpus has been
        # read, and before a report has been saved. Outside that window the
        # model's prose is a plan or a completion claim, and saving one of those
        # as the report would put text on disk that is not what it says it is.
        attempted = _attempted(messages)
        answering_draft_request = bool(state.get("draft_requested")) and not state.get(
            "report_text"
        )
        drafted: dict[str, Any] = (
            {"draft": reply.content, "draft_requested": False}
            if answering_draft_request and len(reply.content.strip()) >= _MIN_DRAFT
            else {}
        )

        if not reply.wants_tools:
            missing = [t for t in required_tools if t not in attempted]
            nudges = int(state.get("nudges") or 0)
            if missing and nudges < MAX_NUDGES:
                events.model(
                    "model declared completion with work outstanding; corrected",
                    outstanding=",".join(missing),
                )
                correction = _next_step(missing[0], drafted or state.get("draft"), nudges + 1)
                asking_for_draft = missing[0] == "write_internal_report" and not (
                    drafted or state.get("draft")
                )
                if asking_for_draft:
                    # The corpus, restated in the USER turn that asks for the
                    # report. Measured: this model summarises well when the
                    # material sits in the turn it is answering, and narrates its
                    # plan when the same material sits in an earlier tool result.
                    # It is the same text it already read -- no new information,
                    # and nothing about what the report should SAY.
                    correction = f"{_corpus_text(messages)}\n\n{correction}"
                return {
                    "messages": [
                        *added,
                        {"role": "assistant", "content": reply.content},
                        {"role": "user", "content": correction},
                    ],
                    "pending": None,
                    "nudge": True,
                    "nudges": nudges + 1,
                    "draft_requested": asking_for_draft,
                    **drafted,
                }
            events.model("model produced a final answer, no tool requested")
            return {
                "messages": [*added, {"role": "assistant", "content": reply.content}],
                "pending": None,
                "nudge": False,
                "answer": reply.content,
                **drafted,
            }

        # One act per turn. A model that proposes several tool calls at once gets
        # the first attempted and the rest re-proposed on the next turn: two
        # governed nodes must never suspend concurrently.
        call = reply.tool_calls[0]
        if call.name not in TOOLS_BY_NAME:
            events.model(f"model proposed an unknown tool {call.name!r}")
            return {
                "messages": [
                    *added,
                    {"role": "assistant", "content": "", "tool_calls": [_as_wire(call)]},
                    _tool_result(call.id, call.name, f"no such tool: {call.name}"),
                ],
                "pending": None,
            }

        sequence = int(state.get("sequence") or 0) + 1
        events.model(
            f"tool selected: {call.name}",
            capability=TOOLS_BY_NAME[call.name].capability,
        )
        pending: PendingAct = {
            "call_id": call.id,
            "tool": call.name,
            "arguments": call.arguments,
            "sequence": sequence,
        }
        return {
            "messages": [
                *added,
                {"role": "assistant", "content": reply.content, "tool_calls": [_as_wire(call)]},
            ],
            "pending": pending,
            "sequence": sequence,
            "nudge": False,
            **drafted,
        }

    return reason


def _as_wire(call: Any) -> dict[str, Any]:
    return {
        "id": call.id,
        "type": "function",
        "function": {"name": call.name, "arguments": json.dumps(call.arguments, sort_keys=True)},
    }


def route(state: GraphState) -> str:
    """Exactly one destination per turn, so no two governed nodes suspend at once."""
    pending = state.get("pending")
    if not pending:
        return NODE_REASON if state.get("nudge") else END
    return TOOL_NODES.get(pending["tool"], END)


def _node(
    settings: Settings,
    events: EventLog,
    execute: Callable[[Settings, dict[str, Any]], str],
) -> Callable[[GraphState], dict[str, Any]]:
    """Build a tool node around a side effect.

    The body runs the act and records the result as a tool message. When this
    node is wrapped by `governed_node`, everything in here happens strictly
    after the authority has authorised it -- the wrapper's decision is made
    before the wrapped callable is entered.
    """

    def node(state: GraphState) -> dict[str, Any]:
        act = state.get("pending")
        if not act:
            raise RuntimeError("tool node entered with no pending act")
        # The SAME resolution the binding projection digested. Not a second
        # computation of the arguments -- the identical one -- so the act that
        # runs is the act that was authorised.
        resolved = resolve_act(state)
        update: dict[str, Any] = {}
        try:
            result = execute(settings, resolved)
        except ToolRefused as refusal:
            result = f"the tool refused this call: {refusal}"
            events.execution(f"{act['tool']} refused by the tool: {refusal}")
        else:
            events.execution(f"{act['tool']} executed", **_summary(act, resolved))
            if act["tool"] == "write_internal_report":
                update["report_text"] = str(resolved.get("content", ""))
        return {
            "messages": [_tool_result(act["call_id"], act["tool"], result)],
            "pending": None,
            **update,
        }

    return node


def _summary(act: PendingAct, resolved: dict[str, Any]) -> dict[str, Any]:
    args = resolved
    if act["tool"] == "send_external_email":
        return {"recipient": args.get("recipient")}
    if act["tool"] == "read_documents":
        return {"documents": ",".join(args.get("documents") or [])}
    if act["tool"] == "write_internal_report":
        return {"filename": args.get("filename")}
    if act["tool"] == "upload_external":
        return {"destination": args.get("destination")}
    return {}


def build_tool_nodes(
    settings: Settings, events: EventLog
) -> dict[str, Callable[[GraphState], dict[str, Any]]]:
    """The four side-effecting callables, before any governance is applied.

    The two external acts stamp their artefact with the capability they were
    governed under and the decision reference the boundary recorded, so an
    outbox artefact can be traced back to the answer that authorised it.
    """

    def send(s: Settings, args: dict[str, Any]) -> str:
        return send_external_email(s, args, governance=last_authorisation("send_external_email"))

    def upload(s: Settings, args: dict[str, Any]) -> str:
        return upload_external(s, args, governance=last_authorisation("upload_external"))

    return {
        NODE_READ: _node(settings, events, read_documents),
        NODE_WRITE_INTERNAL: _node(settings, events, write_internal_report),
        NODE_SEND_EXTERNAL: _node(settings, events, send),
        NODE_UPLOAD_EXTERNAL: _node(settings, events, upload),
    }


def build_graph(
    settings: Settings,
    model: ChatModel,
    events: EventLog,
    *,
    checkpointer: Any = None,
    required_tools: tuple[str, ...] = (),
) -> Any:
    """Compile the governed graph.

    The four `governed_node(...)` registrations below are the ONLY lines that
    differ from the plain LangGraph application this started as
    (`docs/INTEGRATION_DIFF.md` carries that diff).
    """
    nodes = build_tool_nodes(settings, events)

    builder = StateGraph(GraphState)
    builder.add_node(NODE_REASON, make_reason_node(settings, model, events, required_tools))
    # The governance boundary, one capability key per node. `select=` projects the
    # arguments that CONSTITUTE the act: whatever is not named there is not bound,
    # and LangGraph lets a caller merge state on resume, so an unprojected field
    # could be substituted after a human approved.
    builder.add_node(
        NODE_READ,
        governed_node(CAP_DOCUMENTS_READ, nodes[NODE_READ], select=bind_read),
    )
    builder.add_node(
        NODE_WRITE_INTERNAL,
        governed_node(
            CAP_REPORT_WRITE_INTERNAL, nodes[NODE_WRITE_INTERNAL], select=bind_write_internal
        ),
    )
    builder.add_node(
        NODE_SEND_EXTERNAL,
        governed_node(
            CAP_COMMUNICATIONS_SEND_EXTERNAL, nodes[NODE_SEND_EXTERNAL], select=bind_send_external
        ),
    )
    builder.add_node(
        NODE_UPLOAD_EXTERNAL,
        governed_node(
            CAP_DATA_UPLOAD_EXTERNAL, nodes[NODE_UPLOAD_EXTERNAL], select=bind_upload_external
        ),
    )

    builder.add_edge(START, NODE_REASON)
    builder.add_conditional_edges(
        NODE_REASON,
        route,
        {
            NODE_REASON: NODE_REASON,
            NODE_READ: NODE_READ,
            NODE_WRITE_INTERNAL: NODE_WRITE_INTERNAL,
            NODE_SEND_EXTERNAL: NODE_SEND_EXTERNAL,
            NODE_UPLOAD_EXTERNAL: NODE_UPLOAD_EXTERNAL,
            END: END,
        },
    )
    for tool_node in (NODE_READ, NODE_WRITE_INTERNAL, NODE_SEND_EXTERNAL, NODE_UPLOAD_EXTERNAL):
        builder.add_edge(tool_node, NODE_REASON)

    return builder.compile(checkpointer=checkpointer)
