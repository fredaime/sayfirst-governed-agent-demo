#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Start the control plane this demonstration asks: the published daemon, on one local
# socket, reading the policy file beside this script.
#
# Per-user mode, which is the right mode for a demonstration on one machine and also the
# mode with the fewest ways to get wrong: the daemon serves one account — the one it runs
# as — it creates every level of its socket's directory at 0700 whatever the umask, and it
# refuses an admission group, an account to drop to and a list of accounts, because it has
# one principal and a configuration that pretended otherwise would be a confusion of modes.
#
# It also sidesteps a consequence of the other mode that would bite this demonstration
# immediately: in system mode a program running as the administrator or as the admission
# group obtains no decision at all, because either could rewrite the configuration that
# decides where the socket is and which file is the policy.
#
# Everything this writes is under one run directory, and nothing is written into the
# checkout: the daemon establishes the permissions of its own policy and configuration, and
# a file in a checkout has whatever permissions the checkout has.
set -euo pipefail
cd "$(dirname "$0")/.."

# The configuration file, if there is one, BEFORE anything reads a setting. `.env` is what
# the bootstrap writes and `.env.example` documents, and nothing inside this package reads
# it: the settings module resolves the environment and only the environment, so the scripts
# are where a file becomes an environment.
# The environment wins: the helper assigns only what nobody has already named, so a setting
# given on the command line means what it says whatever the file holds.
. scripts/lib/environment.sh
read_environment_file .env

run="${SAYFIRST_DEMO_RUN:-${XDG_RUNTIME_DIR:-$HOME/.cache}/sayfirst-demo}"
principal="${SAYFIRST_PRINCIPAL:-user:$(id -un)}"
placeholder="user:the-account-that-runs-this-demonstration"

# The principal is checked before it is interpolated into anything. What it is checked
# against is a RENDERING-SAFE SUBSET of what the control plane admits, not parity with it:
# the control plane's own rule for a principal reference is one colon, a kind, and up to
# two hundred and fifty-six characters that are not control characters, so it accepts
# references — an upper-case letter, an address with an at sign — that this script refuses.
# The subset exists because the reference is written into the policy with a stream edit
# and checked with a fixed-string search, and a lowercase letter or digit followed by up to
# sixty-three of lowercase letters, digits, dots, underscores and dashes is what those two
# tools handle with the delimiter chosen below. Anything else is refused here, with the
# rule it broke, rather than corrupting the policy file quietly further down; the
# placeholder itself is refused too, because a file rendered to itself would pass the
# fixed-string check while naming nobody.
if [ "$principal" = "$placeholder" ]; then
  echo "SAYFIRST_PRINCIPAL is the policy file's placeholder, which names no account." >&2
  echo "Set it to 'user:' and the account that runs this demonstration, or unset it." >&2
  exit 1
fi
if ! [[ "$principal" =~ ^user:[a-z0-9][a-z0-9._-]{0,63}$ ]]; then
  echo "SAYFIRST_PRINCIPAL=$principal is not a reference this script can render." >&2
  echo "It wants 'user:' and an identifier: a lowercase letter or a digit, then up to 63" >&2
  echo "more of lowercase letters, digits, dots, underscores and dashes." >&2
  exit 1
fi

# The daemon, asked for by name. The earlier sentence here sent a reader to the bootstrap,
# which is the script that had just run and could not have fixed it: the gate's reduced mode
# prepares this same environment WITHOUT the server, so what a reader needs told is which
# distribution is missing and the two ways to obtain it.
require_the_daemon

mkdir -p "$run"
chmod 700 "$run"

# The policy, rendered with this account's own reference. `sed` and not a template engine:
# one substitution, visible in the diff of the file it produced.
#
# Two details make that substitution safe for every reference the check above admits. The
# delimiter is a vertical bar, which the admitted set does not contain, so a dot or a dash in
# an identifier can never end the expression early. And the check that the placeholder is
# gone is `grep -F`, a fixed string rather than a pattern, so a dot in the reference means a
# dot and not « any character » — which would otherwise be a check that passed on a file the
# substitution had missed.
sed "s|${placeholder}|${principal}|g" demo-policy.toml >"$run/policy.toml"
chmod 600 "$run/policy.toml"
grep -qF "${principal}" "$run/policy.toml" || {
  echo "the policy still names the placeholder principal: check demo-policy.toml" >&2
  exit 1
}

cat >"$run/daemon.toml" <<TOML
# SPDX-License-Identifier: Apache-2.0
[socket]
mode = "per_user"
path = "$run/daemon.sock"

[policy]
path = "$run/policy.toml"

[evidence]
path = "$run/evidence"
TOML
chmod 600 "$run/daemon.toml"

# Where the daemon will be, written before the `exec` below rather than after it: `exec`
# replaces this shell with the daemon, so this shell's own process id IS the daemon's from
# that line onward. `./scripts/reset-demo.sh` reads this to stop what it is about to clear,
# because a daemon left running over a removed run directory would hold open files nothing
# can reach and would answer with an evidence store that is no longer there.
echo $$ >"$run/daemon.pid"
chmod 600 "$run/daemon.pid"

cat <<INFO

control plane
  socket     $run/daemon.sock
  policy     $run/policy.toml   (rendered from demo-policy.toml for $principal)
  evidence   $run/evidence

Point the agent at it, in another terminal:
  export SAYFIRST_SOCKET=$run/daemon.sock

Answer a suspended act, in another terminal:
  sayfirst approvals show    --approval REF --scope local --socket $run/daemon.sock
  sayfirst approvals approve --approval REF --scope local --socket $run/daemon.sock

INFO

exec "$demo_environment/bin/sayfirst-daemon" serve --config "$run/daemon.toml"
