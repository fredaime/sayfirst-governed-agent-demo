<!-- SPDX-License-Identifier: Apache-2.0 -->
# Contributing

## Sign off every commit

Every commit carries a `Signed-off-by:` line certifying the Developer Certificate of Origin.
`git commit -s` writes it; `git rebase --signoff` repairs a branch that missed it.
`scripts/check_developer_certificate_of_origin.py --base <ref>` reads a range and refuses a
commit without one — and refuses a range it cannot read rather than reporting that it
passed.

## The gate is one command

`./scripts/gate.sh` is the whole gate: format, lint, and every test. It has three outcomes
and not two, and the middle one matters: **`75` is a reduced run, not a pass.** It happens
when the open distributions cannot be built, names and counts every check it did not run,
and proves nothing about this demonstration against a real control plane. `0` is the full
gate. Anything else is a failure.

## Every authored file names its licence

The first line carries an SPDX identifier — `Apache-2.0` for code and documents,
`Apache-2.0 OR MIT-0` for the invented material under `demo_data/`, which a reader may lift
into a demonstration of their own. `tests/test_spdx_identifiers.py` holds it.

## One rule per file

A guard is one file with one rule, so a new rule arrives as a new file and a new file never
conflicts with somebody else's.

## What this repository will not take

It re-implements no governance. A change that decided anything here, cached a decision, or
derived an answer the control plane did not give would be a change to what this
demonstration is for, and belongs in neither this repository nor a patch to it.
