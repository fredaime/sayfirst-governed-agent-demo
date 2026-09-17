# SPDX-License-Identifier: Apache-2.0
"""The screen-recordable event stream.

Two kinds of line, and the difference is load-bearing. An `OBSERVED` event
records something the runtime actually did or was told -- a model turn, a
boundary refusal, an approval reference the authority minted, a file that
appeared on disk. A `DERIVED` event is presentation: a heading, a restatement,
a count computed for the viewer. Only `OBSERVED` lines are evidence, and the
renderer marks the difference so a viewer is never invited to read a caption as
a security property.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, TextIO


class Kind(StrEnum):
    observed = "OBSERVED"
    derived = "DERIVED"


class Channel(StrEnum):
    model = "MODEL"
    policy = "POLICY"
    control = "CONTROL"
    agent = "AGENT"
    human = "HUMAN"
    exec = "EXEC"
    evidence = "EVIDENCE"
    demo = "DEMO"


_COLOUR = {
    Channel.model: "\033[38;5;118m",  # the model's channel
    Channel.policy: "\033[38;5;214m",
    Channel.control: "\033[38;5;39m",
    Channel.agent: "\033[38;5;245m",
    Channel.human: "\033[38;5;213m",
    Channel.exec: "\033[38;5;51m",
    Channel.evidence: "\033[38;5;111m",
    Channel.demo: "\033[38;5;245m",
}
_RESET = "\033[0m"
_DIM = "\033[2m"


@dataclass(frozen=True)
class Event:
    at: str
    channel: Channel
    kind: Kind
    message: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventLog:
    """Prints as it goes and keeps the sequence for the evidence view."""

    stream: TextIO = sys.stdout
    colour: bool = True
    events: list[Event] = field(default_factory=list)

    def record(
        self,
        channel: Channel,
        message: str,
        *,
        kind: Kind = Kind.observed,
        **detail: Any,
    ) -> Event:
        event = Event(
            at=datetime.now(UTC).strftime("%H:%M:%S"),
            channel=channel,
            kind=kind,
            message=message,
            detail=detail,
        )
        self.events.append(event)
        self._print(event)
        return event

    # Convenience wrappers, one per channel, so call sites read as the story does.
    def model(self, message: str, **detail: Any) -> Event:
        return self.record(Channel.model, message, **detail)

    def policy(self, message: str, **detail: Any) -> Event:
        return self.record(Channel.policy, message, **detail)

    def control(self, message: str, **detail: Any) -> Event:
        return self.record(Channel.control, message, **detail)

    def agent(self, message: str, **detail: Any) -> Event:
        return self.record(Channel.agent, message, **detail)

    def execution(self, message: str, **detail: Any) -> Event:
        return self.record(Channel.exec, message, **detail)

    def record_human(self, answer: str) -> Event:
        """A person answered with the command. OBSERVED: read from the authority."""
        return self.record(Channel.human, f"operator {answer} the request", answer=answer)

    def evidence_record(self, record: Any) -> Event:
        """One outcome record the boundary made. OBSERVED, and metadata only.

        `dropped_before` travels with it because a record that did not say how many were
        lost before it would read as a complete history of an incomplete one.
        """
        return self.record(
            Channel.evidence,
            "the boundary recorded an outcome",
            sequence=record.sequence,
            capability=record.capability,
            decision=record.decision_ref,
            outcome=record.outcome_digest,
            dropped_before=record.dropped_before,
        )

    def note(self, message: str, **detail: Any) -> Event:
        """A DERIVED line: for the viewer, never evidence."""
        return self.record(Channel.demo, message, kind=Kind.derived, **detail)

    def _print(self, event: Event) -> None:
        colour = _COLOUR.get(event.channel, "") if self.colour else ""
        reset = _RESET if self.colour else ""
        dim = _DIM if self.colour else ""
        mark = " " if event.kind is Kind.observed else "~"
        detail = ""
        if event.detail:
            rendered = "  ".join(f"{k}={v}" for k, v in event.detail.items() if v is not None)
            detail = f"  {dim}{rendered}{reset}" if rendered else ""
        line = (
            f"{dim}{event.at}{reset} {mark}{colour}{event.channel.value:<8}{reset} "
            f"{event.message}{detail}"
        )
        print(line, file=self.stream, flush=True)

    def dump(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps([asdict(e) | {"channel": e.channel.value} for e in self.events], indent=2),
            encoding="utf-8",
        )
