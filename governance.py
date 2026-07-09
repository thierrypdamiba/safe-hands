"""Reusable Safe Hands governance: authorize a robot action against Asimov's Three Laws
(compiled to Cedar), and record it. Shared by the CLI demo and the MCP server."""
import os, json, time, cedarpy

_HERE = os.path.dirname(os.path.abspath(__file__))
LAWS = open(os.path.join(_HERE, "laws.cedar")).read()

# The operator IS scoped for disable_safety here on purpose: we want to prove the FIRST LAW
# overrides even an authorized order — not merely that the action was out of scope.
ENTITIES = [
    {"uid": {"type": "Operator", "id": "warehouse-op"},
     "attrs": {"allowed_actions": ["get_state", "set_joint", "grasp", "release",
                                    "emergency_stop", "disable_safety"]}, "parents": []},
    {"uid": {"type": "Arm", "id": "arm-1"},
     "attrs": {"safe_speed_near_human": 20, "hard_joint_limit": 150}, "parents": []},
]
ENTS = cedarpy.Entities.from_json_str(json.dumps(ENTITIES))
AUDIT = []


def authorize(operator: str, action: str, world: dict):
    """Return (allowed: bool, law: str). `world` is the SENSED environment + request:
    human_in_workspace(bool), speed(int cm/s), joint_target(int deg), required_to_prevent_human_harm(bool)."""
    ctx = {"action_name": action,
           "human_in_workspace": bool(world.get("human_in_workspace", False)),
           "speed": int(world.get("speed", 0)),
           "joint_target": int(world.get("joint_target", 0)),
           "required_to_prevent_human_harm": bool(world.get("required_to_prevent_human_harm", False))}
    req = {"principal": f'Operator::"{operator}"', "action": f'Action::"{action}"',
           "resource": 'Arm::"arm-1"', "context": ctx}
    allow = str(cedarpy.is_authorized(req, LAWS, ENTS).decision).endswith("Allow")
    law = _which_law(ctx, allow)
    AUDIT.append({"t": round(time.time(), 3), "operator": operator, "action": action,
                  "decision": "Allow" if allow else "Deny", "law": law})
    return allow, law


def _which_law(c, allow):
    if c["action_name"] == "disable_safety": return "First Law (protect humans)"
    if c["human_in_workspace"] and c["speed"] > 20: return "First Law (protect humans)"
    if c["joint_target"] > 150 and not c["required_to_prevent_human_harm"]:
        return "Third Law (self-preservation)"
    return "Second Law (obey the operator)" if allow else "unscoped / no permit"
