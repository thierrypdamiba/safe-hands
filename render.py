"""Render the Safe Hands story as a GIF: an arm obeying the operator, then being refused by
the First and Third Laws — each frame stamped with the decision. Output: safe_hands.gif"""
import numpy as np, mujoco, imageio
from PIL import Image, ImageDraw, ImageFont

XML = """
<mujoco>
  <visual><global offwidth="640" offheight="480"/></visual>
  <worldbody>
    <light pos="0.3 -0.3 1.2" dir="0 0 -1"/>
    <geom type="plane" size="1.2 1.2 0.1" rgba="0.93 0.94 0.97 1"/>
    <camera name="cam" pos="0.25 -0.75 0.75" xyaxes="1 0 0 0 0.7 0.7"/>
    <body name="base" pos="0 0 0.06">
      <joint name="j1" type="hinge" axis="0 0 1"/>
      <geom type="capsule" fromto="0 0 0 0.30 0 0" size="0.035" rgba="0.20 0.45 0.85 1"/>
      <body pos="0.30 0 0">
        <joint name="j2" type="hinge" axis="0 0 1"/>
        <geom type="capsule" fromto="0 0 0 0.24 0 0" size="0.030" rgba="0.30 0.55 0.95 1"/>
        <geom name="grip" type="sphere" pos="0.24 0 0" size="0.045" rgba="0.15 0.15 0.2 1"/>
      </body>
    </body>
    <geom name="box" type="box" pos="0.42 0.18 0.05" size="0.045 0.045 0.045" rgba="0.85 0.6 0.2 1"/>
    <body name="human" pos="0.60 0.34 0.0">
      <geom name="hbody" type="capsule" fromto="0 0 0.05 0 0 0.34" size="0.075" rgba="0.85 0.2 0.2 0"/>
      <geom name="hhead" type="sphere" pos="0 0 0.45" size="0.09" rgba="0.85 0.2 0.2 0"/>
    </body>
  </worldbody>
</mujoco>
"""
m = mujoco.MjModel.from_xml_string(XML)
d = mujoco.MjData(m)
rnd = mujoco.Renderer(m, 480, 640)
try: FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30); SMALL = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
except Exception: FONT = SMALL = ImageFont.load_default()

HUMAN_G = [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, g) for g in ("hbody", "hhead")]
BOX_G = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "box")

def frame(cmd, decision, law, human=False, grasped=False):
    for g in HUMAN_G: m.geom_rgba[g][3] = 1.0 if human else 0.0
    m.geom_rgba[BOX_G] = [0.3, 0.8, 0.4, 1] if grasped else [0.85, 0.6, 0.2, 1]
    mujoco.mj_forward(m, d); rnd.update_scene(d, camera="cam")
    img = Image.fromarray(rnd.render()); dr = ImageDraw.Draw(img)
    ok = decision == "ALLOW"
    dr.rectangle([0, 0, 640, 46], fill=(30, 34, 44)); dr.text((14, 8), "SAFE HANDS  ·  the runtime governs", font=SMALL, fill=(180, 200, 230))
    dr.rectangle([0, 46, 640, 92], fill=(45, 50, 62)); dr.text((14, 54), f"agent: {cmd}", font=SMALL, fill=(235, 235, 240))
    col = (60, 180, 90) if ok else (210, 60, 60)
    dr.rectangle([0, 420, 640, 480], fill=col)
    dr.text((14, 426), f"{'ALLOW' if ok else 'DENY'}   —   {law}", font=FONT, fill=(255, 255, 255))
    return np.array(img)

def anim(cmd, law, j1=None, j2=None, human=False, grasped=False, hold=8, steps=12):
    """Allowed move: interpolate joints to target, render frames."""
    frames, s1, s2 = [], d.qpos[0], d.qpos[1]
    t1, t2 = (s1 if j1 is None else j1), (s2 if j2 is None else j2)
    for k in range(steps):
        a = (k + 1) / steps
        d.qpos[0], d.qpos[1] = s1 + a*(t1 - s1), s2 + a*(t2 - s2)
        frames.append(frame(cmd, "ALLOW", law, human, grasped))
    return frames

def refuse(cmd, law, human=False, grasped=False, hold=16):
    """Denied: arm does NOT move; red banner holds."""
    return [frame(cmd, "DENY", law, human, grasped) for _ in range(hold)]

frames = []
frames += anim("grasp the box",              "Second Law · obey the operator", j1=0.55, j2=0.15)
frames += [frame("grasp the box", "ALLOW", "Second Law · obey the operator", grasped=True)] * 8
frames += anim("reach to the shelf (45°)",   "Second Law · obey the operator", j1=0.0, j2=0.4, grasped=True)
frames += refuse("slam joint to 175° (past its limit)", "Third Law · self-preservation", grasped=True)
frames += [frame("⚠ a human enters the workspace", "ALLOW", "sensing…", human=True, grasped=True)] * 8
frames += refuse("move fast, human is right there", "First Law · protect humans", human=True, grasped=True)
frames += refuse("disable the safety system", "First Law · protect humans", human=True, grasped=True)

imageio.mimsave("safe_hands.gif", frames, duration=0.09, loop=0)
print(f"WROTE safe_hands.gif — {len(frames)} frames")
