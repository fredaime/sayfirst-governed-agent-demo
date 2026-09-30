# SPDX-License-Identifier: Apache-2.0
"""Article 2: no file says the distributions are unpublished; they are on the index."""

from __future__ import annotations

import re
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]

#: The sentences the pages carried while the distributions were unpublished, in the shapes
#: they were actually written. Widened each time a page was found still saying one of them:
#: the last four came off the publication checklist, which predicted what publication would
#: retire and was read as a description long after it stopped being a prediction.
STALE = re.compile(
    r"published on no index|once it is published|not published yet|once they are published"
    r"|exists on any index|published nowhere|not public yet|publication retires"
    r"|the reduced mode goes",
    re.IGNORECASE,
)
FILES = [
    *REPOSITORY.glob("scripts/**/*.sh"),
    *REPOSITORY.glob("docs/*.md"),
    REPOSITORY / "README.md",
    REPOSITORY / ".env.example",
    REPOSITORY / ".github" / "workflows" / "ci.yml",
]


def test_nothing_says_the_distributions_are_unpublished() -> None:
    stale = [
        f"{path.relative_to(REPOSITORY)}:{number}: {line.strip()}"
        for path in FILES
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if STALE.search(line)
    ]
    assert stale == [], "\n".join(stale)


def test_the_rule_fires_on_the_sentences_the_pages_used_to_carry() -> None:
    """WATCHED FIRING, on the shapes the checklist carried before it was rewritten.

    A rule whose only evidence is that it passes today would also pass if it had stopped
    applying; these are the sentences it was widened to catch, and the first two are the
    ones it did not catch until it was.
    """
    for sentence in (
        "neither the contract nor the command exists on any index, so the gate is told",
        "a fork gets a reduced gate because the distributions are published nowhere.",
        "their names are not this repository's to publish and their content is not public yet.",
        "Publication retires both arrangements, and until it does,",
        "The reduced mode goes too: the distributions are no longer absent anywhere,",
        "the daemon is published on no index yet",
    ):
        assert STALE.search(sentence), sentence
