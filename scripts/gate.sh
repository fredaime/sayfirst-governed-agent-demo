#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# The whole gate of this repository, in one command. What it runs is what CI runs; there is
# no step that exists only on a machine.
#
#   format   ruff format --check      every authored file is formatted
#   lint     ruff check               the lint rules this project selects
#   tests    pytest                   every tier, including the guards and the acceptance
#                                     suite against a daemon this run starts
#
# The three distributions this demonstration is built on are published on no index yet, so
# this gate is told where a checkout of each is and builds them from a NAMED REF of it
# rather than from whatever that clone has out. A recording or a gate broken by somebody
# else's uncommitted work is a hazard this project has met, and an archive of a named ref is
# the answer to it — solved once, here.
#
#   SAYFIRST_CONTRACT_SOURCE   a checkout holding the contract, the boundary and the server
#   SAYFIRST_CONTRACT_REF      default main
#   SAYFIRST_CLIENT_SOURCE     a checkout holding the command a person answers with
#   SAYFIRST_CLIENT_REF        default main
#   SAYFIRST_PYTHON            default 3.13
#   SAYFIRST_GATE_TMP          default /tmp — the short root the test run's own directory is
#                              made under, and short for a reason a local address decides
#
# Neither source has a default PATH, and that is deliberate: a default would name a
# repository this one does not publish, inside a file it does publish.
#
# ONE ENVIRONMENT, in both modes. `.venv` is what this gate prepares and what every script
# beside it reads; a reduced run is that same environment WITHOUT the open distributions and
# the daemon, which is why a reduced run removes them rather than leaving an earlier full
# run's copies importable. A second environment of its own was the arrangement here before,
# and it cost the reader this mode exists for the whole demonstration: the bootstrap said
# « complete » and named three commands, and all three died on an interpreter that was in
# the other directory.
#
# Three outcomes rather than two, which is article 2's rule about status surfaces applied to
# this gate's own status:
#
#   0            full green. Everything above ran.
#   75           reduced green. Something a check needed is absent — either the open
#                distributions, or only the command a person answers with — and the run says
#                which of the two it was. Format, lint and every check that could run
#                without it ran and passed; every check that could not is named, counted and
#                printed. A reduced run is not a pass and never renders as one.
#   any other    failure. Something the gate ran said no — including a reduced run whose
#                environment turned out to hold the distributions after all.
#
# What a reduced run does not prove: nothing about this demonstration against a control
# plane, because the cases that start one are among those it could not run; nothing about
# the boundary, for the same reason. It proves that the source is formatted, that it lints,
# and that the guards reading only this repository's own files still hold.
#
# Which checks need what is decided by collecting them, never by a list here:
# `tests/open_packages.py` holds the rule, this script reads back what it skipped through
# SAYFIRST_GATE_NOT_RUN, and the count it prints comes from that collection.
#
#   ./scripts/gate.sh                      the gate
#   ./scripts/gate.sh --environment-only   prepare the environment and stop
set -euo pipefail

#: Two of the three outcomes have a status of their own; the third is every other status
#: there is. `tests/test_gate_modes.py` reads these two lines and requires the workflow to
#: render all three differently.
readonly GATE_FULL_GREEN=0
readonly GATE_REDUCED_GREEN=75

# 75 is a status no tool this gate runs produces, so it cannot be forged by a failure. If
# one ever does produce it, it is reported as the failure it is rather than as a pass.
on_failure() {
  status=$?
  trap - ERR
  if [ "$status" -eq "$GATE_REDUCED_GREEN" ]; then
    echo "gate: a check exited $GATE_REDUCED_GREEN, which is reserved for a reduced run" >&2
    status=1
  fi
  exit "$status"
}
trap on_failure ERR

repository="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository"

