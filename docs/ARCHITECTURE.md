<!-- SPDX-License-Identifier: Apache-2.0 -->
# Architecture

## The four boundaries, kept apart

| Question | Answered by | Where |
|---|---|---|
| What did the agent do? | **Observability** | the evidence chain the control plane keeps, metadata only |
| Was it permitted? | **Governance** | the policy, one rule per capability, in `demo-policy.toml` |
| Who had the power to permit it? | **Authority** | the control plane's daemon, and for a suspended act a person |
| Can we prove the decision? | **Evidence** | the decision record, the approval, the boundary's outcome records, and the chain |

This demonstration never collapses these. A line printed on a terminal is not a decision, and
the agent never asks the thing it is printing to for permission: the authority is a separate
process, reached over a socket whose peer this program verified before it wrote a byte.

## The request path

Read off `src/sayfirst_governed_agent_demo/boundary_setup.py`, which is the whole of the
integration:

```
reason node                 the model chooses a tool
  │  state["pending"] = {tool, arguments, sequence}
  ▼
route()                     exactly one governed node per turn
  │
  ▼
governed_node(capability, fn, select=bind_*)
  │  1. binding_arguments(state, select)   -> the act's arguments, as a mapping
  │  2. boundary.request(capability, arguments, scope="local")
  │        └─ the published client, over a socket whose peer it verified
  │              allow    -> the body runs, at most once, inside the block
  │              suspend  -> Suspended -> interrupt(): the graph checkpoints
  │              deny     -> Denied, carrying the reason the plane gave
  │              refused  -> AskRefused: the question was rejected
  │              no answer-> CouldNotAsk: never permission
  │  3. ONLY inside the block: fn(state) — the side effect
  │  4. grant.record_outcome(digest) — metadata, into a bounded log
  ▼
tool node body              writes the file / the outbox artefact
```

`Denied`, `Suspended`, `AskRefused` and `CouldNotAsk` are every type
`sayfirst_boundary.errors` publishes under its base `BoundaryError`, and an allow is not among
them because an allow is the body running. There is no fifth: an outcome this document named
and the library did not would be a claim a reader could not check.

`binding_arguments` refuses, before any question is put, a value the wire cannot carry. The
control plane pins the arguments digest as a grant condition and compares it exactly, so a
value digested through a printed representation would not reproduce, and the refusal is
better placed where the binding was written than after somebody has approved it.

## Why the node registration is the interception point

Earlier is not a committed act: a model response or a routing condition is a proposal, and
refusing there refuses a thought rather than an act. Later is too late: inside the tool body
a partial effect may already have happened. The node registration is where the framework has
committed and the effect has not started.

One node carries one capability key. A prebuilt tool node would execute whichever tool the
model picked under a single key, which cannot express four different answers — so each tool
gets its own node, and the router fans to exactly one per turn, which is what keeps two
governed nodes from suspending at once.

## How a resume finds its own pending wait

The caller carries nothing. On resume the framework re-executes the suspended node from the
top, so the wrapper asks again with the same capability, the same scope and the same
arguments digest, and the control plane recognises the question it already has a wait for.

What makes a re-ask the same ask is **the control plane's rule and not this repository's
derivation**: its approval question is the scope, the principal reference, the capability and
the arguments digest, and every member of it must be present. Nothing in this repository
computes a key of its own, and nothing in it can widen or narrow that identity.

The consequence is the one that matters: **change a bound argument and it is a different
question**, so a substituted act gets a wait of its own rather than somebody else's approval.
That is why the substitution attack fails, and it is asserted against a real daemon rather
than argued here.

`sequence` is part of every binding projection, set by the reasoning node and never by the
tool node. Two identical acts in one run are therefore two acts — reading the same document
twice is two reads — while a resumed node re-reads the same value and asks identically.

## Where the grant lives, and what this demonstration does not claim

