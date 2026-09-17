# SPDX-License-Identifier: Apache-2.0
"""Article 14 at repository scope: what ships names nothing a reader cannot reach.

This repository is public by intent, so every tracked file's content is the thing that gets
published and a docstring is as published as a paragraph of `README.md`. Two families are
refused here.

**Names of things outside this repository.** The product this demonstration was built
beside, the repositories it was built from, the packages it used to depend on and the verbs
of the command that used to write its boundary. A reader outside the project cannot open
any of them, and a sentence naming one tells them nothing about the behaviour in front of
them. These are a deny-list, which is unusual and is the right shape here: this repository
was written before the open product had a name, the names are few, and they are exactly
what a careless rename leaves behind. Beside the list stands one detector that reads the
CONSTRUCTION rather than a name: a sentence that calls a source closed and then says what
it is called. That refuses a source this repository cannot publish even when the name it
gives is one this list has never heard of — and, being a shape rather than a name, it is
written out below and not illustrated here, because an illustration of it would be an
occurrence of it.

**Pointers into records this project keeps private.** A numbered work item, a ruling
number, a planning document by file name, a decision label, a section sign and a number, an
abbreviated commit identifier in prose. What is refused is the INDEX, not the word: « a
review found this » is a fact about the code a reader can check against the code beside it;
the same sentence with a number attached sends them to a document nobody outside the project
can open.

The section-sign detector is the one this guard gained last, and it is worth saying why it is
in the same family. Seven comments here cited numbered sections of a design note this
repository does not contain: a shape that reads like a citation, resolves to nothing, and no
detector saw. The sign appears nowhere in this tree now — the one sound use, a citation of a
document here by its heading, was rewritten in words as well — so the detector has no
exception to argue about.

**The detectors are structural, and every pattern is assembled from pieces** so that this
file is not itself the occurrence it forbids. `report` is deliberately NOT among the
planning-document words: this agent's whole task is to write a report, so it is a domain
word here, the way `manifest` is one in the product command-line interface's own copy of
this rule.

**What is read of each file under those roots, per suffix**, because a root read in part is
not a root read. Every detector in `EVERYWHERE` reads every published file whole, whatever
its suffix. The detectors in `PROSE_ONLY` read the sentences a file publishes, and
`prose_of` below decides what those are: a `.md`, `.rst` or `.txt` file, and `NOTICE`,
whole; a `.py` file's comments and docstrings; the `#` comment lines of a `.yml`, `.yaml`,
`.toml` or `.sh` file; and of anything else, nothing. The last group is there on purpose
rather than by omission: the gate script and the workflow argue their rules in comment
blocks the way a module argues them in a docstring — this repository's gate carries about
sixty such lines and its workflow about thirty — while the lines around those comments pin
actions, read pins and match patterns, which is a program's ordinary business and not a
sentence.

**Where this guard came from, and the one rule about adapting it.** It is the product
command-line interface's own copy of this rule, read from the head of the release branch
that landed on that repository's `main`, and adapted: the roots are this repository's, the
first family above is this repository's own, and `report` left the planning-document words
for the reason given above. The head is named here in words rather than by its identifier,
because an abbreviated object name in a sentence is one of the things this guard refuses
and a file may not make the exception it denies everyone else. Nothing else was dropped:
an adapted guard is never weaker than the guard it was adapted from, and where it is
weaker the difference is stated and argued rather than silent.

Three further deltas from that copy, each in this direction: `demo-policy.toml` and
`.env.example` are roots it has no counterpart for; `.gitignore` and `demo_data/` are roots
this guard did not read until a sweep found a survivor in each — an ignore list describing a
credential store this tree never had, and an invented corpus describing a product shape this
demonstration does not have. Both were tracked, both become public with the repository, and
both were invisible here because the per-root check below proves that every root reaches a
file and nothing proves the converse. A root never added is a root nobody misses.

It needs no installed package, so it speaks in a reduced run too.
"""

