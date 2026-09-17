# SPDX-License-Identifier: Apache-2.0
"""The reasoning engine: one OpenAI-compatible transport, plus a scripted stand-in.

Deliberately NOT a provider abstraction, and that is a decision this module
owns rather than inherits. vLLM, Ollama and every other OpenAI-compatible
server differ only in `base_url` and `model`, so one client covers all of them
and a second implementation would be dead weight.

The scripted model exists for tests only. `MODEL_MODE=real` never falls back to
it: an inference endpoint that cannot be reached is a loud startup failure and
never a quiet substitution, because a demonstration that degraded silently
would be showing governance over a model that was never in the loop.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from sayfirst_governed_agent_demo.settings import ModelMode, ModelSettings


class ModelUnavailable(RuntimeError):
    """The configured inference endpoint could not answer. Never swallowed."""


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelReply:
    """One assistant turn: free text, tool calls, or both."""

    content: str
    tool_calls: tuple[ToolCall, ...] = ()

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class ChatModel(Protocol):
    #: What the terminal prints and the event stream records. Part of the contract
    #: because this demonstration names the model wherever it says anything about a
    #: turn -- and those two are where it says it: there is no interface beyond the
    #: terminal, and no evidence record carries a model name.
    identity: str

    def complete(
        self, messages: Sequence[dict[str, Any]], tools: Sequence[dict[str, Any]]
    ) -> ModelReply: ...


#: The keys a doubly-wrapped tool call carries beside its real arguments. Small
#: instruct models regularly emit `{"arguments": {...}, "type": "<tool name>"}`
#: instead of the argument object itself.
_ENVELOPE_KEYS = {"arguments", "type", "name", "parameters"}


def _unwrap(arguments: dict[str, Any]) -> dict[str, Any]:
    """Undo a doubly-wrapped argument object, conservatively.

    This normalises TRANSPORT SHAPE, never content: the model chose the tool and
    wrote these arguments, and nothing here supplies, renames or defaults a
    value it did not send. The unwrap fires only when the outer object carries
    nothing but envelope keys, so a tool that legitimately takes a parameter
    called `arguments` is never unwrapped out from under itself.
    """
    inner = arguments.get("arguments")
    if isinstance(inner, dict) and set(arguments) <= _ENVELOPE_KEYS:
        return inner
    return arguments


def _parse_arguments(raw: Any) -> dict[str, Any]:
    """Tool arguments as a dict, whatever shape the server chose to send them in.

    Servers disagree: some send a JSON string, some send an object. A model that
    emits malformed JSON is a model failure the agent must see, so this raises
    rather than guessing at an empty argument set -- executing a tool with
    invented arguments would be worse than failing the turn.
    """
    if isinstance(raw, dict):
        return _unwrap(raw)
    if raw is None or raw == "":
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ModelUnavailable(f"the model emitted unparseable tool arguments: {raw!r}") from exc
    if not isinstance(parsed, dict):
        raise ModelUnavailable(f"tool arguments must be an object, got {type(parsed).__name__}")
    return _unwrap(parsed)


class OpenAICompatibleModel:
    """A tool-calling model behind any OpenAI-compatible `/chat/completions`."""

    def __init__(self, settings: ModelSettings) -> None:
        self._settings = settings
        self.identity = settings.display_name
        headers = {"Content-Type": "application/json"}
        if settings.api_key:
            headers["Authorization"] = f"Bearer {settings.api_key}"
        self._client = httpx.Client(base_url=settings.base_url, headers=headers, timeout=180.0)

    def probe(self) -> None:
        """Fail loudly, at startup, with the fix in the message.

        An endpoint that cannot answer is a refusal a reader can act on, and the
        sentence below names the address that was tried and says that nothing was
        substituted for it.
        """
        try:
            response = self._client.get("/models")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ModelUnavailable(
                f"the inference endpoint at {self._settings.base_url} could not answer "
                f"({type(exc).__name__}). Nothing degrades to a transcript: a "
                f"demonstration of governance over a model that was never there would be "
                f"showing nothing."
            ) from exc

    def complete(
        self, messages: Sequence[dict[str, Any]], tools: Sequence[dict[str, Any]]
    ) -> ModelReply:
        payload: dict[str, Any] = {
            "model": self._settings.name,
            "messages": list(messages),
            "temperature": self._settings.temperature,
        }
        if tools:
            payload["tools"] = list(tools)
            payload["tool_choice"] = "auto"
        try:
            response = self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPError as exc:
            raise ModelUnavailable(
                f"the inference endpoint at {self._settings.base_url} could not answer "
                f"({type(exc).__name__}). Nothing degrades to a transcript: a "
                f"demonstration of governance over a model that was never there would be "
                f"showing nothing."
            ) from exc
        except ValueError as exc:
            raise ModelUnavailable("the inference endpoint returned a non-JSON body") from exc

        try:
            message = body["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelUnavailable(f"unrecognised completion shape: {body!r}") from exc

        calls = tuple(
            ToolCall(
                id=str(call.get("id") or f"call_{index}"),
                name=str(call["function"]["name"]),
                arguments=_parse_arguments(call["function"].get("arguments")),
            )
            for index, call in enumerate(message.get("tool_calls") or [])
        )
        return ModelReply(content=(message.get("content") or "").strip(), tool_calls=calls)


@dataclass
class ScriptedModel:
    """A deterministic transcript. Tests only -- never reachable in demo mode.

    Each entry is consumed in order; the last one repeats, so a graph that loops
    one turn longer than the script anticipated ends rather than hanging.
    """

    replies: list[ModelReply]
    identity: str = "scripted transcript (no model)"
    calls: list[tuple[Any, ...]] = field(default_factory=list)
    _cursor: int = 0

    def complete(
        self, messages: Sequence[dict[str, Any]], tools: Sequence[dict[str, Any]]
    ) -> ModelReply:
        self.calls.append((tuple(m.get("role", "") for m in messages),))
        if not self.replies:
            return ModelReply(content="")
        index = min(self._cursor, len(self.replies) - 1)
        self._cursor += 1
        return self.replies[index]


def build_model(settings: ModelSettings) -> ChatModel:
    """The one place the mode decides which engine runs, and says so loudly."""
    if settings.mode is ModelMode.fixture:
        raise ConfigurationRefused(
            "MODEL_MODE=fixture builds no model here: the scripted transcript is the "
            "tests' own, constructed by the test that scripts it. To watch this agent "
            "reason, set MODEL_MODE=real with MODEL_BASE_URL and MODEL_NAME."
        )
    model = OpenAICompatibleModel(settings)
    model.probe()
    return model


class ConfigurationRefused(RuntimeError):
    """A mode that cannot produce a usable model in this call path."""
