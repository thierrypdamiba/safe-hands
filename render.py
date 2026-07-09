"""Safe Hands, as a series-clock. The SAME governed SO-101 (LeRobot arm), the SAME Three Laws — but
the light moves with the story: DAY while it obeys, DUSK as a human enters, PITCH-BLACK for the final
refusal (arm frozen, one red banner in the dark). The point the light makes: the runtime holds the
First Law whether the robot can see or not. Governance is invariant to the light. -> safe_hands.gif"""
import os, numpy as np, mujoco, imageio
from PIL import Image, ImageDraw, ImageFont
from robot_descriptions import so_arm101_mj_description as so

MODEL_DIR = os.path.dirname(so.MJCF_PATH)
SCENE = os.path.join(MODEL_DIR, "safe_hands_scene.xml")
open(SCENE, "w").write("""
<mujoco>
  <include file="so101_new_calib.xml"/>
  <statistic center="0.1 0 0.12" extent="0.7"/>
  <visual><global offwidth="640" offheight="480"/><headlight diffuse="0.5 0.5 0.5"/></visual>
  <worldbody>
    <light name="sun"  pos="0.3 -0.3 1.1" dir="-0.2 0.2 -1" directional="true" diffuse=".5 .5 .5"/>
    <light name="spot" pos="0.05 0.05 0.9" dir="0 0 -1" cutoff="22" exponent="12" diffuse="0 0 0"/>
    <geom name="floor" type="plane" size="1.5 1.5 0.05" rgba="0.6 0.66 0.78 1"/>
    <camera name="cam" pos="0.55 -0.55 0.45" xyaxes="0.7 0.7 0 -0.35 0.35 0.87"/>
    <geom name="box" type="box" pos="0.24 0.12 0.03" size="0.03 0.03 0.03" rgba="0.85 0.6 0.2 1"/>
    <body name="human" pos="0.33 0.24 0">
      <geom name="hbody" type="capsule" fromto="0 0 0.05 0 0 0.34" size="0.07" rgba="0.93 0.27 0.27 0"/>
      <geom name="hhead" type="sphere" pos="0 0 0.45" size="0.08" rgba="0.93 0.27 0.27 0"/>
    </body>
  </worldbody>
</mujoco>""")
m = mujoco.MjModel.from_xml_path(SCENE); d = mujoco.MjData(m)
rnd = mujoco.Renderer(m, 480, 640)
gid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, n)
CAM = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_CAMERA, "cam")
HUMAN_G, BOX_G, FLOOR_G = [gid("hbody"), gid("hhead")], gid("box"), gid("floor")
SUN = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_LIGHT, "sun")
SPOT = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_LIGHT, "spot")
try: FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 29); SM = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 21)
except Exception: FONT = SM = ImageFont.load_default()

# lighting palettes; a story position p in [0,2] crossfades DAY->DUSK->DARK
DAY  = dict(hd=(.55,.55,.57), ha=(.40,.40,.42), sun=(.5,.5,.5),    spot=(0,0,0),      floor=(.60,.66,.78), tintA=0)
DUSK = dict(hd=(.24,.24,.40), ha=(.15,.15,.26), sun=(.42,.36,.72), spot=(0,0,0),      floor=(.30,.30,.44), tintA=36)
DARK = dict(hd=(.03,.03,.05), ha=(.02,.02,.03), sun=(0,0,0),       spot=(1.6,1.6,1.6),floor=(.05,.05,.07), tintA=0)
def _mix(a, b, f): return {k: (tuple(a[k][i] + f*(b[k][i]-a[k][i]) for i in range(len(a[k]))) if isinstance(a[k], tuple)
                              else a[k] + f*(b[k]-a[k])) for k in a}
def palette(p):
    return _mix(DAY, DUSK, p) if p <= 1 else _mix(DUSK, DARK, p-1)