environment_only=no
case "${1:-}" in
  "") ;;
  --environment-only) environment_only=yes ;;
  *)
    # Refused rather than ignored, and with a status of its own. The script this gate
    # replaced took a flag that added a tier, which a reader's hands will reach for; a gate
    # that ran everything and said nothing about the flag would teach them it still works.
    echo "gate: $1 is not an argument of this gate. Usage: ./scripts/gate.sh" >&2
    echo "gate: [--environment-only] — with no argument it runs everything, including the" >&2
    echo "gate: tier a flag used to add; with --environment-only it prepares the" >&2
    echo "gate: environment and stops." >&2
    exit 2
    ;;
esac
if [ "$#" -gt 1 ]; then
  echo "gate: this gate takes one argument at most. Usage: ./scripts/gate.sh" >&2
  echo "gate: [--environment-only]." >&2
  exit 2
fi

contract_source="${SAYFIRST_CONTRACT_SOURCE:-}"
contract_ref="${SAYFIRST_CONTRACT_REF:-main}"
client_source="${SAYFIRST_CLIENT_SOURCE:-}"
client_ref="${SAYFIRST_CLIENT_REF:-main}"
python_version="${SAYFIRST_PYTHON:-3.13}"

wheelhouse="$repository/.wheelhouse"
plane_tree="$wheelhouse/control-plane"
client_tree="$wheelhouse/client"
not_run="$wheelhouse/not-run"
# A short run root for the runner's own directories, OUTSIDE this checkout, so that an
# address composed below it leaves the margin the published binding asks for. The limit is
# the kernel's and it is small — a hundred and four bytes on one of the two platforms this
# contract is replayed on — and a root chosen for tidiness is how a suite arrives at zero
# headroom without anyone deciding to spend it. Measured with the published reader: `/tmp`
# costs nine bytes here and leaves the margin; `$wheelhouse/t`, the tidy choice this gate
# was first written with, costs sixty and does not.
#
# `/tmp` outright rather than TMPDIR: on one of those two platforms TMPDIR is a long
# per-session path, and spending it here is spending the address budget. A machine where
# /tmp is not the right place names SAYFIRST_GATE_TMP, and the check further down is what
# tells it whether the choice fits — the published rule, asked rather than restated.
run_root="${SAYFIRST_GATE_TMP:-/tmp}"

# ONE development environment, in both modes, because every script beside this one reads it.
# A reduced run is this same environment without the open distributions — removed below if an
# earlier full run left them — rather than a second directory the other scripts cannot find.
venv="$repository/.venv"

if [ -n "$contract_source" ] && [ -d "$contract_source" ]; then
  mode=full
else
  mode=reduced
  echo "gate: SAYFIRST_CONTRACT_SOURCE names no checkout, so this run is reduced."
  echo "gate: the contract, the boundary and the server are published on no index yet and"
  echo "gate: are not vendored here, so a machine without a checkout of them cannot run"
  echo "gate: the checks that need them. Set SAYFIRST_CONTRACT_SOURCE to such a checkout,"
  echo "gate: and SAYFIRST_CLIENT_SOURCE to one holding the command a person answers with,"
  echo "gate: for the full gate."
fi

mkdir -p "$wheelhouse"

# The runner's own directory, made fresh under the run root with a SHORT template per run, so
# that two gate runs on one machine cannot take each other's — the fixed path this gate used
# before was one directory both runs cleared at the start. Short because the template's own
# bytes are spent out of the address budget the check further down asks the published rule
# about; four random characters cost four of the twenty-seven bytes of margin that check
# leaves. Removed when the run ends, whichever way it ends.
mkdir -p "$run_root"
basetemp="$(mktemp -d "$run_root/sfdXXXX")"
remove_the_runners_directory() {
  if [ -n "${basetemp:-}" ]; then
    rm -rf "$basetemp"
  fi
}
trap remove_the_runners_directory EXIT

