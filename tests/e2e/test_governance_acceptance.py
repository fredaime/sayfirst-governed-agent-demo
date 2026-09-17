# SPDX-License-Identifier: Apache-2.0
"""The acceptance suite: what this demonstration claims, against a real control plane.

Seven claims, lettered A to G, in eight cases: the suspension is two of them, because
« the effect did not happen » and « a resume without an answer suspends again on the same
wait » are two statements and one case asserting both would pass on its first half.

Every case drives the real node wrapper, the real published boundary, the real published
client and a real daemon in its own process. Only the MODEL is scripted — so that a case
controls which acts the agent proposes, not whether they are allowed. The authority is
never stubbed, and the assertion is almost always the same one: how many artefacts are in
the outbox.

**This module needs a control plane, and its first statement says so.** Every open import
it depends on is inside a conftest fixture, so on a machine without those distributions this
module collects and then errors in the fixture, case by case — a failure where the truth is
« this could not run ». The declaration below stands the module down instead, with a reason
the gate counts and names.
"""

from __future__ import annotations

import pytest

# The open imports of this module are in the conftest's fixtures, so without this line it
# collects and then errors in the daemon fixture.
from open_packages import require_the_open_packages

require_the_open_packages(
    __file__, "it starts a real control plane as its own process and answers it"
)

pytestmark = pytest.mark.e2e

#: What the task asks for, per case. Passed to the graph exactly as the demonstration
#: passes it, so a scripted run drives the same validation loop a real run does.
READS_AND_WRITES = ("read_documents", "write_internal_report")
FULL = ("read_documents", "write_internal_report", "send_external_email")

REPORT_TEXT = (
    "The corpus reports three findings. Pricing for hosted small models fell "
    "sharply this quarter, so the hosted margin assumption no longer holds. "
    "Buyers in regulated sectors now ask who authorised an automated action "
    "during procurement rather than after it. The partner summary is the "
    "critical path for the pilot contract."
)

SEND = ("send_external_email", {"recipient": "partner@example.test"})
UPLOAD = ("upload_external", {"destination": "https://drop.example.test/inbox"})
READ = ("read_documents", {})
WRITE = ("write_internal_report", {})


def drafted(scripted, *after):
    """A transcript with the rhythm a real run has.

    The graph asks for the report before it accepts one — only the prose that ANSWERS that
    request is taken as the report — so a transcript that simply volunteered prose would
    not exercise the path a run takes. This one reads, claims completion (which the graph
    refuses), writes the report when asked, saves it, and then does `after`.
    """
    return scripted(
        READ,
        "I have reviewed the corpus and the task is complete.",
        REPORT_TEXT,
        WRITE,
        *after,
    )


# -- A: an allowed capability executes -----------------------------------------


def test_an_allowed_capability_executes(governed, workspace, scripted, outbox):
    run = governed(drafted(scripted, "Done."), required_tools=READS_AND_WRITES)
    result = run.start("Review the corpus and save an internal report.")

    assert result.verdict == "completed"
    assert (workspace / "reports" / "research-report.md").is_file()
    assert outbox() == [], "no external act was proposed, so none may have happened"


# -- B: a suspension happens BEFORE the side effect ----------------------------


def test_a_suspension_leaves_the_side_effect_not_executed(governed, scripted, outbox):
    run = governed(drafted(scripted, SEND, "Sent."), required_tools=FULL)
    result = run.start("Review the corpus, save a report and send it to the partner.")

    assert result.verdict == "suspended"
    assert result.capability == "communications.send.external"
    assert result.approval_ref, "the control plane names the wait a person is to answer"
    assert outbox() == [], "suspended means the side effect has NOT happened"


def test_resuming_without_an_answer_suspends_again_on_the_same_wait(governed, scripted, outbox):
    """Resuming is not authorisation.

    The strongest single statement this demonstration makes. The caller drives the graph
    forward exactly as it would after an approval — and because nobody has answered, the
    control plane answers the wait it still has open, on the SAME reference. Four facts
    make a re-ask the same ask: the scope, the principal reference, the capability and the
    arguments digest, and the resumed node reproduces all four.
    """
    run = governed(drafted(scripted, SEND, "Sent."), required_tools=FULL)
    first = run.start("Review the corpus, save a report and send it to the partner.")
    assert first.verdict == "suspended"

    again = run.resume()

    assert again.verdict == "suspended"
    assert again.approval_ref == first.approval_ref, "no rival wait was opened"
    assert outbox() == [], "resuming granted nothing"


# -- C: one approval, exactly one execution ------------------------------------