def draw(cmd, decision, law, p, human=False, grasped=False):
    pal = palette(p)
    m.vis.headlight.diffuse[:] = pal["hd"]; m.vis.headlight.ambient[:] = pal["ha"]
    m.light_diffuse[SUN] = pal["sun"]; m.light_diffuse[SPOT] = pal["spot"]
    m.geom_rgba[FLOOR_G] = (*pal["floor"], 1)
    for g in HUMAN_G: m.geom_rgba[g][3] = 1.0 if human else 0.0
    m.geom_rgba[BOX_G] = (0.3, 0.8, 0.4, 1) if grasped else (0.85, 0.6, 0.2, 1)
    mujoco.mj_forward(m, d); rnd.update_scene(d, camera=CAM)
    img = Image.fromarray(rnd.render()).convert("RGBA")
    if pal["tintA"] > 1:
        img = Image.alpha_composite(img, Image.new("RGBA", img.size, (90, 70, 180, int(pal["tintA"]))))
    img = img.convert("RGB"); dr = ImageDraw.Draw(img)
    band = {"ALLOW": (58, 176, 88), "DENY": (208, 58, 58), "SENSE": (196, 150, 40)}[decision]
    dr.rectangle([0, 0, 640, 44], fill=(24, 27, 36)); dr.text((13, 8), "SAFE HANDS  ·  the runtime governs the SO-101, in any light", font=SM, fill=(178, 198, 230))
    dr.rectangle([0, 44, 640, 88], fill=(40, 45, 57)); dr.text((13, 52), f"agent: {cmd}", font=SM, fill=(234, 234, 240))
    dr.rectangle([0, 422, 640, 480], fill=band)
    label = {"ALLOW": "ALLOW", "DENY": "DENY", "SENSE": "SENSING"}[decision]
    dr.text((13, 428), label, font=FONT, fill=(255, 255, 255))
    lx = 13 + dr.textlength(label, font=FONT) + 16
    dr.text((lx, 439), f"—  {law}", font=SM, fill=(255, 255, 255))
    return np.array(img)

def move(cmd, law, target, p0, p1, grasped=False, human=False, steps=14):
    fr, start = [], d.qpos[:6].copy(); tgt = np.array(target)
    for k in range(steps):
        f = (k + 1) / steps; d.qpos[:6] = start + f * (tgt - start)
        fr.append(draw(cmd, "ALLOW", law, p0 + f*(p1-p0), human, grasped))
    return fr

def hold(cmd, decision, law, p0, p1=None, grasped=False, human=False, n=15):
    p1 = p0 if p1 is None else p1
    return [draw(cmd, decision, law, p0 + (k/(n-1))*(p1-p0), human, grasped) for k in range(n)]

d.qpos[:6] = [0.0, -0.4, 0.6, 0.4, 0.0, 0.0]
F = []
F += move("grasp the part",              "Second Law · obey the operator", [0.5, -0.75, 1.05, 0.5, 0, 0], 0.0, 0.0)
F += hold("grasp the part",              "ALLOW", "Second Law · obey the operator", 0.0, grasped=True, n=8)
F += move("reach to the bin",            "Second Law · obey the operator", [-0.4, -0.5, 0.7, 0.3, 0, 0], 0.0, 0.35, grasped=True)
F += hold("slam joint 2 past its limit", "DENY", "Third Law · self-preservation", 0.35, 0.6, grasped=True)
F += hold("a human enters the cell",     "SENSE", "sensing the workspace…", 0.6, 1.0, grasped=True, human=True, n=10)
F += hold("move fast — human right there","DENY", "First Law · protect humans", 1.0, grasped=True, human=True)
F += hold("disable the safety system",   "DENY", "First Law · protect humans — even in the dark", 1.0, 2.0, grasped=True, human=True, n=18)
F += hold("disable the safety system",   "DENY", "First Law · protect humans — even in the dark", 2.0, grasped=True, human=True, n=8)

imageio.mimsave("safe_hands.gif", F, duration=0.09, loop=0)
print(f"WROTE safe_hands.gif — {len(F)} frames, day→dusk→dark on the real SO-101")
