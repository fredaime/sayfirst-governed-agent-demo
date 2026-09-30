<!-- SPDX-License-Identifier: Apache-2.0 -->
# Recording the sixty-second take

Three terminals and no browser. That is the change this script absorbs: the beat where a
person decides used to be a click in an interface, and it is now a command with a reference
in it — which reads better, because there is no interface a viewer has to take on trust.

Terminal 2 runs the take and terminal 3 answers it; both are on camera. Terminal 1 holds the
control plane and is never shown.

## Before you start

```bash
./scripts/reset-demo.sh               # nothing kept from the last take
./scripts/start-control-plane.sh      # terminal 1 — leave it running, off camera
./scripts/check-demo.sh               # terminal 2 — until it says READY
```

`./scripts/check-demo.sh` prints one line per observation — `[OK]` for something observed
and good, `[--]` for something observed and bad — and a last line, `DEMO READY` or
`NOT READY` with the count, read off those lines and never off configuration. « Not
observed » is never rendered as « OK ». Before a take the model line is the one to look at:
in the default mode it reads

```
  [OK] no model: MODEL_MODE=fixture plays a scripted transcript  set MODEL_MODE=real with MODEL_BASE_URL and MODEL_NAME to watch a model reason
```

and the take plays a scripted transcript: the model's turns are fixed, and every answer to
them is the control plane's, as in any other take. A model is opt-in — in `.env`, or on the
command line, which wins over the file — with `MODEL_MODE=real` and the two settings that
have no default:

```bash
MODEL_MODE=real
MODEL_BASE_URL=http://127.0.0.1:11434/v1
MODEL_NAME=a-tool-calling-model
```

Once those are set, `./scripts/check-demo.sh` reads `[OK] the model is served (...)` and the
whole page is green.

---

## The take, second by second

With a model named, the one stretch whose length the recording does not control is the
model's reasoning. Cut to it: everything before the suspension is as long as the model
takes, and the beats below are what the viewer sees, not a stopwatch on the machine.

**Every terminal block below was pasted from a run of this tree** in the default mode, with
the references, the paths and the account replaced — a reference is a fresh value on every
take, written `REF` for the approval and `DECISION_REF` for a decision, and a path is a fact
about the machine that recorded it. Each `DECISION_REF` stands for that line's own decision
reference: they are different values, one per decision, and the one to hand
`sayfirst trace --decision` is the artefact's `decision_ref`. Every line of the take's own
log carries an `HH:MM:SS` prefix, the time it was printed, and the frames keep it. Nothing
here is typed from memory. The only block that is not a frame is the end card at the close,
which is a caption a recording adds and this repository prints nowhere.

### 0–8 s — the header

Terminal 2, full screen:

```bash
./scripts/run-demo.sh hitl
```

Five lines — the model, the address the decision goes to, the axis it is asked on, the
agent, and the take — then the task the agent is given:

```
A governed agent demonstration
The model proposes. The control plane decides.

  Model          scripted transcript, no model (MODEL_MODE=fixture)
  Control plane  /run/user/1000/sayfirst-demo/daemon.sock
  Scope          local
  Agent          ResearchOps Agent  (user:<your account>)
  Scenario       hitl -- read + internal write execute automatically; the external send waits for a human

Task
  Review the documents in the internal research corpus, summarise the important findings, save an internal report, and send the report to the external partner at partner@example.test.
```

> "An ordinary agent, on an ordinary model. The thing deciding what it may do is a separate
> process, on that socket."

### 8–20 s — the model works, and two answers are automatic

Green `MODEL` lines scroll as the model reads the corpus and writes the report; cyan `EXEC`
lines confirm each act ran. The scripted transcript also declares itself done twice with
work outstanding, and the run corrects it rather than taking its word:

```
00:59:31  MODEL    scripted transcript, no model (MODEL_MODE=fixture) proposes  turn=2
00:59:31  MODEL    tool selected: read_documents  capability=documents.read
00:59:31  EXEC     read_documents executed  documents=customer-feedback.md,market-note.md,project-status.md
00:59:31  MODEL    scripted transcript, no model (MODEL_MODE=fixture) proposes  turn=4
00:59:31  MODEL    model declared completion with work outstanding; corrected  outstanding=write_internal_report,send_external_email
00:59:31  MODEL    scripted transcript, no model (MODEL_MODE=fixture) proposes  turn=6
00:59:31  MODEL    model declared completion with work outstanding; corrected  outstanding=write_internal_report,send_external_email
00:59:31  MODEL    scripted transcript, no model (MODEL_MODE=fixture) proposes  turn=8
00:59:31  MODEL    tool selected: write_internal_report  capability=report.write.internal
00:59:31  EXEC     write_internal_report executed  filename=research-report.md
```

