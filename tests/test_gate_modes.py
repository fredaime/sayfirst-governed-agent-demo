# SPDX-License-Identifier: Apache-2.0
"""The gate has three outcomes, the workflow renders three, and here they are held.

    "an absence — a missing record, an unreachable control plane, an empty list — is
    never rendered as a negative fact, a zero or a healthy state"   — article 2

`scripts/gate.sh` can finish without the open distributions, which a reader who cloned only
this repository always will. That is worth having and it is exactly the kind of change that
decays into a lie: the reduced run keeps working, the reason it is reduced stops being
visible, and a green tick comes to mean two different things. So the three outcomes are read
out of the script itself, the workflow is required to render each of them differently, and
the status the script reserves for a reduced run is required to be one the workflow knows
about — a script and a workflow that stopped agreeing about that number would fail open, and
green.

Two more rules are held here because both are claims about these same two files.

**The gate prepares ONE environment, in both of its modes.** A reduced run is `.venv` without
the open distributions and without the daemon, never a second directory of its own, because
every script beside the gate reads `.venv` — and a gate that prepared one directory while the
bootstrap's own next three commands read another is how a reader reaches « complete » and then
an interpreter that was never installed.

**The sign-off check runs on a pull request, and it is the one check outside the gate.** That
is the exception this workflow's header states; the rule the gate jobs are held to is
unchanged, and any OTHER job running a script of this repository is the defect that rule
exists to catch.

One rule here is this repository's own rather than adapted, and publication turned it round.
While the two products this gate builds from were not this repository's to publish, no line
of the workflow was allowed to spell a repository name: the names were settings the workflow
read, because a name written in a public file is published whether anyone reads it or not.
They are public addresses now, so the rule is stricter rather than gone — **the workflow
checks out these two repositories, at the tag this project pins, and nothing else** — and the
credential that used to reach them is required to be absent everywhere.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
GATE = REPOSITORY / "scripts" / "gate.sh"
WORKFLOW = REPOSITORY / ".github" / "workflows" / "ci.yml"

GATE_TEXT = GATE.read_text(encoding="utf-8")
WORKFLOW_TEXT = WORKFLOW.read_text(encoding="utf-8")

#: The one development environment this gate prepares, as the gate's own assignment spells it.
ENVIRONMENT = "$repository/.venv"

#: The second environment this arrangement used to have, refused by name as well as by the
#: rule above: a mode-dependent path is how the gate and the scripts beside it come to read
#: two different directories, and the name is what a reader reintroducing it would type.
SECOND_ENVIRONMENT = ".venv" + "-reduced"

#: Every shell file of this repository, which is where an environment path is spelled.
SHELL_FILES = tuple(sorted(REPOSITORY.glob("scripts/**/*.sh")))

#: The job that reads the sign-offs of a change. Article 15 asks for the trailer and
#: `CONTRIBUTING.md` names the script; the job is where « runs on every pull request » stops
#: being a sentence and becomes a file.
SIGN_OFF_JOB = "developer-certificate-of-origin"

#: The action version this repository runs. An earlier one runs on a deprecated runtime,
#: and a warning nobody clears is a warning nobody reads.
CHECKOUT = "v5"

#: The installer this workflow runs, and the version of it, as the two lines a workflow
#: spells them on. Asserted as EXACT LINES rather than by pattern, and both rather than
#: one: the two other open repositories of this project pin the same action and the same
#: version, for the reason a review found there — a job whose toolchain is whichever
#: version resolved that morning is a job nobody can reproduce, and the difference arrives
#: as a red run months later rather than as a diff somebody read.
UV_ACTION = "      - uses: astral-sh/setup-uv@v5"
UV_VERSION = '          version: "0.12.5"'


#: The one way this gate may read a sibling: an archive of the ref it was given, unpacked
#: into a destination of its own. Asserted as the INVOCATION rather than as two substrings,
#: because both substrings a first version of this rule looked for survive in a gate that
#: copies a checkout instead — one on the line that resolves the ref, the other in a comment.
ARCHIVE = re.compile(r'archive "\$ref" \| tar -x -C "\$destination"')

#: A source tree copied rather than archived, in the two forms somebody writes it. That is
#: the defect the rule above exists to refuse, and it is refused by name as well as by
#: absence: a fallback that copies a checkout is how a gate comes to report on whatever its
#: owner happened to have out that morning.
COPIES_A_TREE = re.compile(
    r"(?:^|\s)(?:cp\s+-a|rsync)\b[^\n]*\$\{?(?:source|contract_source|client_source)"
)

#: A check spelled out in the workflow itself. `uv` is deliberately not among them: the
#: installer action is how this workflow gets the tool the gate runs, not a check of its own.
CI_ONLY_TOOLS = ("pytest", "ruff", "python -m", "coverage", "mypy")

#: The two products this workflow checks out, at the public names publication gave them.
#: Written here rather than read out of the workflow: a name a file was asked to prove
#: against itself proves nothing, and these two are what a reviewer of THIS rule reads.
PUBLIC_PRODUCTS = ("fredaime/sayfirst-control-plane", "fredaime/sayfirst-cli")


def _pinned_release() -> str:
    """The one number this demonstration pins, read out of the project file.

    The tag the workflow reads the two products at is that number, and it is read rather
    than spelled so that a release which moves the pin and forgets the workflow fails here
    instead of building a tree nobody asked for. The project file says one number is said
    everywhere; this is where « everywhere » includes the workflow.
    """
    document = tomllib.loads((REPOSITORY / "pyproject.toml").read_text(encoding="utf-8"))
    pinned = [
        item
        for item in [*document["project"]["dependencies"], *document["dependency-groups"]["e2e"]]
        if item.startswith("sayfirst-")
    ]
    assert len(pinned) >= 3, f"the project file pins fewer of them than it declares: {pinned}"
    versions = {item.split("==", 1)[1] for item in pinned if "==" in item}
    assert len(versions) == 1, f"one number is said everywhere, and here it is not: {versions}"
    return versions.pop()


#: The tag both products are read at: the release this demonstration shows.
TAG = f"v{_pinned_release()}"


def _code(text: str) -> str:
    """The workflow without its comments: what the runner acts on."""
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def _toolchain_that_moves(text: str) -> list[str]:
    """Every way this workflow's toolchain could change without the file changing.

    One reading of the rule, so that the green case and the planted mutations below ask the
    same question: two copies of one rule is how a guard and its own probe stop agreeing.
    """
    lines = text.splitlines()
    problems: list[str] = []
    if UV_ACTION not in lines:
        problems.append("the installer is not the pinned action")
    if UV_VERSION not in lines:
        problems.append(
            "the installer action asks for no version, so it installs the one of the day"
        )
    used = set(re.findall(r"actions/checkout@(\S+)", _code(text)))
    if used != {CHECKOUT}:
        problems.append(f"the checkout action is pinned to {sorted(used)} rather than {CHECKOUT}")
    if not used:
        problems.append("nothing here checks anything out, so the rule above would hold vacuously")
    return problems


WORKFLOW_CODE = _code(WORKFLOW_TEXT)


def _declared(name: str) -> int:
    found = re.search(rf"^readonly {name}=(\d+)$", GATE_TEXT, re.MULTILINE)
    assert found, f"{GATE} declares no {name}"
    return int(found.group(1))


def _lines_under(header: str, text: str | None = None) -> list[str]:
    lines = (WORKFLOW_TEXT if text is None else text).splitlines()
    for index, line in enumerate(lines):
        if line == f"{header}:":
            body = []
            for follower in lines[index + 1 :]:
                if follower and not follower.startswith(" "):
                    break
                body.append(follower)
            return body
    raise AssertionError(f"{WORKFLOW} has no top-level {header!r}")


def _jobs(text: str | None = None) -> dict[str, list[str]]:
    jobs: dict[str, list[str]] = {}
    current: str | None = None
    for line in _lines_under("jobs", text):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            if current is not None:
                jobs[current].append(line)
            continue
        if re.fullmatch(r"  [a-z0-9-]+:", line):
            current = stripped[:-1]
            jobs[current] = []
        elif current is not None:
            jobs[current].append(line)
    assert len(jobs) >= 3, f"{WORKFLOW} was not parsed into jobs: {sorted(jobs)}"
    return jobs


def _name(lines: list[str]) -> str:
    for line in lines:
        found = re.fullmatch(r"    name: (.+)", line)
        if found:
            return found.group(1)
    raise AssertionError("a job of the workflow has no name")


def _gate_jobs() -> dict[str, list[str]]:
    return {
        identifier: lines
        for identifier, lines in _jobs().items()
        if any("scripts/gate.sh" in line for line in lines)
    }


def _reduced_identifier() -> str:
    reduced = [
        identifier
        for identifier, lines in _gate_jobs().items()
        if "reduced" in _name(lines).lower()
    ]
    assert len(reduced) == 1, f"expected one reduced job, found {reduced}"
    return reduced[0]


def test_the_gate_declares_three_outcomes_and_not_two() -> None:
    full, reduced = _declared("GATE_FULL_GREEN"), _declared("GATE_REDUCED_GREEN")
    assert full == 0
    assert reduced != full, "a reduced run and a full run cannot share a status"
    assert reduced != 1, "a reduced run cannot share a status with an ordinary failure"


def test_the_reduced_status_is_never_written_as_a_number() -> None:
    """Two paths reach it — the environment-only stop and the end of a reduced run — and
    both write it through the name, so the value lives in exactly one line of this file."""
    assert GATE_TEXT.count('exit "$GATE_REDUCED_GREEN"') == 2
    assert f"exit {_declared('GATE_REDUCED_GREEN')}" not in GATE_TEXT
    assert 'echo "gate: the open distributions are absent:' in GATE_TEXT


def test_a_failure_can_never_be_read_as_a_reduced_run() -> None:
    """A tool that happened to exit with the reserved status would otherwise forge a tick."""
    assert 'if [ "$status" -eq "$GATE_REDUCED_GREEN" ]; then' in GATE_TEXT
    assert "trap on_failure ERR" in GATE_TEXT


def test_the_gate_reads_the_pins_out_of_the_project_file() -> None:
    """Two spellings of one pin is how a gate and its project stop agreeing."""
    assert "pyproject.toml" in GATE_TEXT
    assert "--reinstall" in GATE_TEXT, "a sibling changes without changing its version"


def _reads_a_working_tree(text: str) -> list[str]:
    """Every way this gate could come to read a checkout's files instead of a named ref.

    One reading, so that the green case and the planted fallbacks below ask the same
    question: two copies of one rule is how a guard and its own probe stop agreeing.
    """
    problems: list[str] = []
    if not ARCHIVE.search(text):
        problems.append("nothing here unpacks an archive of the ref it was given")
    copied = [line.strip() for line in text.splitlines() if COPIES_A_TREE.search(line)]
    if copied:
        problems.append(f"a source tree is copied rather than archived: {copied}")
    by_ref = re.findall(r'^\s*materialise "\$(\w+)_source" "\$(\w+)_ref"', text, re.MULTILINE)
    if sorted(by_ref) != [("client", "client"), ("contract", "contract")]:
        problems.append(f"the two siblings are not both read at their own ref: {by_ref}")
    return problems


def test_the_gate_reads_a_named_ref_and_never_a_working_tree() -> None:
    """A recording, or a gate, broken by somebody else's uncommitted work is the hazard
    this solves once: an archive of a named ref, never the files a checkout has out.

    Read as the branch rather than as two substrings, because the substrings survive the
    defect: a gate that copied a checkout would still spell the version-control command on
    the line that resolves the ref, and would still say « archive » in its own header.
    """
    assert _reads_a_working_tree(GATE_TEXT) == []
    assert "SAYFIRST_CONTRACT_REF" in GATE_TEXT
    assert "SAYFIRST_CLIENT_REF" in GATE_TEXT


def test_the_named_ref_rule_catches_a_gate_that_would_read_a_checkout() -> None:
    """WATCHED FIRING, one planted fallback per shape, against copies of the real file.

    The first is the fallback this gate carried until the rule above was asked to bite on
    it. The second is the form that keeps the archive and copies beside it. The third reads
    one sibling at the other's ref, which is a gate that no longer says which tree it read.
    """
    for mutation, was, becomes in (
        (
            "a copy instead of the archive",
            'archive "$ref" | tar -x -C "$destination"',
            'cp -a "$source/." "$destination/"',
        ),
        (
            "a copy beside the archive",
            '  echo "gate: reading $what at $ref',
            '  cp -a "$source/." "$destination/"\n  echo "gate: reading $what at $ref',
        ),
        (
            "one sibling read at the other's ref",
            '"$client_source" "$client_ref"',
            '"$client_source" "$contract_ref"',
        ),
    ):
        planted = GATE_TEXT.replace(was, becomes)
        assert planted != GATE_TEXT, f"the plant for {mutation} changed nothing"
        assert _reads_a_working_tree(planted), f"FAIL {mutation} was not caught"


def test_the_gate_names_no_checkout_by_default() -> None:
    """The variables have no default path. A default would name a repository this
    repository does not publish, in a file it does publish."""
    for variable in ("SAYFIRST_CONTRACT_SOURCE", "SAYFIRST_CLIENT_SOURCE"):
        found = re.search(rf"{variable}:-([^}}]*)\}}", GATE_TEXT)
        assert found, f"{GATE} does not read {variable} with a default at all"
        assert found.group(1) == "", f"{variable} has a default path: {found.group(1)!r}"


def test_both_gate_jobs_decide_every_status() -> None:
    jobs = _gate_jobs()
    assert len(jobs) == 2, f"expected a full job and a reduced job, found {sorted(jobs)}"
    for identifier, lines in jobs.items():
        body = "\n".join(lines)
        for branch in (r"^\s*0\)", rf"^\s*{_declared('GATE_REDUCED_GREEN')}\)", r"^\s*\*\)"):
            assert re.search(branch, body, re.MULTILINE), f"{identifier} ignores {branch}"


def test_a_reduced_run_is_not_rendered_as_an_ordinary_green_tick() -> None:
    """The job's own name carries the absence, before anyone opens the summary."""
    name = _name(_gate_jobs()[_reduced_identifier()])
    assert "absent" in name.lower(), name
    assert "not run" in name.lower(), name
    assert len({_name(lines) for lines in _jobs().values()}) == len(_jobs())


