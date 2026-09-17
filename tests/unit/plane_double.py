# SPDX-License-Identifier: Apache-2.0
"""A scripted stand-in for the published client, and the channel an answer rides.

The contract distribution DOES ship a fake, and it is not the double this tier needs.
Measured against its published sources: `sayfirst_contract_stub.stub.Stub` is "a
scenario-scripted fake that never computes policy" and it implements `ask_decision`; the
boundary calls `hold_decision`; and the fake's socket form strips the grant channel from
every answer on purpose (`sayfirst_contract_stub.stub_http`, `_without_grant`). So that
fake answers a reader's question rather than a holder's, and putting it behind a socket to
reach `hold_decision` would be a second daemon in a tier that is supposed to need none.

The double below answers `hold_decision` from a script, in the shape the boundary's own
tests use, and it mints no grant: nothing is cached, so every act in this tier asks. The
held-grant path is the boundary's own property, proven where the boundary lives. Every
claim about a real daemon is made in `tests/e2e/` against a real daemon.
"""

from __future__ import annotations

from collections.abc import Iterator

from sayfirst_contract.client import Answered, CouldNotAsk, Refused
from sayfirst_contract.decisions import Decision, DecisionAsk, Outcome, Reason
from sayfirst_contract.problems import Problem, ProblemCode, problem_retryable

AT = "2026-09-16T12:00:00+00:00"
VERSION = "sha256:" + "a" * 64

#: The generation every answer here echoes. One, because that is what the daemon this
#: demonstration speaks to answers, and a double that echoed another would be scripting a
#: disagreement rather than an answer.
GENERATION = 1


class Channel:
    """What an answer rides on. `grant` is `None`: this double mints none."""

    def __init__(self) -> None:
        self.grant = None
        self.closed = False

    def signals(self) -> Iterator[object]:
        return iter(())

    def close(self) -> None:
        self.closed = True


def _decision(outcome: Outcome, reason: Reason, *, approval_ref: str | None = None) -> Decision:
    return Decision(
        decision_ref="decision-1",
        scope="local",
        capability="communications.send.external",
        outcome=outcome,
        reason=reason,
        policy_version=VERSION,
        approval_ref=approval_ref,
        decided_at=AT,
        correlation=None,
        contract_generation=1,
        extra={},
    )


def allowed() -> tuple[object, Channel]:
    return Answered(_decision(Outcome.ALLOW, Reason.POLICY_ALLOWS), GENERATION), Channel()


def denied(reason: Reason = Reason.POLICY_DENIES) -> tuple[object, Channel]:
    return Answered(_decision(Outcome.DENY, reason), GENERATION), Channel()


def suspended(approval_ref: str) -> tuple[object, Channel]:
    return (
        Answered(
            _decision(Outcome.SUSPEND, Reason.POLICY_REQUIRES_REVIEW, approval_ref=approval_ref),
            GENERATION,
        ),
        Channel(),
    )


def could_not_ask(code: ProblemCode = ProblemCode.UNREACHABLE) -> tuple[object, Channel]:
    """A problem this side made for itself: nothing answered, so nothing was refused.

    `control_plane_answered=False` is the whole difference between this and `refused`
    below, and it is set here rather than derived, because the published reader is the one
    place a document from the far end becomes a problem that claims otherwise.
    `contract_generation` is `None` for the same reason: a generation is something an
    answer carries, and there was no answer.
    """
    problem = Problem(
        code=code,
        message="nothing is listening at that address",
        retryable=problem_retryable(code),
        contract_generation=None,
        member=None,
        control_plane_answered=False,
    )
    return CouldNotAsk(problem), Channel()


def refused(code: ProblemCode = ProblemCode.REQUEST_MALFORMED) -> tuple[object, Channel]:
    """A refusal: the question reached the control plane and it rejected it."""
    problem = Problem(
        code=code,
        message="the question was rejected",
        retryable=problem_retryable(code),
        contract_generation=GENERATION,
        member=None,
        control_plane_answered=True,
    )
    return Refused(problem), Channel()


class ScriptedPlane:
    """Answer each ask from a script, and keep every ask that was made.

    The asks are the measurement: a resumed node must put the SAME question, and a
    refused binding must put none at all.
    """

    def __init__(self, answers: list[tuple[object, Channel]]) -> None:
        self._answers = list(answers)
        self.asks: list[DecisionAsk] = []

    def hold_decision(self, ask: DecisionAsk) -> tuple[object, Channel]:
        self.asks.append(ask)
        if not self._answers:
            raise AssertionError(f"the script ran out at ask {len(self.asks)}: {ask}")
        return self._answers.pop(0)
