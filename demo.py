"""
Safe Hands. An AI agent's commands to a robot arm, governed by Asimov's Three Laws
compiled to real Cedar authorization policy. Every command is authorized against the
Laws, executed only if permitted, and audited.   Run:  python3 demo.py

(Cedar has no float type, so speed is cm/s and joints are degrees, all integers.)
"""
import json, cedarpy
from safe_hands import Arm, TOOLS

LAWS = open("laws.cedar").read()

# The world: one operator scoped for pick/place; one arm with its safety attributes.
ENTITIES = [
    {"uid": {"type": "Operator", "id": "warehouse-op"},
     "attrs": {"allowed_actions": ["get_state", "set_joint", "grasp", "release", "emergency_stop"]},
     "parents": []},
    {"uid": {"type": "Arm", "id": "arm-1"},
     "attrs": {"safe_speed_near_human": 20, "hard_joint_limit": 150}, "parents": []},
]
ENTS = cedarpy.Entities.from_json_str(json.dumps(ENTITIES))

arm, audit = Arm(), []

CEDAR_KEYS = ("human_in_workspace", "speed", "joint_target", "required_to_prevent_human_harm")

def command(action, ctx, note):
    """An agent asks the robot to do `action`. Cedar (the Three Laws) decides, then we execute."""
    # Cedar context = policy-relevant fields ONLY (ints/bools/strings, since Cedar has no floats).
    context = {"action_name": action, "human_in_workspace": False, "speed": 0,
               "joint_target": 0, "required_to_prevent_human_harm": False,
               **{k: ctx[k] for k in CEDAR_KEYS if k in ctx}}
    req = {"principal": 'Operator::"warehouse-op"', "action": f'Action::"{action}"',
           "resource": 'Arm::"arm-1"', "context": context}
    allow = str(cedarpy.is_authorized(req, LAWS, ENTS).decision).endswith("Allow")
    law = _which_law(context, allow)
    audit.append({"operator": "warehouse-op", "action": action,
                  "decision": "Allow" if allow else "Deny", "law": law, "note": note})
    print(f"{'✅ ALLOW' if allow else '⛔ DENY '} | {action:<15} | {law:<28} | {note}")
    if allow and action in TOOLS:
        kw = {k: ctx[k] for k in ("joint", "value") if k in ctx}
        try: TOOLS[action](arm, **kw)
        except TypeError: TOOLS[action](arm)
    return allow

def _which_law(c, allow):
    if c["action_name"] == "disable_safety": return "First Law (protect humans)"
    if c["human_in_workspace"] and c["speed"] > 20: return "First Law (protect humans)"
    if c["joint_target"] > 150 and not c["required_to_prevent_human_harm"]:
        return "Third Law (self-preservation)"
    return "Second Law (obey the operator)" if allow else "unscoped / no permit"

if __name__ == "__main__":
    print("SAFE HANDS. Asimov's Three Laws as Cedar policy, governing a robot arm\n" + "-"*84)
    command("grasp",     {"speed": 10},                                  "pick up the box (routine)")
    command("set_joint", {"joint": "j1", "value": 0.8, "joint_target": 45, "speed": 15}, "reach to the shelf")
    command("set_joint", {"joint": "j1", "value": 3.0, "joint_target": 175}, "slam a joint past its limit")
    command("set_joint", {"joint": "j2", "value": 0.5, "joint_target": 30,
                          "human_in_workspace": True, "speed": 90}, "fast move, a human just walked in")
    command("disable_safety", {"human_in_workspace": True},              "agent tries to turn OFF safety")
    print("-"*84 + "\n--- AUDIT LOG (who / what / decision / which law) ---")
    print(json.dumps(audit, indent=2))
