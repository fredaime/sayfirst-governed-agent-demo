# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures: a real control plane in a separate process, and a graph pointed at it.

The model is faked. **The governance is not.** Every case in `tests/e2e/` drives the real
node wrapper, the real published boundary, the real published client and a real daemon
started as its own process, and answers a suspended act with the command a person types. A
case that stubbed the authority would prove nothing about the property it names.

The daemon is started the way its own deployment document says to start it, in per-user
mode: the policy at mode 0600 inside a run directory at 0700, the configuration beside it,
the socket beside that, and the announcement line read before anything dials. Three details
are worth saying out loud because each has cost this project, or its siblings, a debugging
session:

* **the run directory is this fixture's own, made under `/tmp` with a short template**, and
  the socket is composed inside it rather than under a directory the runner chose. A local
  address is not a name of unbounded length — the limit is the kernel's, 104 bytes on one
  of the two platforms this contract is replayed on — and a per-test directory named after
  the test spends thirty-two of them before a fixture has written anything. A suite that
  composed its socket under such a directory would pass on the machine it was measured on
  and fail on somebody else's, with `AF_UNIX path too long` and no mention of either the
  limit or the path;
* **the address is checked against the rule the binding publishes, by calling it**, before
  the daemon binds it. The check is the contract's own `refuse_a_long_address`, which
  refuses while there is still margin — sixteen bytes, one more directory level — so the
  fix is renaming a leaf rather than moving a run root;
* the wait for the announcement is bounded, because a daemon that neither announces itself
  nor exits would otherwise hang every case in the module with nothing said about why.

The policy is the file this repository ships, with this account's reference substituted for
the placeholder — read rather than repeated, so a rule the documents describe and a rule
these cases exercise cannot drift apart.

**Every import of an open distribution below is inside a fixture on purpose.** A test module
that cannot import what it needs is stood down by name and counted (`tests/open_packages.py`
owns that rule); a CONFTEST that could not import would stop the whole session instead of
reducing it, and the gate's reduced mode — where none of these distributions is installed —
would have nothing to report and no run to report it from. So this file imports the standard
library and `pytest` at module level, and nothing else.
"""

from __future__ import annotations

import json
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any

import pytest

_here = Path(__file__).resolve().parent
# So that the hooks below, and any case that asks, read the rule from the same file the
# gate reads its count from. Two copies of one rule is how a gate and its tests stop
# agreeing.
sys.path.insert(0, str(_here))

REPOSITORY = Path(__file__).resolve().parents[1]


def principal() -> str:
    """The account these cases run as, in the one spelling the boundary uses for a person.

    Read when a case asks, never at import: a host whose effective uid has no account
    entry must lose the cases that need one, not the collection of every tier.
    """
    try:
        return f"user:{pwd.getpwuid(os.geteuid()).pw_name}"
    except KeyError:
        pytest.skip("the effective uid has no account entry, so no principal can be named")


#: The policy this repository ships, and the reference it names for a reader to replace.
POLICY_TEMPLATE = REPOSITORY / "demo-policy.toml"
PLACEHOLDER_PRINCIPAL = "user:the-account-that-runs-this-demonstration"

#: The template every run directory of this suite is made from, under `/tmp` and short:
#: four characters and a separator, so that `/tmp/sgd-XXXXXXXX/daemon.sock` is about thirty
#: bytes and leaves the published margin on both platforms the contract names. It is NOT
#: composed under the runner's per-test directory, for the reason the module docstring
#: gives. The parent is the same one the gate script works under, read from the same
#: variable with the same default, so a machine that needs another place says it once.
RUN_PREFIX = "sgd-"
RUN_PARENT = os.environ.get("SAYFIRST_GATE_TMP", "").strip() or "/tmp"

#: How long the daemon has to announce its socket before the wait gives up.
ANNOUNCE_SECONDS = 15


def _policy_for(principal: str) -> str:
    """The shipped policy, with this account's own reference in the rules."""
    text = POLICY_TEMPLATE.read_text(encoding="utf-8")
    assert PLACEHOLDER_PRINCIPAL in text, "the shipped policy no longer names the placeholder"
    return text.replace(PLACEHOLDER_PRINCIPAL, principal)


def _first_line(process: subprocess.Popen) -> str:
    assert process.stdout is not None
    return process.stdout.readline()


def _written(run: Path) -> str:
    """What the daemon wrote on its error stream, kept in a file beside its socket.

    A pipe nobody drains is a wedge waiting for a chattier daemon; a file is read when a
    case needs the evidence and costs nothing otherwise.
    """
    try:
        return (run / "daemon.log").read_text(encoding="utf-8")
    except OSError:
        return ""


def _launch(config: Path) -> subprocess.Popen:
    """Start the published daemon on a written configuration, and wait for its socket."""
    with (config.parent / "daemon.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "sayfirst_control_plane.cli", "serve", "--config", str(config)],
            stdout=subprocess.PIPE,
            stderr=log,
            text=True,
        )
    announced: list[str] = []
    reader = threading.Thread(target=lambda: announced.append(_first_line(process)), daemon=True)
    reader.start()
    reader.join(ANNOUNCE_SECONDS)
    ready = announced[0] if announced else ""
    if not ready.startswith("serving "):
        process.kill()
        process.wait(timeout=20)
        raise AssertionError(
            f"the daemon did not announce a socket within {ANNOUNCE_SECONDS} s: "
            f"said {ready!r}, wrote {_written(config.parent)!r}"
        )
    return process