# An archive of a named ref, and nothing else. There is NO fallback that copies a checkout:
# a working tree carries whatever its owner has out at that moment, so a gate that read one
# would report on a tree nobody can name — the hazard this whole arrangement exists to solve
# once. A source that cannot be archived at the ref it was given is a failure that says so,
# with the source and the ref in it, rather than a copy nobody asked for.
materialise() {
  local source="$1" ref="$2" destination="$3" what="$4"
  rm -rf "$destination"
  mkdir -p "$destination"
  # The tool is asked whether the source is under version control, rather than the path
  # being tested for a directory: a worktree or a submodule keeps a file there, not a
  # directory, and is as much a checkout as a clone.
  if ! git -C "$source" rev-parse --git-dir >/dev/null 2>&1 || ! git -C "$source" rev-parse \
    --verify --quiet "$ref^{commit}" >/dev/null; then
    echo "gate: $what at $source cannot be read at $ref: either nothing there is under" >&2
    echo "gate: version control, or that ref does not exist in it. This gate reads an" >&2
    echo "gate: archive of a named ref and never the files a checkout has out, so there is" >&2
    echo "gate: nothing to fall back to. Name a checkout and a ref that exists in it." >&2
    exit 1
  fi
  echo "gate: reading $what at $ref ($(git -C "$source" rev-parse "$ref"))"
  git -C "$source" archive "$ref" | tar -x -C "$destination"
}

# Where the command a person answers with is when this gate has built it — named even when
# it has not. `tests/open_packages.py` reads a named path that is not a file as « not on
# this machine », which is the truth, and naming it is what keeps a command somebody happens
# to have on their path out of this run: a suite that answered its approvals with a version
# nobody chose would be proving something about that machine rather than about this ref.
client_command="$repository/.venv-client/bin/sayfirst"
client_built=no
if [ "$mode" = full ]; then
  materialise "$contract_source" "$contract_ref" "$plane_tree" "the control plane's checkout"
  echo "gate: building the contract, its published fake, the boundary and the server"
  # The fake is built beside the three this repository pins because the contract's own
  # optional extra resolves to it, so a machine holding this wheelhouse can install it
  # without a second materialisation. Nothing here pins it, and only what the project file
  # pins is installed.
  for package in sayfirst-contract sayfirst-contract-stub sayfirst-boundary sayfirst-control-plane; do
    uv build --project "$plane_tree" --package "$package" --wheel -o "$wheelhouse" >/dev/null
  done

  if [ -n "$client_source" ] && [ -d "$client_source" ]; then
    materialise "$client_source" "$client_ref" "$client_tree" "the client's checkout"
    echo "gate: building the command a person answers with"
    uv build --project "$client_tree" --wheel -o "$wheelhouse" >/dev/null
    uv venv --allow-existing --python "$python_version" "$repository/.venv-client" >/dev/null
    # By wheel and not by pin: this repository declares no dependency on that command — it
    # is a tool a person types, not a library — so there is no pin here to read, and the
    # wheel built from the named ref is exactly what a reader is told to install.
    uv pip install --quiet --python "$repository/.venv-client/bin/python" --reinstall \
      --no-index --find-links "$wheelhouse" "$wheelhouse"/sayfirst_cli-*.whl
    client_built=yes
  else
    # Not built, so it must not be found. An earlier full run's client left on disk would
    # answer this run's approvals, and the run would report on a version it did not build.
    rm -rf "$repository/.venv-client"
    echo "gate: SAYFIRST_CLIENT_SOURCE names no checkout, so the cases that answer a"
    echo "gate: suspended act the way a person does will stand down and be counted."
  fi
fi

echo "gate: preparing the development environment ($mode)"
uv venv --allow-existing --python "$python_version" "$venv" >/dev/null
python="$venv/bin/python"

# Every pin is READ from pyproject.toml and never spelled here a second time: two copies of
# one rule is how a gate and its project stop agreeing.
read_pins() {
  "$python" - "$@" <<'PY'
import sys, tomllib
document = tomllib.load(open("pyproject.toml", "rb"))
where, prefix, keep = sys.argv[1], sys.argv[2], sys.argv[3]
if where == "runtime":
    items = document["project"]["dependencies"]
else:
    items = document["dependency-groups"][where]
matching = [item for item in items if item.startswith(prefix) == (keep == "yes")]
print(" ".join(matching))
PY
}

open_pins="$(read_pins runtime sayfirst- yes)"
agent_pins="$(read_pins runtime sayfirst- no)"
server_pins="$(read_pins e2e sayfirst- yes)"
dev_pins="$(read_pins dev sayfirst- no)"

