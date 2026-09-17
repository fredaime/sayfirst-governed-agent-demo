<!-- SPDX-License-Identifier: Apache-2.0 -->
# Changelog

Every release of this demonstration carries a section here, named for the version the
project file declares; a release with no section fails the gate. This demonstration is
cloned and run rather than installed from an index, so what the version is for is a person
deciding whether the copy in front of them is the one these documents describe.

## Unreleased

## 0.2.0

- The demonstration runs against the open control plane: a daemon on a local socket, a
  policy file of four rules, and one person answering a suspended act with the product
  command-line interface.
- The boundary is composed by hand from the published contract and the published boundary,
  in one module: a socket client whose peer it verifies, and a node wrapper that suspends
  the graph rather than parking a thread on a person.
- Resuming grants nothing, and that is the claim the acceptance suite is built around: a
  resumed node asks the same question, and the control plane answers the wait it already
  has rather than minting a rival one.
- Evidence is metadata. The boundary's outcome records carry a sequence, a capability, a
  decision and how many records were lost before them; no prompt, completion, message body
  or recipient reaches them, and the durable chain is the one the control plane kept.
- The model is opt-in. Nothing runs a model until a reader names one, and a mode that asks
  for a real model with no address refuses and says which two settings it wanted.