def test_the_reduced_job_says_what_it_did_not_run_and_what_would_fix_it() -> None:
    body = "\n".join(_gate_jobs()[_reduced_identifier()])
    assert "gate: the open distributions are absent:" in body
    assert "GITHUB_STEP_SUMMARY" in body
    assert "::warning::" in body


def _checks_out_something_else(text: str) -> list[str]:
    """Every way this workflow could come to read a tree that is not one of the two public
    products at the tag this project pins.

    One reading, so that the green case and the planted mutations below ask the same
    question: two copies of one rule is how a guard and its own probe stop agreeing.
    """
    problems: list[str] = []
    code = _code(text)
    named = sorted(re.findall(r"^\s*repository:\s*(.+)$", code, re.MULTILINE))
    if named != sorted(PUBLIC_PRODUCTS):
        problems.append(f"the workflow checks out {named} rather than {sorted(PUBLIC_PRODUCTS)}")
    read_at = re.findall(r"^\s*ref:\s*(.+)$", code, re.MULTILINE)
    if read_at != [TAG] * len(PUBLIC_PRODUCTS):
        problems.append(f"the products are read at {read_at} rather than at {TAG}")
    archived = re.findall(r"^\s*SAYFIRST_(?:CONTRACT|CLIENT)_REF:\s*(.+)$", code, re.MULTILINE)
    if archived != [TAG] * 2:
        problems.append(f"the gate is told to archive {archived} rather than {TAG}")
    if "vars." in code:
        problems.append("a name this file is now free to spell is read out of a setting instead")
    return problems


