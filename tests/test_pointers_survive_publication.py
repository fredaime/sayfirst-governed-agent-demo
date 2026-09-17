# SPDX-License-Identifier: Apache-2.0
"""Every address this repository publishes about itself points somewhere a reader can go.

Two halves, and the second is the one a package page shows a stranger.

A **reader-facing document** may link to any of the three public repositories of this
project and to nothing else under that account. Each is created fresh in the act that
publishes it, and the order is the one `docs/publication-checklist.md` gives — the control
plane, then the command, then this demonstration, since a repository published before the
distributions it pins is one a reader cannot install from. The three are written down here
rather than searched for, so that each act has a name to check against.

A **project URL** is narrower still: `[project.urls]` is the one place a distribution sends
somebody who holds nothing of this project, rendered on an index page before anybody
installs anything, so every value there is this repository's own public address.

The rule constrains the OPERATION and not the name. A local directory path is not a claim
that a reader can open a page, and the gate has to be able to say which checkout it reads.
What is refused is a **URL**: the form that promises somewhere to go.

The name of the repository this project has decided never to publish is assembled from
pieces below, so that this file is not an occurrence of what the vocabulary guard refuses.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[1]

#: The account the three public repositories live under.
ACCOUNT = "https://github.com/fredaime"

#: The three, and the one this distribution is. The two products are published before this
#: repository, at the tag it pins; this one is created by the act that publishes this tree.
PUBLIC_DEMO = f"{ACCOUNT}/sayfirst-governed-agent-demo"
PUBLIC_CLIENT = f"{ACCOUNT}/sayfirst-cli"
PUBLIC_CONTROL_PLANE = f"{ACCOUNT}/sayfirst-control-plane"
PUBLIC = (PUBLIC_DEMO, PUBLIC_CLIENT, PUBLIC_CONTROL_PLANE)

#: A hyperlink in any of the forms these documents use: a bare URL, a link target, an
#: autolink. The scheme is what makes it a promise that something is reachable, so the
#: scheme is what this matches — a relative path is deliberately outside it.
_URL = re.compile(r"https?://[^\s)>\]\"']+")


def _reader_facing() -> list[Path]:
    """Every document a person outside the project reads.

    Walked, never enumerated: a governance file added next month is covered without anyone
    remembering to add it here. Test sources are excluded — this module has to be able to
    name the thing it forbids.
    """
    found = [path for path in sorted(REPOSITORY.glob("*.md")) if path.is_file()]
    found += [path for path in sorted(REPOSITORY.glob("docs/**/*.md")) if path.is_file()]
    notice = REPOSITORY / "NOTICE"
    if notice.is_file():
        found.append(notice)
    return found


DOCUMENTS = _reader_facing()


def project_urls(root: Path) -> dict[str, str]:
    """The `[project.urls]` table of the distribution at `root`, or an empty one."""
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return dict(project.get("urls") or {})


def test_the_walk_finds_the_documents_this_rule_is_about() -> None:
    """ANTI-VACUITY. A glob that matched nothing would make every assertion below pass by
    absence, which is the failure mode this project has met often enough to have a standing
    rule against it."""
    names = {path.name for path in DOCUMENTS}
    assert len(DOCUMENTS) >= 4, f"only {len(DOCUMENTS)} reader-facing documents found"
    assert "README.md" in names


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda p: p.name)
def test_no_reader_facing_link_points_outside_the_public_repositories(path: Path) -> None:
    """A link under this account that is not one of the three resolves for nobody."""
    text = path.read_text(encoding="utf-8")
    offenders = [
        url for url in _URL.findall(text) if url.startswith(ACCOUNT) and not url.startswith(PUBLIC)
    ]
    assert not offenders, (
        f"{path.relative_to(REPOSITORY)} links to a repository this project does not "
        f"publish: {offenders}. Name it without a URL until a public one exists, and "
        f"write the URL in the act that creates it."
    )


def test_every_published_url_of_this_distribution_is_this_repositorys_own() -> None:
    """A package page is read by people who hold nothing of this project."""
    urls = project_urls(REPOSITORY)
    assert set(urls) == {"Repository", "Documentation", "Changelog"}, urls
    for name, url in urls.items():
        assert url.startswith(PUBLIC_DEMO), (name, url)


def test_the_rule_fires_on_a_pointer_to_a_repository_that_is_never_published(
    tmp_path: Path,
) -> None:
    """WATCHED FIRING, through the same two readers the real tree is read through. A rule
    whose only evidence is that it passes today would also pass if it had stopped
    applying."""
    never = "sf" + "-control-plane-lt"
    document = f"[the constitution]({ACCOUNT}/{never}/blob/main/CONSTITUTION.md)"
    offenders = [
        url
        for url in _URL.findall(document)
        if url.startswith(ACCOUNT) and not url.startswith(PUBLIC)
    ]
    assert offenders, "the document reader saw nothing: the probe proves nothing"

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "planted"\nversion = "0.0.0"\n'
        "[project.urls]\n"
        f'Repository = "{ACCOUNT}/{never}"\n',
        encoding="utf-8",
    )
    planted = project_urls(tmp_path)
    assert planted, "the project reader saw no table: the probe proves nothing"
    assert not all(url.startswith(PUBLIC_DEMO) for url in planted.values())


def test_the_rule_leaves_a_local_checkout_path_alone() -> None:
    """WATCHED NOT FIRING. The gate documents the checkout it reads and must keep being
    able to: a detector that flagged every mention of a directory would pass the probe
    above and mean nothing."""
    line = "$ SAYFIRST_CONTRACT_SOURCE=../" + "sf" + "-control-plane-lt ./scripts/gate.sh"
    assert not [url for url in _URL.findall(line) if url.startswith(ACCOUNT)]
