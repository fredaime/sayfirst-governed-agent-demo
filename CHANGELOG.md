<!-- SPDX-License-Identifier: Apache-2.0 -->
# Changelog

Every release of this demonstration carries a section here, named for the version the
project file declares; a release with no section fails the gate. This demonstration is
cloned and run rather than installed from an index, so what the version is for is a person
deciding whether the copy in front of them is the one these documents describe.

## Unreleased

## 0.3.3

- Pins the control plane and the client at 0.3.3. No change to the demonstration's own
  code.

## 0.3.2

- Pins the control plane and the client at 0.3.2, which carry security fixes; an approval in
  the demonstration now authorises exactly the one act it answers. No change to the
  demonstration's own code.

## 0.3.1

- Fixture mode plays a scripted transcript, so every take runs with no model behind it. The
  governance is unchanged: the same boundary asks the same daemon for every decision.
- A bare bootstrap or gate installs the pinned open distributions from the index, and from
  checkouts when they are named. `SAYFIRST_INDEX=no`, with no checkout named, forces the
  reduced run, and the gate says which route delivered the packages it ran against.
- The gate refuses a named checkout that is not there rather than taking the index route in
  its place, and a bare run that finds distributions, or the command a person answers with,
  that a checkouts run built, with the index unable to serve its own, refuses rather than
  reduces: nothing an earlier run installed is removed.
- A new CI job, `gate (from the index)`, runs the gate the way a person who cloned the
  repository would.
- A refused precondition exits 7, and « nothing is listening » exits 4, so a script can tell
  the two apart.
- The notice printed when an act is suspended now shows the three answers a person can
  give: show, approve and reject.
- The pages are rewritten around one path, from a clone to a running demonstration.
- The pins move to 0.3.1: the three open distributions, and the tag the workflow checks the
  two public products out at.

## 0.3.0

- The demonstration runs against the 0.3.0 control plane and command-line interface: the
  three open distributions it pins, and the tag its workflow checks the two public products
  out at, move together to 0.3.0 — one number, said everywhere.
- The gate installs only the wheels a run builds. A wheel an earlier run left in the
  wheelhouse can no longer answer for a tree this run never read: across a version bump the
  command a person answers with used to meet two candidates, and a pinned distribution could
  resolve to the earlier run's build.

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