# The same pins as names, for the one thing a name is needed for: removing a distribution.
# `tests/open_packages.py` owns which packages the absence is read from; these are the
# distributions that provide them, and they are read from the project file like everything
# else rather than spelled here a second time.
# shellcheck disable=SC2086
open_distributions="$(printf '%s\n' $open_pins $server_pins | sed 's/[][<>=!~;].*$//')"

if [ "$mode" = full ]; then
  # --reinstall is not optional: a checkout can change without changing its version, and an
  # installer that saw the same version already present leaves the old one in place.
  # shellcheck disable=SC2086
  uv pip install --quiet --python "$python" --reinstall \
    --no-index --find-links "$wheelhouse" $open_pins $server_pins
fi
# shellcheck disable=SC2086
uv pip install --quiet --python "$python" $dev_pins $agent_pins
uv pip install --quiet --python "$python" --no-deps --editable "$repository"

# One environment means a reduced run may find what an earlier FULL run installed in it. That
# is not a reduced run: it would prove more than it says here and more than it would prove on
# the machine this mode exists for. So the open distributions are removed rather than left
# importable — which is what makes « the same environment without them » a true sentence —
# and the removal is then measured rather than assumed.
if [ "$mode" = reduced ]; then
  for distribution in $open_distributions; do
    uv pip show --python "$python" "$distribution" >/dev/null 2>&1 || continue
    echo "gate: $distribution was installed by an earlier full run; removing it, because a"
    echo "gate: reduced run is this environment without the open distributions."
    uv pip uninstall --quiet --python "$python" "$distribution"
  done
fi

# Asked of the same rule the tests use rather than of a second reading written here. Before
# the environment-only stop as well as before the run, because the bootstrap stops there and
# the scripts a reader then types read this same environment.
if [ "$mode" = reduced ] && "$python" -c 'import sys
sys.path.insert(0, "tests")
from open_packages import open_packages_are_installed
sys.exit(0 if open_packages_are_installed() else 1)'; then
  echo "gate: the open distributions are importable in the reduced environment at $venv." >&2
  echo "gate: a reduced run must not borrow them; this run would prove more than it says." >&2
  echo "gate: remove them from that environment and run again." >&2
  exit 1
fi

if [ "$environment_only" = yes ]; then
  if [ "$mode" = full ]; then
    echo "gate: the environment is ready at $venv"
    exit "$GATE_FULL_GREEN"
  fi
  echo "gate: the environment at $venv holds everything but the open distributions and the"
  echo "gate: daemon. What it reaches is a configured demonstration whose every take refuses"
  echo "gate: BY NAME — the scripts say which distribution is missing and what installs it —"
  echo "gate: until a checkout of the two open repositories, or a published index, provides"
  echo "gate: them."
  exit "$GATE_REDUCED_GREEN"
fi

# Whether the run root can hold a local address, asked of the published rule rather than
# asserted in the comment above it. Full mode only: it is the mode that starts a daemon, and
# it is the only mode where the contract is installed to ask. A root that fails this is a
# gate that would refuse every end-to-end case for a reason a reader of the failure could
# not guess — so it is refused here, by name, with the number in it.
if [ "$mode" = full ] && ! "$python" - "$basetemp" <<'PY'
import sys
from sayfirst_contract.binding.http_unix_socket.addresses import (
    address_budget,
    root_leaves_the_margin,
    sun_path_limit,
)

root = sys.argv[1]
if not root_leaves_the_margin(root, platform=sys.platform):
    print(
        f"gate: the run root {root} cannot hold a local address: its budget is "
        f"{address_budget(root)} bytes against a limit of {sun_path_limit(sys.platform)}, "
        f"and the margin is spent before a fixture writes anything.",
        file=sys.stderr,
    )
    sys.exit(1)
PY
then
  echo "gate: choose a shorter root (SAYFIRST_GATE_TMP), and run again." >&2
  exit 1
fi

