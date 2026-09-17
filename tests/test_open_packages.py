# SPDX-License-Identifier: Apache-2.0
"""The rule that decides which checks the open distributions carry, held to its edges.

`tests/open_packages.py` lets a run continue on a machine where the contract, the boundary
and the server are not installed, reporting by name what it could not run. That is a
mechanism for *not running tests*, so it is the last mechanism in this repository that may
be trusted on its description. Every claim it makes is planted against here:

* the modules it does not run are the ones that said they needed the distributions or that
  collection could not import — and the set is read off a real run, not off a list;
* a run it lets through still runs tests, and a run with the distributions installed runs
  strictly more of them;
* an import failure that is not an absence stays a failure;
* a missing submodule of an installed distribution is a broken distribution, not an absent
  one;
* the reason pytest wraps an import failure in is walked, not the exception that arrived;
* the packages the rule names are the ones those distributions actually provide;
* a check stopped by either door is counted, and the report is written only when asked.

The absence is arranged by HIDING packages from a child interpreter rather than by
uninstalling anything: the import machinery is asked first and answers with the
`ModuleNotFoundError` a real absence gives, carrying the same `name`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

import pytest

from open_packages import (
    NOT_RUN,
    OPEN_DISTRIBUTIONS,
    OPEN_PACKAGES,
    absent_open_package,
    client_command,
    open_packages_are_installed,
    stand_down,
    write_report,
)

REPOSITORY = Path(__file__).resolve().parents[1]

#: A `sitecustomize` that makes named top-level packages unimportable to a child
#: interpreter, the way an uninstalled distribution is.
_HIDER = """\
import os
import sys
from importlib.abc import MetaPathFinder


class _Absent(MetaPathFinder):
    def __init__(self, names):
        self.names = names

    def find_spec(self, fullname, path=None, target=None):
        top = fullname.split(".")[0]
        if top in self.names:
            raise ModuleNotFoundError(f"No module named {top!r}", name=top)
        return None


hidden = {name for name in os.environ.get("SAYFIRST_TEST_HIDE", "").split(",") if name}
if hidden:
    sys.meta_path.insert(0, _Absent(hidden))
"""


#: A module planted under `tests/` for the length of one child run: it imports an open
#: package at module level and declares nothing, which is the shape the collected door
#: exists for and the one shape no module of this repository has. Written and removed by the
#: case below, which is why it is a string here rather than a file.
_UNDECLARED_MODULE = """\
# SPDX-License-Identifier: Apache-2.0
\"\"\"A module that imports an open package at module level and says nothing about it.

Planted by `tests/test_open_packages.py` for one child run, and removed again.
\"\"\"

from sayfirst_contract.decisions import Reason


def test_the_planted_module_would_run_where_the_distributions_are_installed() -> None:
    assert Reason is not None
