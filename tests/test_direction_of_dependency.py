# SPDX-License-Identifier: Apache-2.0
"""Article 14: this demonstration points in no server direction and imports no client.

One rule, in one file. It depends on the published contract and the published boundary and
on nothing else this project publishes: not the control plane's own distribution, which is
the SERVER — a separate process this program speaks to over a socket and never imports —
and not the product command-line interface, which is a command a person types.

The server's distribution IS installed, and calling it « test-only » would understate where it
is used: `./scripts/start-control-plane.sh` runs its daemon as a separate process during
development, and the end-to-end tier starts one of its own. What is genuinely test-only is
nothing about it — what is true of it everywhere is that it is a PROGRAM this repository runs
and never a module it imports, reached as a process and an address. So it is declared in a
group of its own rather than among the runtime dependencies, and the difference between
« installed beside the program » and « imported by the program » is the whole of what this
file holds.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
SOURCE = REPOSITORY / "src"

#: What this demonstration runs on, exactly.
RUNTIME = [
    "langgraph>=1.0,<2.0",
    "httpx>=0.27",
    "sayfirst-contract==0.3.0",
    "sayfirst-boundary==0.3.0",
]

#: What it never imports, whatever is installed beside it.
NEVER_IMPORTED = ("sayfirst_control_plane", "sayfirst_cli")


def _project() -> dict[str, object]:
    return tomllib.loads((REPOSITORY / "pyproject.toml").read_text(encoding="utf-8"))


def imports_of(root: Path) -> set[str]:
    """Every top-level module name imported anywhere under `root`."""
    imported: set[str] = set()
    sources = sorted(root.rglob("*.py"))
    assert sources, f"no module found under {root}: this rule would pass by absence"
    for source in sources:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
    return imported


def test_this_demonstration_depends_on_the_contract_and_the_boundary_and_nothing_else() -> None:
    project = _project()["project"]
    assert project["dependencies"] == RUNTIME, project["dependencies"]


def test_the_server_is_declared_apart_and_the_client_is_no_dependency_at_all() -> None:
    document = _project()
    groups = document["dependency-groups"]
    assert groups["e2e"] == ["sayfirst-control-plane==0.3.0"], groups["e2e"]
    declared = [requirement for group in groups.values() for requirement in group] + list(
        document["project"]["dependencies"]
    )
    assert not [item for item in declared if item.startswith("sayfirst-cli")], declared
    # A path-resolved source is how a published distribution comes to depend on somebody's
    # working tree. There is none here, and that is the point of the pins above.
    assert "uv" not in document.get("tool", {}), document.get("tool", {}).keys()


def test_nothing_this_program_ships_imports_the_server_or_the_client() -> None:
    imported = imports_of(SOURCE)
    for name in NEVER_IMPORTED:
        assert name not in imported, name
    # Anti-vacuity: the reader has to be reading the modules that matter.
    assert {"sayfirst_boundary", "sayfirst_contract"} <= imported, imported


def test_the_reader_catches_an_import_that_would_break_the_rule(tmp_path: Path) -> None:
    """WATCHED FIRING. A rule whose only evidence is that it passes today would also pass
    if it had stopped reading anything."""
    planted = tmp_path / "package"
    planted.mkdir()
    (planted / "module.py").write_text(
        "from " + "sayfirst_control_plane" + " import bootstrap\n", encoding="utf-8"
    )
    assert "sayfirst_control_plane" in imports_of(planted)