echo "== format =="
"$python" -m ruff format --check .
echo "== lint =="
"$python" -m ruff check .
echo "== tests =="
rm -f "$not_run"
SAYFIRST_GATE_NOT_RUN="$not_run" SAYFIRST_CLIENT="$client_command" \
  "$python" -m pytest -q -rs --basetemp="$basetemp"

if [ ! -f "$not_run" ]; then
  echo "gate: the test run left no record of what it did not run at $not_run" >&2
  echo "gate: tests/open_packages.py owns that record; the gate will not guess." >&2
  exit 1
fi
checks_not_run="$(grep -c . "$not_run" || true)"
modules_not_run="$(grep -c '^module	' "$not_run" || true)"
modules_present="$(find tests -name 'test_*.py' | wc -l | tr -d ' ')"
modules_run=$((modules_present - modules_not_run))

# What was absent, in this run's own words. THREE states rather than two, because a machine
# that has the control plane's checkout and not the client's is not a machine without the
# open distributions: everything about this demonstration against a control plane ran there,
# and only the claims a person answers stood down. Saying « the open distributions are
# absent » of that run would understate what it proved, which is as much a false status
# surface as overstating it.
if [ "$mode" = reduced ]; then
  absent="the open distributions"
elif [ "$client_built" = no ]; then
  absent="the command a person answers with"
else
  absent=""
fi

if [ -z "$absent" ]; then
  if [ "$checks_not_run" -ne 0 ]; then
    echo "gate: everything was built and installed and $checks_not_run checks still stood" >&2
    echo "gate: down. That is a failure, not a reduced run:" >&2
    sed 's/^/gate:   /' "$not_run" >&2
    exit 1
  fi
  echo "gate: full green — format, lint and $modules_run test modules ran."
  exit "$GATE_FULL_GREEN"
fi

# A reduced run that skipped nothing, or that ran nothing, is a broken rule rather than a
# good result, and either way it is not a green tick.
if [ "$checks_not_run" -lt 1 ]; then
  echo "gate: $absent was absent and no check said it needed it." >&2
  echo "gate: tests/open_packages.py is not doing what this run depends on." >&2
  exit 1
fi
if [ "$modules_run" -lt 1 ]; then
  echo "gate: nothing was left to run." >&2
  exit 1
fi

if [ "$mode" = reduced ]; then
  echo "gate: the open distributions are absent: $checks_not_run checks not run"
else
  echo "gate: the command a person answers with is absent: $checks_not_run checks not run"
fi
while IFS=$'\t' read -r kind what why; do
  [ -n "$what" ] || continue
  echo "gate:   not run: $what — $why"
done <"$not_run"
if [ "$modules_not_run" -gt 0 ]; then
  echo "gate: reduced green — format, lint and $modules_run of $modules_present test modules ran."
else
  # Every module ran and cases inside them stood down. « 14 of 14 » beside a list of checks
  # that did not run is a line contradicting itself, so it is not the line printed.
  echo "gate: reduced green — format, lint and all $modules_present test modules ran, and"
  echo "gate: $checks_not_run cases inside them stood down."
fi
echo "gate: A check counted above is a test module or a single case. The cases inside a"
echo "gate: module that would not import cannot be counted, and are not: this run does not"
echo "gate: know how many of them there are."
if [ "$mode" = reduced ]; then
  echo "gate: This is not a pass. It proves nothing about this demonstration against a"
  echo "gate: control plane and nothing about the boundary — read the list above rather than"
  echo "gate: this line. Point SAYFIRST_CONTRACT_SOURCE and SAYFIRST_CLIENT_SOURCE at"
  echo "gate: checkouts, and this becomes the full gate."
else
  echo "gate: This is not a pass. The control plane was real and every tier that needs one"
  echo "gate: ran; what did not run is every claim a person answers, because the command"
  echo "gate: they answer it with was not built — read the list above rather than this line."
  echo "gate: Point SAYFIRST_CLIENT_SOURCE at a checkout holding that command, and this"
  echo "gate: becomes the full gate."
fi
exit "$GATE_REDUCED_GREEN"
