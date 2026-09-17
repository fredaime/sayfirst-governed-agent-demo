<!-- SPDX-License-Identifier: Apache-2.0 -->
# A governed agent

**The model proposes. The control plane decides.**

An ordinary agent reasons and asks to act; `sayfirst` decides, independently, whether each
act may execute. The model is never the security boundary, and swapping it changes nothing
about the governance — which is the claim this demonstration exists to make and the reason
it is worth running rather than reading about.

```
┌───────────────────┐
│ A model           │   reasons, chooses a tool
└─────────┬─────────┘
          │ proposes a tool call
          ▼
┌───────────────────┐
│ The agent         │   an ordinary graph of nodes
└─────────┬─────────┘
          │ the execution boundary  ← governed_node(...)
          ▼
┌───────────────────┐
│ sayfirst          │   a decision BEFORE the side effect
└─────────┬─────────┘
          │
     ┌────┼─────┐
     ▼    ▼     ▼
   ALLOW SUSPEND DENY
          │ the graph checkpoints, nothing has executed
          ▼
┌───────────────────┐
│ A person answers  │   out of band, with one command
└─────────┬─────────┘
          │ the next ask allows, once
          ▼
      the side effect, and evidence
```

Reasoning is not authority. The model never decides whether it may act; it cannot. The
decision is asked for by the runtime, answered by a separate process, and the tool body is
not entered until that answer is an allow.

---

## The sixty-second demonstration

The agent is asked to review an internal research corpus, write a report, and send it to an
external partner. Four capabilities, four answers — set in **policy**, in a file, not in the
agent:

| Capability | Answer | What happens |
|---|---|---|
| `documents.read` | `allow` | executes |
| `report.write.internal` | `allow` | executes |
| `communications.send.external` | `suspend` | **the graph suspends, nothing is sent** |
| `data.upload.external` | `deny` | never executes |

That table is `demo-policy.toml`, in full, and editing it is how you change what the agent
is allowed to do.

The moment that matters: the model decides to send the report, and the run stops with
`Outbox messages: 0`. A person approves with one command. The graph resumes — and
**resuming grants nothing**: the node asks again, the control plane answers the wait it
already had, and exactly one message appears.

```
  GOVERNANCE: A PERSON MUST ANSWER
  Capability          communications.send.external
  Approval reference  <the reference the control plane minted>
  Graph state         SUSPENDED
  Outbox messages     0
  Side effect status  NOT EXECUTED
```

---

## Quickstart

```bash
./scripts/bootstrap.sh                # the environment, a configuration file, directories
./scripts/start-control-plane.sh      # terminal 1 — the control plane, on a local socket
./scripts/check-demo.sh               # terminal 2 — every precondition, observed
./scripts/run-demo.sh hitl            # terminal 2 — run the agent
```

On a fresh clone the fourth command refuses, and that is the expected first outcome rather
than a fault. It refuses for one of two reasons and says which: on a clone beside no checkout
of the two open repositories, the distributions this demonstration is built on are not
installed, and the run names the missing one and the two ways to obtain it; on an environment
that holds them, no model is named yet, and the run ends saying which two settings to set —
`docs/DEMO_SCRIPT.md` shows that line and what to put in `.env`.

Those distributions are published on **no index yet**, which is the whole of why a checkout
is named here rather than an install. Both products are public, so the checkout is two
commands, at the tag of the release this demonstration shows:

```bash
git clone --branch v0.2.0 https://github.com/fredaime/sayfirst-control-plane
git clone --branch v0.2.0 https://github.com/fredaime/sayfirst-cli
SAYFIRST_CONTRACT_SOURCE=../sayfirst-control-plane SAYFIRST_CONTRACT_REF=v0.2.0 \
SAYFIRST_CLIENT_SOURCE=../sayfirst-cli SAYFIRST_CLIENT_REF=v0.2.0 \
  ./scripts/bootstrap.sh
```

The gate reads an archive of the ref it is given rather than the files a checkout has out,
so naming the tag is what makes a run reproducible. When the distributions do reach an
index, installing the pins replaces all of this.

The shell scripts are the front door and the only readers of `.env`: nothing inside the
package reads a file, so the installed console script reads the environment alone, by
design, and a name already set on the command line always wins over the file.

When the run suspends it prints the command that answers it, with the reference already in
place:

```bash
sayfirst approvals show    --approval REF --scope local --socket /run/user/1000/sayfirst-demo/daemon.sock
sayfirst approvals approve --approval REF --scope local --socket /run/user/1000/sayfirst-demo/daemon.sock
```

One person's act, and nothing that counts signatures. A rejection is final for as long as
the wait is open — fifteen minutes, in the policy this repository ships
(`review_deadline_seconds`) — and after that the next ask opens a new wait rather than
treating a lapsed one as a refusal.

