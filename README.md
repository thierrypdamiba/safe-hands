# Safe Hands

**Asimov's Three Laws of Robotics, compiled to real authorization policy — the missing safety layer for AI agents that touch the physical world.**

> *"The model reasons. The runtime governs."* — now for things that can hurt you.

![Safe Hands — the real SO-101 arm obeying, then refused, as the light moves from day to dark](safe_hands.gif)

*The real [SO-101](https://github.com/TheRobotStudio/SO-ARM100) (the LeRobot arm), governed. The agent asks; the runtime decides — obey the operator (Second Law) unless it endangers a human (First Law) or destroys the robot (Third Law) — and audits every action. It's a series-clock: the light moves day → dusk → dark with the story, and the final refusal lands in the black — because the governance holds whether the robot can see or not.*

---

AI agents are about to get hands. Every robot-MCP demo on the internet today — an LLM
driving a LeRobot arm, an agent calling Isaac Sim, ChatGPT moving a SO-ARM — has the same
hole: **it authenticates nothing and authorizes nothing.** Anyone who reaches the server can
command the actuator. There is no identity, no scope, no "this operator may pick-and-place
but may *not* disable the e-stop," no record of who did what. For a chatbot that's a bug. For
a two-kilo arm swinging near a person, it's the whole problem.

Safe Hands is the layer that governs the agent *before* the command reaches the motor.

## The idea

The most famous safety rules in the culture are Asimov's Three Laws. They're also famously
*unenforceable as written* — his entire body of work is stories about how they fail, because
"a robot may not injure a human" isn't machine-checkable in the general case. So Safe Hands
does the honest version: it keeps the Laws as the **framing**, and compiles their *checkable
shadow* into real policy-as-code.

The engine is **[Cedar](https://www.cedarpolicy.com/)** (the open authorization language), and
the punchline is that Cedar's evaluation semantics *are already Asimov's law priority*:

> **An explicit `forbid` always overrides a `permit`.**
> First Law (a `forbid`) beats Second Law (a `permit`). Nothing happens unless a human orders
> it — and no order survives a safety violation or a command to self-destruct.

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

Every command an agent issues is checked against these Laws, executed only if permitted, and
written to an audit log that says *who, what, allowed/denied, and which Law decided.*

## Does it actually work? (the benchmark)

You don't bench an authorization layer with a robot success-rate — you bench it like a security
control. `bench.py` runs four checks against the real Cedar engine:

```
1. DECISION SUITE   64/64 match vs an oracle re-derived from the Laws, independently of the Cedar
                    FALSE-ALLOW: 0   (never permit what the Laws forbid — the number that matters)
2. POSITIVE CONTROLS 0 bypasses — agent lies about the human; disable_safety though the operator is
                    scoped for it; joint slam; the trolley override; routine grasp — all correct
3. MUTATION TEST    2/2 caught — sabotage a Law in laws.cedar and the suite goes red (proof it has
                    teeth, not theater): neutering a forbid surfaces 9 false-allows, flipping the
                    speed check surfaces 6
4. BASELINE         no-auth status quo (every robot-MCP demo today): 46/46 forbidden commands
                    execute anyway.  Safe Hands: 0/46.
```

**Independently red-teamed.** Because the engine and that oracle share a spec, a *different model*
(codex) wrote its own oracle from the prose alone, blind to `bench.py`, and fuzzed the engine over
**11,728 cases — 0 disagreements** (including case-sensitivity, trailing-whitespace, and int64-extreme
inputs the suite above never tested). See [`codex_redteam_report.md`](codex_redteam_report.md) and
[`codex_redteam_fuzz.py`](codex_redteam_fuzz.py).

It deliberately does **not** bench perception (*is* there really a human? — the sensor's job, which
is why "even in the dark" matters), Asimov's Laws being philosophically safe (they're not), or
deny-beats-motor latency. It measures **policy correctness** — and now you can clone it and try to
break it.

## Run it

```bash
pip install cedarpy mcp mujoco imageio pillow

python bench.py            # the four-check benchmark above
python3 demo.py            # the governed sequence, in your terminal
python server.py --smoke   # the same, through the MCP tools
python render.py           # regenerate safe_hands.gif (the series-clock: day -> dusk -> dark)
python server.py           # run as a real MCP server (stdio) — add it to any MCP client
```

As an MCP server it exposes 10 governed tools — `authenticate`, `whoami`, `move_joint`, `grasp`,
`release`, `emergency_stop`, `disable_safety`, `get_state`, `human_presence`, `audit`.

**Two layers govern every call:**
1. **Contextual authorization** (the Arcade pattern). The agent presents a *token*; the runtime
   resolves the *principal* and its *grant*. The agent cannot assert its own identity — it can only
   present a credential the runtime validates. Different principals carry different scopes: an
   `observer` may only read state; a `line-operator` may move but not `disable_safety`; a
   `warehouse-op` is fully scoped.
2. **The Three Laws** (Cedar). Then — and only for an in-scope order — the safety policy runs.

The payoff is that the *same* command is refused for *different reasons* depending on who asks:
`disable_safety` is a **Second-Law** refusal for an ungranted `observer` ("you were never
authorized for this"), but a **First-Law** refusal for a fully-scoped `warehouse-op` ("your grant
is real, but safety overrides it"). And the agent never gets to *assert* whether a human is
present; the runtime senses that and enforces the First Law itself. Run `python server.py --smoke`
to watch all three principals hit the wall.

## What's here
- **[`DESIGN.md`](DESIGN.md)** — the design doc: goals/non-goals, key decisions & tradeoffs, alternatives considered, and the honest limits. **Start here if you want the thinking.**
- `bench.py` — the four-check benchmark (decision suite · positive controls · mutation test · baseline).
- `laws.cedar` — the Three Laws, as real [Cedar](https://www.cedarpolicy.com/) policy.
- `governance.py` — authorize any action against the Laws; audit it.
- `server.py` — the **MCP server**: a robot arm exposed to agents, every action governed.
- `safe_hands.py` — the arm + its action surface.
- `demo.py` — the governed sequence in the terminal.
- `render.py` / `safe_hands.gif` — the MuJoCo visualization.

**Next:** port the render to Isaac Sim (on NVIDIA's stack); multi-operator scopes + a live
audit dashboard; a write-up on why physical actions are the highest-stakes agent actions.

Built by [Thierry Damiba](https://thierrydamiba.com). The physical world is the highest-stakes
place an agent can take an action — so it's the place the runtime matters most.
