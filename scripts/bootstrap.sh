#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# One-time setup. Idempotent: safe to re-run.
#
# The open distributions come from the index, at the version pinned here, or from checkouts
# when SAYFIRST_CONTRACT_SOURCE and SAYFIRST_CLIENT_SOURCE name them; the command a person
# answers with is installed beside them. A model is not installed: fixture mode plays a
# scripted transcript, and a reader who wants to watch a model reason names an endpoint. The
# pull below is one vendor's way of getting one locally, offered and not required.
set -euo pipefail
cd "$(dirname "$0")/.."

# 7, the precondition status scripts/lib/environment.sh names: nothing is sourced yet here.
command -v uv >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/" >&2; exit 7; }

echo "==> the environment"
# A reduced environment is a fact about this machine, not a failure: the gate reserves 75
# for it and has already said that neither the index nor a named checkout delivered the open
# distributions. Tolerated here, and what it reaches is said in full below rather than
# implied: ONE environment, at `.venv`, which a reduced run prepares without the open
# distributions and without the daemon. So a reader on a machine with neither route — no
# network, or SAYFIRST_INDEX=no and no checkout named — reaches a CONFIGURED demonstration,
# and every take of it refuses by name until the distributions are installed. Any other
# non-zero status is a failure and stops here.
environment_status=0
./scripts/gate.sh --environment-only || environment_status=$?
if [ "$environment_status" -ne 0 ] && [ "$environment_status" -ne 75 ]; then
  exit "$environment_status"
fi
if [ "$environment_status" -eq 75 ]; then
  echo "    the environment is reduced: neither the index nor a named checkout delivered the"
  echo "    open distributions. ./scripts/gate.sh says which checks that leaves out."
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
# At the release this tree carries, read rather than spelled: the gate installs the command
# at the contract's pinned version, and one number is said everywhere in this project — a
# script that spelled it would be the second place it was said. The reader runs under a
# bare interpreter, so a reduced environment answers it too.
release="$(.venv/bin/python scripts/release_version.py)"
if [ -x .venv-client/bin/sayfirst ]; then
  echo "    sayfirst is at .venv-client/bin/sayfirst — put it on your PATH, or install it"
  echo "    for your account with: uv tool install sayfirst-cli==$release"
elif command -v sayfirst >/dev/null; then
  echo "    sayfirst is on the path"
else
  echo "    sayfirst is not installed. It answers a suspended act: uv tool install sayfirst-cli==$release"
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
  echo "    no model: MODEL_MODE=fixture plays a scripted transcript. To watch a model reason,"
  echo "    set MODEL_MODE=real, MODEL_BASE_URL and MODEL_NAME in .env (any OpenAI-compatible"
  echo "    endpoint serving a tool-calling model)."
fi

cat <<'NEXT'

Bootstrap complete. Next:

  ./scripts/start-control-plane.sh      # terminal 1 — the control plane, on a local socket
  ./scripts/check-demo.sh               # terminal 2 — every precondition, observed
  ./scripts/run-demo.sh hitl            # terminal 2 — run the agent; answer in a third
  ./scripts/reset-demo.sh               # between takes — a fresh control plane and outbox
NEXT

# What this environment reaches, said here rather than discovered one command later. A
# reduced environment is CONFIGURED — `.env` is written, the directories are there, the
# agent's own dependencies are installed — and each of the first three commands above
# refuses by name, saying which distribution is missing and the two ways to obtain it; the
# fourth needs none of them. That is the honest reading of « complete »: complete for what
# this machine holds.
if [ "$environment_status" -eq 75 ]; then
  cat <<'REDUCED'
The first three will REFUSE on this machine, by name: neither the index nor a named checkout
delivered the open distributions. Re-run with network access, or with
SAYFIRST_CONTRACT_SOURCE and SAYFIRST_CLIENT_SOURCE naming checkouts of the two open
repositories.
REDUCED
fi
