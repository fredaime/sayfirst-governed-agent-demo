# SPDX-License-Identifier: Apache-2.0
"""Article 16: a release with no changelog entry is red before anybody tags it.

The guard reads the FIRST heading that is a version. An « Unreleased » section sits above
them and is skipped on purpose: ordinary development appends to it, and a guard that
demanded a release heading at the top would be red on every working branch and would teach
people to ignore it.

This repository publishes no distribution to an index — it is cloned and run — so what the
version and this file are for is a person deciding whether the copy in front of them is the
one the documents describe.

It needs no installed package, so it speaks in a reduced run too.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[1]
CHANGELOG = REPOSITORY / "CHANGELOG.md"

sys.path.insert(0, str(REPOSITORY / "scripts"))

from release_version import main, release_version  # noqa: E402

#: A release section's heading: two hashes, a semantic version, nothing else required.
RELEASE_HEADING = re.compile(r"^## (\d+\.\d+\.\d+)\b", re.MULTILINE)


def top_release(changelog: str) -> str | None:
    """The version of the newest release section, or None when there is none."""
    found = RELEASE_HEADING.search(changelog)
    return found.group(1) if found else None


def test_the_changelog_names_the_version_this_tree_would_release() -> None:
    assert top_release(CHANGELOG.read_text(encoding="utf-8")) == release_version(REPOSITORY)


def test_an_unreleased_section_above_the_release_is_not_mistaken_for_one() -> None:
    """WATCHED NOT FIRING."""
    assert (
        top_release("# Changelog\n\n## Unreleased\n\n- a change\n\n## 0.2.0\n\n- shipped\n")
        == "0.2.0"
    )


def test_a_changelog_with_no_entry_for_the_version_is_caught() -> None:
    """WATCHED FIRING."""
    assert top_release("# Changelog\n\n## Unreleased\n\n- a change\n") is None
    assert top_release("# Changelog\n\n## 0.1.0\n\n- shipped\n") != release_version(REPOSITORY)


def test_a_project_file_with_no_version_is_refused(tmp_path: Path) -> None:
    """WATCHED FIRING on the reader itself: a project file with no version is a REFUSAL,
    named after the file that declares none — never a `KeyError` surfacing from the middle
    of a release step, which would report a crash rather than a refusal and name nothing a
    reader can go and open. `main` catches that refusal the same way it catches any other:
    one sentence on stderr and exit code 1, not a traceback."""
    project_file = tmp_path / "pyproject.toml"
    project_file.write_text('[project]\nname = "sayfirst-governed-agent-demo"\n', encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape(str(project_file))):
        release_version(tmp_path)
    assert main(["--expect", "0.2.0", "--repository", str(tmp_path)]) == 1