def test_the_workflow_checks_out_the_two_public_products_at_the_pinned_tag() -> None:
    """The one thing publication changed in this file, held as a rule.

    Four things, because each alone would pass on a workflow reading a tree nobody chose:
    the two names are these two and no others; each is read at the tag; the gate is told to
    archive that same tag inside each checkout, so what it builds is what was checked out;
    and no name is read out of a setting any more, which is what would hide a third one.
    """
    assert _checks_out_something_else(WORKFLOW_TEXT) == []
    for name in PUBLIC_PRODUCTS:
        assert name in WORKFLOW_CODE, name


def test_the_checkout_rule_catches_a_workflow_that_reads_another_tree() -> None:
    """WATCHED FIRING, one planted mutation per shape, against copies of the real file.

    The last two are the ones a release actually arrives as: a ref left on a branch after a
    tag was cut, and a gate told to archive a ref the checkout was not taken at.
    """
    for mutation, was, becomes in (
        (
            "a third repository checked out",
            "          repository: fredaime/sayfirst-cli\n",
            "          repository: fredaime/example-other\n",
        ),
        (
            "a name put back behind a setting",
            "          repository: fredaime/sayfirst-control-plane\n",
            "          repository: ${{ vars.A_REPOSITORY }}\n",
        ),
        (
            "a product read at a branch rather than at the tag",
            f"          ref: {TAG}\n          path: client\n",
            "          ref: main\n          path: client\n",
        ),
        (
            "the gate told to archive something else",
            f"          SAYFIRST_CONTRACT_REF: {TAG}\n",
            "          SAYFIRST_CONTRACT_REF: origin/main\n",
        ),
    ):
        planted = WORKFLOW_TEXT.replace(was, becomes, 1)
        assert planted != WORKFLOW_TEXT, f"the plant for {mutation} changed nothing"
        assert _checks_out_something_else(planted), f"FAIL {mutation} was not caught"


