# SPDX-License-Identifier: Apache-2.0
"""Article 0: the decided name is the only name this repository declares.

The product name was decided on 2026-09-04 and this repository was written before it.
What that leaves is a hole a later commit falls into: a retired prefix can be typed again
from memory or arrive in a merge, and a placeholder written three ways — angle-bracketed
in prose, hyphenated for a distribution, underscored for an import package — is a further
hazard the other open repositories of this project have already met.

The last thing guarded here is not a placeholder. A blanket substring replacement in this
project once turned an ordinary English word into one with the brand glued inside it,
across twelve files, and was caught by a person reading the diff and by no test. So the
decided name is required to stand as a word.

Every pattern is assembled from pieces, so this file is not itself the occurrence it
forbids.

**The retired prefix is read in a PATH and in a declared name, not in a file's body.** A
path and a declared name are names this repository chooses; a name it imports is a
question about the direction of a dependency, and `tests/test_public_vocabulary.py` owns
that. Two files, one rule each.

It needs no installed package, so it speaks before this repository has an environment.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from collections.abc import Iterator
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]

#: The name the operator decided on 2026-09-04. One word, so the distribution prefix, the
#: import prefix and the environment prefix are the same string.
DECIDED_NAME = "sayfirst"

#: What this distribution is called, and the command it installs. Deliberately not the
#: bare decided name: that belongs to the product command-line interface's distribution.
DISTRIBUTION = f"{DECIDED_NAME}-governed-agent-demo"
IMPORT_PACKAGE = f"{DECIDED_NAME}_governed_agent_demo"

#: Directories a non-git enumeration must not walk into.
UNTRACKED_DIRECTORIES = frozenset(
    {
        ".git",
        ".venv",
        ".venv-reduced",
        ".wheelhouse",
        "__pycache__",
        ".ruff_cache",
        ".pytest_cache",
        "dist",
        "runtime",
    }
)

#: The retired prefix, either separator, either case: the prefix the operator retired
#: because those two letters are another project's command. Bounded on the left so a
#: name that merely contains them is not an occurrence.
_RETIRED = "sf"
RETIRED_PREFIX = re.compile(r"(?<![A-Za-z0-9])" + _RETIRED + r"[-_][A-Za-z0-9]", re.IGNORECASE)

#: The retired placeholder, in each of the three ways this project wrote it.
_PLACEHOLDER_STEM = "oss" + "[-_]" + "brand"
PLACEHOLDER = re.compile("<?" + _PLACEHOLDER_STEM + ">?", re.IGNORECASE)

#: The name a branch of another repository of this project carried for one day.
_RETIRED_CANDIDATE = "man" + "dat"
RETIRED_CANDIDATE = re.compile(
    r"\b" + _RETIRED_CANDIDATE + r"(?![A-Za-z])|\b" + _RETIRED_CANDIDATE + r"[-_]",
    re.IGNORECASE,
)

#: The decided name with a letter welded to it — what a blanket replacement leaves behind.
GLUED_NAME = re.compile("(?<![A-Za-z])" + DECIDED_NAME + "(?=[A-Za-z])", re.IGNORECASE)

#: Read in a path AND in a file's body.
PATTERNS = {
    "placeholder": PLACEHOLDER,
    "retired candidate": RETIRED_CANDIDATE,
    "the decided name glued into a word": GLUED_NAME,
}

#: Read in a path only, for the reason the module docstring gives.
PATH_PATTERNS = {"the retired prefix in a path": RETIRED_PREFIX}

#: An environment variable of this repository's own, in the retired spelling.
RETIRED_ENVIRONMENT = re.compile(r"(?<![A-Za-z0-9_])" + _RETIRED.upper() + r"_[A-Z][A-Z0-9_]*")


def _tracked_files(root: Path) -> list[Path]:
    """Every file this repository would publish, as repository-relative paths."""
    if (root / ".git").exists() and shutil.which("git") is not None:
        listed = subprocess.run(
            ("git", "ls-files", "-z"), cwd=root, capture_output=True, text=True, check=True
        ).stdout
        return [Path(name) for name in listed.split("\0") if name]
    return sorted(
        item.relative_to(root)
        for item in root.rglob("*")
        if item.is_file() and not UNTRACKED_DIRECTORIES & set(item.relative_to(root).parts)
    )


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def occurrences(root: Path) -> Iterator[tuple[Path, str, str]]:
    """Yield (file, which rule, matched text) for everything still to replace."""
    for item in _tracked_files(root):
        content = _read(root / item)
        for label, pattern in PATTERNS.items():
            in_path = pattern.search(item.as_posix())
            if in_path is not None:
                yield item, label, in_path.group(0)
            if content is not None:
                in_content = pattern.search(content)
                if in_content is not None:
                    yield item, label, in_content.group(0)
        for label, pattern in PATH_PATTERNS.items():
            found = pattern.search(item.as_posix())
            if found is not None:
                yield item, label, found.group(0)
        if content is not None:
            retired = RETIRED_ENVIRONMENT.search(content)
            if retired is not None:
                yield item, "an environment variable in the retired spelling", retired.group(0)


def _project(root: Path) -> dict[str, object]:
    return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_no_tracked_file_carries_a_retired_name() -> None:
    """Article 0: every occurrence is replaced, and none has come back."""
    tracked = _tracked_files(REPOSITORY)
    # Anti-vacuity floor: an enumeration that found nothing cannot pass.
    assert len(tracked) >= 20, tracked
    assert sorted(set(occurrences(REPOSITORY))) == []


def test_the_distribution_the_command_and_the_package_carry_the_decided_name() -> None:
    """A guard that only forbids proves nothing about what replaced the retired name."""
    project = _project(REPOSITORY)
    name, scripts = project["name"], project["scripts"]
    assert isinstance(name, str) and isinstance(scripts, dict)
    assert name == DISTRIBUTION, name
    assert not name.startswith(f"{_RETIRED}-"), name
    # The bare decided name is the product command-line interface's, not this demo's.
    assert set(scripts) == {DISTRIBUTION}, scripts
    assert DECIDED_NAME not in set(scripts), scripts
    assert (REPOSITORY / "src" / IMPORT_PACKAGE).is_dir()


def test_the_guard_catches_each_spelling_it_exists_to_catch(tmp_path: Path) -> None:
    """Every example is invented, one planted file at a time, in a tree of its own."""
    planted = tmp_path / "planted.md"
    for character in ("-", "_"):
        for text in (
            "oss" + character + "brand",
            "<" + "oss" + character + "brand" + ">",
            ("oss" + character + "brand").upper(),
        ):
            planted.write_text(f"The prefix is {text} here.\n", encoding="utf-8")
            assert list(occurrences(tmp_path)) == [(Path("planted.md"), "placeholder", text)], text

    for text in (_RETIRED_CANDIDATE, f"{_RETIRED_CANDIDATE}-cli"):
        planted.write_text(f"Installed as {text} once.\n", encoding="utf-8")
        assert [item[1] for item in occurrences(tmp_path)] == ["retired candidate"], text

    for text in (f"{DECIDED_NAME}ory", f"{DECIDED_NAME}Ory"):
        planted.write_text(f"This field is {text}.\n", encoding="utf-8")
        assert [item[1] for item in occurrences(tmp_path)] == [
            "the decided name glued into a word"
        ], text

    planted.write_text(f"The token is {_RETIRED.upper()}" + "_TOKEN here.\n", encoding="utf-8")
    assert [item[1] for item in occurrences(tmp_path)] == [
        "an environment variable in the retired spelling"
    ]
    planted.unlink()

    at_path = tmp_path / "src" / (_RETIRED + "_governed_agent_demo")
    at_path.mkdir(parents=True)
    (at_path / "__init__.py").write_text("", encoding="utf-8")
    assert [item[1] for item in occurrences(tmp_path)] == ["the retired prefix in a path"]
    shutil.rmtree(tmp_path / "src")


def test_the_guard_leaves_the_names_this_repository_does_carry_alone(tmp_path: Path) -> None:
    """WATCHED NOT FIRING.

    A guard that fired on the decided name itself, or on the ordinary English words a
    blanket replacement once mangled, would be turned off within a week, and a guard
    nobody runs holds nothing.
    """
    planted = tmp_path / "innocent.md"
    planted.write_text(
        "Reading the diff is mandatory; the review mandates it, and it was mandated.\n"
        f"The distribution is {DISTRIBUTION}, the package {IMPORT_PACKAGE}, "
        f"the variable {DECIDED_NAME.upper()}_SOCKET.\n",
        encoding="utf-8",
    )
    assert list(occurrences(tmp_path)) == []