"""

#: Where that module is written. Named once, because the case asserts on the same path it
#: planted and a second spelling is how the two stop agreeing.
_UNDECLARED_PATH = "tests/test_a_module_that_declares_nothing.py"


def _is_a_reason(why: str) -> bool:
    """Whether a recorded reason is one of the two shapes this rule documents.

    `assert why` passes on « x ». What the gate prints, and what a reader decides from, is
    this string: either the package a module could not import, in the collected door's own
    words, or a sentence from the module saying what a run without it does not prove.
    """
    if why.removeprefix("it imports ") in OPEN_PACKAGES:
        return True
    return why.startswith("it ") and len(why.split()) >= 6


class Collected:
    """What one child `pytest --collect-only` run collected, and what it did not."""

    def __init__(self, completed: subprocess.CompletedProcess[str], report: Path) -> None:
        self.completed = completed
        self.output = completed.stdout + completed.stderr
        self.tests = [line for line in completed.stdout.splitlines() if "::" in line]
        self.not_run = [
            line.split("\t") for line in report.read_text(encoding="utf-8").splitlines() if line
        ]
        self.modules = {what: why for kind, what, why in self.not_run if kind == "module"}


def collect(tmp_path: Path, hide: tuple[str, ...] = ()) -> Collected:
    """Collect this repository's tests in a child interpreter, hiding what is named."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "sitecustomize.py").write_text(_HIDER, encoding="utf-8")
    report = tmp_path / "not-run"
    report.write_text("", encoding="utf-8")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(tmp_path), *([environment["PYTHONPATH"]] if environment.get("PYTHONPATH") else [])]
    )
    environment["SAYFIRST_TEST_HIDE"] = ",".join(hide)
    environment["SAYFIRST_GATE_NOT_RUN"] = str(report)
    completed = subprocess.run(
        (sys.executable, "-m", "pytest", "-q", "--collect-only", "-p", "no:cacheprovider"),
        cwd=REPOSITORY,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    return Collected(completed, report)


def test_the_modules_the_open_distributions_carry_are_the_ones_a_real_run_stood_down(
    tmp_path: Path,
) -> None:
    """The set comes off a real run: hide the three packages, and read what was skipped."""
    run = collect(tmp_path, hide=tuple(sorted(OPEN_PACKAGES)))

    assert run.completed.returncode == 0, run.output
    assert run.modules, "the distributions were hidden and no module said it needed them"
    for module, why in run.modules.items():
        assert (REPOSITORY / module).is_file(), module
        assert _is_a_reason(why), f"{module} was stood down with {why!r}"
    # Anti-vacuity: a rule that skipped everything would satisfy the lines above and prove
    # nothing at all.
    assert run.tests, "the distributions were hidden and nothing was left to run"


def test_a_module_that_imports_an_open_package_without_saying_so_is_stood_down_by_name(
    tmp_path: Path,
) -> None:
    """The collected door, planted — the backstop for a module nobody declared.

    Every test module of this repository takes the DECLARED door today, so the door this
    case exercises has no instance here and would otherwise be held by its description
    alone, which is the one thing a mechanism for not running tests may never be held by. A
    module that grows a module-level open import tomorrow is exactly what it catches, and
    the reason it records is read for its documented shape rather than for being a non-empty
    string: that sentence is what the gate prints and what a reader acts on.
    """
    planted = REPOSITORY / _UNDECLARED_PATH
    assert not planted.exists(), f"{planted} is not this case's to write"
    planted.write_text(_UNDECLARED_MODULE, encoding="utf-8")
    try:
        run = collect(tmp_path, hide=tuple(sorted(OPEN_PACKAGES)))
    finally:
        planted.unlink(missing_ok=True)

    assert run.completed.returncode == 0, run.output
    stood_down = run.modules.get(_UNDECLARED_PATH)
    assert stood_down is not None, f"the planted module was not recorded: {run.not_run}"
    assert stood_down.removeprefix("it imports ") in OPEN_PACKAGES, stood_down
    # And it was skipped rather than run: a module that could not import has no cases here.
    assert not [name for name in run.tests if _UNDECLARED_PATH in name], run.tests


def test_the_distributions_installed_skip_nothing_and_collect_strictly_more(
    request, tmp_path: Path
) -> None:
    """The modules it skips do hold cases, and the rule stands down when it must."""
    if not open_packages_are_installed():
        stand_down(request, "this comparison needs a run with them and one without")

    absent = collect(tmp_path / "hidden", hide=tuple(sorted(OPEN_PACKAGES)))
    present = collect(tmp_path / "present")

    assert present.completed.returncode == 0, present.output
    assert present.not_run == []
    assert len(present.tests) > len(absent.tests)


def test_an_import_failure_that_is_not_an_absence_stays_a_failure(tmp_path: Path) -> None:
    """The planted defect: hide this repository's OWN package, and the run must go red.

    A mechanism that turns « this module would not import » into « not run » is one typo
    away from turning a broken repository into a quiet green. So the rule is asked about a
    module it must not recognise, and the child run has to fail, naming what was missing.
    """
    run = collect(tmp_path, hide=("sayfirst_governed_agent_demo",))

    assert run.completed.returncode != 0, run.output
    assert "sayfirst_governed_agent_demo" in run.output
    assert not [entry for entry in run.not_run if "sayfirst_governed_agent_demo" in entry[1]]


def test_a_missing_submodule_of_an_installed_distribution_is_not_an_absence() -> None:
    """A broken distribution is not an absent one, and only the second is excusable."""
    submodule = ModuleNotFoundError("x", name="sayfirst_contract.client")
    neighbour = ModuleNotFoundError("x", name="sayfirst_contractor")
    assert absent_open_package(submodule) is None
    assert absent_open_package(neighbour) is None
    assert absent_open_package(ImportError("cannot import name 'Answered'")) is None
    assert absent_open_package(None) is None


def test_the_rule_reads_the_cause_the_runner_wraps_an_import_failure_in() -> None:
    """The runner raises its own error *from* the `ImportError`; the chain is walked."""
    cause = ModuleNotFoundError("No module named 'sayfirst_contract'", name="sayfirst_contract")
    try:
        try:
            raise cause
        except ModuleNotFoundError as error:
            raise RuntimeError("ImportError while importing test module") from error
    except RuntimeError as wrapper:
        assert absent_open_package(wrapper) == "sayfirst_contract"


def test_the_packages_the_rule_names_are_the_ones_those_distributions_provide(request) -> None:
    """Named by hand because an absent distribution cannot be asked; checked here."""
    provided: set[str] = set()
    for name in OPEN_DISTRIBUTIONS:
        try:
            found = _top_level_packages(name)
        except PackageNotFoundError:
            stand_down(request, f"{name} is not installed, so it cannot be asked")
        assert found, f"{name} is installed and provides no top-level package"
        provided |= found
    assert provided == set(OPEN_PACKAGES)


def test_an_unasked_report_is_not_written(tmp_path: Path) -> None:
    """The gate asks for the list by naming a path; nothing else writes a file."""
    assert write_report("") is None
    written = write_report(str(tmp_path / "asked"))
    assert written is not None and written.exists()


def test_a_case_that_stands_down_is_counted_too(request) -> None:
    """A skip left out of the count would shrink the number that matters.

    The planted entry is removed again: this case runs inside the very run whose count it
    is checking, and a count with a plant in it is the defect twice.
    """
    before = len(NOT_RUN)
    with pytest.raises(pytest.skip.Exception):
        stand_down(request, "planted")
    try:
        assert len(NOT_RUN) == before + 1
        assert NOT_RUN[-1].kind == "test"
        assert NOT_RUN[-1].why == "planted"
        assert NOT_RUN[-1].what.endswith("test_a_case_that_stands_down_is_counted_too")
    finally:
        del NOT_RUN[before:]


def test_the_command_a_person_answers_with_is_read_from_the_variable_or_the_path(
    tmp_path: Path, monkeypatch
) -> None:
    """The other absence this gate reports, and the one that decides the approval cases.

    A named file that is not there is not the command: a run that treated the variable as
    proof would try to execute a path and fail with the kind of error nobody reads as « the
    tool is missing ».
    """
    monkeypatch.setenv("SAYFIRST_CLIENT", str(tmp_path / "not-here"))
    assert client_command() is None

    pretend = tmp_path / "sayfirst"
    pretend.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    monkeypatch.setenv("SAYFIRST_CLIENT", str(pretend))
    assert client_command() == str(pretend)


def _top_level_packages(name: str) -> set[str]:
    """The top-level import packages a distribution installs, read from its own files.

    A top-level directory counts when the distribution installs that directory's OWN
    `__init__.py`, and a top-level module counts by itself. The server distribution is why
    the first half is written that way rather than by reading the first path component of
    every file: it also installs modules under a namespace package that several
    distributions of this project contribute to, which carries no `__init__.py` of its own
    and belongs to none of them. Such a package is not one whose absence could mean « the
    open distributions are not here », so it is not one this rule names — and a reading
    that counted it would fail this case against a distribution that is exactly right.
    """
    installed = distribution(name)
    declared = installed.read_text("top_level.txt")
    if declared:
        return {line.strip() for line in declared.splitlines() if line.strip()}
    files = installed.files or ()
    return {
        file.parts[0]
        for file in files
        if len(file.parts) == 2
        and file.parts[1] == "__init__.py"
        and not file.parts[0].endswith((".dist-info", ".data"))
    } | {
        file.parts[0].removesuffix(".py")
        for file in files
        if len(file.parts) == 1 and file.parts[0].endswith(".py")
    }
