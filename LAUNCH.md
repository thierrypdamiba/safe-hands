# Launch pack — Safe Hands (the last mile is yours)

Everything's built and committed locally. To make it *public* (which is what the goal counts as
progress), it's one command + one post. I can't do these — they need your identity.

## 1. Publish the repo (one command)
```bash
cd ~/safe-hands
gh repo create safe-hands --public --source=. --remote=origin --push
```
Then set the repo's social preview to `safe_hands.gif` so the card animates.

## 2. The X / Twitter thread (paste, attach safe_hands.gif to tweet 1)

**1/** Every "AI agent controls a robot" demo has the same terrifying hole: it authenticates
*nothing*. Anyone who reaches the server can command the arm. For a chatbot that's a bug. For a
2-kilo arm swinging near a person, it's the whole problem. So I built the missing layer. 🧵 [GIF]

**2/** **Safe Hands** — Asimov's Three Laws of Robotics, compiled to *real* authorization policy
(Cedar). The agent asks; the runtime decides: obey the operator — unless it endangers a human
(First Law) or destroys the robot (Third Law). Every action authorized + audited.

**3/** The elegant part: **Cedar's "forbid overrides permit" *is* Asimov's law priority.** Law 1
(a `forbid`) beats Law 2 (a `permit`). Not a metaphor — it's literally how the policy engine
resolves the decision.

**4/** The honest part: Asimov's Laws are famously unenforceable *as written* — his whole catalog
is stories about them failing. So Safe Hands keeps the Laws as the framing and enforces their
*checkable shadow*: no fast moves near a sensed human, no disabling safety, no self-destruction.

**5/** It's a real **MCP server** — drop it into any agent. And the agent can't even *lie* about
whether a human is present: the runtime senses that and enforces the First Law itself.

**6/** Physical actions are the highest-stakes actions an agent can take — exactly where the
*runtime*, not the model, has to govern. Code + the arm obeying and refusing:
github.com/thierrypdamiba/safe-hands

## 3. LinkedIn version
AI agents are about to get hands — and almost every "agent controls a robot" demo authenticates
nothing. Anyone who reaches the server can command the arm.

So I built **Safe Hands**: Asimov's Three Laws of Robotics, compiled to *real* authorization
policy with Cedar, exposed as an MCP server. The agent asks; the runtime governs — obey the
operator, unless it would endanger a human or destroy the robot — and audits every action. The
neat bit: Cedar's "forbid overrides permit" turns out to *be* Asimov's law priority.

Physical actions are the highest-stakes actions an agent can take. That's where the runtime, not
the model, has to hold the line. [repo + GIF]

## 4. Who to tag / send it to (warm, value-first)
- NVIDIA robotics DevRel (the Isaac/GR00T developer-advocacy folks) — this is on-theme for them.
- The Cedar / authorization crowd (it's a genuinely novel use of the language).
- Robot-MCP builders (phosphobot, the robotmcp org, LeRobot Discord) — you're filling the auth
  gap their demos all have.
- Arcade colleagues (Alex Salazar, Sam Partee) — it extends the company's "the runtime governs"
  thesis to the physical world.
