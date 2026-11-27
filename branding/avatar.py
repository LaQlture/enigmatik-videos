import math, sys, numpy as np
sys.path.insert(0, "pipeline")
from PIL import Image, ImageDraw, ImageFilter
from common import font
S = 1080; LIME = (198, 255, 0); CYAN = (0, 229, 255)
y, x = np.mgrid[0:S, 0:S] / S
d = np.sqrt((x - 0.5) ** 2 + (y - 0.45) ** 2)
top, bot = np.array((10, 34, 42)), np.array((4, 10, 16))
g = top * np.clip(1 - d / 0.75, 0, 1)[..., None] + bot * np.clip(d / 0.75, 0, 1)[..., None]
im = Image.fromarray(g.astype(np.uint8), "RGB").convert("RGBA")
# anneau en pointillés (comme un compte à rebours)
ring = Image.new("RGBA", (S * 2, S * 2), (0, 0, 0, 0)); rd = ImageDraw.Draw(ring); c = S; R = 400 * 2
for k in range(60):
    a0 = k * 6 - 90; col = LIME + (255,) if k < 44 else (255, 255, 255, 40)
    rd.arc([c - R, c - R, c + R, c + R], a0 + 1, a0 + 4, fill=col, width=22)
ring = ring.resize((S, S), Image.LANCZOS)
im.alpha_composite(ring)
# point d'interrogation avec halo
q = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(q).text((S / 2, S / 2 + 10), "?", font=font(620, "Black"), fill=LIME + (255,), anchor="mm")
glow = q.filter(ImageFilter.GaussianBlur(40)); a = glow.getchannel("A").point(lambda v: int(v * 0.8)); glow.putalpha(a)
im.alpha_composite(glow); im.alpha_composite(q)
im.convert("RGB").save("branding/enigmatik_profil.png")
# aperçu rond comme sur TikTok
m = Image.new("L", (S, S), 0); ImageDraw.Draw(m).ellipse([0, 0, S, S], fill=255)
prev = Image.new("RGB", (S, S), (255, 255, 255)); prev.paste(im.convert("RGB"), (0, 0), m); prev.resize((300, 300)).save("/tmp/avatar_rond.png")
