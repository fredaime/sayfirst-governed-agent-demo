# SPDX-License-Identifier: Apache-2.0
"""Every environment-derived value this demonstration reads, resolved in one place.

Nothing else in this package calls `os.environ`. A hardcoded address scattered across
modules is the failure mode this file exists to prevent: the control plane's socket, the
model endpoint and the runtime directories each have exactly one name here.

Two settings have no default on purpose, and the difference between them and the rest is
the point. The socket has one, because this repository's own start script creates it and
prints it. The model's address has none, because inventing one would be a claim about the
reader's machine.
"""

from __future__ import annotations

import os
import pwd
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

#: The four capability keys this demonstration governs, and the only place the strings are
#: written in this package: every module that governs a node imports these names.
#:
#: Lowercase words joined by DOTS. That is what the published spelling admits and all it
#: admits — an underscore inside a segment is refused, the rule carrying it is refused with
#: it, and one refused rule makes the policy file unparseable, so the control plane would
#: hold no policy at all rather than three working rules. `demo-policy.toml` names these
#: four and `tests/test_the_policy_says_what_the_documents_say.py` reads them off this
#: module, so a key renamed here and not there is red before anything starts.
CAP_DOCUMENTS_READ = "documents.read"
CAP_REPORT_WRITE_INTERNAL = "report.write.internal"
CAP_COMMUNICATIONS_SEND_EXTERNAL = "communications.send.external"
CAP_DATA_UPLOAD_EXTERNAL = "data.upload.external"


class ModelMode(StrEnum):
    """`real` talks to an endpoint you name; `fixture` replays a scripted transcript.

    There is deliberately no automatic fallback between them: a demonstration that quietly
    degraded to the transcript would be showing governance over a model that was never
    there. `fixture` is the default so that a reader who clones this and runs the tests
    gets a green run with no model at all, and `real` is what a take opts into.
    """

    real = "real"
    fixture = "fixture"


class ConfigurationError(RuntimeError):
    """A setting is missing or unusable. Raised at startup, never at the boundary."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _path(name: str, default: str) -> Path:
    raw = os.environ.get(name, "").strip()
    candidate = Path(raw) if raw else _repo_root() / default
    return candidate if candidate.is_absolute() else (_repo_root() / candidate).resolve()


def _run_directory() -> Path:
    """Where this demonstration's own start script puts the socket, policy and evidence."""
    named = os.environ.get("SAYFIRST_DEMO_RUN", "").strip()
    if named:
        return Path(named)
    runtime = os.environ.get("XDG_RUNTIME_DIR", "").strip()
    return Path(runtime or Path.home() / ".cache") / "sayfirst-demo"


@dataclass(frozen=True)
class ModelSettings:
    """One transport, deliberately. Every server that speaks the OpenAI-compatible API
    differs only in the address, the model name and the key."""

    mode: ModelMode
    base_url: str | None
    name: str | None
    api_key: str | None
    temperature: float

    @property
    def display_name(self) -> str:
        named = os.environ.get("MODEL_DISPLAY_NAME", "").strip()
        return named or self.name or "no model"


@dataclass(frozen=True)
class Settings:
    agent_display_name: str
    #: The address the control plane is listening at.
    socket_path: Path
    #: The scope every question is asked in. There is no tenant: the axis is the scope.
    scope: str
    #: Who the agent is, as the boundary spells a person. Never sent as a credential — the
    #: control plane establishes identity from the connection's peer — and it is the
    #: reference the policy file's rules name.
    principal_reference: str
    model: ModelSettings
    demo_data: Path
    outbox: Path
    reports: Path
    events: Path

    def export_environment(self) -> None:
        """Publish what the boundary module reads when it is imported.

        That module composes its client and its boundary at import time, so calling this
        BEFORE importing anything that imports it is what lets an environment file, a
        command-line flag and a test fixture all reach the boundary through one resolved
        set of settings rather than through scattered lookups that could disagree.
        """
        os.environ["SAYFIRST_SOCKET"] = str(self.socket_path)
        os.environ["SAYFIRST_SCOPE"] = self.scope
        os.environ["SAYFIRST_PRINCIPAL"] = self.principal_reference


def _this_account() -> str:
    return f"user:{pwd.getpwuid(os.geteuid()).pw_name}"


def _model_mode() -> ModelMode:
    raw = os.environ.get("MODEL_MODE", "fixture").strip().lower()
    try:
        return ModelMode(raw)
    except ValueError as exc:
        raise ConfigurationError(
            f"MODEL_MODE={raw!r} is not a mode. Use 'fixture' (a scripted transcript, and "
            f"the default: no model is needed) or 'real' (an endpoint you name in "
            f"MODEL_BASE_URL and MODEL_NAME)."
        ) from exc


def _model() -> ModelSettings:
    mode = _model_mode()
    base_url = os.environ.get("MODEL_BASE_URL", "").strip().rstrip("/") or None
    name = os.environ.get("MODEL_NAME", "").strip() or None
    if mode is ModelMode.real and (base_url is None or name is None):
        raise ConfigurationError(
            "MODEL_MODE=real asks for a model, and neither MODEL_BASE_URL nor MODEL_NAME "
            "has a default here: a default address would be a claim about your machine, "
            "and a default model name would be a claim about what that address serves. "
            "Set both — any server speaking the OpenAI-compatible API will do — or leave "
            "MODEL_MODE unset, which is 'fixture' and needs no model at all."
        )
    return ModelSettings(
        mode=mode,
        base_url=base_url,
        name=name,
        api_key=os.environ.get("MODEL_API_KEY", "").strip() or None,
        temperature=float(os.environ.get("MODEL_TEMPERATURE", "0")),
    )


def load_settings() -> Settings:
    socket_path = os.environ.get("SAYFIRST_SOCKET", "").strip()
    return Settings(
        agent_display_name=os.environ.get("DEMO_AGENT_NAME", "ResearchOps Agent").strip(),
        socket_path=Path(socket_path) if socket_path else _run_directory() / "daemon.sock",
        scope=os.environ.get("SAYFIRST_SCOPE", "").strip() or "local",
        principal_reference=os.environ.get("SAYFIRST_PRINCIPAL", "").strip() or _this_account(),
        model=_model(),
        demo_data=_path("DEMO_DATA", "demo_data"),
        outbox=_path("DEMO_OUTBOX", "runtime/outbox"),
        reports=_path("DEMO_REPORTS", "runtime/reports"),
        events=_path("DEMO_EVENTS", "runtime/events"),
    )
