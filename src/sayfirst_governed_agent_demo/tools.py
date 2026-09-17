# SPDX-License-Identifier: Apache-2.0
"""The four acts the agent can request, and the schemas the model chooses from.

None of these functions asks the control plane anything. The question is put
by the wrapper around the graph node that calls them (`graph.py`), before the
call; the two functions whose act leaves the machine take the answer they were
called under as a keyword-only argument and write it into the artefact they
produce, so the artefact names the decision and the capability it was executed
under. A tool cannot be called without one, and none of them reads or asks for
anything beyond it.

Every side effect is real -- a file appears on disk -- but every destination is
local. No email is ever sent. The outbox is the objective evidence the
acceptance tests assert on: empty before approval, empty after rejection,
exactly one artefact after an authorised send.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sayfirst_governed_agent_demo.settings import (
    CAP_COMMUNICATIONS_SEND_EXTERNAL,
    CAP_DATA_UPLOAD_EXTERNAL,
    CAP_DOCUMENTS_READ,
    CAP_REPORT_WRITE_INTERNAL,
    Settings,
)

#: A filename the demo is willing to create. Anything else is refused rather
#: than sanitised: a model that proposes `../../etc/passwd` should see a refusal,
#: not a quietly rewritten path.
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class ToolRefused(RuntimeError):
    """The act itself is malformed. Distinct from a governance refusal: this is
    the tool saying "that is not a thing I can do", never "you may not"."""


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _checked_name(candidate: str) -> str:
    name = Path(str(candidate)).name
    if not _SAFE_NAME.match(name):
        raise ToolRefused(f"{candidate!r} is not a name this demo will write")
    return name


@dataclass(frozen=True)
class ToolSpec:
    """One tool as the model sees it, plus the capability it is governed under.

    The two live together deliberately: a tool the model can propose and the
    capability key the authority answers about are one fact, and splitting them
    across two files is how they drift.
    """

    name: str
    capability: str
    description: str
    parameters: dict[str, Any]

    def as_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="read_documents",
        capability=CAP_DOCUMENTS_READ,
        description=(
            "Read the internal research corpus and return every document in it. "
            "Call this once, first, before writing anything. Takes no arguments."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
    ),
    ToolSpec(
        name="write_internal_report",
        capability=CAP_REPORT_WRITE_INTERNAL,
        description=(
            "Save the report you have just written to the internal report store. "
            "Write the report as an ordinary message FIRST, then call this to save "
            "it. It saves your own last written report; it does not take the text "
            "as an argument."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
    ),
    ToolSpec(
        name="send_external_email",
        capability=CAP_COMMUNICATIONS_SEND_EXTERNAL,
        description=(
            "Send the saved internal report by email to a recipient OUTSIDE the "
            "organisation. Use this once, after the internal report is saved."
        ),
        parameters={
            "type": "object",
            "properties": {
                "recipient": {
                    "type": "string",
                    "description": "REQUIRED. The external email address named in the task.",
                }
            },
            "required": ["recipient"],
        },
    ),
    ToolSpec(
        name="upload_external",
        capability=CAP_DATA_UPLOAD_EXTERNAL,
        description=(
            "Upload the saved report to an external storage destination outside the "
            "organisation. Only use this if explicitly asked to upload data."
        ),
        parameters={
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "REQUIRED. The external destination URL named in the task.",
                }
            },
            "required": ["destination"],
        },
    ),
)

#: The demo's own naming for the artefacts the agent produces. These are product
#: decisions, not model output: the model writes the REPORT and chooses WHO
#: receives it, and those are the two things the governance boundary binds.
REPORT_FILENAME = "research-report.md"
EXTERNAL_SUBJECT = "ResearchOps report"
UPLOAD_FILENAME = REPORT_FILENAME

TOOLS_BY_NAME: dict[str, ToolSpec] = {spec.name: spec for spec in TOOLS}
CAPABILITY_BY_TOOL: dict[str, str] = {spec.name: spec.capability for spec in TOOLS}


def openai_tool_schemas() -> list[dict[str, Any]]:
    return [spec.as_openai_schema() for spec in TOOLS]


# -- the side effects ----------------------------------------------------------
#
# Each takes the already-validated argument dict and performs exactly one act.
# They are called from inside the governed node's body, which means they run
# only under a decision the authority has already answered.


def corpus(settings: Settings) -> list[Path]:
    """The documents this capability covers, in a stable order."""
    return sorted(settings.demo_data.glob("*.md"))


def read_documents(settings: Settings, args: dict[str, Any]) -> str:
    """Read the whole internal corpus: one capability, one act.

    One act rather than one per file because `documents.read` is a statement
    about the corpus, not about a filename -- and because a governed node is one
    capability key, so a per-file loop would be the same key asked N times for
    no additional governance meaning.
    """
    documents = corpus(settings)
    if not documents:
        raise ToolRefused(f"the research corpus at {settings.demo_data} is empty")
    return "\n\n".join(f"## {path.name}\n{path.read_text(encoding='utf-8')}" for path in documents)


def write_internal_report(settings: Settings, args: dict[str, Any]) -> str:
    """Save the report the model wrote in its own prose.

    The text is not a tool ARGUMENT -- it is the model's own last written
    message, carried in graph state. Small instruct models emit short arguments
    reliably and long ones not at all, and a demo that demanded a long argument
    would be demonstrating a transport limit rather than a governance boundary.
    What is governed is unchanged: the binding projects the filename and the
    DIGEST of exactly this text, so what a human approves is what gets written.
    """
    name = _checked_name(args.get("filename", "") or REPORT_FILENAME)
    content = str(args.get("content", ""))
    if not content.strip():
        raise ToolRefused(
            "you have not written a report yet. Write the report as an ordinary "
            "message first, then call write_internal_report to save it."
        )
    settings.reports.mkdir(parents=True, exist_ok=True)
    path = settings.reports / name
    path.write_text(content, encoding="utf-8")
    return f"internal report saved to {path.name} ({len(content)} characters)"


def send_external_email(settings: Settings, args: dict[str, Any], *, governance: dict) -> str:
    """The protected act. Writes one artefact to the outbox and nothing else.

    Idempotent by construction: the artefact's name carries the REFERENCE of the
    governance decision that authorised it, as the control plane minted it and
    unhashed, so a body that somehow ran twice under one decision overwrites
    rather than duplicates. The demo does not claim distributed exactly-once --
    it claims that ONE authorised decision yields ONE outbox artefact, and the
    filename is what makes that true rather than a counter nobody checks.
    """
    recipient = str(args.get("recipient", "")).strip()
    subject = str(args.get("subject", "")).strip()
    body = str(args.get("body", ""))
    if not recipient or "@" not in recipient:
        raise ToolRefused(f"{recipient!r} is not an email address")

    settings.outbox.mkdir(parents=True, exist_ok=True)
    reference = str(governance.get("decision_ref") or "no-decision")
    artefact = settings.outbox / f"message-{reference}.json"
    artefact.write_text(
        json.dumps(
            {
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "executed_at": _iso_now(),
                "governance": governance,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return f"external message delivered to {recipient}"


def upload_external(settings: Settings, args: dict[str, Any], *, governance: dict) -> str:
    destination = str(args.get("destination", "")).strip()
    name = _checked_name(args.get("filename", "") or "payload.bin")
    settings.outbox.mkdir(parents=True, exist_ok=True)
    reference = str(governance.get("decision_ref") or "no-decision")
    artefact = settings.outbox / f"upload-{reference}.json"
    artefact.write_text(
        json.dumps(
            {
                "destination": destination,
                "filename": name,
                "executed_at": _iso_now(),
                "governance": governance,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return f"uploaded {name} to {destination}"


def outbox_count(settings: Settings) -> int:
    """The filesystem assertion the acceptance suite rests on -- never telemetry."""
    if not settings.outbox.is_dir():
        return 0
    return len(list(settings.outbox.glob("*.json")))
