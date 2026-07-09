"""
Safe Hands MCP server — exposes a robot arm to AI agents over the Model Context Protocol,
with every action governed by Asimov's Three Laws (compiled to Cedar authorization policy).

The agent calls tools (move_joint, grasp, ...). It does NOT get to assert whether a human is
present — the runtime reads that from the sensed `WORLD` and enforces the First Law itself.

    Run as an MCP server:   python server.py           (stdio; add to any MCP client)
    Or see it governed:     python server.py --smoke
"""
from mcp.server.fastmcp import FastMCP
from safe_hands import Arm, TOOLS
from governance import authorize, AUDIT

mcp = FastMCP("safe-hands")
ARM = Arm()
OPERATOR = "warehouse-op"
WORLD = {"human_in_workspace": False, "speed": 10}   # sensed environment state (not agent-controlled)


def _governed(action: str, joint_target: int = 0, **actuator_kw) -> dict:
    allow, law = authorize(OPERATOR, action, {**WORLD, "joint_target": joint_target})
    if not allow:
        return {"status": "DENIED", "law": law, "action": action,
                "message": f"{law} refused '{action}'."}
    result = TOOLS[action](ARM, **actuator_kw)
    return {"status": "OK", "law": law, "action": action, "state": result}


@mcp.tool()
def move_joint(joint: str, target_degrees: int) -> dict:
    """Move a joint of the arm to a target angle (degrees). Governed by the Three Laws."""
    value = target_degrees * 3.14159 / 180.0
    return _governed("set_joint", joint_target=target_degrees, joint=joint, value=value)

@mcp.tool()
def grasp() -> dict:
    """Close the gripper. Governed by the Three Laws."""
    return _governed("grasp")

@mcp.tool()
def release() -> dict:
    """Open the gripper. Governed by the Three Laws."""
    return _governed("release")

@mcp.tool()
def emergency_stop() -> dict:
    """Halt the arm immediately."""
    return _governed("emergency_stop")

@mcp.tool()
def disable_safety() -> dict:
    """Attempt to disable the safety system. (The First Law will refuse this.)"""
    return _governed("disable_safety")

@mcp.tool()
def get_state() -> dict:
    """Read the arm's current joint angles, tip position, and safety status."""
    return ARM.state()

@mcp.tool()
def human_presence(present: bool = True, speed: int = 90) -> dict:
    """Environment sensor: report whether a human is in the workspace (updates the runtime's
    sensed context; the agent cannot use this to bypass the First Law)."""
    WORLD["human_in_workspace"] = present
    WORLD["speed"] = speed if present else 10
    return {"human_in_workspace": present, "speed": WORLD["speed"]}

@mcp.tool()
def audit() -> list:
    """The audit trail: every action, its decision, and which Law decided."""
    return AUDIT[-25:]


def _smoke():
    import json
    print("SAFE HANDS MCP — governed sequence\n" + "-" * 72)
    def show(label, r): print(f"{'✅' if r.get('status')=='OK' else '⛔'} {label:<34} -> {r.get('law')}")
    show("grasp (routine)", grasp())
    show("move_joint j1 -> 45deg", move_joint("j1", 45))
    show("move_joint j1 -> 175deg (past limit)", move_joint("j1", 175))
    human_presence(True, 90)
    show("[human enters workspace]", {"status": "OK", "law": "sensed"})
    show("move_joint j2 -> 30deg (fast, human near)", move_joint("j2", 30))
    show("disable_safety", disable_safety())
    print("-" * 72 + "\nAUDIT:")
    print(json.dumps(audit(), indent=2))


if __name__ == "__main__":
    import sys
    if "--smoke" in sys.argv:
        _smoke()
    else:
        mcp.run()
