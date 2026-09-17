#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# One-time setup. Idempotent: safe to re-run.
#
# Two of the three things it installs are published distributions; the third is a command a
# person types, installed as a tool rather than as a dependency of anything. A model is
# NOT installed: this demonstration runs its tests with no model at all, and a reader who
# wants to watch it reason names an endpoint and a model of their own. The pull below is
# one vendor's way of getting one locally, offered and not required.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v uv >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/" >&2; exit 1; }

echo "==> the environment"
# A reduced environment is a fact about this machine, not a failure: the gate reserves 75
# for it and has already said which checkouts it could not find. Tolerated here, and what it
# reaches is said in full below rather than implied: ONE environment, at `.venv`, which a
# reduced run prepares without the open distributions and without the daemon. So the reader
# this mode exists for — someone who cloned this repository and nothing else — reaches a
# CONFIGURED demonstration, and every take of it refuses by name until the distributions are
# installed. Any other non-zero status is a failure and stops here.
environment_status=0
./scripts/gate.sh --environment-only || environment_status=$?
if [ "$environment_status" -ne 0 ] && [ "$environment_status" -ne 75 ]; then
  exit "$environment_status"
fi
if [ "$environment_status" -eq 75 ]; then
  echo "    the environment is reduced: the checkouts the open distributions are built from"
  echo "    are absent, so the tiers that need them will stand down BY NAME when you run"
  echo "    ./scripts/gate.sh, which counts them and says what they do not prove."
fi

echo "==> configuration"
[ -f .env ] || { cp .env.example .env; echo "    wrote .env from .env.example"; }

# The file, read straight after it is written, the way every other script here reads it: the
# optional model pull below looks for MODEL_NAME, and a reader who put one in `.env` means
# that one. A name already in the environment still wins over the file.
. scripts/lib/environment.sh
read_environment_file .env

echo "==> runtime directories"
mkdir -p runtime/outbox runtime/reports runtime/events

echo "==> the command a person answers with"
if command -v sayfirst >/dev/null; then
  echo "    sayfirst is on the path"
elif [ -x .venv-client/bin/sayfirst ]; then
  echo "    sayfirst is at .venv-client/bin/sayfirst (the gate built it)"
else
  echo "    sayfirst is not installed. It is the product command-line interface and it is"
  echo "    what answers a suspended act. Install it with 'uv tool install sayfirst-cli'"
  echo "    once it is published, or let ./scripts/gate.sh build it from a checkout."
fi

echo "==> a model, if you want one"
if [ -n "${MODEL_NAME:-}" ] && command -v ollama >/dev/null; then
  if ollama list | grep -q "^${MODEL_NAME%%:*}"; then
    echo "    $MODEL_NAME is already present"
  else
    echo "    pulling $MODEL_NAME"
    ollama pull "$MODEL_NAME" || echo "    the pull did not finish; the demonstration does not need it"
  fi
  if ollama show "$MODEL_NAME" 2>/dev/null | grep -q "tools"; then
    echo "    $MODEL_NAME advertises tool calling"
  else
    echo "    WARNING: $MODEL_NAME does not advertise tool calling — this agent has to be" >&2
    echo "             able to CHOOSE an act. See docs/ARCHITECTURE.md." >&2
  fi
else
  echo "    no model was pulled. Set MODEL_MODE=real, MODEL_BASE_URL and MODEL_NAME to any"
  echo "    endpoint that speaks the OpenAI-compatible API and serves a tool-calling model."
fi

cat <<'NEXT'

Bootstrap complete. Next:

  ./scripts/start-control-plane.sh      # terminal 1 — the authority, on a local socket
  ./scripts/check-demo.sh               # terminal 2 — every precondition, observed
  ./scripts/run-demo.sh hitl            # terminal 2 — run the agent
NEXT

# What this environment reaches, said here rather than discovered one command later. A
# reduced environment is CONFIGURED — `.env` is written, the directories are there, the
# agent's own dependencies are installed — and each of the three commands above refuses by
# name, saying which distribution is missing and the two ways to obtain it. That is the
# honest reading of « complete »: complete for what this machine holds.
if [ "$environment_status" -eq 75 ]; then
  cat <<'REDUCED'
Each of those three will REFUSE on this machine, by name: the open distributions are
published on no index yet and no checkout of them was found, so the environment holds the
interpreter, this package and its own dependencies and not them. Re-run this script with
SAYFIRST_CONTRACT_SOURCE and SAYFIRST_CLIENT_SOURCE naming checkouts of the two open
repositories, and the same three commands run.
REDUCED
fi
