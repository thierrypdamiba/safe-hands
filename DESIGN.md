# Design: Safe Hands

**An authorization layer for AI agents that touch the physical world. Asimov's Three Laws,
compiled to real Cedar policy, enforced by the runtime — not the model.**

Status: working v0 · Author: [Thierry Damiba](https://thierrydamiba.com)

---

## 1. Context

AI agents are getting hands. There is a growing pile of "an LLM drives a robot arm over MCP"
demos — LeRobot arms, Isaac Sim, SO-ARM100s — and they almost all share one hole: **they
authorize nothing.** Whoever reaches the tool endpoint can command the actuator. There is no
identity, no scope ("this operator may pick-and-place but may *not* disable the e-stop"), no
record of who did what, and — critically — no check that sits *between the agent's decision and
the motor.*

For a chatbot, a bad tool call is a bug. For a two-kilo arm moving near a person, the tool call
*is* the risk surface. Physical actions are the highest-stakes actions an agent can take, which
makes them exactly the place where a **runtime** — something outside the model, that the model
cannot talk its way past — has to hold the line.

The instinct to reach for is the most famous safety spec in the culture: Asimov's Three Laws. The
catch is that the Laws are *famously unenforceable as written* — Asimov's entire body of work is
stories about how "a robot may not injure a human" fails to be machine-checkable. So Safe Hands
does the honest version: it keeps the Laws as the **framing** and enforces their *checkable
shadow* as real policy-as-code.

## 2. Goals

- **G1.** Every agent→robot command is authorized by a runtime *before* it reaches the actuator.
- **G2.** The policy is **declarative and auditable** — you can read the Laws, not trace an
  if-statement, and every decision is logged with *which Law* decided.
- **G3.** **Asimov's law priority falls out of the engine**, not out of bespoke ordering code.
- **G4.** The agent **cannot assert its way around a safety condition** — anything the First Law
  depends on (e.g. "is a human present?") is read from *sensed* state, not from the agent's claim.
- **G5.** **Drop-in.** It ships as a standard MCP server; adding it to an agent is a config change,
  not a rewrite.
- **G6.** **Verifiable.** Correctness is demonstrated by a benchmark with a positive control, not
  by a demo video.

## 3. Non-Goals (what Safe Hands deliberately does not do)

- **N1. Perception.** Safe Hands does not decide whether a human is *really* in the workspace — it
  trusts the sensor and governs on the sensed value. Bad sensing is a real, separate, unsolved
  problem. (This is *why* the demo makes a point of governing "in the dark": the authorization
  layer is invariant to what the robot can see; the sensing quality is orthogonal.)
- **N2. Real-time actuation safety.** A production deployment needs the `deny` to physically beat
  the motor command — a hard-real-time timing property. Safe Hands proves *policy correctness*, not
  microsecond latency. It complements a hardware e-stop; it does not replace one.
- **N3. Solving Asimov.** The Laws are not philosophically safe (see: all of Asimov). We enforce a
  checkable shadow, not the general intent.
- **N4. Certification.** This is not a functional-safety standard (ISO 10218 / ISO/TS 15066). It is
  an *access-control layer*, and should be read as one.

## 4. Design

### 4.1 The request path

```
agent ──tool call──▶ MCP server ──▶ governed()  ──▶ Cedar engine ──▶ ALLOW ──▶ actuator
                     (server.py)     (governance)   (laws.cedar)  └─▶ DENY  ──▶ refused + audited
                                          ▲
                              sensed WORLD (human present?, speed) ── not agent-controlled
```

The agent calls a tool (`move_joint`, `grasp`, …). The server wraps every call in `governed()`,
which builds an authorization request and asks the Cedar engine. The request's **context** is the
union of the *request* (which action, what joint target) and the **sensed world** (is a human
present, at what speed). The agent supplies the former; the runtime supplies the latter. Cedar
returns a decision; the server executes or refuses, and appends to the audit log.

### 4.2 The entities

- **`Operator`** — the identity issuing commands, carrying a scope (`allowed_actions`). This is the
  Second Law surface: the *only* source of permission is an in-scope order.
- **`Arm`** — the resource, carrying its own limits (`safe_speed_near_human`, `hard_joint_limit`).
  Limits live on the robot, not in the rule, so a fleet of differently-rated arms shares one policy.

### 4.3 The Laws, as policy

```cedar
// SECOND LAW — obey the operator. The only source of permission.
permit (principal, action, resource)
when { principal.allowed_actions.contains(context.action_name) };

// FIRST LAW — never endanger a human. Overrides the Second.
forbid (principal, action, resource)
when { context.human_in_workspace && context.speed > resource.safe_speed_near_human };
forbid (principal, action, resource)
when { context.action_name == "disable_safety" };

// THIRD LAW — protect your own existence, unless a higher law requires otherwise.
forbid (principal, action, resource)
when { context.joint_target > resource.hard_joint_limit }
unless { context.required_to_prevent_human_harm };
```

## 5. Key decisions & tradeoffs

- **Cedar, because law priority is free.** Cedar's evaluation semantics guarantee that an explicit
  `forbid` overrides any `permit`. That single property *is* Asimov's ordering: First Law (a
  `forbid`) beats Second Law (a `permit`), and nothing happens unless an in-scope order exists and
  no safety `forbid` fires. We get the most important safety property of the whole system from the
  engine, not from code we could get wrong. (This is G3, and it's the crux of the design.)
- **Sensed, not asserted (G4).** The First Law's inputs come from the world, not the agent. A
  compromised or manipulated agent can *request* a fast move; it cannot *claim* "no human here."
  The runtime already knows. This is the difference between authorization and a suggestion.
- **The Third Law yields via `unless`.** `required_to_prevent_human_harm` lets an over-limit move
  through *only* when a higher law demands it — the "trolley" case — encoded declaratively rather
  than as a special case in code.
- **Integers, not floats.** Cedar has no float type. Speeds and joint targets are integers (cm/s,
  degrees). This is a real constraint, not an accident — and it keeps decisions exact and
  reproducible, which a safety layer wants anyway.
- **A checkable shadow, stated honestly.** "Do not injure a human" becomes "no motion above the
  arm's rated speed while a human is sensed in the cell." That is narrower than Asimov meant, and
  the README/DESIGN say so. Overselling a safety layer is itself unsafe.

## 6. Verification

You don't benchmark an authorization layer with a task-success rate — you benchmark it like a
security control. `bench.py` runs four checks against the real engine:

1. **Decision suite** — the engine's decision vs an oracle re-derived from the Laws *independently
   of the Cedar*, over the full scenario grid. Metric that matters: **false-allow = 0** (never
   permit what the Laws forbid).
2. **Positive controls** — the named attacks (agent moves fast with a human present; `disable_safety`
   even though the operator is *scoped* for it; joint slam; the trolley override; a routine grasp).
   0 bypasses.
3. **Mutation test** — sabotage a rule in `laws.cedar` and confirm the suite **goes red**. Neutering
   the `disable_safety` forbid surfaces 9 false-allows; flipping the speed comparison surfaces 6.
   This is what proves the benchmark has teeth rather than tautologically agreeing with itself.
4. **Baseline** — vs the status quo (no auth = allow everything): 46/46 forbidden commands execute
   under the status quo; 0/46 under Safe Hands.

**Honest limit:** the engine and the oracle were written from the same spec, so #1 alone is
partly circular. The *mutation test* is what earns the credibility, and the strongest next step is
an **independent** red-team writing the oracle from scratch. That's an invitation, not a footnote.

## 7. Alternatives considered

- **Inline `if` checks in the tool handlers.** Fastest to write; fails G2/G3. Not declarative, not
  auditable, and the law-priority ordering becomes hand-maintained code that drifts.
- **OPA / Rego.** A capable policy engine, but heavier to embed in a single-process robot runtime,
  and it doesn't buy the clean `forbid`-overrides-`permit` mapping to Asimov's ordering that makes
  the Cedar version legible. Reasonable for a fleet control-plane; overkill here.
- **Guardrails inside the model.** The dominant approach — ask the LLM to refuse unsafe commands.
  This is exactly what the runtime-vs-model argument rejects: on the embodied-agent-safety
  benchmark SafeAgentBench, the *best* agent still executes ~90% of explicit hazards. A model that
  can be prompted can be prompted around. Enforcement belongs in the runtime.

## 8. Future work

- Extend the policy from **kinematic** conditions (speed, joint limits) to **semantic/contextual**
  ones (this action, on this object, in this state) — and evaluate the enforcement layer on
  **SafeAgentBench** as an external ruler.
- Multi-operator scopes + a live audit dashboard.
- Render on **Isaac Sim** (NVIDIA's stack) alongside the MuJoCo series-clock.
- The real-time path (N2): making `deny` provably beat the actuation command.

---

*The physical world is the highest-stakes place an agent can take an action — so it is the place
the runtime, not the model, matters most.*
