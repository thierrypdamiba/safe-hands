# Safe Hands

**Asimov's Three Laws of Robotics, compiled to real authorization policy — the missing safety layer for AI agents that touch the physical world.**

> *"The model reasons. The runtime governs."* — now for things that can hurt you.

![Safe Hands demo — an arm obeying the operator, then refused by the First and Third Laws](safe_hands.gif)

*The agent asks; the runtime decides. Obey the operator (Second Law) — unless it endangers a human (First Law) or destroys the robot (Third Law). Every action is authorized and audited.*

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

## Run it

```bash
pip install cedarpy mcp mujoco imageio pillow

python3 demo.py            # the governed sequence, in your terminal
python server.py --smoke   # the same, through the MCP tools
python render.py           # regenerate safe_hands.gif
python server.py           # run as a real MCP server (stdio) — add it to any MCP client
```

As an MCP server it exposes 8 governed tools — `move_joint`, `grasp`, `release`,
`emergency_stop`, `disable_safety`, `get_state`, `human_presence`, `audit`. The agent never
gets to *assert* whether a human is present; the runtime reads that from the sensed world and
enforces the First Law itself.

## What's here
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
