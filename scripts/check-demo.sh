#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Is this machine ready to record a take?  Observations, not configuration.
#
# The configuration file is read first, for the reason every script here reads it: the
# settings module resolves the environment and only the environment, so a check that had not
# read the file would be reporting on a configuration nobody is about to run.
set -euo pipefail
cd "$(dirname "$0")/.."

# The environment wins: the helper assigns only what nobody has already named, so a setting
# given on the command line means what it says whatever the file holds.
. scripts/lib/environment.sh
read_environment_file .env

# What this check imports, asked before it runs: the health check speaks to the daemon
# through the published client, and an environment the gate prepared in its reduced mode has
# the interpreter and not that distribution. A refusal naming it is a sentence a reader can
# act on; an import error out of a program they did not start is not.
require_distribution sayfirst_contract "the contract distribution (sayfirst-contract)"

exec "$demo_environment/bin/python" -m sayfirst_governed_agent_demo.healthcheck
