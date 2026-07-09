"""A Monet series of a governed robot: the SAME SO-101, the SAME allowed grasp, painted across the
light — day, dawn, dusk, moody, pitch-black, partial-shadow. The point: the governance is invariant
to the light. The runtime holds the First Law whether the robot can see or not. -> _lights_contact.png"""
import os, numpy as np, mujoco
from PIL import Image, ImageDraw, ImageFont
from robot_descriptions import so_arm101_mj_description as so

MODEL_DIR = os.path.dirname(so.MJCF_PATH)
POSE = [0.4, -0.72, 1.02, 0.5, 0.0, 0.0]   # a clean reach, box grasped

# each preset: (headlight rgb, extra <light> xml, floor rgba, tint-overlay rgba or None)
PRESETS = {
 "DAY":            ((.55,.55,.57), '<light pos="0.3 -0.3 1.1" dir="-0.2 0.2 -1" diffuse=".5 .5 .5"/>', (.60,.66,.78,1), None),
 "DAWN":           ((.42,.34,.28), '<light pos="1.0 -0.2 0.35" dir="-1 0.2 -0.35" diffuse=".9 .55 .35"/>', (.46,.40,.40,1), (255,150,70,26)),
 "DUSK":           ((.28,.28,.40), '<light pos="-0.9 0.3 0.4" dir="1 -0.3 -0.4" diffuse=".45 .40 .75"/>', (.30,.30,.44,1), (90,70,180,30)),
 "MOODY":          ((.12,.12,.14), '<light pos="0.7 -0.5 0.7" dir="-0.8 0.6 -0.7" diffuse="1 .95 .9"/>', (.16,.18,.22,1), None),
 "PITCH BLACK":    ((.03,.03,.04), '<light pos="0.05 0.05 0.9" dir="0 0 -1" diffuse="1.4 1.4 1.4" cutoff="20" exponent="12"/>', (.05,.05,.07,1), None),
 "PARTIAL SHADOW": ((.30,.30,.32), '<light pos="1.1 -0.9 0.45" dir="-1 0.85 -0.45" diffuse="1 .98 .95"/>', (.40,.44,.52,1), None),
}

def render(name, hl, light, floor, tint):
    scene = os.path.join(MODEL_DIR, "_lights_scene.xml")
    open(scene, "w").write(f"""
<mujoco>
  <include file="so101_new_calib.xml"/>
  <statistic center="0.1 0 0.12" extent="0.7"/>
  <visual><global offwidth="440" offheight="360"/><headlight diffuse="{hl[0]} {hl[1]} {hl[2]}" ambient="{hl[0]} {hl[1]} {hl[2]}"/></visual>
  <worldbody>
    {light}
    <geom name="floor" type="plane" size="1.5 1.5 0.05" rgba="{floor[0]} {floor[1]} {floor[2]} {floor[3]}"/>
    <camera name="cam" pos="0.55 -0.55 0.45" xyaxes="0.7 0.7 0 -0.35 0.35 0.87"/>
    <geom name="box" type="box" pos="0.24 0.12 0.03" size="0.03 0.03 0.03" rgba="0.3 0.8 0.4 1"/>
  </worldbody>
</mujoco>""")
    m = mujoco.MjModel.from_xml_path(scene); d = mujoco.MjData(m)
    d.qpos[:6] = POSE; mujoco.mj_forward(m, d)
    r = mujoco.Renderer(m, 360, 440); r.update_scene(d, camera="cam")
    img = Image.fromarray(r.render()).convert("RGB")
    if tint:
        ov = Image.new("RGBA", img.size, tint); img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    dr = ImageDraw.Draw(img)
    try: f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except Exception: f = ImageFont.load_default()
    dr.rectangle([0, 330, 440, 360], fill=(20, 22, 28))
    dr.text((10, 335), f"{name}   ·   ALLOW — Second Law", font=f, fill=(230, 232, 240))
    print(f"  {name:<15} mean={np.asarray(img).mean():.1f}")
    return img

imgs = [render(n, *p) for n, p in PRESETS.items()]
W, H = 440, 360; sheet = Image.new("RGB", (W*3, H*2), (10, 10, 12))
for i, im in enumerate(imgs): sheet.paste(im, ((i % 3)*W, (i // 3)*H))
sheet.save("_lights_contact.png")
print("WROTE _lights_contact.png — same governed arm, six lights")
