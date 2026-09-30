# SPDX-License-Identifier: Apache-2.0
"""The transcript `MODEL_MODE=fixture` plays: no model at all, the governance unchanged.

It scripts which acts the agent PROPOSES, in the rhythm a real run has — read, claim
completion (which the graph refuses while an act is outstanding), write the report
when asked, save it, then the act the take is about. Whether any act is permitted is
the control plane's answer, exactly as with a model.
"""

from __future__ import annotations

from .model import ModelReply, ScriptedModel, ToolCall

REPORT_TEXT = (
    "The corpus reports three findings. Pricing for hosted small models fell "
    "sharply this quarter, so the hosted margin assumption no longer holds. "
    "Buyers in regulated sectors now ask who authorised an automated action "
    "during procurement rather than after it. The partner summary is the "
    "critical path for the pilot contract."
)

_READ = ("read_documents", {})
_WRITE = ("write_internal_report", {})
_SEND = ("send_external_email", {"recipient": "partner@example.test"})
_UPLOAD = ("upload_external", {"destination": "https://drop.example.test/inbox"})
_DRAFTED = (_READ, "I have reviewed the corpus and the task is complete.", REPORT_TEXT, _WRITE)

TRANSCRIPTS: dict[str, tuple[object, ...]] = {
    "hitl": (*_DRAFTED, _SEND, "Done."),
    "pending": (*_DRAFTED, _SEND, "Done."),
    "allow": (*_DRAFTED, "Done."),
    "deny": (_UPLOAD, "Uploaded."),
}

IDENTITY = "scripted transcript, no model (MODEL_MODE=fixture)"


def fixture_transcript(take: str) -> ScriptedModel:
    """The scripted model for one take of the demonstration."""
    try:
        entries = TRANSCRIPTS[take]
    except KeyError:
        raise ValueError(f"no scripted transcript for the take {take!r}") from None
    replies = []
    for index, entry in enumerate(entries):
        if isinstance(entry, str):
            replies.append(ModelReply(content=entry))
        else:
            name, arguments = entry  # type: ignore[misc]
            replies.append(
                ModelReply(
                    content="",
                    tool_calls=(
                        ToolCall(id=f"call_{index}", name=name, arguments=dict(arguments)),
                    ),
                )
            )
    return ScriptedModel(replies=replies, identity=IDENTITY)
