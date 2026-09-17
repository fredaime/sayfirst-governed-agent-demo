<!-- SPDX-License-Identifier: Apache-2.0 -->
# Security

This is a **demonstration**, not a product. It shows what the `sayfirst` control plane does
by putting a real boundary in front of a real agent and letting a real daemon decide. It
implements no governance of its own: every decision in it is the control plane's, and every
claim it appears to make is a claim about what the published contract and the published
boundary already do.

## What this software is, and is not

It is an ordinary agent application plus one module that asks before it acts. It decides
nothing, it caches no decision, and it derives no answer the control plane did not give.

It does **not** confine anything. The control plane it speaks to is a governance and
observability layer, not a confinement mechanism: a program that does not call the boundary
is not governed, and nothing here changes that. Pair the system with operating-system
sandboxing for code you do not trust.

## There is nothing here to steal

No token, no session, no key, no credential store, and no address to point at a network.
Identity is the operating system's: the control plane listens on a Unix domain socket and
only there, and it learns who is calling from the peer credential the kernel reports when
the connection is accepted. This program presents nothing.

What replaces a credential is the socket's permissions and the connection's verification.
The client this demonstration composes verifies which account is listening at the address
before it writes a byte, and a connection it could not verify is reported as unverified
rather than quietly trusted.

## Three outcomes, and a fourth thing that is not one

The control plane answers **allow**, **deny** or **suspend**, and that set is closed. When
it cannot be reached at all, that is **not** a fourth outcome: the act does not run, and the
run ends as « could not ask » with an exit code of its own. A caller that branched on a
single non-zero exit would read an unreachable control plane as a refusal; the codes exist
so that it cannot.

## What this demonstration does not prove

Read this as carefully as the rest.

- **Nothing is formally verified.** These are executable claims about observed behaviour.
- **No regulatory conformity is claimed.** Whether a deployment satisfies a legal
  obligation is a question about that deployment, its documentation and its operator.
- **This is not a comprehensive agent-safety claim.** It governs tool execution at a node
  boundary. It says nothing about prompt injection, about what the model writes, about what
  the model infers, or about an act reached by a path that is not a governed node.
- **Exactly-once is not claimed.** What is claimed and checked: one person's approval
  authorises one execution, and the artefact this demonstration writes is named after the
  decision that authorised it, so a body that somehow ran twice under one decision
  overwrites rather than duplicates.
- **The pause is not durable.** The graph checkpoints in memory, so a suspension dies with
  the process. The approval does not: it is the control plane's, and a graph restarted and
  resumed asks the same question again.

## Publication

This repository was created **fresh**, at the tag: its first commit is the reviewed tree, and
no history, no branch, no issue and no pull request came with it. What that history held is
not this repository's to show, and a repository created fresh cannot show it by accident.

GitHub's **private vulnerability reporting** is enabled on it, set in the same act, so that
this file names a channel that exists from the first public minute; the hosting platform
permits that setting on a public repository only. Both acts are lines of
`docs/publication-checklist.md`.

## Reporting a vulnerability

Do not open a public issue. Use GitHub's **private vulnerability reporting** on this
repository — Security → Report a vulnerability — which only its administrators and security
managers can read.

That is the channel and it is the only one. There is no address in this file: an address
published here is read by whoever harvests it, and a report sent to one arrives outside the
process below rather than inside it.

We aim to acknowledge within seven days. Coordinated disclosure applies, with a ninety-day
default that can be shortened by agreement or extended when a fix needs it. Reporters are
credited unless they prefer not to be.

If a report concerns the control plane or the product command-line interface rather than
this demonstration, it belongs in that repository's channel; if you are unsure which, open
it here and we will route it rather than ask you to judge.