The grant is bound to the channel the answer arrived on. The graph checkpoints in memory and
resumes in this process, and nothing copies a grant reference onto an artefact, into a file
or across a process boundary — there is no reference a body could copy, which is the shape
that makes at-most-once hold rather than a convention anybody has to keep.

So the durable thing is the approval, not the connection. A graph resumed anywhere asks the
same question again and the control plane answers it; a graph resumed nowhere leaves an
approval the control plane still holds. **No cross-process resume is claimed here**: the
checkpointer this demonstration uses is in memory, and a suspension dies with the process
that opened it.

## The model layer

One transport, deliberately: every server that speaks the OpenAI-compatible API differs only
in `MODEL_BASE_URL`, `MODEL_NAME` and `MODEL_API_KEY`, so one client covers all of them and a
second implementation would be dead weight.

`fixture` is the default mode and needs no model at all — which is why a clone of this
repository runs its whole gate with nothing installed to reason with. `MODEL_MODE=real` never
falls back to the transcript: an endpoint that cannot be reached is a loud startup failure,
because a demonstration that degraded quietly would be showing governance over a model that
was never in the loop. Neither the address nor the model name has a default, and a `real` run
naming neither refuses at startup and says which two settings it wanted.

### What was measured about model choice

Measured with a small quantised instruct model served locally, because that is the hardest
case and the one a reader is most likely to have. Three limits shaped the tool surface, and
all three are properties of small instruct models rather than of any one of them:

1. **Short arguments are emitted reliably and long ones not at all.** Asked for a call
   carrying a long `body`, the model returns an empty object; asked for a call carrying one
   short argument, it returns it correctly. So the tools take one short argument each, and
   the report text travels as the model's own prose in graph state rather than as a tool
   argument. What is governed is unchanged: the binding projects the digest of exactly the
   text that will be written.
2. **Arguments are sometimes double-wrapped**, as `{"arguments": {...}, "type": "..."}`.
   `model._unwrap` normalises that transport shape conservatively — only when the outer
   object carries nothing but envelope keys — and never supplies, renames or defaults a
   value.
3. **Task phrasing matters disproportionately.** Measured with everything else held constant
   — same system prompt, same tools, same authority: the full task ("review the corpus,
   summarise, save an internal report, and send the report to the external partner") reliably
   produces tool calls, while a shortened variant ending at "and save an internal report"
   produced zero tool calls in five consecutive runs, and no amount of escalating correction
   recovered it. This is why the demonstration always issues the full task: the scenario name
   is the authority's answer, not the agent's instruction.

### The validation loop

Small instruct models declare completion before doing the work. The reasoning node refuses a
premature "I am done" when a required act has never been *attempted*, and says which step is
outstanding. It never supplies an argument: the recipient, the destination and the report
text come from the model or from the task. `MAX_NUDGES` bounds it at six, so a model that
ignores every correction finishes and the run reports what it actually did.

## Repository layout

```
src/sayfirst_governed_agent_demo/
  settings.py         every environment-derived value, resolved once; the four capability keys
  model.py            the OpenAI-compatible client and the scripted stand-in
  tools.py            the four acts and their schemas; the two external ones stamp a decision
  state.py            the binding projections, resolve_act(), and the members they read
  graph.py            the graph and the state it runs (GraphState); the four registrations
  agent.py            the run loop, including the caller's half of a resume
  app.py              the command-line entry point and the screen-recordable output
  healthcheck.py      what ./scripts/check-demo.sh reports
  governance_stamp.py what an outbox artefact records about its authorisation
  demo_events.py      the event stream, OBSERVED lines and DERIVED lines kept apart
  boundary_setup.py   the boundary, composed by hand from the two published distributions
demo-policy.toml      the whole of what this demonstration's control plane decides
scripts/              bootstrap, start, check, run, reset — and the gate
```

`resolve_act()` is the one function both the binding projection and the node body call. That
identity is deliberate: a binding computed from proposed arguments while the body ran on
resolved ones would let an approved act execute with something else.