from __future__ import annotations

import ast
import io
import re
import shutil
import subprocess
import tokenize
from collections.abc import Iterator
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]

#: What this repository publishes and this guard therefore reads. Named as roots rather
#: than as a file list, so a document added next month is covered without anyone
#: remembering to add it here. `LICENSE` is deliberately outside it: it is a notice rather
#: than a work, which is the same exception article 15 makes.
PUBLISHED_ROOTS = (
    "src",
    "tests",
    "scripts",
    "docs",
    "demo_data",
    ".github/workflows",
    "README.md",
    "NOTICE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "pyproject.toml",
    "demo-policy.toml",
    ".env.example",
    ".gitignore",
)

#: Suffixes whose whole content is prose.
PROSE_SUFFIXES = frozenset({".md", ".rst", ".txt"})

#: Suffixes whose `#` comment lines are prose and whose other lines are not. The gate
#: script, the workflow and the policy file argue their rules in comments — the gate does it
#: at length, and the policy file's comments are the only place the four answers are
#: explained — and a guard that read none of them would leave unread exactly the prose that
#: is written last and reviewed least. What those comments sit among is a program: a pinned
#: action, a pin read out of the project file, an identifier a script builds.
COMMENT_SUFFIXES = frozenset({".yml", ".yaml", ".toml", ".sh"})

#: Files that are prose and carry no suffix to say so. `NOTICE` is a document a reader
#: reads, and a guard that judged it by its extension would read the one file most likely to
#: name an origin as if it were a program.
PROSE_NAMES = frozenset({"NOTICE"})

#: Directories an enumeration without a version-control listing must not enter. Two are this
#: repository's own additions to the set the product client's guard carries: `runtime`, which
#: holds what a run writes and is never published, and `dist`, which holds what a build
#: writes. One more is kept rather than added: the gate prepares ONE environment now, so
#: nothing creates the second one any more — and every machine that ran the earlier
#: arrangement still holds one, where an installed distribution's own files would be read as
#: this repository's prose.
NOT_PUBLISHED = frozenset(
    {
        ".venv",
        ".venv-reduced",
        ".wheelhouse",
        "__pycache__",
        ".ruff_cache",
        ".pytest_cache",
        "runtime",
        "dist",
    }
)

#: The product this demonstration was built beside, in either case.
PARENT_PRODUCT = re.compile("swarm" + "forge", re.IGNORECASE)

#: The retired prefix: the repositories, the packages and the variables that carried it.
#: One pattern covers all of them, because all of them are the same two letters and a
#: separator, and a list of the names themselves would be the leak it is meant to prevent.
RETIRED_PREFIX = re.compile(r"(?<![A-Za-z0-9])" + "sf" + r"[-_][A-Za-z0-9]", re.IGNORECASE)

#: A component of the parent product, in the short spelling it carries.
EXPERIMENTAL_COMPONENT = re.compile(
    r"(?<![A-Za-z0-9])" + "sf" + "xp" + r"(?![A-Za-z0-9])", re.IGNORECASE
)

#: The verbs of the command that used to write this repository's boundary module. A reader
#: cannot install that command, and this repository no longer runs under it.
RETIRED_COMMAND = re.compile(
    r"(?<![A-Za-z0-9])" + "sf" + r"\s+(?:inspect|skills|integrate)(?![A-Za-z0-9])",
    re.IGNORECASE,
)

#: A work item of a tracker this repository does not publish. The NUMBER is what makes it
#: a pointer. This comment carries no example, because an example of the construction
#: inside the guard would be an occurrence of it.
WORK_ITEM = re.compile(
    r"\b(?:task|finding|epic|ticket|fix\s+round|round\s+of\s+fixes)\s*[-_#]?\s*\d+",
    re.IGNORECASE,
)

