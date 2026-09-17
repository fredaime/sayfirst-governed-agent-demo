<!-- SPDX-License-Identifier: Apache-2.0 -->
# Security properties

What this demonstration proves, how each claim is checked, and — at the end, and more
carefully — what it does **not** prove.

Every claim below is checked by a case that drives the real published boundary against a real
control plane running as its own process. Only the model is scripted, so that a case controls
which acts the agent *proposes*. Nothing about whether an act is *permitted* is scripted, and
the assertion is almost always the same one: how many artefacts are in the outbox.

Run them: `./scripts/gate.sh`.

---

## What is proven

### The side effect is behind the boundary

`governed_node` asks for the decision and enters the wrapped callable only inside the block
an allow opened. No part of a protected act runs first, and no tool function decides anything:
the two that write an artefact are handed the decision that authorised them and record it,
and neither asks for one or can proceed without one. That is why the ordering cannot drift —
there is no path into `send_external_email` that does not pass the boundary.

*Checked by:* `test_an_allowed_capability_executes`,
`test_a_suspension_leaves_the_side_effect_not_executed`.

### A suspension happens before the side effect, not after it

A rule whose answer is `suspend` raises `Suspended` at the boundary, before the block is
entered. The wrapper hands the approval reference to the framework's `interrupt()`: the graph
checkpoints, the caller regains control, and the outbox is empty.

*Checked by:* `test_a_suspension_leaves_the_side_effect_not_executed` — asserts the outbox is
empty while a wait is open.

### Resuming the graph does not itself grant authority

This is the load-bearing one. The caller resumes with a value that carries no approval
reference and no verdict; the framework re-executes the suspended node from the top; the
boundary asks **identically**; and the control plane answers. A resume before anybody has
answered suspends again on the same wait rather than opening a rival one.

*Checked by:* `test_resuming_without_an_answer_suspends_again_on_the_same_wait` — resumes with
no answer and asserts the graph suspends again on the *same* approval reference, with an
empty outbox. If resumption were decided in this process, that case would send the message.

### The control plane remains the authority

This demonstration asks; it never decides. It caches no answer and derives none the control
plane did not give, and the artefact a permitted act writes names the decision that
authorised it — read off the handle the boundary gave the body, never off a value this
process invented.

*Checked by:* `test_one_approval_authorises_exactly_one_execution` — one approval, exactly one
artefact in the outbox, and its governance record asserted exhaustively: two members, the
capability and the decision reference, and nothing else.

### Denied and rejected acts do not execute

A rule whose answer is `deny` is refused at the ask: no wait is opened and nothing runs. A
rejection comes back as a denial carrying the reason for it — it is surfaced, never converted
into a fresh ask, and driving the graph again keeps answering the same way while the wait it
ended is still running.

*Checked by:* `test_a_denied_capability_never_executes`,
`test_a_rejection_prevents_execution_and_stays_the_answer`.

### An act fails closed when the control plane cannot be reached

Every transport failure, timeout and unreadable answer becomes `CouldNotAsk`, which is not an
outcome: the closed set is allow, deny and suspend, and « no answer » is the fourth thing that
is not one of them. The body does not run. This holds for a capability the policy allows too:
a boundary that could not ask has no answer to act on, whatever the answer would have been.

*Checked by:* `tests/integration/test_fail_closed.py`, both cases, with no control plane
running at all.

### An approval is bound to the arguments of the act it approved

`select=` projects every field that constitutes the act — for an external send: the recipient,
the destination domain, the subject and the payload digest. That projection is digested into
the question, and the control plane's approval question is the scope, the principal reference,
the capability and that digest. Change any bound field and it is a **different question**, so
it gets a wait of its own rather than somebody else's approval.

*Checked by:* `test_changing_the_recipient_after_approval_does_not_execute` — approves one
recipient, resumes with state merged to substitute another, and asserts the graph suspends
again on a *different* approval with nothing sent.

### Evidence names the act and never its content

The boundary's outcome records carry a sequence, the capability, the decision reference and
how many records were lost before them. No prompt, completion, message body or recipient
reaches them, and none reaches the durable chain the control plane keeps either.

*Checked by:* `test_evidence_names_the_act_and_carries_no_payload` — asserts on both
artefacts: the records this process made, and the chain read back with
`sayfirst evidence history`, the way the documents tell a reader to read it.

---

## What is NOT proven

Read this half as carefully as the first.

**No formal verification.** Nothing here is machine-checked beyond its tests. These are
executable claims about observed behaviour, not proofs.

**No regulatory conformity claim.** This demonstration shows an authorisation boundary and an
audit trail. Whether a deployment satisfies any legal obligation is a question about that
deployment, its documentation and its operator — not about this repository.

**No comprehensive agent-safety claim.** This governs *tool execution* at the node boundary.
It says nothing about prompt injection into the model, about what the model writes, about
data the model infers, or about an act reached through a path that is not a governed node.

**Durability of the pause is not proven.** The graph checkpoints in memory. The suspension
dies with the agent's process, and the approval the control plane holds outlives it. A durable
checkpointer is a deployment choice this demonstration does not make.

**Exactly-once is not claimed.** One person's act authorises one execution. The artefact is
named after the decision that authorised it, so a body that somehow ran twice under one
decision overwrites rather than duplicates. The grant that makes at-most-once hold is bound to
the channel the answer arrived on, which is why nothing in this repository copies a grant
reference anywhere — there is none on the artefact, and the case that reads it asserts the
absence rather than trusting it.

**A rejection is final for as long as the wait is.** Fifteen minutes here. After that the next
ask opens a new wait, because treating a lapse as a refusal would make an absence into a
decision.

**Evidence is bounded.** The boundary's outcome log holds 1024 records and declares what it
lost: every record carries how many were dropped before it, so a store under pressure never
produces a clean record by losing part of one. The durable chain is the control plane's, read
with `sayfirst evidence history`. A bundle exported while the control plane's current epoch is
still open verifies with coverage `unknown` rather than `complete` — the honest answer, and
not a failure.
