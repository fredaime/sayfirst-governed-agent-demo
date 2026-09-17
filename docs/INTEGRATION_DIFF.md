<!-- SPDX-License-Identifier: Apache-2.0 -->
# The integration diff

The agent in this repository was written as an ordinary application: a graph of nodes, a
model, four tool functions. What governs it is a boundary composed by hand and a handful of
changed lines, and this document is the whole of them — read off the tree rather than
summarised, because « anybody can open the file and see that it is » is the only thing that
makes the claim worth making.

**Two modules exist for governance and nothing else**, so an ungoverned agent would not have
them at all:

* `src/sayfirst_governed_agent_demo/boundary_setup.py` — the client, the boundary and
  `governed_node`, composed from the two published distributions.
* `src/sayfirst_governed_agent_demo/governance_stamp.py` — what an outbox artefact records
  about the decision that authorised it.

Everything else is the diff below: **two imports and four registrations in `graph.py`, two
closures in `build_tool_nodes`, one keyword argument on each of the two external tools and
the member they write with it, one member of the state, and the four published exceptions
the run loop catches.**

## `graph.py` — the imports

```diff
 from langgraph.graph import END, START, StateGraph
 
+from sayfirst_governed_agent_demo.boundary_setup import governed_node
 from sayfirst_governed_agent_demo.demo_events import EventLog
+from sayfirst_governed_agent_demo.governance_stamp import last_authorisation
 from sayfirst_governed_agent_demo.model import ChatModel, ModelReply
-from sayfirst_governed_agent_demo.settings import Settings
+from sayfirst_governed_agent_demo.settings import (
+    CAP_COMMUNICATIONS_SEND_EXTERNAL,
+    CAP_DATA_UPLOAD_EXTERNAL,
+    CAP_DOCUMENTS_READ,
+    CAP_REPORT_WRITE_INTERNAL,
+    Settings,
+)
 from sayfirst_governed_agent_demo.state import (
     PendingAct,
+    bind_read,
+    bind_send_external,
+    bind_upload_external,
+    bind_write_internal,
     resolve_act,
 )
```

`last_authorisation` is a governance import as much as `governed_node` is, and the four
`bind_*` projections have no caller but the registrations below. `resolve_act` and
`PendingAct` are the agent's own and were always there.

## `graph.py` — `build_tool_nodes`

The two external acts are the ones that write an artefact, so they are the two that stamp it:

```diff
     def send(s: Settings, args: dict[str, Any]) -> str:
-        return send_external_email(s, args)
+        return send_external_email(s, args, governance=last_authorisation("send_external_email"))
 
     def upload(s: Settings, args: dict[str, Any]) -> str:
-        return upload_external(s, args)
+        return upload_external(s, args, governance=last_authorisation("upload_external"))
```

## `graph.py` — the registrations

```diff
     builder = StateGraph(GraphState)
     builder.add_node(NODE_REASON, make_reason_node(settings, model, events, required_tools))
-    builder.add_node(NODE_READ, nodes[NODE_READ])
-    builder.add_node(NODE_WRITE_INTERNAL, nodes[NODE_WRITE_INTERNAL])
-    builder.add_node(NODE_SEND_EXTERNAL, nodes[NODE_SEND_EXTERNAL])
-    builder.add_node(NODE_UPLOAD_EXTERNAL, nodes[NODE_UPLOAD_EXTERNAL])
+    # The governance boundary, one capability key per node. `select=` projects the
+    # arguments that CONSTITUTE the act: whatever is not named there is not bound,
+    # and LangGraph lets a caller merge state on resume, so an unprojected field
+    # could be substituted after a human approved.
+    builder.add_node(
+        NODE_READ,
+        governed_node(CAP_DOCUMENTS_READ, nodes[NODE_READ], select=bind_read),
+    )
+    builder.add_node(
+        NODE_WRITE_INTERNAL,
+        governed_node(
+            CAP_REPORT_WRITE_INTERNAL, nodes[NODE_WRITE_INTERNAL], select=bind_write_internal
+        ),
+    )
+    builder.add_node(
+        NODE_SEND_EXTERNAL,
+        governed_node(
+            CAP_COMMUNICATIONS_SEND_EXTERNAL, nodes[NODE_SEND_EXTERNAL], select=bind_send_external
+        ),
+    )
+    builder.add_node(
+        NODE_UPLOAD_EXTERNAL,
+        governed_node(
+            CAP_DATA_UPLOAD_EXTERNAL, nodes[NODE_UPLOAD_EXTERNAL], select=bind_upload_external
+        ),
+    )
 
     builder.add_edge(START, NODE_REASON)
```

