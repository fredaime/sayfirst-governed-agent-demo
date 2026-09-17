#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Clear everything a take produced: the artefacts, and the authority that decided them.
#
# Clearing the outbox is not a reset, and restarting the control plane is not one either.
# The daemon keeps its decisions and its evidence chain in FILES under its run directory and
# reopens them when it starts, so take two would show take one's chain — under the very
# command a take ends by printing. What a reset has to remove is that directory: the socket,
# the configuration, the rendered policy, the decisions, the approvals and the evidence. So
# this stops the daemon if one is running and removes the whole of it. A new take starts a
# fresh daemon with nothing kept.
#
# What decides that nothing is running is the recorded process AND the socket, not either
# alone: a run directory with no process id in it but a socket sitting in it is a directory
# this script knows nothing about, and something may well be listening there. So it removes
# nothing in that case and says how to look.
#
# Nothing outside runtime/ and that one run directory is touched.
set -euo pipefail
cd "$(dirname "$0")/.."

# The configuration file, if there is one, BEFORE anything reads a setting: it is where
# SAYFIRST_DEMO_RUN may name a run directory other than the default, and clearing the wrong
# directory would leave the take in place and say it had gone.
# The environment wins: the helper assigns only what nobody has already named, so a setting
# given on the command line means what it says whatever the file holds.
. scripts/lib/environment.sh
read_environment_file .env

run="${SAYFIRST_DEMO_RUN:-${XDG_RUNTIME_DIR:-$HOME/.cache}/sayfirst-demo}"

# Liveness is asked with `kill -0`, which is a signal-zero permission check and exists
# everywhere a signal does: it answers whether THIS account may signal that process, with no
# `ps`, no output format to parse and nothing to be absent in a container. What it cannot do
# is confirm a name, so the rule below is the safeguard that replaces the name: the run
# directory is removed only once nothing is alive at the recorded process. A daemon left
# running over a removed directory would hold open files nothing can reach and would answer
# out of an evidence store that is no longer there — so a reset that cannot stop it refuses
# to remove anything and says so, rather than reporting a reset that did not happen.
recorded_process=""

# Nothing is recorded, and something may still be listening. The one case where this script
# has no process to ask about and no right to assume: it refuses, and points at the socket.
refuse_an_unattributed_socket() {
  local why="$1"
  echo "[--] $why, and a socket is present at $run/daemon.sock." >&2
  echo "     A control plane may be listening there. Nothing was removed: taking the run" >&2
  echo "     directory out from under a live daemon leaves it holding files nothing can" >&2
  echo "     reach. Find what is serving that socket and stop it, then run this again:" >&2
  echo "       fuser $run/daemon.sock        # or: lsof $run/daemon.sock" >&2
  echo "       kill \$(the process it names)" >&2
  echo "     If nothing is listening, the socket is stale and you can remove it by hand:" >&2
  echo "       rm $run/daemon.sock" >&2
  exit 1
}

stop_the_control_plane() {
  local recorded="$run/daemon.pid"
  if [ ! -f "$recorded" ]; then
    [ -S "$run/daemon.sock" ] && refuse_an_unattributed_socket "no control plane was recorded as running"
    echo "[OK] no control plane was recorded as running"
    return 0
  fi
  recorded_process="$(cat "$recorded")"
  case "$recorded_process" in
    '' | *[!0-9]*)
      [ -S "$run/daemon.sock" ] && refuse_an_unattributed_socket "$recorded does not name a process"
      echo "[--] $recorded does not name a process; nothing was stopped" >&2
      recorded_process=""
      return 0
      ;;
  esac
  if ! kill -0 "$recorded_process" 2>/dev/null; then
    echo "[OK] no control plane is running   (a stale process id was left behind)"
    recorded_process=""
    return 0
  fi
  kill "$recorded_process" 2>/dev/null || true
  for _ in {1..40}; do
    if ! kill -0 "$recorded_process" 2>/dev/null; then
      echo "[OK] control plane stopped         (process $recorded_process)"
      return 0
    fi
    sleep 0.25
  done
  kill -9 "$recorded_process" 2>/dev/null || true
  for _ in {1..20}; do
    if ! kill -0 "$recorded_process" 2>/dev/null; then
      echo "[OK] control plane stopped         (process $recorded_process, which did not answer a request to stop)"
      return 0
    fi
    sleep 0.25
  done
  return 1
}

if ! stop_the_control_plane; then
  echo "[--] the control plane at process $recorded_process is still running." >&2
  echo "     Nothing was removed: a run directory taken out from under a live daemon" >&2
  echo "     leaves it holding files nothing can reach. Stop it and run this again." >&2
  exit 1
fi

rm -rf "$run"
echo "[OK] run directory removed         ($run)"
echo "     its decisions, approvals, evidence, socket and configuration went with it"

rm -f runtime/outbox/*.json runtime/reports/* runtime/events/*.json 2>/dev/null || true
mkdir -p runtime/outbox runtime/reports runtime/events
echo "[OK] outbox cleared                ($(ls runtime/outbox | wc -l) artefacts)"
echo "[OK] reports cleared"
echo "[OK] events cleared"
echo
echo "A new take starts a fresh daemon with nothing kept:"
echo "  ./scripts/start-control-plane.sh"