def test_the_reduced_job_asks_for_no_repository_and_no_credential() -> None:
    body = _code("\n".join(_gate_jobs()[_reduced_identifier()]))
    assert "repository:" not in body
    assert "token:" not in body
    assert "secrets." not in body, "the job that needs no credential reads one"


def _checks_outside_the_gate(text: str) -> list[str]:
    """Every check this workflow runs that is not `scripts/gate.sh`.

    One reading, shared by the green case and the plants: a step that exists only here is a
    step nobody can reproduce, and this file says so about itself in its own first comment.
    """
    code = _code(text)
    problems = [f"the workflow runs {tool} itself" for tool in CI_ONLY_TOOLS if tool in code]
    if "scripts/gate.sh" not in code:
        problems.append("nothing here runs the gate, so the rule would hold vacuously")
    return problems


def test_every_check_the_workflow_runs_is_the_gate() -> None:
    """The claim this file's own first comment makes, held rather than read.

    Restored from the guard this one was adapted from, where it is
    `test_every_check_the_workflow_runs_is_the_gate`: a check that exists only in CI is a
    check nobody can reproduce locally, and a merge decided by one is decided by something
    a contributor cannot run.
    """
    assert _checks_outside_the_gate(WORKFLOW_TEXT) == []
    assert WORKFLOW_CODE.count("scripts/gate.sh") == 2, "the two gate jobs run it, and only it"


