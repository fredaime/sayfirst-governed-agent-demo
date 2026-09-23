<!-- SPDX-License-Identifier: Apache-2.0 -->
# Open-source readiness

## Status

**Publishable.** Two of the three things that used to block this are published distributions
that this repository now pins, and the third — the authority itself — is a process a reader
starts with a script in this repository, from a policy file they can read and edit. Nothing
is left that a reader cannot obtain.

What remains is an act rather than a question, and `docs/publication-checklist.md` is the
page that names it.

## What this depends on, and at which pin

| Distribution | Why | Where it is declared |
|---|---|---|
| `sayfirst-contract==0.3.0` | the socket client the boundary speaks through | `project.dependencies` |
| `sayfirst-boundary==0.3.0` | the boundary itself | `project.dependencies` |
| `langgraph` | the agent framework this demonstration governs a node of | `project.dependencies` |
| `httpx` | the OpenAI-compatible transport, and the health check's model probe | `project.dependencies` |
| `sayfirst-control-plane==0.3.0` | **development and test, never imported**: `./scripts/start-control-plane.sh` runs its daemon as a separate process, and the acceptance tier starts one of its own | a dependency group of its own |

One number, said everywhere: this demonstration shows one release and pins that release, so
the version is not a range.

**Where they come from today.** None of the three is on an index yet, so the way to hold one
is a checkout of the product that builds it, at the tag of that release — and both products
are public repositories a reader can open:

| What | Public repository | Tag |
|---|---|---|
| the contract, the boundary and the server | [`fredaime/sayfirst-control-plane`](https://github.com/fredaime/sayfirst-control-plane) | `v0.3.0` |
| the command a person answers with | [`fredaime/sayfirst-cli`](https://github.com/fredaime/sayfirst-cli) | `v0.3.0` |

`scripts/gate.sh` builds the wheels from an archive of that tag rather than from whatever a
checkout has out, and `.github/workflows/ci.yml` checks both repositories out at it with no
credential. That is what publication changed here: the two addresses are public, so the
workflow spells them instead of reading them out of a setting. `README.md` carries the two
commands a reader runs.

**Not a dependency at all:** the product command-line interface. It is a command a person
installs as a tool and types — to answer a suspended act and to read the chain — and nothing
here imports it or declares it.

## What it never depends on, and why that is mechanical

The server is **installed and never imported** — a program this repository's start script runs
during development and the acceptance tier starts for itself, reached as a process and an
address rather than as a module. The command is never imported either, and is a dependency of
nothing. Neither is a promise: `tests/test_direction_of_dependency.py` reads the project file
and every module under `src/` and holds both — the runtime pins exactly as listed above, the
server's distribution in a group of its own and nowhere else, no requirement beginning with
the command's name anywhere,
no path-resolved source that would make a published distribution depend on somebody's working
tree, and neither import name reachable from any module this distribution ships. It plants an
import that would break the rule and checks its own reader sees it.

## Provenance

> **No file in this repository arrived by copy.** The table is empty, and that is the answer
> rather than an omission.
>
> | File | Copyright holder | Licence | What changed on the way |
> |---|---|---|---|
> | *(no file in this repository arrived by copy)* | — | — | — |
>
> The module that composes the boundary is the one this had to be true of. An earlier version
> of it was generated from a template held elsewhere and carried that template's documentation
> word for word, and publishing it would have published that text. It was **rewritten** against
> the published surface instead — which nine of its twenty-five imports forced anyway, having
> no counterpart there — so nothing in this repository reproduces anything from anywhere, and
> the honest number of copied files is zero. A module authored fresh against a published API
> is not a copy of anything.

## What must not be published

* **`runtime/`** — the outbox, the reports and the event dumps a take produces. It holds
  nothing else: there is no export of any other repository under it, and the daemon's own run
  directory is not in the checkout at all, since the start script puts the socket, the
  rendered policy and the evidence under a run directory outside it.
* **`.env`** — a reader's own configuration. `.env.example` carries no secret and is tracked.

Both are in `.gitignore`. `./scripts/reset-demo.sh` removes what a take left under `runtime/`
and the daemon's run directory whole — its decisions, its approvals, its evidence, its socket
and its configuration — so that a new take keeps nothing. It never touches `.env`, which is
the reader's own.

`demo_data/` is invented. It contains no client, customer or personal data, which is why it
carries the permissive licence alternative — `Apache-2.0 OR MIT-0` — so a reader may lift
those documents into a demonstration of their own.
