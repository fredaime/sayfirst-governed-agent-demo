<!-- SPDX-License-Identifier: Apache-2.0 -->
# Publication checklist

One page, for the person who publishes this demonstration. Nothing here is done by a workflow:
each line is an act somebody takes. There is no release job in this repository and no
distribution for one to publish — this demonstration is cloned and run — so its publication is
the repository itself, at a tag, and the lines below are what that act needs.

## Before the act

- **Confirm or rename the public repository.** Every address this distribution publishes begins
  with `https://github.com/fredaime/sayfirst-governed-agent-demo`, and
  `tests/test_pointers_survive_publication.py` holds that name in three project URLs. A
  different name is a change to both, in one commit, before the act.
- **Set the sign-off check as a required status** in the public repository's branch protection.
  Contributions arrive under the Developer Certificate of Origin, `CONTRIBUTING.md` says so and
  `.github/workflows/ci.yml` runs `scripts/check_developer_certificate_of_origin.py` on every
  pull request — but whether a failing check blocks a merge is a branch-protection setting of
  the public repository, which no check in this tree can read. Two acts in one order: the
  workflow runs the check, and the setting makes a failure block. It is a line here because an
  act held by review with no line is an act nobody is reminded to perform.
- **Read what the tree pins, and decide nothing.** Two published distributions at one version,
  `sayfirst-contract==0.2.0` and `sayfirst-boundary==0.2.0`, plus `langgraph` and `httpx`; the
  control plane's own distribution at the same version, in a group of its own, because the
  start script and the acceptance suite each run its daemon as a separate process and nothing
  this distribution ships imports it; and the product command-line interface, which is a
  command a person types and a dependency of nothing. One number, said everywhere, and it is
  the number of the release this demonstration shows.

## The two things publication changes

During development neither the contract nor the command exists on any index, so the gate is
told where a checkout of each is — `SAYFIRST_CONTRACT_SOURCE` with `SAYFIRST_CONTRACT_REF`, and
`SAYFIRST_CLIENT_SOURCE` with `SAYFIRST_CLIENT_REF` — and it builds the wheels from an archive
of that named ref. Neither variable has a default path, deliberately: a default would name a
repository this one does not publish, inside a file it does publish. Publication retires both
arrangements, and until it does, two published files describe a world that is one act away:

1. **the gate's sources become the index.** `scripts/gate.sh` builds four wheels from a checkout
   and installs them with no index; afterwards it installs the pins from the index and the
   `materialise` step goes with them. The reduced mode goes too: the distributions are no longer
   absent anywhere, so a reduced run has nothing to report and `tests/test_gate_modes.py`, which
   requires three outcomes, is what has to be rewritten with it;
2. **the workflow's two checkouts become an install.** `.github/workflows/ci.yml` reads the two
   repositories out of repository variables and reaches them with a credential, because their
   names are not this repository's to publish and their content is not public yet. On
   publication day both checkouts become an ordinary install, the credential and the two
   variables are retired, and the reduced job — which exists for a fork that has neither — is
   retired with them.

Read those two files again after the edits: each says, in its own comments, that a fork gets a
reduced gate because the distributions are published nowhere. That sentence stops being true on
the day this list is worked through, and a published file claiming it afterwards is the defect
this line exists to prevent.

## The order

**After the two products, and in this order for a reason.** This demonstration pins them at a
version; a repository published before the distributions it pins is a repository a reader cannot
install from, whatever its documents say. So: the control plane, then the command, then this.

The repository is created **fresh**, at the tag, with private vulnerability reporting enabled in
the same act — `SECURITY.md` names that channel and the hosting platform permits the setting on
a public repository only — and the history is not carried. One consequence worth naming: the
private history holds a commit that certifies no sign-off, and a fresh repository disposes of it
rather than carrying it into the open.