def test_the_rule_catches_a_check_that_exists_only_here() -> None:
    """WATCHED FIRING, one plant per job, in the form a second checker actually arrives as."""
    for mutation, was, becomes in (
        (
            "a second test run in the full job",
            "      - name: gate\n",
            "      - run: uv run pytest -q\n\n      - name: gate\n",
        ),
        (
            "a lint step in the reduced job",
            "      - name: gate (reduced)\n",
            "      - run: ruff check .\n\n      - name: gate (reduced)\n",
        ),
    ):
        planted = WORKFLOW_TEXT.replace(was, becomes, 1)
        assert planted != WORKFLOW_TEXT, f"the plant for {mutation} changed nothing"
        assert _checks_outside_the_gate(planted), f"FAIL {mutation} was not caught"


def _grants_more_than_read(text: str) -> list[str]:
    """Everything this workflow grants beyond reading the repository it runs in."""
    problems: list[str] = []
    granted = [line.strip() for line in _lines_under("permissions", text) if line.strip()]
    if granted != ["contents: read"]:
        problems.append(f"the workflow grants {granted}")
    if _code(text).count("permissions:") != 1:
        problems.append("a job grants itself a block of its own")
    return problems


def test_the_workflow_grants_read_and_nothing_else() -> None:
    """The floor under « this workflow publishes nothing »: a token that can only read.

    Restored from the guard this one was adapted from. The publishing rule below refuses
    the three names a publishing job is spelled with; this refuses the grant that would let
    any step write, whatever it is called.
    """
    assert _grants_more_than_read(WORKFLOW_TEXT) == []


def test_the_permission_rule_catches_a_grant_this_workflow_must_not_have() -> None:
    """WATCHED FIRING: the grant widened at the top, and a job granting itself one."""
    for mutation, was, becomes in (
        (
            "the top-level grant widened",
            "permissions:\n  contents: read\n",
            "permissions:\n  contents: write\n",
        ),
        (
            "a job granting itself more",
            "    name: gate (full)\n",
            "    name: gate (full)\n    permissions:\n      contents: write\n"
            "      packages: write\n",
        ),
    ):
        planted = WORKFLOW_TEXT.replace(was, becomes, 1)
        assert planted != WORKFLOW_TEXT, f"the plant for {mutation} changed nothing"
        assert _grants_more_than_read(planted), f"FAIL {mutation} was not caught"


def _reads_a_credential(text: str) -> list[str]:
    """Every credential this workflow reads, which after publication is none at all.

    Both products are public, so there is no secret for a job to ask about and no token for
    a checkout to be handed. That is STRICTER than the rule this replaces — which allowed
    the emptiness of a secret to be read and the secret itself to be handed to a checkout —
    and it is stricter because the thing it allowed no longer exists. A credential that
    came back would make this repository's own runs pass while every fork's failed, which
    is the shape the reduced job exists to avoid.
    """
    problems: list[str] = []
    code = _code(text)
    problems += [
        f"a credential is read: {line.strip()}" for line in code.splitlines() if "secrets." in line
    ]
    if re.search(r"^\s*token:", code, re.MULTILINE):
        problems.append("a checkout is handed a credential")
    if "actions/checkout@" not in code:
        problems.append("nothing here checks anything out, so the rule would hold vacuously")
    return problems


def test_no_job_reads_a_credential_and_the_question_is_asked_before_any_checkout() -> None:
    """No credential anywhere, and the question both gate jobs turn on is asked first.

    « Before » is `needs:`, not the order of the lines in this file: both gate jobs wait on
    the answer, so neither can start a checkout against a tree this run has established
    nothing about. The question itself is required to be answerable BOTH ways — it names
    the two products and the tag, and writes either answer — because a question with one
    possible answer would leave the reduced job unreachable and its own name a lie.
    """
    jobs, gates = _jobs(), _gate_jobs()
    waited = {
        tuple(line.strip() for line in lines if line.strip().startswith("needs:"))
        for lines in gates.values()
    }
    assert len(waited) == 1, f"the two gate jobs wait on different things: {waited}"
    needs = waited.pop()
    assert len(needs) == 1, f"a gate job waits on {needs}"
    question = needs[0].removeprefix("needs: ")
    assert question in jobs, f"{question} is not a job of this workflow: {sorted(jobs)}"
    assert question not in gates, "the question is answered by a job that also runs the gate"
    body = _code("\n".join(jobs[question]))
    assert "uses:" not in body, "the question needs no action and no checkout"
    for name in PUBLIC_PRODUCTS:
        assert name in body, f"the question does not ask about {name}"
    assert TAG in body, "the question does not ask about the tag the project file pins"
    assert "answer=reachable" in body and "answer=absent" in body, body
    assert _reads_a_credential(WORKFLOW_TEXT) == []


