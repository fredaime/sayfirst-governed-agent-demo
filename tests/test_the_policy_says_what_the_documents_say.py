# SPDX-License-Identifier: Apache-2.0
"""The policy file is the whole of what this demonstration's control plane decides.

Four capabilities, four answers, and the documents say which is which. A policy file that
drifted from those sentences would make every document in this repository wrong at once,
and nothing would say so — so the four rows are read out of the file here.

What this does NOT do is evaluate policy. The rules the control plane applies are its own,
published as a recipe and implemented there; this reads the file's shape against the recipe's
stated bounds — the root keys, the required members, the capability spelling, the closed set
of outcomes, and the wait a suspension is measured by.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[1]
POLICY = REPOSITORY / "demo-policy.toml"

#: What the documents say, capability by capability.
EXPECTED = {
    "documents.read": "allow",
    "report.write.internal": "allow",
    "communications.send.external": "suspend",
    "data.upload.external": "deny",
}

#: The principal the shipped file names, which the start script replaces with the account
#: running the demonstration. Read from here by the end-to-end fixture too, so a rename
#: lands in one place.
PLACEHOLDER_PRINCIPAL = "user:the-account-that-runs-this-demonstration"

#: How long a person has to answer, in the shipped file. Long enough for a take and for the
#: acceptance suite, and short of the recipe's upper bound of a day.
REVIEW_DEADLINE_SECONDS = 900


@pytest.fixture(scope="module")
def policy() -> dict[str, object]:
    return tomllib.loads(POLICY.read_text(encoding="utf-8"))


def test_the_file_is_the_format_the_control_plane_reads(policy) -> None:
    assert set(policy) <= {"format", "revision", "rule"}, policy
    assert policy["format"] == 1
    assert policy["format"] is not True, "the format is the integer one, never a boolean"
    reason = policy["revision"]["reason"]
    assert isinstance(reason, str) and 0 < len(reason) <= 512
    assert set(policy["revision"]) == {"reason"}


def test_the_four_capabilities_carry_the_four_answers_the_documents_name(policy) -> None:
    rules = policy["rule"]
    assert len(rules) == len(EXPECTED), rules
    answers = {rule["capability"]: rule["outcome"] for rule in rules}
    assert answers == EXPECTED


def test_every_rule_is_shaped_the_way_the_recipe_requires(policy) -> None:
    identifiers = set()
    for rule in policy["rule"]:
        assert set(rule) <= {
            "id",
            "capability",
            "principals",
            "outcome",
            "reason",
            "scope",
            "arguments_digest",
            "grant_lifetime_seconds",
            "review_deadline_seconds",
        }, rule
        assert {"id", "capability", "principals", "outcome", "reason"} <= set(rule), rule
        assert rule["id"] not in identifiers, rule["id"]
        identifiers.add(rule["id"])
        assert rule["scope"] == "local", "one scope, and there is no tenant beside it"
        assert rule["principals"] == [PLACEHOLDER_PRINCIPAL], rule
        assert rule["outcome"] in {"allow", "deny", "suspend"}, rule
        assert 0 < len(rule["reason"]) <= 512
        waits = rule.get("review_deadline_seconds")
        if rule["outcome"] == "suspend":
            assert waits == REVIEW_DEADLINE_SECONDS, rule
            assert 1 <= waits <= 86400
        else:
            assert waits is None, "a wait on a rule that never suspends is refused, not ignored"


def test_the_capability_keys_are_spelled_the_way_the_contract_requires(policy) -> None:
    """The one rule of this file that a whole slice of work turned on.

    The published spelling admits lowercase, dotted segments and nothing else: no
    underscore inside a segment. Three of these four keys were written with one, and the
    consequence was not a warning — the loader refuses the rule, a refused rule makes the
    whole file unparseable, and a daemon holding no policy answers nothing, so every
    acceptance case would have failed against a control plane that was never governing
    anything. They are dotted now, and what they mean is unchanged: internal or external
    is said with a dot.

    The pattern is written out rather than imported, so this case holds where the server
    distribution is not installed at all. What keeps the policy and the agent from drifting
    is the case below; what asks the loader itself is the acceptance suite, which starts a
    real daemon on this very file and would refuse to serve at all if a rule were invalid.
    """
    import re

    spelling = re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*)*$")
    for rule in policy["rule"]:
        assert spelling.match(rule["capability"]), rule["capability"]
        assert "_" not in rule["capability"], rule["capability"]


def test_the_agent_asks_about_exactly_these_capabilities() -> None:
    """The one drift this file exists to catch: a policy and an agent that disagree.

    The capability keys are read from the agent's own settings module rather than repeated
    here, so a key renamed in one place and not the other is red.
    """
    from sayfirst_governed_agent_demo import settings

    asked = {
        settings.CAP_DOCUMENTS_READ,
        settings.CAP_REPORT_WRITE_INTERNAL,
        settings.CAP_COMMUNICATIONS_SEND_EXTERNAL,
        settings.CAP_DATA_UPLOAD_EXTERNAL,
    }
    assert asked == set(EXPECTED)
