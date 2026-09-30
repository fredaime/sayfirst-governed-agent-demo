# SPDX-License-Identifier: Apache-2.0
"""`MODEL_MODE=fixture` plays a scripted transcript in the real application.

The default mode used to refuse, so a reader with no model endpoint could not see the
demonstration at all. The transcript scripts what the agent PROPOSES and nothing else:
whether an act is permitted is still the control plane's answer.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from sayfirst_governed_agent_demo.app import SCENARIOS
from sayfirst_governed_agent_demo.model import ScriptedModel
from sayfirst_governed_agent_demo.transcripts import IDENTITY, fixture_transcript


def _proposed(model: ScriptedModel) -> set[str]:
    return {call.name for reply in model.replies for call in reply.tool_calls}


@pytest.mark.parametrize("take", sorted(SCENARIOS))
def test_each_take_proposes_every_act_its_task_requires(take: str) -> None:
    model = fixture_transcript(take)
    assert set(SCENARIOS[take].required_tools) <= _proposed(model)


def test_the_deny_take_proposes_only_the_upload() -> None:
    assert _proposed(fixture_transcript("deny")) == {"upload_external"}


def test_an_unknown_take_has_no_transcript() -> None:
    with pytest.raises(ValueError, match="no scripted transcript"):
        fixture_transcript("nonsense")


def test_fixture_mode_builds_the_transcript_and_names_it() -> None:
    # Imported here, not at module level, deliberately: another test purges and
    # re-imports this package, and `build_model` imports `transcripts` lazily, so a
    # module-level `ScriptedModel` could be a DIFFERENT class object from the one
    # the call returns.
    from sayfirst_governed_agent_demo import model as engine
    from sayfirst_governed_agent_demo import transcripts

    model = engine.build_model(SimpleNamespace(mode=engine.ModelMode.fixture), take="allow")
    assert isinstance(model, engine.ScriptedModel)
    assert model.identity == transcripts.IDENTITY
    assert "scripted transcript" in IDENTITY and "fixture" in IDENTITY


def test_a_scripted_take_says_it_proposes() -> None:
    assert fixture_transcript("hitl").turn_verb == "proposes"


def test_the_turn_line_of_a_scripted_take_claims_no_reasoning() -> None:
    """The line the graph records on every turn, built by the function the graph calls."""
    from sayfirst_governed_agent_demo.model import turn_line

    said = turn_line(fixture_transcript("hitl"))
    assert said == f"{IDENTITY} proposes"
    assert "reasoning" not in said


def test_a_model_without_a_turn_verb_still_reasons() -> None:
    from sayfirst_governed_agent_demo.model import turn_line

    assert turn_line(SimpleNamespace(identity="some-model")) == "some-model reasoning"