def test_the_credential_rule_catches_a_workflow_that_reads_one() -> None:
    """WATCHED FIRING: the three shapes a retired credential comes back as."""
    secret = "${{ secrets.A_CREDENTIAL }}"
    for mutation, was, becomes in (
        (
            "the secret in an environment of the gate step",
            f"          SAYFIRST_CLIENT_REF: {TAG}\n",
            f"          SAYFIRST_CLIENT_REF: {TAG}\n          CREDENTIAL: {secret}\n",
        ),
        (
            "the secret written to an output",
            '            echo "answer=reachable" >> "$GITHUB_OUTPUT"\n',
            f'            echo "answer={secret}" >> "$GITHUB_OUTPUT"\n',
        ),
        (
            "a checkout handed a token",
            "          path: control-plane\n",
            f"          path: control-plane\n          token: {secret}\n",
        ),
    ):
        planted = WORKFLOW_TEXT.replace(was, becomes, 1)
        assert planted != WORKFLOW_TEXT, f"the plant for {mutation} changed nothing"
        assert _reads_a_credential(planted), f"FAIL {mutation} was not caught"


def test_no_checkout_falls_back_to_a_token_scoped_to_this_repository() -> None:
    assert "github.token" not in WORKFLOW_CODE


def test_every_job_runs_the_pinned_toolchain() -> None:
    """Three tools stand between a commit and a verdict here: the checkout, the installer
    and the version of the installer. Each is named with a version, and BOTH GATE jobs carry
    the installer — a job that installed whatever resolved that morning would report on
    this tree under a toolchain nobody chose. The sign-off job carries neither: it runs one
    script of this repository with the runner's own interpreter and installs nothing."""
    assert _toolchain_that_moves(WORKFLOW_TEXT) == []
    lines = WORKFLOW_TEXT.splitlines()
    assert lines.count(UV_ACTION) == 2, "both the full job and the reduced job install it"
    assert lines.count(UV_VERSION) == 2


def test_the_pinning_rule_catches_a_toolchain_that_moves() -> None:
    """WATCHED FIRING, one planted mutation per pin, against copies of the real file.

    A rule whose only evidence is that it passes today would also pass if it had stopped
    applying. Each mutation is a form somebody would plausibly write: the action's own
    documentation offers the moving ref, and « latest » is what a version field invites.
    """
    original = WORKFLOW_TEXT
    for mutation, was, becomes in (
        ("the installer action", UV_ACTION, "      - uses: astral-sh/setup-uv@main"),
        ("the installer version", UV_VERSION, "          version: latest"),
        ("the checkout action", "actions/checkout@v5", "actions/checkout@v4"),
    ):
        planted = original.replace(was, becomes)
        assert planted != original, f"the plant for {mutation} changed nothing"
        assert _toolchain_that_moves(planted), f"FAIL {mutation} was not caught: {becomes}"


def test_the_gate_runs_the_suite_under_a_root_an_address_fits_in() -> None:
    """The one thing about this gate that a socket's length limit decides.

    The end-to-end tier binds a local address, the limit is the kernel's and it is small, so
    a run root chosen for its convenience is how a suite arrives at zero headroom without
    anyone deciding to spend it. Three things are required of the gate here: it makes the
    runner's directory under the short temporary root, it makes a FRESH one per run rather
    than reusing a fixed path two runs on one machine would take from each other, and it
    ASKS the published rule whether that directory leaves the margin rather than asserting it
    in a comment. The rule is the contract's own `root_leaves_the_margin`, and the fixtures
    ask the same module about the address itself.

    The template is required to be short, and the number here is the budget's and not a
    preference: every character of it is spent out of the margin that rule leaves, so a
    template somebody widened for readability would arrive as `AF_UNIX path too long` on a
    platform nobody ran it on.
    """
    assert 'run_root="${SAYFIRST_GATE_TMP:-/tmp}"' in GATE_TEXT, "the run root is not under /tmp"
    made = re.search(r'^basetemp="\$\(mktemp -d "\$run_root/(\S+)"\)"$', GATE_TEXT, re.MULTILINE)
    assert made, "the runner's directory is not made fresh under the run root"
    template = made.group(1)
    assert len(template) <= 12, f"the template {template} spends too much of the margin"
    assert template.endswith("XXXX"), f"{template} asks for no randomness, so two runs collide"
    assert "root_leaves_the_margin" in GATE_TEXT, "the gate asks nobody whether the root fits"
    assert '--basetemp="$basetemp"' in GATE_TEXT, "the runner is not given that root"
    # And never under the wheelhouse, which is long, inside the repository, and was the
    # first thing this gate reached for.
    assert 'basetemp="$wheelhouse' not in GATE_TEXT


