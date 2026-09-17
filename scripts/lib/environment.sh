# SPDX-License-Identifier: Apache-2.0
# Two things every script beside this one needs before it reads a setting or runs a program:
# the configuration file, read the way a file should be read, and the refusal a script owes
# when the environment lacks what that program imports.
#
# Sourced, not executed. The scripts that bootstrap, start, check, run and reset this
# demonstration source it and call `read_environment_file` before they read a setting,
# because nothing inside the package reads a file — the settings module resolves the
# environment and only the environment, so a script is where a file becomes an environment.
#
# ## The one environment, and the refusal
#
# `./scripts/gate.sh` prepares `.venv` in BOTH of its modes, and a reduced mode is that same
# environment without the open distributions and the daemon. So an interpreter being there is
# no longer the same question as what it can import, and the difference is a reader's ordinary
# first state: someone who cloned this repository and nothing else has the environment and not
# the distributions. `require_distribution` is what a script asks before it hands over to a
# program, so that state arrives as a sentence naming the distribution and what installs it
# rather than as an import error out of a program the reader did not start.
#
# **A variable already set is left alone.** That is the whole rule, and it is the one an
# automated caller depends on: `MODEL_MODE=real ./scripts/run-demo.sh` has to mean what it
# says, whatever `.env` holds, or a take driver and a continuous-integration job cannot
# steer a run without editing a file first. So the file supplies what nobody named, and
# names nothing over the top of a caller. An empty value counts as named: `MODEL_MODE=` on
# the command line is a deliberate blank, not an absence.
#
# **Nothing here evaluates the file.** A configuration file is data. Each line is matched
# against `NAME=value`, the assignment is built from the two halves the match yields, and a
# line that is not that shape is refused with a sentence naming the file and the line rather
# than being handed to the shell to interpret. The alternative — sourcing it — runs whatever
# it contains, which is how a file that is only ever meant to carry settings becomes a way
# to run a command.
#
# **A name assigned twice is refused, loudly.** One file, one meaning: a second assignment of
# a name the file has already made is a file that says two things, and which of them applies
# would be an accident of order rather than a decision. The second is not applied and a
# sentence names the file and both lines, so the ambiguity is fixed where it was written
# instead of being resolved quietly here. The first assignment stands, because a reader whose
# file is otherwise sound should not have their run refused outright — the same treatment a
# line that is not an assignment gets.
#
# Quoted values are honoured, comments and blank lines are skipped, and a trailing carriage
# return is dropped so a file written on another system reads the same here.

read_environment_file() {
  local file="${1:-.env}"
  [ -f "$file" ] || return 0

  local line name value number=0
  # Names already assigned by this file, as one string of " NAME=LINE" entries: a plain
  # string rather than an associative array, so a stock macOS bash (version 3) runs this
  # file too — it is the one place the four scripts would otherwise need bash 4.
  local assigned=" " earlier
  while IFS= read -r line || [ -n "$line" ]; do
    number=$((number + 1))
    line="${line%$'\r'}"
    case "$line" in
      '' | [[:space:]]* ) [ -n "${line//[[:space:]]/}" ] || continue ;;
    esac
    case "${line#"${line%%[![:space:]]*}"}" in
      '#'*) continue ;;
    esac

    if [[ "$line" =~ ^[[:space:]]*(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      name="${BASH_REMATCH[2]}"
      value="${BASH_REMATCH[3]}"
    else
      echo "$file line $number is not NAME=value and was not read: $line" >&2
      continue
    fi

    case "$assigned" in
      *" $name="*)
        earlier="${assigned#* "$name"=}"
        earlier="${earlier%% *}"
        echo "$file assigns $name twice, at lines $earlier and $number, and one" >&2
        echo "file has one meaning: line $number was refused. Remove one of the two." >&2
        continue
        ;;
    esac
    assigned="$assigned$name=$number "

    case "$value" in
      \"*\") value="${value:1:${#value}-2}" ;;
      \'*\') value="${value:1:${#value}-2}" ;;
    esac

    # The rule, in one line: assign only what nobody has named.
    if [ -z "${!name+x}" ]; then
      export "$name=$value"
    fi
  done <"$file"
}

#: The environment the gate prepares, in BOTH of its modes, and the one every script reads.
#: Lower case because it is this library's own name and not a setting: the gate decides where
#: the environment is, and a script that read a different answer from `.env` would be checking
#: one directory and running a program out of another.
demo_environment=".venv"

#: The status a refusal here exits with — the one these scripts already used for a
#: precondition nothing they could do would satisfy.
demo_refusal_status=1

refuse() {
  local line
  for line in "$@"; do
    echo "$line" >&2
  done
  exit "$demo_refusal_status"
}

require_the_environment() {
  if [ -x "$demo_environment/bin/python" ]; then
    return 0
  fi
  refuse "there is no environment at $demo_environment — run ./scripts/bootstrap.sh, which" \
    "prepares it and writes .env from .env.example."
}

# ONE sentence, so that the three scripts refuse in one voice and only the name differs. It
# names the distribution and both ways to obtain it, because a reader who meets this refusal
# has done nothing wrong: the distributions are published on no index yet, so the only way to
# hold one today is a checkout of the two open repositories, and the bootstrap builds them
# from one when it is told where they are.
refuse_a_missing_distribution() {
  refuse "$1 is not installed here;" \
    "run ./scripts/bootstrap.sh with SAYFIRST_CONTRACT_SOURCE and SAYFIRST_CLIENT_SOURCE" \
    "naming checkouts of the two open repositories, or install it from the index once" \
    "it is published."
}

# Whether this environment can import what the program about to run imports, asked of the
# interpreter rather than guessed from a directory listing: a distribution is installed or it
# is not, and only the interpreter that would import it knows which. One distribution per
# call, named in the singular, because one sentence naming two of them would be wrong about
# whichever of the two is present.
#
#   require_distribution sayfirst_contract "the contract distribution (sayfirst-contract)"
require_distribution() {
  local package="$1" named="$2"
  require_the_environment
  if "$demo_environment/bin/python" -c "import importlib.util, sys
sys.exit(0 if importlib.util.find_spec('$package') else 1)" 2>/dev/null; then
    return 0
  fi
  refuse_a_missing_distribution "$named"
}

# The daemon is a PROGRAM this repository runs and never imports, so what says whether it is
# here is the executable and not an import.
require_the_daemon() {
  require_the_environment
  if [ -x "$demo_environment/bin/sayfirst-daemon" ]; then
    return 0
  fi
  refuse_a_missing_distribution "the control plane distribution (sayfirst-control-plane)"
}
