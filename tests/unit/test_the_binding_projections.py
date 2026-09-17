# SPDX-License-Identifier: Apache-2.0
"""Unit tier: no control plane, no model, no GPU, no network.

Three things are worth checking in isolation, because each is a place where a
governance property could be lost quietly rather than loudly:

* the binding projections -- what a human's approval is actually bound to;
* transport normalisation -- a tool call arrives however the model wrapped
  it, and what reaches the tool must be the arguments themselves;
* what an external act WRITES under a decision, which is the only assertion
  that enters the fourth capability's body: the acceptance suite reaches that
  capability under a `deny` rule, so the tier that drives a real control plane
  never runs the lines that produce its artefact.
"""

from __future__ import annotations

import json

import pytest

from sayfirst_governed_agent_demo.model import ModelUnavailable, _parse_arguments
from sayfirst_governed_agent_demo.settings import load_settings
from sayfirst_governed_agent_demo.state import (
    _digest,
    bind_send_external,
    bind_write_internal,
    resolve_act,
)
from sayfirst_governed_agent_demo.tools import outbox_count, upload_external


def _state(tool: str, arguments: dict, **extra):
    return {
        "pending": {"call_id": "c1", "tool": tool, "arguments": arguments, "sequence": 3},
        **extra,
    }


# -- the binding names every security-relevant field ---------------------------


def test_the_external_send_binds_recipient_domain_subject_and_payload():
    state = _state(
        "send_external_email",
        {"recipient": "partner@example.test"},
        report_text="the report",
    )
    binding = bind_send_external(state)

    assert binding["recipient"] == "partner@example.test"
    assert binding["destination_domain"] == "example.test"
    assert binding["subject"], "the operation identity is bound, not just the address"
    assert binding["body_digest"], "the payload is bound by digest"
    assert "the report" not in str(binding), "the payload itself never travels into governance"


def test_changing_any_bound_field_changes_the_binding():
    """Each of these is a different act, so each must digest differently."""
    base = bind_send_external(
        _state("send_external_email", {"recipient": "partner@example.test"}, report_text="r")
    )
    attacker = bind_send_external(
        _state("send_external_email", {"recipient": "attacker@example.test"}, report_text="r")
    )
    other_payload = bind_send_external(
        _state("send_external_email", {"recipient": "partner@example.test"}, report_text="r2")
    )

    elsewhere = bind_send_external(
        _state("send_external_email", {"recipient": "partner@evil.test"}, report_text="r")
    )

    assert base != attacker, "a different recipient is a different act"
    assert base != other_payload, "a different payload is a different act"
    # Same domain, different mailbox: the recipient carries it, not the domain.
    assert base["destination_domain"] == attacker["destination_domain"]
    assert base["recipient"] != attacker["recipient"]
    # A different domain moves both.
    assert base["destination_domain"] != elsewhere["destination_domain"]


def test_the_binding_digests_what_the_body_will_actually_use():
    """The projection and the side effect read ONE resolution.

    If these could diverge, an approval could name one thing while the body did
    another -- which is the whole failure this demo exists to rule out.
    """
    state = _state("write_internal_report", {}, draft="the model's own report text")

    resolved = resolve_act(state)
    binding = bind_write_internal(state)

    assert binding["content_digest"] == _digest(resolved["content"])
    assert resolved["content"] == "the model's own report text"


# -- transport normalisation ---------------------------------------------------


def test_a_doubly_wrapped_tool_call_is_unwrapped():
    assert _parse_arguments('{"arguments": {"recipient": "p@example.test"}, "type": "send"}') == {
        "recipient": "p@example.test"
    }


def test_a_tool_that_really_takes_arguments_is_left_alone():
    """The unwrap must not eat a legitimate parameter called `arguments`."""
    payload = '{"arguments": {"a": 1}, "recipient": "p@example.test"}'
    assert _parse_arguments(payload) == {"arguments": {"a": 1}, "recipient": "p@example.test"}


def test_malformed_tool_arguments_are_loud():
    # `ModelUnavailable` is imported at module level, with `_parse_arguments`,
    # deliberately: the e2e fixtures purge and re-import this package between
    # tests, so a late import here would resolve to a DIFFERENT module object
    # and the raised exception would not match the caught one.
    with pytest.raises(ModelUnavailable):
        _parse_arguments("{not json")


# -- what an authorised external act writes ------------------------------------


def test_the_upload_writes_one_artefact_naming_its_decision(monkeypatch, tmp_path) -> None:
    """The fourth capability's body, entered once, with no boundary anywhere.

    Called directly and under a governance dictionary, which is how it is called
    for real: the wrapper has already asked, the answer is what arrives as the
    keyword argument, and the body's whole job is to write the artefact and name
    it. Three things are asserted because each is a claim a document makes: one
    artefact, its name carrying the decision REFERENCE as the control plane
    minted it and unhashed, and the decision recorded inside it.

    A second call under the same decision is what makes « one authorised
    decision, one artefact » a property of the filename rather than of a counter,
    so it is made here rather than described.
    """
    monkeypatch.delenv("MODEL_MODE", raising=False)
    monkeypatch.setenv("DEMO_OUTBOX", str(tmp_path / "outbox"))
    settings = load_settings()
    governance = {
        "capability": "data.upload.external",
        "decision_ref": "11111111-2222-3333-4444-555555555555",
    }

    said = upload_external(
        settings,
        {"destination": "https://drop.example.test/inbox", "filename": "payload.bin"},
        governance=governance,
    )

    assert "drop.example.test" in said
    assert outbox_count(settings) == 1
    artefact = settings.outbox / f"upload-{governance['decision_ref']}.json"
    assert artefact.is_file(), sorted(p.name for p in settings.outbox.iterdir())
    written = json.loads(artefact.read_text(encoding="utf-8"))
    assert written["governance"] == governance
    assert written["destination"] == "https://drop.example.test/inbox"
    assert written["filename"] == "payload.bin"

    upload_external(
        settings,
        {"destination": "https://drop.example.test/inbox", "filename": "payload.bin"},
        governance=governance,
    )
    assert outbox_count(settings) == 1, "a second run under one decision overwrote nothing"
