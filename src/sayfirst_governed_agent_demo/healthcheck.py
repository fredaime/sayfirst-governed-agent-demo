# SPDX-License-Identifier: Apache-2.0
"""`./scripts/check-demo.sh` — is this machine ready to record a take?

Every line is an OBSERVATION, made against the running system, in the order a take depends
on them. Nothing here is inferred from configuration.

Three values and not two, because one of the things worth reporting is neither a pass nor a
failure: a check that could not be made says so and fails, and a facility that is not
configured at all — a model, in the default mode — is reported as absent rather than as
either. « Not observed » is never rendered as « OK ».

One limit is stated rather than worked around. This generation of the contract serves no
per-capability policy read, so « documents.read is allowed » cannot be observed from out
here; what can be, and is, is that the daemon loaded a policy of the right format with the
right number of rules. Which answer each capability gets is exercised end to end by the
acceptance suite, against a real daemon, which is where a claim about a decision belongs.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from sayfirst_contract.client import Answered

from sayfirst_governed_agent_demo.settings import (
    ConfigurationError,
    ModelMode,
    Settings,
    load_settings,
)
from sayfirst_governed_agent_demo.tools import corpus, outbox_count

GREEN = "\033[38;5;118m"
RED = "\033[31m"
AMBER = "\033[38;5;214m"
DIM = "\033[2m"
RESET = "\033[0m"

#: How many rules the policy this demonstration ships carries.
EXPECTED_RULES = 4


@dataclass
class Check:
    #: `True` observed and good, `False` observed and bad, `None` not observed at all.
    ok: bool | None
    label: str
    detail: str = ""


def _reader(settings: Settings):
    """A client for this one run of checks, composed the way the agent composes its own."""
    from sayfirst_contract.binding.http_unix_socket.client import SocketClient
    from sayfirst_contract.transport.socket_client import SocketProfile, expected_principal_uid

    profile = SocketProfile(str(settings.socket_path), scope=settings.scope)
    return SocketClient(
        socket_path=Path(settings.socket_path),
        expected_uid=expected_principal_uid(profile),
        timeout=5.0,
    )


def run_checks(settings: Settings) -> list[Check]:
    checks: list[Check] = []

    if not settings.socket_path.exists():
        checks.append(
            Check(
                False,
                f"the control plane is listening ({settings.socket_path})",
                "nothing is at that address — run ./scripts/start-control-plane.sh",
            )
        )
        return checks

    reader = _reader(settings)

    identity = reader.read_whoami()
    if isinstance(identity, Answered):
        who = identity.value
        # The principal is read INSIDE the established branch and nowhere else. The contract
        # types it as optional, and an identity that is not established is exactly the answer
        # that may carry none — so a check written to print a failure line must not raise
        # while composing the label of that very line.
        established = who.status == "established" and who.principal is not None
        if established:
            checks.append(
                Check(True, f"the control plane knows who is calling ({who.principal.name})")
            )
        else:
            missing = "" if who.principal is not None else ", and it names no principal"
            checks.append(
                Check(
                    False,
                    "the control plane knows who is calling",
                    f"the identity is {who.status!r}{missing}",
                )
            )
        checks.append(Check(who.mode == "per_user", f"the daemon is in per-user mode ({who.mode})"))
    else:
        checks.append(Check(False, "the control plane answers", str(identity.problem.message)))
        return checks

    served = reader.read_status()
    if isinstance(served, Answered):
        checks.append(
            Check(
                True,
                f"contract generation {served.value.contract_generation}",
                f"integrity grade {served.value.integrity_grade.grade}",
            )
        )
    else:
        checks.append(Check(False, "the daemon reports its status", str(served.problem.message)))

    policy = reader.read_policy_status()
    if isinstance(policy, Answered):
        right = policy.value.format == 1 and policy.value.rule_count == EXPECTED_RULES
        checks.append(
            Check(
                right,
                f"a policy of {EXPECTED_RULES} rules is loaded (format {policy.value.format})",
                "" if right else f"the daemon loaded {policy.value.rule_count} rule(s)",
            )
        )
        checks.append(Check(True, f"policy version {policy.value.policy_version[:23]}..."))
    else:
        checks.append(Check(False, "the policy authority answers", str(policy.problem.message)))

    if settings.model.mode is ModelMode.fixture:
        checks.append(
            Check(
                None,
                "no model is configured (MODEL_MODE=fixture)",
                "a take needs MODEL_MODE=real with MODEL_BASE_URL and MODEL_NAME",
            )
        )
    else:
        import httpx

        try:
            answer = httpx.get(f"{settings.model.base_url}/models", timeout=5.0)
            answer.raise_for_status()
            names = {served.get("id") for served in answer.json().get("data", [])}
            present = settings.model.name in names
            checks.append(
                Check(
                    present,
                    f"the model is served ({settings.model.name})",
                    ""
                    if present
                    else f"the endpoint is up and does not serve {settings.model.name}",
                )
            )
        except httpx.HTTPError as exc:
            checks.append(
                Check(
                    False, "the model is served", f"{settings.model.base_url}: {type(exc).__name__}"
                )
            )

    count = outbox_count(settings)
    checks.append(
        Check(
            count == 0,
            "the outbox is empty",
            "" if count == 0 else f"{count} artefact(s) — run ./scripts/reset-demo.sh",
        )
    )
    documents = corpus(settings)
    checks.append(
        Check(
            bool(documents),
            f"the research corpus is present ({len(documents)} documents)",
            "" if documents else f"nothing under {settings.demo_data}",
        )
    )
    return checks


def main() -> int:
    try:
        settings = load_settings()
    except ConfigurationError as unusable:
        # The treatment the run itself gives this, for the same reason: a check made against
        # a configuration that cannot resolve has exactly one useful thing to say, and it is
        # the sentence the refusal composed — not the stack that carried it here.
        #
        # And the same CODE the run answers with, which is 7 and not 1: a setting that will
        # not resolve is a different fact from an observation that came back negative, and 1
        # is already this check's own « NOT READY ». A caller that read one as the other
        # would report a machine as unready when nothing about it had been observed at all.
        print(f"\n{RED}{unusable}{RESET}\n", file=sys.stderr, flush=True)
        return 7
    checks = run_checks(settings)
    print()
    for check in checks:
        if check.ok is True:
            mark = f"{GREEN}[OK]{RESET}"
        elif check.ok is False:
            mark = f"{RED}[--]{RESET}"
        else:
            mark = f"{AMBER}[ ?]{RESET}"
        detail = f"  {DIM}{check.detail}{RESET}" if check.detail else ""
        print(f"  {mark} {check.label}{detail}")
    failed = [check for check in checks if check.ok is False]
    absent = [check for check in checks if check.ok is None]
    print()
    if failed:
        print(f"  {RED}NOT READY{RESET} — {len(failed)} check(s) did not pass\n")
        return 1
    if absent:
        print(f"  {GREEN}READY{RESET}, and {len(absent)} thing(s) are not configured\n")
        return 0
    print(f"  {GREEN}DEMO READY{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
