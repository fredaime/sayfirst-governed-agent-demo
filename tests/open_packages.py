# SPDX-License-Identifier: Apache-2.0
"""Which checks the open distributions' absence cost, established by collecting them.

The three distributions this demonstration is built on are published on no index yet, and
they cannot be vendored here. So there are machines where they simply are not present: a
reader who cloned this repository and nothing else, and this project's own CI whenever the
read credential is not set.

A gate that stops dead on those machines proves nothing. A gate that runs what it can and
calls the result an ordinary pass proves less than it says it does. Article 2 forbids the
second in as many words — "an absence … is never rendered as a negative fact, a zero or a
healthy state" — and asks a status surface for three values where a reader might expect two.

So the checks that need nothing are run, and the rest are reported by name. There are two
doors, and both lead here:

* **declared.** A module that needs the open distributions says so in its first statement —
  `require_the_open_packages(__file__, why)` — and is stood down with the reason it gave.
  This is the door for a module whose open imports are inside its own functions or in a
  fixture: such a module imports perfectly well without the distributions and then fails
  one case at a time, at run time, which counts as failures where the truth is « this could
  not run ». Three modules of this repository use it;
* **collected.** A module that imports an open package at module level fails to import, and
  the collector below reads the failure, recognises the absence and skips the module by
  name. Nothing has to remember to list it: a module that grows such an import tomorrow is
  accounted for tomorrow. That is the backstop, and it is why the declared door is not a
  list of modules kept somewhere — it is each module's own sentence about itself.

**Presence is read in exactly one place** (`open_packages_are_installed`), and the gate asks
this module rather than reading the environment a second time.

Three things this refuses to do, and `tests/test_open_packages.py` plants a defect against
each of them, because a mechanism for not running tests is the last mechanism in a
repository that may be trusted on its description:

* it never hides an import failure that is not an absence — a mistyped import, a module this
  repository broke, anything at all — because a gate that swallows those is worse than none;
* it never fires while the distributions are installed. There, a module that cannot import
  one is a failure and stays one;
* it never leaves a check it stopped out of the count, whichever door it came through.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[1]

#: The import packages whose absence this rule reads as « the open distributions are not
#: here ». Named because a distribution that is not installed cannot be asked what it calls
#: itself. The server is among them: the end-to-end tier starts a real daemon, and a run
#: without one proves nothing about this demonstration against a control plane. So is the
#: quickstart launcher its distribution has shipped beside the server since 0.3.0: one
#: distribution, two packages, absent together — and a list that named one of them would be
#: asked to agree with a distribution that provides both.
OPEN_PACKAGES: frozenset[str] = frozenset(
    {"sayfirst_contract", "sayfirst_boundary", "sayfirst_control_plane", "sayfirst_quickstart"}
)

#: The distributions that provide them, in the spelling the project file pins.
OPEN_DISTRIBUTIONS: tuple[str, ...] = (
    "sayfirst-contract",
    "sayfirst-boundary",
    "sayfirst-control-plane",
)

#: The variable the gate uses to ask for the list of what was not run.
REPORT_VARIABLE = "SAYFIRST_GATE_NOT_RUN"

#: Where the command a person answers with is, when it is here.
CLIENT_VARIABLE = "SAYFIRST_CLIENT"


@dataclass(frozen=True)
class NotRun:
    """Something an absence stopped from running, and why.

    `kind` is `module` for a test module collection could not import, and `test` for a
    single case that stood down. Both are checks that did not run; counting only the first
    would make the number smaller than the truth, in the direction that flatters the run.
    """

    what: str
    kind: str
    why: str


#: Filled during collection and during the run; read by the summary and by the report.
NOT_RUN: list[NotRun] = []


def open_packages_are_installed() -> bool:
    for package in sorted(OPEN_PACKAGES):
        try:
            found = importlib.util.find_spec(package)
        except (ImportError, ValueError):
            return False
        if found is None:
            return False
    return True


def client_command() -> str | None:
    """The command a person answers with, or `None` when it is not on this machine."""
    named = os.environ.get(CLIENT_VARIABLE, "").strip()
    if named:
        return named if Path(named).is_file() else None
    return shutil.which("sayfirst")


def absent_open_package(error: BaseException | None) -> str | None:
    """The package whose absence raised `error`, or `None`.

    `None` is the answer that matters, and it is the answer for everything except the one
    case: a `ModuleNotFoundError` for one of the packages themselves. A missing SUBmodule of
    an installed distribution is a broken distribution rather than an absent one, and reads
    as `None` so that it stays a failure.

    The runner wraps a test module's import failure in a collection error raised `from` it,
    so the chain is walked rather than the exception that arrived.
    """
    seen: set[int] = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, ModuleNotFoundError) and error.name in OPEN_PACKAGES:
            return error.name
        error = error.__cause__ or error.__context__
    return None


def record(module_path: Path | str, package: str) -> str:
    """Record a module that was not run, and return the sentence that says why."""
    module = _relative(module_path)
    why = f"it imports {package}"
    NOT_RUN.append(NotRun(module, "module", why))
    return f"the open distributions are absent: {module} {why[len('it ') :]}"


def require_the_open_packages(module_file: str, why: str) -> None:
    """Declare, at module level, that this module needs the open distributions.

    Called as the first statement of a test module that does, BEFORE it imports one:

        require_the_open_packages(__file__, "it drives the published boundary")

    Two things make this the declared door rather than the collected one, and the
    repository has both on purpose. A module that imports an open package at module level
    is caught by `OpenAwareModule` below, which reads the import failure and skips the
    module by name — collected, never listed, and the right backstop for a module that
    grows an import nobody declared. But a module whose open imports live inside its own
    functions imports fine and then fails one case at a time, at run time, and a failure is
    not what « this could not run » means: the count is smaller than the truth and the run
    is red for a reason that is a fact about the machine. This function is what such a
    module says instead, and it is why no test module of this repository needs an open
    import at module level at all.

    The reason travels into the record in the module's own words, because « it starts a
    control plane » tells a reader what the run did not prove and « it imports a package »
    does not.
    """
    if open_packages_are_installed():
        return
    module = _relative(module_file)
    NOT_RUN.append(NotRun(module, "module", why))
    pytest.skip(f"the open distributions are absent: {module} — {why}", allow_module_level=True)


def stand_down(request, why: str) -> None:
    """Stand this case down, and be counted.

    A case that can only run against something this machine does not have is as much a
    check the absence cost as a module that would not import, and the gate counts it as
    one. A plain skip would leave it out of the count and make the reduced run look like it
    proved more than it did.
    """
    NOT_RUN.append(NotRun(request.node.nodeid, "test", why))
    pytest.skip(f"not run: {why}")


def write_report(destination: str | None = None) -> Path | None:
    """Write what was not run where the gate asked for it, one item a line.

    Written even when it is empty: « nothing was skipped » and « the run never got this
    far » are different facts, and the gate reads the difference.
    """
    destination = os.environ.get(REPORT_VARIABLE) if destination is None else destination
    if not destination:
        return None
    path = Path(destination)
    path.write_text(
        "".join(f"{item.kind}\t{item.what}\t{item.why}\n" for item in NOT_RUN), encoding="utf-8"
    )
    return path


def _relative(path: Path | str) -> str:
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(REPOSITORY))
    except ValueError:
        return str(resolved)


class OpenAwareModule(pytest.Module):
    """A test module that says what is absent instead of erroring out."""

    def collect(self):  # type: ignore[no-untyped-def]
        try:
            return super().collect()
        except Exception as error:
            if open_packages_are_installed():
                raise
            package = absent_open_package(error)
            if package is None:
                raise
            pytest.skip(record(self.path, package), allow_module_level=True)