def test_a_missing_client_is_not_reported_as_missing_distributions() -> None:
    """Two absences, two sentences, because they are two different facts about a run.

    A machine that built the contract, the boundary and the server and could not build only
    the command a person answers with proved everything this demonstration claims against a
    real control plane; every claim a person answers is what stood down. « The open
    distributions are absent » would understate that run, and understating what ran is as
    much a false status surface as overstating it — article 2 is about the reading, not the
    direction of the error.
    """
    assert 'echo "gate: the open distributions are absent:' in GATE_TEXT
    assert 'echo "gate: the command a person answers with is absent:' in GATE_TEXT
    # And the client that answers is the one this gate built from the source it was given —
    # never one a machine happened to have, which would answer with a version nobody chose.
    assert 'client_command="$repository/.venv-client/bin/sayfirst"' in GATE_TEXT
    assert 'SAYFIRST_CLIENT="$client_command"' in GATE_TEXT
    assert "client_built=yes" in GATE_TEXT and "client_built=no" in GATE_TEXT
    # A run where every module ran and only cases stood down never renders as « N of N ».
    assert 'if [ "$modules_not_run" -gt 0 ]; then' in GATE_TEXT


def test_an_unknown_argument_is_refused_rather_than_ignored() -> None:
    """The flag the deleted script took is the one a reader's hands reach for.

    A gate that ran everything and said nothing about the flag would teach them it still
    works, and the next reader would believe a run had been narrowed when it had not.
    """
    assert "exit 2" in GATE_TEXT, "an unknown argument shares a status with something"
    assert "is not an argument of this gate. Usage: ./scripts/gate.sh" in GATE_TEXT
    assert GATE_TEXT.count("--environment-only)") == 1, "the option is read by a case, once"


def test_the_workflow_publishes_nothing() -> None:
    """There is no release job here, and adding one would be a decision about publishing
    rather than a convenience: this demonstration publishes no distribution."""
    assert "pypi" not in WORKFLOW_CODE.lower()
    assert "twine" not in WORKFLOW_CODE.lower()
    assert "id-token" not in WORKFLOW_CODE.lower()
    assert not (REPOSITORY / ".github" / "workflows" / "release.yml").exists()


def _prepares_more_than_one_environment(text: str) -> list[str]:
    """Every way this gate could come to prepare an environment the other scripts cannot
    find.

    One reading, so that the green case and the planted mutations below ask the same
    question: two copies of one rule is how a guard and its own probe stop agreeing.
    """
    problems: list[str] = []
    assigned = re.findall(r'^\s*venv="([^"]*)"', text, re.MULTILINE)
    if assigned != [ENVIRONMENT]:
        problems.append(f"the gate assigns its environment {assigned} rather than [{ENVIRONMENT}]")
    if SECOND_ENVIRONMENT in text:
        problems.append(f"a second environment is named: {SECOND_ENVIRONMENT}")
    if "mode=reduced" not in text:
        problems.append("nothing here has two modes, so the rule above would hold vacuously")
    return problems


def test_the_gate_prepares_one_environment_in_both_modes() -> None:
    """The gate prepares `.venv` whichever mode it is in, and a reduced run is that same
    environment without the open distributions rather than a directory of its own.

    Three things, because each alone would pass on a gate that stranded a reader: there is
    exactly ONE assignment and it is `.venv`; the retired second environment is named
    nowhere in this gate nor in any script beside it; and a reduced run REMOVES the open
    distributions an earlier full run may have installed there, which is what makes « the
    same environment without them » a claim about this run rather than about this machine.
    """
    assert _prepares_more_than_one_environment(GATE_TEXT) == []
    assert SHELL_FILES, "no script was found: this rule would pass by absence"
    for script in SHELL_FILES:
        text = script.read_text(encoding="utf-8")
        assert SECOND_ENVIRONMENT not in text, script.relative_to(REPOSITORY)
    assert SECOND_ENVIRONMENT not in WORKFLOW_TEXT
    assert "uv pip uninstall" in GATE_TEXT, "a reduced run leaves an earlier full run's copies"
    assert "open_packages_are_installed" in GATE_TEXT, "the removal is assumed rather than read"