def test_one_approval_authorises_exactly_one_execution(governed, scripted, outbox, approve):
    run = governed(drafted(scripted, SEND, "Sent."), required_tools=FULL)
    suspended = run.start("Review the corpus, save a report and send it to the partner.")
    assert suspended.verdict == "suspended"
    assert outbox() == []

    approve(str(suspended.approval_ref))
    result = run.resume()

    assert result.verdict == "completed"
    messages = outbox()
    assert len(messages) == 1, "one approval, one message"
    assert messages[0]["recipient"] == "partner@example.test"
    governance = messages[0]["governance"]
    assert governance["capability"] == "communications.send.external"
    assert governance["decision_ref"], "the artefact names the decision that authorised it"
    # And it names nothing else. What a governed body holds is the decision and the
    # capability; at-most-once is the grant the boundary holds on the channel the answer
    # arrived on, which is not a reference a body could copy onto a file.
    assert set(governance) == {"capability", "decision_ref"}, governance


# -- D: a rejection prevents execution, and is final while the wait runs -------


def test_a_rejection_prevents_execution_and_stays_the_answer(governed, scripted, outbox, reject):
    """A rejection denies the re-ask while the wait it ended is still running.

    Which is why the policy this repository ships gives a person fifteen minutes: the
    finality this case asserts is the wait's, and a deadline short enough to lapse inside a
    test run would make the second resume open a new wait instead.
    """
    run = governed(drafted(scripted, SEND, "Sent."), required_tools=FULL)
    suspended = run.start("Review the corpus, save a report and send it to the partner.")
    assert suspended.verdict == "suspended"

    reject(str(suspended.approval_ref))
    result = run.resume()

    assert result.verdict == "rejected", "a rejection is surfaced, not retried"
    assert outbox() == [], "rejected means nothing left the building"

    again = run.resume()
    assert again.verdict == "rejected"
    assert outbox() == []


# -- E: a denied capability never executes -------------------------------------


def test_a_denied_capability_never_executes(governed, scripted, outbox):
    run = governed(scripted(UPLOAD, "Uploaded."), required_tools=("upload_external",))
    result = run.start("Upload the report to the external destination.")

    assert result.verdict == "denied"
    assert outbox() == [], "a deny opens no wait and runs nothing"


# -- F: the approval is bound to the arguments of the act ----------------------


def test_changing_the_recipient_after_approval_does_not_execute(
    governed, scripted, outbox, approve
):
    """Approve one recipient, resume with another.

    The framework lets a caller merge state on resume, so this is a real capability a
    caller has rather than a contrived one. The recipient is inside the binding
    projection, so the substituted act digests differently, is a DIFFERENT question, and
    the control plane answers it with a wait of its own rather than with the approval
    somebody gave for something else.
    """
    run = governed(drafted(scripted, SEND, "Sent."), required_tools=FULL)
    suspended = run.start("Review the corpus, save a report and send it to the partner.")
    assert suspended.verdict == "suspended"

    approve(str(suspended.approval_ref))

    attacked = run.resume(
        update={
            "pending": {
                "call_id": "substituted",
                "tool": "send_external_email",
                "arguments": {"recipient": "attacker@example.test"},
                "sequence": 1,
            }
        }
    )

    assert attacked.verdict == "suspended", "a substituted act is a new question"
    assert attacked.approval_ref != suspended.approval_ref, "it did not inherit the approval"
    assert outbox() == [], "nothing was sent to the substituted address"


# -- G: evidence names the act and never its content ---------------------------


def test_evidence_names_the_act_and_carries_no_payload(governed, scripted, records, evidence):
    """Two artefacts, and the claim is the same about both.

    The boundary's own records are bounded in memory and carry a sequence, the capability,
    the decision and how many records were lost before them — which is the property
    article 10 offers, and what the trace this suite used to assert never had a source for.
    The durable chain is the control plane's, and it is read here the way the documents
    tell a reader to read it, because a claim about evidence nobody can read back is not a
    claim about evidence.
    """
    secret = "Pricing for hosted small models fell"
    run = governed(drafted(scripted, "Done."), required_tools=READS_AND_WRITES)
    run.start("Review the corpus and save an internal report.")

    made = records()
    assert made, "a governed run records what it did"
    assert [record.sequence for record in made] == list(range(1, len(made) + 1)), (
        "the sequence counts every record the boundary made, so a gap would show as a jump"
    )
    for record in made:
        assert record.capability, "every record names the capability"
        assert record.decision_ref, "every record names the decision"
        assert record.dropped_before == 0, "nothing was lost, and the marker says so"
    rendered = str([record.__dict__ for record in made])
    assert secret not in rendered, "the records are metadata: no payload text"
    assert "partner@example.test" not in rendered, "not even a recipient travels into evidence"

    read = evidence()
    assert read.returncode == 0, (read.returncode, read.stdout, read.stderr)
    # One line per entry — its sequence, its kind, the connection it arrived on and its
    # hash — and a last line saying where a reader would continue.
    lines = [line for line in read.stdout.splitlines() if line.strip()]
    assert lines[-1].startswith("next_from:"), read.stdout
    assert len(lines) > 1, "the chain holds nothing: this run asked nothing of the plane"
    assert secret not in read.stdout, "the chain the control plane kept is metadata too"
    assert "partner@example.test" not in read.stdout
