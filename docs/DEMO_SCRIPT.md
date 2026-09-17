<!-- SPDX-License-Identifier: Apache-2.0 -->
# Recording the sixty-second take

Two terminals and no browser. That is the change this script absorbs: the beat where a
person decides used to be a click in an interface, and it is now a command with a reference
in it — which reads better, because there is no interface a viewer has to take on trust.

Terminal 2 is the only one on camera. Terminal 1 holds the control plane and is never shown.

## Before you start

```bash
./scripts/reset-demo.sh               # nothing kept from the last take
./scripts/start-control-plane.sh      # terminal 1 — leave it running, off camera
./scripts/check-demo.sh               # terminal 2 — until it says READY
```

`./scripts/check-demo.sh` reports three kinds of line and not two: `[OK]` for something
observed and good, `[--]` for something observed and bad, and `[ ?]` for a facility that is
not configured at all. « Not observed » is never rendered as « OK ». Before a take the model
line is the one to look at: with no model named it reads

```
  [ ?] no model is configured (MODEL_MODE=fixture)  a take needs MODEL_MODE=real with MODEL_BASE_URL and MODEL_NAME
```

and the run ends in a refusal saying the same thing. That is the expected first outcome on a
fresh clone, not a fault: the default mode needs no model, and a take opts in — in `.env`, or
on the command line, which wins over the file — with `MODEL_MODE=real` and the two settings
that have no default:

```bash
MODEL_MODE=real
MODEL_BASE_URL=http://127.0.0.1:11434/v1
MODEL_NAME=a-tool-calling-model
```

Once those are set, `./scripts/check-demo.sh` reads `[OK] the model is served (...)` and the
whole page is green.

---

## The take, second by second

The one stretch whose length the recording does not control is the model's reasoning. Cut to
it: everything before the suspension is as long as the model takes, and the beats below are
what the viewer sees, not a stopwatch on the machine.

**Every terminal block below was pasted from a run of this tree**, with the references and the
paths replaced — a reference is a fresh value on every take, and a path is a fact about the
machine that recorded it. Nothing here is typed from memory. The only block that is not a
frame is the end card at the close, which is a caption a recording adds and this repository
prints nowhere.

### 0–8 s — the header

Terminal 2, full screen:

```bash
./scripts/run-demo.sh hitl
```

Four facts and no fifth — the model, the address the decision goes to, the axis it is asked
on, and the agent:

```
A governed agent demonstration
The model proposes. The control plane decides.

  Model          <the model you named>
  Control plane  /run/user/1000/sayfirst-demo/daemon.sock
  Scope          local
  Agent          ResearchOps Agent  (user:<your account>)
  Scenario       hitl -- read + internal write execute automatically; the external send waits for a human
```

> "An ordinary agent, on an ordinary model. The thing deciding what it may do is a separate
> process, on that socket."

### 8–20 s — the model works, and two answers are automatic

Green `MODEL` lines scroll as the model reads the corpus and writes the report; cyan `EXEC`
lines confirm each act ran.

```
MODEL    tool selected: read_documents  capability=documents.read
EXEC     read_documents executed  documents=customer-feedback.md,market-note.md,project-status.md
MODEL    tool selected: write_internal_report  capability=report.write.internal
EXEC     write_internal_report executed  filename=research-report.md
```

> "It reads the internal corpus and writes a report. Both of those are allowed — the policy
> file says so, and the policy file is four rules a person can read."

### 20–30 s — the moment

```
MODEL    tool selected: send_external_email  capability=communications.send.external

  GOVERNANCE: A PERSON MUST ANSWER
  Capability          communications.send.external
  Approval reference  <the reference the control plane minted>
  Graph state         SUSPENDED
  Outbox messages     0
  Side effect status  NOT EXECUTED
```

Hold on `Outbox messages     0`. It is the whole claim, and it is read off the filesystem
rather than off a status line.

> "Now it tries to send that report outside the organisation. The control plane suspends it.
> The graph is checkpointed and **nothing has been sent**."

### 30–40 s — the person answers, in terminal 2

The run prints the command that answers it, with the reference already in place. Type it —
on camera, in the same terminal:

```bash
sayfirst approvals approve --approval REF --scope local \
  --socket /run/user/1000/sayfirst-demo/daemon.sock --reason "the report was checked; sending is authorised"
```