#: A ruling of a decision record this repository does not publish. The articles of the
#: constitution it adopts by pointer are cited as « article N », in words, and that
#: spelling is public.
RULING = re.compile(r"\bR\d{1,3}\b|\bLT-\d{2,3}\b")

#: A planning document by file name. `report` is absent for the reason the module
#: docstring gives.
PLANNING_DOCUMENT = re.compile(
    r"\b[A-Za-z0-9_-]*(?:brief|backlog|roadmap|plan)\.md\b", re.IGNORECASE
)

#: A decision or doctrine cited by a label of a record this repository does not hold.
DECISION_LABEL = re.compile(r"\b(?:decision|doctrine)\b(?:\s+[a-z]+){0,2}\s+\(?[A-Z]\d{1,2}\)?\b")

#: A numbered section of a document. The NUMBER is what makes it a pointer, as with a work
#: item: there is no numbered document in this tree, so every one of these resolved to a
#: design note a reader cannot open. A citation of a document here by its HEADING is the
#: form that works and the form this repository now uses. The sign is spelled by its code
#: point so that this guard is not an occurrence of what it refuses.
SECTION_POINTER = re.compile("\u00a7" + r"\s*\d")

#: A non-public source attributed by name: the construction by which a repository nobody
#: outside the project can open enters a public sentence. Naming the OPEN siblings is not
#: that — a document has to be able to say which published distribution it depends on — so
#: the pattern wants the word that claims the source is not public. Kept from the guard
#: this one was adapted from, unchanged: the deny-list above knows the few names this
#: project has retired, and this knows the shape of a name it has never met.
NAMED_NON_PUBLIC_SOURCE = re.compile(
    r"\b(?:private|parent|internal|upstream|proprietary|closed)"
    r"(?:\s+[a-z-]+){0,3}\s+(?:repository|product|source|tree|client)\s+"
    r"(?:named|called)\s+[A-Za-z0-9_.-]+",
    re.IGNORECASE,
)

#: An abbreviated commit identifier. At least one digit is required, because English is
#: written in the same alphabet.
COMMIT_IN_PROSE = re.compile(r"(?<![0-9A-Za-z])(?=[0-9a-f]*\d)[0-9a-f]{7,40}(?![0-9A-Za-z])")

#: Detectors that read every published file, code and prose alike.
EVERYWHERE = {
    "the parent product named": PARENT_PRODUCT,
    "the retired prefix": RETIRED_PREFIX,
    "a component of the parent product named": EXPERIMENTAL_COMPONENT,
    "a verb of the retired command": RETIRED_COMMAND,
    "numbered work item": WORK_ITEM,
    "ruling number": RULING,
    "planning document": PLANNING_DOCUMENT,
    "decision label this repository does not define": DECISION_LABEL,
    "numbered section of a document this repository does not contain": SECTION_POINTER,
    "non-public source named outright": NAMED_NON_PUBLIC_SOURCE,
}

#: Detectors that read prose only. Code pins digests as its ordinary business; a sentence
#: does not.
PROSE_ONLY = {"commit identifier in prose": COMMIT_IN_PROSE}


