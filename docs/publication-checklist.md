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
  `sayfirst-contract==0.3.2` and `sayfirst-boundary==0.3.2`, plus `langgraph` and `httpx`; the
  control plane's own distribution at the same version, in a group of its own, because the
  start script and the acceptance suite each run its daemon as a separate process and nothing
  this distribution ships imports it; and the product command-line interface, which is a
  command a person types and a dependency of nothing. One number, said everywhere, and it is
  the number of the release this demonstration shows.

## What publication changed

While the two products were not yet this repository's to name, the gate was told where a
checkout of each was — `SAYFIRST_CONTRACT_SOURCE` with `SAYFIRST_CONTRACT_REF`, and
`SAYFIRST_CLIENT_SOURCE` with `SAYFIRST_CLIENT_REF` — and built the wheels from an archive of
that named ref; the workflow read the two repository names out of repository variables and
reached them with a credential. Neither variable had a default path, and neither has one now:
a default would name a repository this one does not publish, inside a file it does publish.

An earlier version of this page said publication would retire both arrangements, and the
reduced mode with them. It did less than that, and what it did is recorded here so that no
published file describes the world this page once predicted:

1. **the distributions are on the index**, at the version this tree pins, and a bare
   `./scripts/gate.sh` installs them from it — the index route, which arrived in 0.3.1
   ([CHANGELOG.md](../CHANGELOG.md) names the release). The checkouts route stayed, for a
   contributor and for the workflow's full job, and `materialise` with it. The reduced mode
   stayed too: a machine neither route reaches — no network, or the index refused with no
   checkout named — still gets a run that names what it did not prove, and
   `tests/test_gate_modes.py` still requires three outcomes;
2. **the workflow checks out the two public repositories by name, at the tag this tree pins,
   with no credential.** The repository variables and the credential are gone, and the same
   guard refuses either coming back. The reduced job stayed, for a fork whose runner reaches
   neither product at the tag, and the index route is a third job beside the two.

Read those two files with this page: each says, in its own comments, where the distributions
come from and what a run without them proves. A published file claiming they are absent
everywhere is the defect `tests/test_no_stale_publication_claims.py` exists to catch, and
this page is the file that guard was widened for.

## The order

**After the two products, and in this order for a reason.** This demonstration pins them at a
version; a repository published before the distributions it pins is a repository a reader cannot
install from, whatever its documents say. So: the control plane, then the command, then this.

The repository is created **fresh**, at the tag, with private vulnerability reporting enabled in
the same act — `SECURITY.md` names that channel and the hosting platform permits the setting on
a public repository only — and the history is not carried. One consequence worth naming: the
private history holds a commit that certifies no sign-off, and a fresh repository disposes of it
rather than carrying it into the open.