Scenarios: `hitl` (approve or reject), `allow` (nothing suspends), `deny` (refused
outright), `pending` (stops at the suspension, for the first half of a recording).
`./scripts/reset-demo.sh` clears a take.

**A model is opt-in.** The tests need none. To watch the agent reason, set `MODEL_MODE=real`
with `MODEL_BASE_URL` and `MODEL_NAME` pointing at any server that speaks the
OpenAI-compatible API and serves a tool-calling model. Asking for a real model without
naming one is refused, and the refusal says which two settings it wanted.

`./scripts/bootstrap.sh` installs no model of its own. It offers one pull and only one: when
`MODEL_NAME` is set and `ollama` is on your path it pulls that name and reports whether the
model advertises tool calling. With `MODEL_NAME` unset, or the tool absent, it pulls nothing
and says so.

---

## Architecture

Three things are deliberately kept apart, and this demonstration shows all three:

* **Observability** — what did the agent do? The evidence chain, metadata only.
* **Governance** — was it permitted? The policy, evaluated per capability.
* **Authority** — who had the power to permit it? The control plane, and for a suspended
  act a person. Never the model, and never the agent's own process.

The interception point is the **node registration**. `governed_node` wraps the callable a
node is registered with, so the decision lands after the framework has committed to the act
and before the body that causes it:

```python
builder.add_node(
    NODE_SEND_EXTERNAL,
    governed_node(
        CAP_COMMUNICATIONS_SEND_EXTERNAL, nodes[NODE_SEND_EXTERNAL], select=bind_send_external
    ),
)
```

The boundary is composed by hand, in one module, from two published distributions:
`sayfirst-contract` for the socket client and `sayfirst-boundary` for the boundary itself.
Using it by hand is a supported way to use it, and it is the only way to govern a node of a
graph: the convenience packs the product command-line interface ships wrap library calls — a
database connection, an outbound request, a subprocess — and none of them can name a node.

Full detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## What the commands here are for

This demonstration runs the agent and starts the control plane. The product command-line
interface is what a person uses on the same machine, and three of its commands apply
directly:

```bash
sayfirst approvals show|approve|reject --approval REF --scope local --socket PATH
sayfirst evidence history --from 1 --scope local --socket PATH
sayfirst packs list
```

The first answers a suspended act: one person, one act. The second reads the chain the control
plane kept — one line per entry, and a last line saying where a reader would continue. The third
prints the convenience packs the command ships.

`sayfirst instrument run` is the other way to govern a program: it puts the boundary in
front of somebody else's program, with no change to that program's code, for effects that
are library calls. This demonstration does not use it, because what it governs is a node of
a graph and no pack can name one — the boundary is composed by hand here instead.

---

## Security properties

What this demonstration **does** prove, and how to check each one, is in
[`docs/SECURITY_PROPERTIES.md`](docs/SECURITY_PROPERTIES.md) — together with what it does
**not** prove, which is the more important half.

```
The external side effect is behind the boundary.
A suspension happens before the side effect, not after it.
Resuming the graph does not itself grant authority.
The control plane remains the authority.
Denied and rejected acts do not execute.
An act fails closed when the control plane cannot be reached.
An approval is bound to the arguments of the act it approved.
Evidence names the act and never its content.
```

---

## The model

Any endpoint that speaks the OpenAI-compatible API and serves a tool-calling model will do;
they differ only in the address, the model name and the key. What was measured about model
choice — including why a small instruct model needs the validation loop this agent has —
is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

This project is independent. It is not affiliated with, sponsored by, or endorsed by any
model vendor, and no vendor's model is required: a model is a configuration line here, which
is the architectural point.

---

## Tests

```bash
./scripts/gate.sh          # format, lint, every tier, against a control plane it starts
```

It has three outcomes. `0` is the full gate. **`75` is a reduced run and not a pass**: it
happens on a machine that cannot build the open distributions, it names and counts every
check it did not run, and it proves nothing about this demonstration against a control
plane. Anything else is a failure.

The model is faked in the tests. **The governance is not**: every acceptance case drives the
real boundary against a real control plane in its own process, answers a suspended act with
the command a person types, and asserts on the filesystem — how many artefacts are in the
outbox — rather than on telemetry.

---

## What is open

Everything in this repository was written here; nothing arrived by copy from anywhere.
[`docs/OPEN_SOURCE_READINESS.md`](docs/OPEN_SOURCE_READINESS.md) records what this depends
on, at which pin, what it never depends on, and what must not be published.

## Licence

Apache-2.0 for this repository's own files; see [LICENSE](LICENSE) and [NOTICE](NOTICE). The
invented documents under `demo_data/` are `Apache-2.0 OR MIT-0`, so a reader may lift them
into a demonstration of their own. A model you point this at is covered by its own terms.
