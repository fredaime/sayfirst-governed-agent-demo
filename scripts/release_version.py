#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The one reader of « the version this tree carries ».

This repository builds one distribution, so the reading is short; it is a module rather
than two inline readings for the reason the other open repositories' is — the changelog
guard and a person checking a copy must agree about the version, and a version spelled
twice is a version that will eventually be spelled two ways.

    python scripts/release_version.py
    python scripts/release_version.py --expect 0.3.0

It needs nothing beyond the standard library's TOML reader, so it runs the same way under
a bare interpreter as it does inside the gate's environment.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]


def distribution_versions(repository: Path) -> dict[str, str]:
    """The distribution this repository builds, and the version it carries.

    Raises `ValueError` naming the project file when it declares no version. A project
    file with no `version` is a mistake somebody made, not a release candidate, and the
    reading has to say which file it read: the alternative is a `KeyError` from the middle
    of a release step, which reports a crash rather than a refusal and names nothing a
    reader can go and open.
    """
    project_file = repository / "pyproject.toml"
    project = tomllib.loads(project_file.read_text(encoding="utf-8"))["project"]
    if "version" not in project:
        raise ValueError(f"{project_file} declares no version, so this tree has none to carry")
    return {project["name"]: project["version"]}


def release_version(repository: Path) -> str:
    """The version this tree carries.

    Raises `ValueError` when two distributions disagree, so a caller gets a refusal rather
    than a number that is true of only one of them. One distribution here today; the shape
    is the one the other repositories use, and it costs nothing.
    """
    versions = distribution_versions(repository)
    distinct = sorted(set(versions.values()))
    if len(distinct) != 1:
        disagreeing = ", ".join(f"{name} {version}" for name, version in sorted(versions.items()))
        raise ValueError(f"the distributions carry more than one version: {disagreeing}")
    return distinct[0]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="the version this tree carries")
    parser.add_argument("--expect", default=None, help="fail unless this is the version")
    parser.add_argument("--repository", type=Path, default=REPOSITORY)
    arguments = parser.parse_args(argv)
    try:
        version = release_version(arguments.repository)
    except ValueError as problem:
        print(f"release_version: {problem}", file=sys.stderr)
        return 1
    if arguments.expect is not None and arguments.expect != version:
        print(
            f"release_version: you named {arguments.expect} and this tree carries {version}",
            file=sys.stderr,
        )
        return 1
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