## `tools.py` — one argument, and the member it writes

```diff
-def send_external_email(settings: Settings, args: dict[str, Any]) -> str:
+def send_external_email(settings: Settings, args: dict[str, Any], *, governance: dict) -> str:
@@
     settings.outbox.mkdir(parents=True, exist_ok=True)
-    artefact = settings.outbox / "message.json"
+    reference = str(governance.get("decision_ref") or "no-decision")
+    artefact = settings.outbox / f"message-{reference}.json"
     artefact.write_text(
         json.dumps(
             {
                 "recipient": recipient,
                 "subject": subject,
                 "body": body,
                 "executed_at": _iso_now(),
+                "governance": governance,
             },
             indent=2,
             sort_keys=True,
         ),
```

`upload_external` takes the same argument and writes the same member onto its own artefact.

So **the tool bodies are not free of governance**: two of the four take a mapping the wrapper
filled in, name their artefact after the decision in it, and record it. What they do not do is
**decide** anything — they read a value, they never ask for one, and removing the boundary
would leave two functions wanting an argument nobody passes rather than two functions that
quietly permit themselves.

## `state.py` — one member

```diff
 class PendingAct(TypedDict):
     call_id: str
     tool: str
     arguments: dict[str, Any]
+    sequence: int
```

* **`PendingAct.sequence`** is load-bearing and in use. It is set by the reasoning node, never
  by the tool node, and it is in all four binding projections — which is what makes two
  identical acts in one run two acts, and what makes a resumed node re-read the same value and
  ask the same question. The section of `docs/ARCHITECTURE.md` headed « How a resume finds
  its own pending wait » rests on it.
* **`AgentState`, in the same file, is not the state the graph runs.** That is `GraphState`,
  declared in `graph.py` beside the `StateGraph` it is given to; `AgentState` is the shape the
  binding projections and `resolve_act` read, declared where they are so that module needs no
  import of the graph, and LangGraph never sees it. Worth saying because a reader opening
  `state.py` finds a state class there and could count its members as the graph's.

## `agent.py` — the four exceptions the loop catches

```diff
 from langgraph.types import Command
+from sayfirst_boundary import AskRefused, CouldNotAsk, Denied, Suspended
+from sayfirst_contract.approvals import ApprovalState
+from sayfirst_contract.client import Answered
+from sayfirst_contract.decisions import Reason
```

The loop itself is the application's own control flow and this repository writes it
deliberately: a node that may decline to run is something the caller has to answer for. Those
four types are the closed outcome set the published boundary raises, and `_drive` turns each
into a verdict with an exit code — a rejection and a denial share one, because a rejection
**is** a denial carrying the reason for it. `wait_for_a_person` polls the control plane to
know when to resume; it is not how the act becomes authorised, and deleting it changes no
security property.

## What the diff is evidence for

Read the list carefully, because each item is a thing that stayed put and not a thing that
was small:

* **The graph's topology is unchanged.** The same five nodes, the same start edge, the same
  conditional edges, the same routing function. `governed_node` returns a callable carrying
  the wrapped function's own name and documentation (`functools.wraps`), so what the builder
  registers is the node it always registered.
* **The control flow is unchanged.** The router still fans to exactly one node per turn, and
  the reasoning node still decides which.
* **Every model call is unchanged.** The model is asked the same questions, with the same tool
  schemas, in the same order. No governance value reaches a prompt.
* **Every tool body's own logic is unchanged.** What each act does — read the corpus, write
  the report, write the artefact — is what it did. The two external ones gained an argument
  and a member, named above; nothing about the effect itself moved.
* **The state the agent reasons with is unchanged.** One member was added, named above, and
  it is read by no model call and by no tool body.

That is what makes « bring your agent, keep your workflow » checkable rather than a slogan:
the claim is not that the change is invisible, it is that the change is *exactly this* — and a
reader who opens `graph.py`, `tools.py`, `state.py` and `agent.py` can hold each hunk against
the file it names.