> "It reads the internal corpus and writes a report. Both of those are allowed — the policy
> file says so, and the policy file is four rules a person can read."

### 20–30 s — the moment

```
00:59:31  MODEL    scripted transcript, no model (MODEL_MODE=fixture) proposes  turn=10
00:59:31  MODEL    tool selected: send_external_email  capability=communications.send.external
00:59:31  EVIDENCE the boundary recorded an outcome  sequence=1  capability=documents.read  decision=DECISION_REF  outcome=sha256:dd80e5b8ceca25f0e5e823387afaa5c3fa4b2006cadaba5fb18fab261866e1fd  dropped_before=0
00:59:31  EVIDENCE the boundary recorded an outcome  sequence=2  capability=report.write.internal  decision=DECISION_REF  outcome=sha256:70dcf6c02429181513dde39d32244075403280ea62edfb6fd5c9904ec10822f6  dropped_before=0

  GOVERNANCE: A PERSON MUST ANSWER
  Capability          communications.send.external
  Approval reference  REF
  Graph state         SUSPENDED
  Outbox messages     0
  Side effect status  NOT EXECUTED

  Answer it, in another terminal:
    sayfirst approvals show --approval REF --scope local --socket /run/user/1000/sayfirst-demo/daemon.sock
    sayfirst approvals approve --approval REF --scope local --socket /run/user/1000/sayfirst-demo/daemon.sock
    sayfirst approvals reject --approval REF --scope local --socket /run/user/1000/sayfirst-demo/daemon.sock
  Resuming grants nothing: the node asks again and the control plane answers.
```

Hold on `Outbox messages     0`. It is the whole claim, and it is read off the filesystem
rather than off a status line.

> "Now it tries to send that report outside the organisation. The control plane suspends it.
> The graph is checkpointed and **nothing has been sent**."

### 30–40 s — the person answers, in terminal 3

The run prints the commands that answer it, with the reference already in place. Type the
`approve` one — on camera, in another terminal (the take is waiting in this one):

```bash
sayfirst approvals approve --approval REF --scope local \
  --socket /run/user/1000/sayfirst-demo/daemon.sock --reason "the report was checked; sending is authorised"
```

`--reason` is optional and this take gives one, because a recording is better for it. The
command answers with the wait, resolved — eight lines — the last one names the person: the
approval, its decision, `state: approved`, when it was asked, its deadline, when it was
answered, the reason typed with it, and the person who answered. Answer without `--reason`
and the reason line reads `reason: not stated`.

```
approval: REF
decision: DECISION_REF
state: approved
requested_at: 2026-09-29T00:59:31.599214Z
deadline: 2026-09-29T01:14:31.599214Z
resolved_at: 2026-09-29T00:59:39.305933Z
reason: the report was checked; sending is authorised
person: user:<your account>
```

> "A person — not the model, not the agent — approves this. One person, one act, and nothing
> counting signatures."

### 40–50 s — the graph resumes on its own

```
00:59:39  HUMAN    operator approved the request  answer=approved
00:59:39  EXEC     send_external_email executed  recipient=partner@example.test
00:59:39  MODEL    scripted transcript, no model (MODEL_MODE=fixture) proposes  turn=12
00:59:39  MODEL    model produced a final answer, no tool requested
00:59:39  EVIDENCE the boundary recorded an outcome  sequence=3  capability=communications.send.external  decision=DECISION_REF  outcome=sha256:cf93dec1b23cbcb867ffbe77456cf907d159396094c9ff7e5e6558018fbdfdbb  dropped_before=0

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
  "body": "The corpus reports three findings. Pricing for hosted small models fell sharply this quarter, so the hosted margin assumption no longer holds. Buyers in regulated sectors now ask who authorised an automated action during procurement rather than after it. The partner summary is the critical path for the pilot contract.",
  "executed_at": "2026-09-29T00:59:39.622388Z",
  "governance": {
    "capability": "communications.send.external",
    "decision_ref": "DECISION_REF"
  },
  "recipient": "partner@example.test",
  "subject": "ResearchOps report"
}
```

Five members, in that order, because `tools.py` writes the artefact sorted. The message the
model composed — here, the scripted transcript's — is one of them, which is the half of the
point: the artefact carries the content, and the chain beside it carries none of it.

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

At the suspension, in terminal 3, the `reject` line as printed, with a reason:

```bash
sayfirst approvals reject --approval REF --scope local --socket /run/user/1000/sayfirst-demo/daemon.sock --reason "not this recipient"
```

Terminal 2 then shows the verdict and the empty outbox:

```
01:00:09  HUMAN    operator rejected the request  answer=rejected
01:00:09  POLICY   the external send was rejected by a person  terminal=True

  REJECTED  execution prevented by a human decision
  denied: communications.send.external (approval_rejected, DECISION_REF)

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