def test_the_one_environment_rule_catches_a_gate_that_prepares_two() -> None:
    """WATCHED FIRING, one planted mutation per shape, against copies of the real file.

    The first is the arrangement this gate carried until a reader on a machine without the
    checkouts was left with three commands that all died on a missing interpreter. The
    second is the form that keeps one assignment and makes it depend on the mode, which
    strands the same reader while reading as a tidy one-liner.
    """
    for mutation, was, becomes in (
        (
            "a second environment under the reduced branch",
            "  mode=reduced\n",
            f'  mode=reduced\n  venv="$repository/{SECOND_ENVIRONMENT}"\n',
        ),
        (
            "one assignment made to depend on the mode",
            f'venv="{ENVIRONMENT}"',
            'venv="$repository/.venv-$mode"',
        ),
    ):
        planted = GATE_TEXT.replace(was, becomes, 1)
        assert planted != GATE_TEXT, f"the plant for {mutation} changed nothing"
        assert _prepares_more_than_one_environment(planted), f"FAIL {mutation} was not caught"


def _runs_the_sign_off_check(text: str) -> list[str]:
    """Everything that would make this workflow's one stated exception prove nothing.

    One reading, shared by the green case and the plants below. Three things are required of
    the job and each alone would pass on a job that checked nothing: it runs the script, it
    is gated to a pull request — a push has no range, which resolves and answers 0 rather
    than 2 — and it checks the whole history out, since a shallow checkout has no range
    either.
    """
    problems: list[str] = []
    jobs = _jobs(text)
    if SIGN_OFF_JOB not in jobs:
        return [f"{WORKFLOW} defines no {SIGN_OFF_JOB} job: {sorted(jobs)}"]
    body = "\n".join(jobs[SIGN_OFF_JOB])
    if "scripts/check_developer_certificate_of_origin.py" not in body:
        problems.append("the job runs something other than the sign-off check")
    # The condition is held as a WHOLE LINE, not as a substring: a widening such as
    # `|| github.event_name == 'push'` keeps the substring and runs the script on a push,
    # against an empty range that resolves and reports that everything passed.
    if "    if: github.event_name == 'pull_request'\n" not in body:
        problems.append("the job is not gated to a pull request as a whole line")
    if "fetch-depth: 0" not in body:
        problems.append("a shallow checkout has no range to read")
    return problems


def test_the_workflow_runs_the_sign_off_check_on_every_pull_request() -> None:
    """`CONTRIBUTING.md` presents that script as the mechanism; this is where it runs.

    An obligation carried by a script nothing executes is an obligation held by nobody, and
    it passed unnoticed here for exactly as long as every commit of the branch happened to
    be signed.
    """
    assert _runs_the_sign_off_check(WORKFLOW_TEXT) == []


def test_the_sign_off_rule_catches_a_job_that_would_prove_nothing() -> None:
    """WATCHED FIRING, one planted mutation per thing the job is required to do."""
    for mutation, was, becomes in (
        (
            "the condition widened to a push",
            "    if: github.event_name == 'pull_request'\n",
            "    if: github.event_name == 'pull_request' || github.event_name == 'push'\n",
        ),
        (
            # Read out of the sign-off job's OWN stanza: the full job checks two siblings
            # out at full depth, so a plant aimed at the first occurrence of the line would
            # shorten a checkout this rule says nothing about and leave this one intact.
            "a shallow checkout",
            "          fetch-depth: 0\n      - name: Every commit certifies",
            "          fetch-depth: 1\n      - name: Every commit certifies",
        ),
        (
            "the check itself removed",
            "python scripts/check_developer_certificate_of_origin.py",
            "true # nothing to do",
        ),
    ):
        planted = WORKFLOW_TEXT.replace(was, becomes, 1)
        assert planted != WORKFLOW_TEXT, f"the plant for {mutation} changed nothing"
        assert _runs_the_sign_off_check(planted), f"FAIL {mutation} was not caught"


def test_the_sign_off_job_is_the_one_check_outside_the_gate() -> None:
    """The rule the gate jobs are held to is unchanged, and this is its stated exception.

    Any OTHER job running a script of this repository would be the defect that rule exists
    to catch: a check nobody can reproduce locally, deciding a merge.
    """
    outside = {
        identifier
        for identifier, lines in _jobs().items()
        if "scripts/" in "\n".join(lines) and "scripts/gate.sh" not in "\n".join(lines)
    }
    assert outside == {SIGN_OFF_JOB}, outside
    assert "the sign-off check" in WORKFLOW_TEXT, "the header does not state the exception"
