# SPDX-License-Identifier: Apache-2.0
"""What an outbox artefact records about the decision that authorised it.

Read off the handle the boundary gave the body, so the stamp names a decision the control
plane recorded and never a value this process invented. When no authorisation is on
record — which cannot happen inside a governed body — the stamp says so rather than
guessing: an artefact that cannot name its authority must not look like one that can.

There is no execution grant on the stamp. The handle a governed body holds publishes the
decision and the capability, and at-most-once is the grant the boundary holds on the
channel the answer arrived on rather than a reference a body could copy onto a file.
"""

from __future__ import annotations

from typing import Any

from sayfirst_governed_agent_demo.tools import CAPABILITY_BY_TOOL

#: The decision that authorised the act now running, per capability. Written by the node
#: wrapper inside the governed block and read by the body it opened.
_LAST: dict[str, str] = {}


def record(*, capability: str, decision_ref: str) -> None:
    _LAST[capability] = decision_ref


def forget() -> None:
    """Drop every authorisation on record. For a test that starts a fresh run."""
    _LAST.clear()


def last_authorisation(tool: str) -> dict[str, Any]:
    capability = CAPABILITY_BY_TOOL.get(tool, tool)
    return {"capability": capability, "decision_ref": _LAST.get(capability)}