def _published_files(root: Path) -> list[Path]:
    """Every file this repository publishes under the roots above.

    The listing and the walk are unioned rather than chosen between: a file added and not
    yet committed is published the moment it is, and a guard that read only what was
    already recorded would pass on the change that adds a leak and fail on the one after.
    """
    found = set(_walked(root))
    if (root / ".git").exists() and shutil.which("git") is not None:
        listed = subprocess.run(
            ("git", "ls-files", "-z", *PUBLISHED_ROOTS),
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        found.update(Path(name) for name in listed.split("\0") if name)
    return sorted(item for item in found if (root / item).is_file())


def _walked(root: Path) -> list[Path]:
    found: list[Path] = []
    for named in PUBLISHED_ROOTS:
        start = root / named
        if start.is_file():
            found.append(Path(named))
            continue
        found.extend(
            item.relative_to(root)
            for item in start.rglob("*")
            if item.is_file() and not NOT_PUBLISHED & set(item.relative_to(root).parts)
        )
    return sorted(found)


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def prose_of(path: Path, content: str) -> str:
    """The sentences a file publishes: a prose file whole, a module's comments and
    docstrings, a script's or a workflow's comment lines, and nothing a program merely
    computes with.

    Python is where this repository keeps most of its prose — every rule it holds is argued
    in a docstring — so a guard that read only Markdown would leave the larger half of what
    ships unread. The gate script, the workflow and the policy file keep the rest, in `#`
    comments, and they are read the same way and for the same reason: the alternative is a
    root this guard enumerates and does not read. It is also why a string a program computes
    with is left out: those carry digests and fixtures, and reading them as sentences is how
    a guard starts firing on the values it is meant to protect.
    """
    if path.suffix in PROSE_SUFFIXES or path.name in PROSE_NAMES:
        return content
    if path.suffix in COMMENT_SUFFIXES:
        return "\n".join(line for line in content.splitlines() if line.lstrip().startswith("#"))
    if path.suffix != ".py":
        return ""
    said: list[str] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(content).readline):
            if token.type == tokenize.COMMENT:
                said.append(token.string)
        tree = ast.parse(content)
    except (SyntaxError, tokenize.TokenError, IndentationError, ValueError):
        return "\n".join(said)
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            docstring = ast.get_docstring(node, clean=False)
            if docstring:
                said.append(docstring)
    return "\n".join(said)


def public_vocabulary(root: Path) -> Iterator[tuple[Path, str]]:
    """Yield (file, class) for every unreachable reference this repository publishes."""
    for item in _published_files(root):
        content = _read(root / item)
        if content is None:
            continue
        for category, pattern in EVERYWHERE.items():
            if pattern.search(content):
                yield item, category
        prose = prose_of(item, content)
        for category, pattern in PROSE_ONLY.items():
            if prose and pattern.search(prose):
                yield item, category


def test_nothing_this_repository_publishes_names_what_a_reader_cannot_reach() -> None:
    """Article 14: every published sentence sends a reader somewhere they can go."""
    published = _published_files(REPOSITORY)
    # Anti-vacuity floor: an enumeration that found nothing cannot pass, and one that
    # found only documents would leave every docstring unread.
    #
    # What is ASSERTED is the floor of twenty, and what the roots above reach as this was
    # written is fifty-six — measured through `_published_files` rather than counted by
    # hand, and stated because the last sentence here said twenty-nine and was wrong by
    # twenty-three files by the time anyone read it. The floor is deliberately far below
    # the measurement: it is there to catch an enumeration that collapsed, not to be
    # revised every time a module is added. Neither number is a pointer into anything,
    # which is why both are written as counts.
    assert len(published) >= 20, published
    assert [item for item in published if item.suffix in PROSE_SUFFIXES]
    assert [item for item in published if item.suffix == ".py"]
    # Every root actually reaches a file. A root spelled wrongly, or dropped from the
    # tuple, makes this guard quietly smaller.
    reached = {item.as_posix() for item in published}
    for root in PUBLISHED_ROOTS:
        assert any(name == root or name.startswith(f"{root}/") for name in reached), root
    assert sorted(set(public_vocabulary(REPOSITORY))) == []


