# SPDX-License-Identifier: Apache-2.0
"""The demo entry point: `run-demo.sh <scenario>`.

Prints a story a viewer can follow in sixty seconds, and asserts the one fact
that matters at every step -- how many artefacts are in the outbox.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from dataclasses import dataclass
from typing import Any

from sayfirst_governed_agent_demo.agent import (
    COMPLETED,
    DENIED,
    REFUSED,
    REJECTED,
    SUSPENDED,
    UNOBSERVABLE,
)
from sayfirst_governed_agent_demo.demo_events import EventLog
from sayfirst_governed_agent_demo.settings import ConfigurationError, Settings, load_settings
from sayfirst_governed_agent_demo.tools import outbox_count

BANNER = "\033[38;5;118m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

TASK_FULL = (
    "Review the documents in the internal research corpus, summarise the important "
    "findings, save an internal report, and send the report to the external partner "
    "at partner@example.test."
)
TASK_UPLOAD = (
    "Upload the file project-status.md to the external storage destination "
    "https://drop.example.test/inbox. Do not read documents, do not write a "
    "report and do not send email -- perform the upload only."
)


@dataclass(frozen=True)
class Scenario:
    name: str
    task: str
    description: str
    #: The acts this task asks for. The graph uses them to refuse a premature
    #: "I am done"; it never uses them to perform an act the model did not ask
    #: for.
    required_tools: tuple[str, ...] = ()
    #: What the demo does when the graph suspends. `wait` polls the authority
    #: until a person answers with the command the suspension notice prints;
    #: `report` stops and prints the pending state (used for the first half of a
    #: recording).
    on_suspend: str = "wait"


SCENARIOS = {
    "hitl": Scenario(
        "hitl",
        TASK_FULL,
        "read + internal write execute automatically; the external send waits for a human",
        required_tools=("read_documents", "write_internal_report", "send_external_email"),
    ),
    "allow": Scenario(
        "allow",
        # Deliberately TASK_FULL's wording minus the delivery clause. Measured:
        # this model follows the imperative list ("Review ..., summarise ...,
        # save ...") and stops calling tools at all when the task is rephrased,
        # so the two scenarios share one sentence shape rather than two.
        "Review the documents in the internal research corpus, summarise the "
        "important findings, and save an internal report.",
        "only automatic capabilities: nothing suspends",
        required_tools=("read_documents", "write_internal_report"),
    ),
    "deny": Scenario(
        "deny",
        TASK_UPLOAD,
        "a capability the policy denies outright: no approval, no side effect",
        required_tools=("upload_external",),
    ),
    "pending": Scenario(
        "pending",
        TASK_FULL,
        "stops at the suspension without waiting -- proves the side effect has not happened",
        required_tools=("read_documents", "write_internal_report", "send_external_email"),
        on_suspend="report",
    ),
}


def _header(settings: Settings, model_identity: str, scenario: Scenario) -> None:
    """What a take opens on: the model, the authority's address, the scope, the agent.

    Four facts and no fifth. The address is where the decision goes and the scope is the
    axis it is asked on — there is no tenant in the open control plane, and a header that
    printed one would be describing a product this is not. The agent's display name stays
    because a recording needs something to call it.
    """
    print(f"\n{BANNER}{BOLD}A governed agent demonstration{RESET}", flush=True)
    print(f"{DIM}The model proposes. The control plane decides.{RESET}\n", flush=True)
    print(f"  Model          {BANNER}{model_identity}{RESET}", flush=True)
    print(f"  Control plane  {settings.socket_path}", flush=True)
    print(f"  Scope          {settings.scope}", flush=True)
    print(
        f"  Agent          {settings.agent_display_name}  ({settings.principal_reference})",
        flush=True,
    )
    print(f"  Scenario       {scenario.name} -- {scenario.description}", flush=True)
    print(f"\n{BOLD}Task{RESET}\n  {scenario.task}\n", flush=True)


def _suspension_notice(result: Any, settings: Settings, boundary_setup: Any) -> None:
    print(f"\n\033[38;5;214m{BOLD}  GOVERNANCE: A PERSON MUST ANSWER{RESET}", flush=True)
    print(f"  Capability          {result.capability}", flush=True)
    print(f"  Approval reference  {result.approval_ref}", flush=True)
    print(f"  Graph state         {BOLD}SUSPENDED{RESET}", flush=True)
    print(f"  Outbox messages     {BOLD}{outbox_count(settings)}{RESET}", flush=True)
    print(f"  Side effect status  {BOLD}NOT EXECUTED{RESET}\n", flush=True)
    print(f"{DIM}  Answer it, in another terminal:", flush=True)
    # The scope and the address are read from the module that actually composed the
    # client, never from a second reading of the environment: a notice that printed a
    # different address from the one the question went to would be worse than none.
    print(
        f"    sayfirst approvals approve --approval {result.approval_ref} "
        f"--scope {boundary_setup.SCOPE} --socket {boundary_setup.SOCKET_PATH}",
        flush=True,
    )
    print(
        f"  Resuming grants nothing: the node asks again and the control plane answers.{RESET}\n",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sayfirst-governed-agent-demo")
    parser.add_argument("scenario", nargs="?", default="hitl", choices=sorted(SCENARIOS))
    parser.add_argument("--thread", default=None, help="graph thread id (default: random)")
    parser.add_argument(
        "--approval-timeout", type=float, default=300.0, help="seconds to wait for a human"
    )
    args = parser.parse_args(argv)
    scenario = SCENARIOS[args.scenario]

    try:
        settings = load_settings()
    except ConfigurationError as unusable:
        # The same treatment the model's own refusals get below, and for the same reason:
        # a setting that is missing composed a sentence saying which one and what to do
        # with it, and a stack trace through a call the reader never made buries it.
        print(f"\n\033[31m{unusable}{RESET}\n", file=sys.stderr, flush=True)
        return 7
    settings.export_environment()

    from sayfirst_governed_agent_demo.model import (
        ConfigurationRefused,
        ModelUnavailable,
        build_model,
    )

    events = EventLog()
    try:
        model = build_model(settings.model)
    except (ConfigurationRefused, ModelUnavailable) as unavailable:
        # Two refusals, one exit. `fixture` is the default mode now and no script forces a
        # mode on a run, so the commonest way to arrive here is a reader who named no model
        # at all — and what they need is the sentence saying which settings to name, not a
        # traceback through a call they did not make.
        print(f"\n\033[31m{unavailable}{RESET}\n", file=sys.stderr, flush=True)
        return 7

    _header(settings, model.identity, scenario)

    # Imported only now: `sayfirst_governed_agent_demo.boundary_setup` composes the boundary
    # from the environment `export_environment()` just published.
    from langgraph.checkpoint.memory import InMemorySaver

    from sayfirst_governed_agent_demo import boundary_setup
    from sayfirst_governed_agent_demo.agent import GovernedRun, wait_for_a_person
    from sayfirst_governed_agent_demo.graph import build_graph

    boundary_setup.also_record_into(events.evidence_record)

    graph = build_graph(
        settings,
        model,
        events,
        checkpointer=InMemorySaver(),
        required_tools=scenario.required_tools,
    )
    run = GovernedRun(
        app=graph, settings=settings, events=events, thread_id=args.thread or uuid.uuid4().hex
    )

    result = run.start(scenario.task)
    while result.verdict is SUSPENDED:
        _suspension_notice(result, settings, boundary_setup)
        if scenario.on_suspend == "report":
            _epilogue(settings, result, events)
            return result.exit_code
        answer = wait_for_a_person(str(result.approval_ref), timeout_s=args.approval_timeout)
        if answer == "pending":
            print(f"{DIM}  Nobody answered inside the wait. Still suspended.{RESET}", flush=True)
            break
        events.record_human(answer)
        result = run.resume()

    _epilogue(settings, result, events)
    return result.exit_code


def _epilogue(settings: Settings, result: Any, events: EventLog) -> None:
    print(flush=True)
    if result.verdict is COMPLETED:
        print(
            f"\033[38;5;51m{BOLD}  EXECUTED{RESET}  the run completed under authority", flush=True
        )
    elif result.verdict is REJECTED:
        print(
            f"\033[38;5;213m{BOLD}  REJECTED{RESET}  execution prevented by a human decision",
            flush=True,
        )
    elif result.verdict is DENIED:
        print(f"\033[38;5;196m{BOLD}  DENIED{RESET}    execution prevented by policy", flush=True)
    elif result.verdict is REFUSED:
        print(
            f"\033[38;5;196m{BOLD}  REFUSED{RESET}   the question was rejected, nothing ran",
            flush=True,
        )
    elif result.verdict is UNOBSERVABLE:
        print(
            f"\033[38;5;196m{BOLD}  FAIL CLOSED{RESET}  the control plane could not be asked, "
            f"nothing executed",
            flush=True,
        )
    if result.message:
        print(f"  {DIM}{result.message}{RESET}", flush=True)
    print(
        f"\n  {BOLD}Outbox artefacts: {outbox_count(settings)}{RESET}"
        f"   {DIM}({settings.outbox}){RESET}",
        flush=True,
    )
    if result.answer:
        print(f"\n{BOLD}Agent answer{RESET}\n  " + result.answer.replace("\n", "\n  "), flush=True)
    from sayfirst_governed_agent_demo import boundary_setup

    boundary_setup.close()
    events.dump(settings.events / "demo-events.json")
    print(f"\n{DIM}  events: {settings.events / 'demo-events.json'}{RESET}", flush=True)
    print(
        f"{DIM}  the chain the control plane kept: sayfirst evidence history --from 1 "
        f"--scope {boundary_setup.SCOPE} --socket {boundary_setup.SOCKET_PATH}{RESET}\n",
        flush=True,
    )


if __name__ == "__main__":
    sys.exit(main())