class Daemon:
    """A running control plane, and the address it is listening at."""

    def __init__(self, run: Path, process: subprocess.Popen, socket_path: Path) -> None:
        self.run = run
        self.process = process
        self.socket_path = socket_path
        self.policy = run / "policy.toml"
        self.config = run / "daemon.toml"
        self.stopped = False

    def stop(self) -> None:
        """Stop the process, and say so if it had already stopped itself.

        A daemon that exited on its own leaves nothing at the address, so the next dial in
        a case reads as « no such file or directory » — a client's problem standing in for
        a server that died. Its exit status and what it wrote are the only evidence of what
        happened, so they are what this raises.
        """
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                # A daemon that ignores the polite signal is not left running under a
                # directory about to be removed with its socket.
                self.process.kill()
                self.process.wait(timeout=20)
            self.stopped = True
            return
        if self.stopped:
            return
        raise AssertionError(
            f"the daemon exited on its own with status {self.process.returncode}: "
            f"{_written(self.run)!r}"
        )


@pytest.fixture
def daemon() -> Any:
    """A control plane of this case's own, reading the policy this repository ships.

    The run directory is made HERE, under `/tmp`, with a four-character template — never
    under the directory the runner gives a test. Both halves of that matter: `/tmp` is
    short, and the runner's directory is named after the test and costs thirty-two bytes
    of an address whose limit is a hundred and four. The published rule is then asked
    about the composed address, by calling it, before anything binds.

    It is removed afterwards, because a fixture that makes its own directory owns its own
    cleanup: the runner deletes what it created and nothing else.
    """
    # Imported here rather than at module level: a conftest that imported a distribution
    # it might not have would stop a reduced run instead of letting it reduce.
    from sayfirst_contract.binding.http_unix_socket.addresses import refuse_a_long_address

    run = Path(tempfile.mkdtemp(prefix=RUN_PREFIX, dir=RUN_PARENT))
    os.chmod(run, 0o700)
    try:
        policy = run / "policy.toml"
        policy.write_text(_policy_for(principal()), encoding="utf-8")
        os.chmod(policy, 0o600)
        socket_path = run / "daemon.sock"
        # Before it is bound, while the fix is still renaming a leaf. The contract's own
        # check, called — not a length compared against a number written out here.
        refuse_a_long_address(socket_path)
        config = run / "daemon.toml"
        config.write_text(
            "# SPDX-License-Identifier: Apache-2.0\n"
            "[socket]\n"
            'mode = "per_user"\n'
            f'path = "{socket_path}"\n'
            "[policy]\n"
            f'path = "{policy}"\n'
            "[evidence]\n"
            f'path = "{run / "evidence"}"\n',
            encoding="utf-8",
        )
        os.chmod(config, 0o600)
        running = Daemon(run, _launch(config), socket_path)
        try:
            yield running
        finally:
            running.stop()
    finally:
        shutil.rmtree(run, ignore_errors=True)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    for name in ("outbox", "reports", "events"):
        (tmp_path / name).mkdir()
    return tmp_path


@pytest.fixture
def governed(daemon, workspace, monkeypatch):
    """A factory for governed graphs, all pointed at this case's own daemon.

    The boundary module composes its client and its boundary when it is imported, so the
    environment is published first and the package imported fresh afterwards: each case
    gets a boundary pointed at its own daemon and its own runtime directories.
    """
    monkeypatch.setenv("SAYFIRST_SOCKET", str(daemon.socket_path))
    monkeypatch.setenv("SAYFIRST_SCOPE", "local")
    monkeypatch.setenv("SAYFIRST_PRINCIPAL", principal())
    monkeypatch.setenv("DEMO_OUTBOX", str(workspace / "outbox"))
    monkeypatch.setenv("DEMO_REPORTS", str(workspace / "reports"))
    monkeypatch.setenv("DEMO_EVENTS", str(workspace / "events"))
    monkeypatch.setenv("DEMO_DATA", str(REPOSITORY / "demo_data"))
    monkeypatch.setenv("MODEL_MODE", "fixture")

    for module in [m for m in list(sys.modules) if m.startswith("sayfirst_governed_agent_demo")]:
        del sys.modules[module]

    from langgraph.checkpoint.memory import InMemorySaver

    from sayfirst_governed_agent_demo import boundary_setup, governance_stamp
    from sayfirst_governed_agent_demo.agent import GovernedRun
    from sayfirst_governed_agent_demo.demo_events import EventLog
    from sayfirst_governed_agent_demo.graph import build_graph
    from sayfirst_governed_agent_demo.settings import load_settings

    governance_stamp.forget()
    settings = load_settings()

    def build(
        model: Any,
        thread_id: str | None = None,
        required_tools: tuple[str, ...] = (),
    ) -> GovernedRun:
        events = EventLog(colour=False)
        graph = build_graph(
            settings, model, events, checkpointer=InMemorySaver(), required_tools=required_tools
        )
        return GovernedRun(
            app=graph,
            settings=settings,
            events=events,
            thread_id=thread_id or uuid.uuid4().hex,
        )

    build.settings = settings  # type: ignore[attr-defined]
    build.boundary_setup = boundary_setup  # type: ignore[attr-defined]
    yield build

    boundary_setup.close()
    for module in [m for m in list(sys.modules) if m.startswith("sayfirst_governed_agent_demo")]:
        del sys.modules[module]


