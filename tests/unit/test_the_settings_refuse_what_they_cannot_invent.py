# SPDX-License-Identifier: Apache-2.0
"""What the settings refuse rather than invent.

Two settings have no default, and the difference between having none and having a bad one is
the whole of what this module holds. An address invented here would be a claim about the
reader's machine, and a model name invented here a claim about what that address serves — so
`real` without them does not fall back, does not guess and does not start. It refuses, and the
refusal names both of the things it wanted, because a message that named one would send a
reader back for the other.

The default mode is the other half of the same rule: a reader who clones this and names
nothing at all gets settings that resolve, and no model is needed for that.
"""

from __future__ import annotations

import pytest

from sayfirst_governed_agent_demo.settings import ConfigurationError, ModelMode, load_settings


@pytest.fixture(autouse=True)
def naming_no_model(monkeypatch) -> None:
    """Whatever the machine running this has exported, these four are unset here."""
    for name in ("MODEL_MODE", "MODEL_BASE_URL", "MODEL_NAME", "MODEL_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_the_default_mode_needs_no_model_at_all() -> None:
    settings = load_settings()
    assert settings.model.mode is ModelMode.fixture
    assert settings.model.base_url is None
    assert settings.model.name is None


@pytest.mark.parametrize(
    "named",
    [
        {},
        {"MODEL_BASE_URL": "http://127.0.0.1:11434/v1"},
        {"MODEL_NAME": "a-tool-calling-model"},
    ],
    ids=["neither", "an address and no model", "a model and no address"],
)
def test_a_real_model_missing_either_setting_refuses_and_names_both(named, monkeypatch) -> None:
    monkeypatch.setenv("MODEL_MODE", "real")
    for name, value in named.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(ConfigurationError) as refused:
        load_settings()

    said = str(refused.value)
    assert "MODEL_BASE_URL" in said, said
    assert "MODEL_NAME" in said, said


def test_a_mode_that_is_not_a_mode_refuses_and_names_the_two_that_are(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_MODE", "whatever-the-reader-typed")

    with pytest.raises(ConfigurationError) as refused:
        load_settings()

    said = str(refused.value)
    assert "fixture" in said, said
    assert "real" in said, said
