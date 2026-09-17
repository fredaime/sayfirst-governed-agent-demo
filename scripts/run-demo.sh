#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Run the governed agent.  ./scripts/run-demo.sh [hitl|allow|deny|pending]
#
# No mode is forced here. `fixture` is the settings' own default and needs no model at all;
# a take that wants to watch the agent reason opts in by naming MODEL_MODE, MODEL_BASE_URL
# and MODEL_NAME in the configuration file this reads below, and a `real` run that names no
# address refuses at startup and says which two settings it wanted.
set -euo pipefail
cd "$(dirname "$0")/.."

# The configuration file, if there is one, BEFORE anything reads a setting. `.env` is what
# the bootstrap writes and `.env.example` documents, and nothing inside this package reads
# it: the settings module resolves the environment and only the environment, so the scripts
# are where a file becomes an environment.
# The environment wins: the helper assigns only what nobody has already named, so
# `MODEL_MODE=real ./scripts/run-demo.sh` means what it says whatever the file holds.
. scripts/lib/environment.sh
read_environment_file .env

# What this run imports, asked before anything else — before the socket, deliberately. Both
# absences are real on a machine that holds only this repository, and this is the one a reader
# has to resolve first: nothing can be listening at that address until the distribution that
# serves it is installed, so « nothing is listening » would send them to a script that would
# refuse for the same reason one command later.
# The boundary, which is what this program imports directly and what the contract arrives
# with: one name, so the sentence is true of whichever of the two is actually absent.
require_distribution sayfirst_boundary "the boundary distribution (sayfirst-boundary)"

run="${SAYFIRST_DEMO_RUN:-${XDG_RUNTIME_DIR:-$HOME/.cache}/sayfirst-demo}"
export SAYFIRST_SOCKET="${SAYFIRST_SOCKET:-$run/daemon.sock}"
[ -S "$SAYFIRST_SOCKET" ] || {
  echo "nothing is listening at $SAYFIRST_SOCKET — run ./scripts/start-control-plane.sh" >&2
  exit 1
}
exec "$demo_environment/bin/python" -m sayfirst_governed_agent_demo.app "${1:-hitl}" "${@:2}"