@pytest.fixture
def records(governed):
    """Every outcome record the boundary made in this case, flushed."""

    def read() -> list[Any]:
        governed.boundary_setup.flush()
        return list(governed.boundary_setup.RECORDS)

    return read


@pytest.fixture
def scripted():
    """Build a scripted model: each entry is a `(tool, arguments)` pair or final text.

    The model is scripted so a case controls which acts the agent PROPOSES. Nothing about
    whether they are permitted is scripted — that is the control plane's answer, and the
    control plane is real in every case here.
    """

    def build(*calls):
        from sayfirst_governed_agent_demo.model import ModelReply, ScriptedModel, ToolCall

        replies = []
        for index, entry in enumerate(calls):
            if isinstance(entry, str):
                replies.append(ModelReply(content=entry))
            else:
                name, arguments = entry
                replies.append(
                    ModelReply(
                        content="",
                        tool_calls=(ToolCall(id=f"call_{index}", name=name, arguments=arguments),),
                    )
                )
        return ScriptedModel(replies=replies)

    return build


def _client(daemon, request, *arguments: str) -> subprocess.CompletedProcess:
    """Run the command a person runs, against this case's daemon.

    A subprocess and not a library call, deliberately: what the documents tell a reader to
    type is what these cases exercise. Nothing here imports the command — this repository
    depends on the contract and the boundary, and the command is a tool.
    """
    from open_packages import client_command, stand_down

    command = client_command()
    if command is None:
        stand_down(
            request,
            "the product command-line interface is not on this machine, and a person "
            "answers a suspended act with it",
        )
    return subprocess.run(
        [command, *arguments, "--scope", "local", "--socket", str(daemon.socket_path)],
        capture_output=True,
        text=True,
    )


@pytest.fixture
def approve(daemon, request):
    def act(approval_ref: str, reason: str = "the report was checked; sending is authorised"):
        done = _client(
            daemon, request, "approvals", "approve", "--approval", approval_ref, "--reason", reason
        )
        assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
        assert "state: approved" in done.stdout, done.stdout
        return done.stdout

    return act


@pytest.fixture
def reject(daemon, request):
    def act(approval_ref: str, reason: str = "not this recipient"):
        done = _client(
            daemon, request, "approvals", "reject", "--approval", approval_ref, "--reason", reason
        )
        assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
        assert "state: rejected" in done.stdout, done.stdout
        return done.stdout

    return act


@pytest.fixture
def evidence(daemon, request):
    """The chain the control plane kept, read the way the documents say to read it.

    `--from` is required by that command and has no default, deliberately: a read of a
    chain names where it starts. One is the beginning of it.
    """

    def read() -> subprocess.CompletedProcess:
        return _client(daemon, request, "evidence", "history", "--from", "1")

    return read


@pytest.fixture
def outbox(workspace):
    def read() -> list[dict]:
        return [json.loads(p.read_text()) for p in sorted((workspace / "outbox").glob("*.json"))]

    return read


def pytest_pycollect_makemodule(module_path, parent):  # type: ignore[no-untyped-def]
    """Collect every test module as one that knows what an absent distribution means."""
    from open_packages import OpenAwareModule

    return OpenAwareModule.from_parent(parent, path=module_path)


def pytest_sessionfinish(session, exitstatus) -> None:  # type: ignore[no-untyped-def]
    """Leave the list of what was not run where `scripts/gate.sh` asked for it."""
    from open_packages import write_report

    write_report()


def pytest_terminal_summary(terminalreporter) -> None:  # type: ignore[no-untyped-def]
    """Say what an absence cost this run, by name and by count.

    A run that skipped four modules and printed « passed » would be article 2's absence
    rendered as a healthy state, whoever was reading it.

    The heading names no particular absence. More than one thing can be missing from a
    machine — the published distributions, or only the command a person answers with — and
    a heading that named the first over a run missing the second would understate what that
    run proved. Each item carries the reason it was given, which is the specific fact.
    """
    from open_packages import NOT_RUN

    if not NOT_RUN:
        return
    terminalreporter.write_sep("=", "checks this run did not make", yellow=True)
    for item in sorted(NOT_RUN, key=lambda entry: (entry.kind, entry.what)):
        terminalreporter.write_line(f"  not run: {item.what} — {item.why}")
    terminalreporter.write_line(
        f"{len(NOT_RUN)} checks were not run. This run proves less than one that could "
        f"make them; `scripts/gate.sh` says what would let it."
    )