`--reason` is optional and this take gives one, because a recording is better for it. The
command answers with the wait, resolved — seven lines: the approval, its decision,
`state: approved`, when it was asked, its deadline, when it was answered, and the reason typed
with it. Answer without `--reason` and that last line reads `reason: not stated`.

> "A person — not the model, not the agent — approves this. One person, one act, and nothing
> counting signatures."

### 40–50 s — the graph resumes on its own

```
HUMAN    operator approved the request  answer=approved
EXEC     send_external_email executed  recipient=partner@example.test
EVIDENCE the boundary recorded an outcome  sequence=3  capability=communications.send.external  ...

  EXECUTED  the run completed under authority

  Outbox artefacts: 1   (<your checkout>/runtime/outbox)
```

> "The agent resumes — and resuming grants nothing. The node asks the same question again,
> the control plane answers the wait it already had, and exactly one message appears."

### 50–60 s — the evidence, side by side

```bash
sayfirst evidence history --from 1 --scope local --socket /run/user/1000/sayfirst-demo/daemon.sock
cat runtime/outbox/*.json
```

The chain is one line per entry — its sequence, its kind, the connection it arrived on and
its hash — and a last line saying where a reader would continue. The artefact is the message
the agent wrote, with a governance record of exactly two members:

```json
{
  "body": "The important findings from the documents I read are that insurance agents cannot deploy without human approval, and the transparency obligations for general-purpose models have entered application in the EU.",
  "executed_at": "2026-09-16T20:49:31.393884Z",
  "governance": {
    "capability": "communications.send.external",
    "decision_ref": "<the decision the control plane recorded>"
  },
  "recipient": "partner@example.test",
  "subject": "ResearchOps report"
}
```

Five members, in that order, because `tools.py` writes the artefact sorted. The message the
model composed is one of them — which is the half of the point: the artefact carries the
content, and the chain beside it carries none of it.

> "The artefact names the decision that authorised it. The chain names the act and never its
> content — no recipient, no subject, no text."

End card — a caption for the recording, not something this repository prints:

```
THE MODEL PROPOSES.
THE CONTROL PLANE DECIDES.
```

---

## The second clip: a rejection

The same run, answered the other way, and arguably the stronger proof. It needs twenty-five
seconds.

```bash
./scripts/reset-demo.sh
./scripts/start-control-plane.sh      # terminal 1 — a reset removed the last one
./scripts/run-demo.sh hitl
```

At the suspension, in terminal 2:

```bash
sayfirst approvals reject --approval REF --scope local --socket /run/user/1000/sayfirst-demo/daemon.sock --reason "not this recipient"
```

Terminal 2 then shows the verdict and the empty outbox:

```
HUMAN    operator rejected the request  answer=rejected
POLICY   the external send was rejected by a person  terminal=True

  REJECTED  execution prevented by a human decision
  denied: communications.send.external (approval_rejected, <the decision the control plane recorded>)

  Outbox artefacts: 0   (<your checkout>/runtime/outbox)
```

The dim line under the verdict is the answer the control plane gave, printed as the published
boundary spells it: a rejection comes back as a `deny` carrying the reason for it, and the run
prints that sentence rather than a verdict of its own invention.

> "Rejected. The agent stops safely, and the outbox is still empty. That answer stands for as
> long as the wait does — fifteen minutes, in the policy this repository ships."

A reset between takes is not optional and is not the same as clearing the outbox: the daemon
keeps its decisions and its chain in files under its run directory and reopens them when it
starts, so take two would show take one's chain under the very command take one ends by
printing. `./scripts/reset-demo.sh` stops the daemon and removes that directory whole.

## What the operator decides

Two things about a recording are not this repository's to settle, and they are named here so
nobody reads the absence of a recording as a missing file.

* **Whether the approval beat is a terminal command on camera.** This script says it is, and
  the reason is that it shows the authority being exercised with no interface in between. An
  operator who would rather film an interface is filming something this repository does not
  ship and does not document.
* **Whether the earlier recordings are re-shot or retired.** Every one of them frames a
  browser and a product this demonstration no longer speaks to, so none of them can be
  trimmed into agreement with the tree. Re-shooting is one act; retiring them is another; the
  one thing that is not available is leaving them up as though they still described this.