def test_the_guard_catches_a_planted_example_of_every_shape(tmp_path: Path) -> None:
    """The rule is proven against a planted example of each class it refuses.

    Every example is invented, and assembled from pieces for the same reason the patterns
    are: reproducing a real reference in order to test for it would publish it.
    """
    planted = tmp_path / "README.md"
    cases = {
        "the parent product named": "Built beside " + "Swarm" + "Forge" + " last year.",
        "the retired prefix": "The authority was " + "sf" + "-control-plane" + " then.",
        "a component of the parent product named": "The transport was " + "sf" + "xp" + ".",
        "a verb of the retired command": "Run " + "sf" + " integrate apply" + " to write it.",
        "numbered work item": "Closes " + "finding" + " 3 of the review.",
        "ruling number": "The requirement is " + "R" + "46, which overrides the letter.",
        "planning document": "The disagreement is recorded in " + "example-9-brief" + ".md.",
        "decision label this repository does not define": (
            "The name was settled by " + "decision" + " Z9."
        ),
        "numbered section of a document this repository does not contain": (
            "Idempotent by construction (" + "\u00a7" + "46)."
        ),
        "non-public source named outright": (
            "A " + "private source repository " + "named" + " example-internal holds it."
        ),
        "commit identifier in prose": "Fixed at commit " + "1a2b3c4" + " on that branch.",
    }
    for category, content in cases.items():
        planted.write_text(content, encoding="utf-8")
        found = {category for _, category in public_vocabulary(tmp_path)}
        assert category in found, (category, content, found)


def test_the_guard_reads_a_docstring_and_leaves_a_pinned_digest_alone(tmp_path: Path) -> None:
    """Two things at once, because each would pass without the other.

    A commit named in a MODULE's own prose is as published as one named in a document. A
    sixty-four character digest a test pins is not a commit and must not be read as one, or
    the guard would fire on the values this repository's own bindings produce.
    """
    source = tmp_path / "src" / "example.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        '"""A module whose docstring names commit ' + "1a2b3c4" + '."""\n', encoding="utf-8"
    )
    assert ("src/example.py", "commit identifier in prose") in {
        (item.as_posix(), category) for item, category in public_vocabulary(tmp_path)
    }

    source.write_text(
        '"""A module that pins a digest and names no commit."""\n\nDIGEST = "'
        + "0123456789abcdef" * 4
        + '"\n',
        encoding="utf-8",
    )
    assert sorted(set(public_vocabulary(tmp_path))) == []


def test_a_comment_line_of_a_script_is_read_as_prose_and_the_lines_around_it_are_not(
    tmp_path: Path,
) -> None:
    """Two things at once, because each would pass without the other.

    A commit named in the gate's own comment block is as published as one named in a
    document, and this repository's gate argues its three outcomes in about sixty such
    lines. A digest on the line below it is a program pinning something, which is a
    script's ordinary business and must not be read as a sentence — or the guard would fire
    on the one construction that makes a build reproducible.
    """
    script = tmp_path / "scripts" / "example.sh"
    script.parent.mkdir(parents=True)
    script.write_text(
        "# A comment naming commit " + "1a2b3c4" + " of another branch.\nset -euo pipefail\n",
        encoding="utf-8",
    )
    assert ("scripts/example.sh", "commit identifier in prose") in {
        (item.as_posix(), category) for item, category in public_vocabulary(tmp_path)
    }

    script.write_text(
        "# A comment that pins a digest and names no commit.\n"
        'expected="' + "0123456789abcdef" * 2 + '"\n',
        encoding="utf-8",
    )
    assert sorted(set(public_vocabulary(tmp_path))) == []


def test_the_words_this_repository_does_use_are_not_refused(tmp_path: Path) -> None:
    """WATCHED NOT FIRING.

    This agent writes a report, saves it under a name ending in `report.md`, and says so in
    three documents; a guard that refused its own domain would be turned off in a week. The
    same for a sentence that says a review found something without pointing at a record of
    the review.
    """
    document = tmp_path / "docs" / "ARCHITECTURE.md"
    document.parent.mkdir(parents=True)
    document.write_text(
        "The agent saves research-report.md, and the binding names its digest.\n"
        "A review found that the resolution had to be one function, and it is.\n"
        "Article 12 is the one this decision answers to.\n",
        encoding="utf-8",
    )
    assert sorted(set(public_vocabulary(tmp_path))) == []
