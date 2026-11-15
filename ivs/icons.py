"""Word-synced illustrated icons: when a concrete word is spoken (sun, mountain, ship, bird, heart, book ...), a drawn icon pops up for ~1.3 s at that moment.
Honest scope: only words that have a picture get an icon (about one every 1-2 s); function words and abstract words do not. Timing is ESTIMATED from the
character position of the word inside the sentence and the voice length (no forced aligner), so it is approximately, not frame-exactly, in sync.
Icons are simple original vector drawings (no people, no faces, nothing copyrighted). Never used to depict Allah, prophets, sahaba or angels."""
from __future__ import annotations
import math, re, subprocess
from pathlib import Path
from PIL import Image, ImageDraw

S = 1024
GOLD = (240, 213, 140, 255); CREAM = (255, 244, 220, 255); DEEP = (18, 22, 46, 190)

def _canvas():
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([20, 20, S - 20, S - 20], fill=DEEP, outline=GOLD, width=18)
    return im, d

def _star(d, cx, cy, r, c=GOLD, pts=5):
    P = []
    for i in range(pts * 2):
        a = -math.pi / 2 + i * math.pi / pts; rr = r if i % 2 == 0 else r * 0.42
        P.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(P, fill=c)

def _sun(d, cx, cy, r, n=12):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD)
    for i in range(n):
        a = i * 2 * math.pi / n
        d.line([(cx + math.cos(a) * r * 1.3, cy + math.sin(a) * r * 1.3), (cx + math.cos(a) * r * 1.75, cy + math.sin(a) * r * 1.75)], fill=GOLD, width=22)

def _cloud(d, cx, cy, w, c=CREAM):
    for dx, dy, r in ((-0.28, 0.05, 0.22), (0.0, -0.08, 0.3), (0.3, 0.05, 0.22)):
        d.ellipse([cx + dx * w - r * w, cy + dy * w - r * w, cx + dx * w + r * w, cy + dy * w + r * w], fill=c)
    d.rectangle([cx - 0.5 * w, cy + 0.05 * w, cx + 0.5 * w, cy + 0.27 * w], fill=c)

def ic_sun(d): _sun(d, 512, 512, 150)
def ic_sunrise(d):
    d.pieslice([312, 380, 712, 780], 180, 360, fill=GOLD)
    for i in range(7):
        a = math.pi + i * math.pi / 6; d.line([(512 + math.cos(a) * 250, 580 + math.sin(a) * 250), (512 + math.cos(a) * 340, 580 + math.sin(a) * 340)], fill=GOLD, width=22)
    d.line([(190, 580), (834, 580)], fill=CREAM, width=20)
def ic_moon(d):
    d.ellipse([300, 280, 700, 680], fill=GOLD); d.ellipse([400, 240, 780, 620], fill=DEEP); _star(d, 640, 700, 60)
def ic_stars(d): _star(d, 512, 420, 150); _star(d, 330, 640, 80, CREAM); _star(d, 700, 660, 90, CREAM)
def ic_mountain(d):
    d.polygon([(150, 740), (400, 330), (560, 560), (680, 420), (880, 740)], fill=CREAM); d.polygon([(400, 330), (335, 440), (400, 410), (455, 450)], fill=GOLD)
def ic_wave(d):
    for k, y in enumerate((400, 520, 640)):
        pts = [(170 + x * 6.8, y + 40 * math.sin(x / 8 + k)) for x in range(0, 101)]; d.line(pts, fill=GOLD if k != 1 else CREAM, width=26)
def ic_ship(d):
    d.polygon([(220, 600), (800, 600), (700, 710), (320, 710)], fill=CREAM); d.line([(510, 600), (510, 230)], fill=GOLD, width=20)
    d.polygon([(530, 250), (730, 560), (530, 560)], fill=GOLD); d.polygon([(490, 320), (330, 560), (490, 560)], fill=CREAM)
def ic_bird(d):
    d.line([(512, 520), (400, 400), (260, 440)], fill=CREAM, width=34); d.line([(512, 520), (624, 400), (764, 440)], fill=CREAM, width=34); d.ellipse([480, 490, 544, 554], fill=GOLD)
def ic_palm(d):
    d.line([(512, 780), (540, 560), (580, 400)], fill=CREAM, width=36)
    for a in (-160, -125, -90, -55, -20):
        r = math.radians(a); d.line([(580, 400), (580 + math.cos(r) * 230, 400 + math.sin(r) * 130 + 60)], fill=GOLD, width=30)
def ic_rain(d):
    _cloud(d, 512, 400, 460)
    for x in (360, 470, 580, 690): d.line([(x, 560), (x - 40, 680)], fill=GOLD, width=22)
def ic_cloud(d): _cloud(d, 512, 512, 520)
def ic_fire(d):
    d.polygon([(512, 200), (700, 460), (680, 700), (512, 790), (344, 700), (324, 470), (430, 560), (450, 380)], fill=GOLD)
    d.polygon([(512, 480), (600, 640), (512, 750), (424, 640)], fill=CREAM)
def ic_lamp(d):
    d.ellipse([362, 460, 662, 700], fill=GOLD); d.polygon([(662, 540), (800, 480), (700, 600)], fill=GOLD); d.rectangle([402, 690, 622, 740], fill=CREAM)
    d.polygon([(380, 460), (512, 340), (644, 460)], fill=CREAM); d.ellipse([480, 250, 544, 340], fill=GOLD)
def ic_heart(d):
    d.ellipse([260, 300, 520, 560], fill=GOLD); d.ellipse([504, 300, 764, 560], fill=GOLD); d.polygon([(285, 470), (739, 470), (512, 760)], fill=GOLD)
def ic_book(d):
    d.polygon([(512, 360), (200, 330), (200, 700), (512, 730)], fill=CREAM); d.polygon([(512, 360), (824, 330), (824, 700), (512, 730)], fill=GOLD)
    for y in (430, 500, 570): d.line([(250, y), (470, y + 15)], fill=DEEP, width=10); d.line([(554, y + 15), (774, y)], fill=DEEP, width=10)
def ic_pen(d):
    d.polygon([(700, 220), (800, 320), (360, 760), (240, 790), (270, 670)], fill=GOLD); d.polygon([(240, 790), (270, 670), (360, 760)], fill=CREAM)
def ic_drop(d):
    d.polygon([(512, 200), (700, 520), (324, 520)], fill=GOLD); d.ellipse([324, 400, 700, 780], fill=GOLD); d.ellipse([400, 560, 460, 660], fill=CREAM)
def ic_sprout(d):
    d.line([(512, 800), (512, 480)], fill=CREAM, width=30); d.polygon([(512, 520), (300, 440), (390, 640)], fill=GOLD); d.polygon([(512, 480), (730, 380), (640, 590)], fill=GOLD)
def ic_path(d):
    d.polygon([(420, 300), (604, 300), (860, 780), (164, 780)], fill=CREAM)
    for y, w in ((420, 14), (540, 20), (680, 28)): d.rectangle([512 - w, y, 512 + w, y + 55], fill=GOLD)
def ic_door(d):
    d.rectangle([300, 400, 724, 800], fill=CREAM); d.pieslice([300, 220, 724, 580], 180, 360, fill=CREAM); d.ellipse([620, 560, 660, 600], fill=GOLD)
    d.rectangle([380, 430, 644, 800], fill=DEEP)
def ic_elephant(d):
    d.ellipse([240, 380, 700, 680], fill=CREAM); d.ellipse([620, 330, 820, 530], fill=CREAM); d.line([(790, 470), (830, 640), (790, 720)], fill=CREAM, width=48)
    d.polygon([(720, 520), (860, 580), (730, 560)], fill=GOLD)
    for x in (300, 400, 560, 640): d.rectangle([x, 640, x + 52, 780], fill=CREAM)
def ic_whale(d):
    d.ellipse([200, 430, 760, 720], fill=CREAM); d.polygon([(740, 560), (860, 440), (850, 640)], fill=CREAM)
    d.line([(400, 430), (400, 310)], fill=GOLD, width=18); d.line([(400, 310), (350, 260)], fill=GOLD, width=18); d.line([(400, 310), (450, 260)], fill=GOLD, width=18)
def ic_mosque(d):
    d.pieslice([340, 380, 684, 724], 180, 360, fill=CREAM); d.rectangle([340, 552, 684, 760], fill=CREAM); d.line([(512, 380), (512, 300)], fill=GOLD, width=16)
    for x in (250, 774):
        d.rectangle([x - 24, 380, x + 24, 760], fill=GOLD); d.polygon([(x - 34, 380), (x, 300), (x + 34, 380)], fill=GOLD)
def ic_hourglass(d):
    d.polygon([(330, 250), (694, 250), (540, 512), (694, 774), (330, 774), (484, 512)], fill=CREAM); d.polygon([(400, 700), (624, 700), (512, 600)], fill=GOLD)
    d.line([(300, 250), (724, 250)], fill=GOLD, width=26); d.line([(300, 774), (724, 774)], fill=GOLD, width=26)
def ic_earth(d):
    d.ellipse([260, 260, 764, 764], outline=CREAM, width=26)
    d.ellipse([400, 260, 624, 764], outline=GOLD, width=18); d.line([(260, 512), (764, 512)], fill=GOLD, width=18); d.arc([300, 340, 724, 480], 0, 180, fill=GOLD, width=14)
def ic_house(d):
    d.polygon([(200, 520), (512, 250), (824, 520)], fill=GOLD); d.rectangle([290, 520, 734, 780], fill=CREAM); d.rectangle([450, 620, 574, 780], fill=DEEP)
def ic_scale(d):
    d.line([(512, 260), (512, 760)], fill=CREAM, width=26); d.line([(250, 360), (774, 360)], fill=GOLD, width=26)
    for x in (250, 774):
        d.line([(x, 360), (x - 90, 560)], fill=CREAM, width=12); d.line([(x, 360), (x + 90, 560)], fill=CREAM, width=12); d.pieslice([x - 130, 470, x + 130, 640], 0, 180, fill=GOLD)
def ic_coin(d):
    d.ellipse([280, 280, 744, 744], fill=GOLD); d.ellipse([340, 340, 684, 684], outline=DEEP, width=16); _star(d, 512, 512, 100, DEEP)
def ic_key(d):
    d.ellipse([250, 340, 520, 610], outline=GOLD, width=40); d.line([(500, 475), (800, 475)], fill=GOLD, width=40); d.line([(700, 475), (700, 570)], fill=GOLD, width=34); d.line([(770, 475), (770, 550)], fill=GOLD, width=34)
def ic_tent(d):
    d.polygon([(200, 760), (480, 300), (544, 300), (824, 760)], fill=CREAM); d.polygon([(480, 760), (512, 520), (544, 760)], fill=DEEP)

ICONS = {n[3:]: f for n, f in list(globals().items()) if n.startswith("ic_")}
KEYWORDS = {
    "sun": ("sun", "daylight", "noon"), "sunrise": ("dawn", "morning", "sunrise", "relief", "ease", "hope", "daybreak"), "moon": ("moon", "night", "evening", "darkness", "sleep"),
    "stars": ("star", "stars", "heaven", "heavens", "sky", "universe", "constellation"), "mountain": ("mountain", "mountains", "hill", "hills", "difficulty", "hardship", "burden", "trial", "peak"),
    "wave": ("sea", "ocean", "waves", "wave"), "ship": ("ship", "ships", "boat", "vessel", "sail"), "bird": ("bird", "birds", "fly", "flying", "wings", "air"),
    "palm": ("palm", "palms", "tree", "trees", "date", "dates", "orchard"), "rain": ("rain", "rains", "downpour", "storm"), "cloud": ("cloud", "clouds"),
    "fire": ("fire", "flame", "flames", "burn", "burning", "blaze"), "lamp": ("light", "lamp", "guidance", "guide", "guided", "illuminate", "shine"),
    "heart": ("heart", "hearts", "love", "mercy", "compassion", "remembrance", "remember", "gratitude", "grateful", "thankful"), "book": ("book", "books", "read", "recite", "knowledge", "scripture", "revelation", "message"),
    "pen": ("pen", "write", "wrote", "taught"), "drop": ("water", "river", "rivers", "spring", "drink", "drop"), "sprout": ("seed", "seeds", "grow", "grew", "plant", "crops", "harvest", "grain", "fruit", "fruits"),
    "path": ("path", "way", "road", "journey", "travel", "straight", "route"), "door": ("door", "gate", "gates", "enter", "open"), "elephant": ("elephant", "elephants", "army", "armies"),
    "whale": ("whale", "fish", "belly", "depths"), "mosque": ("prayer", "pray", "prayers", "worship", "mosque", "prostrate", "prostration", "sacred", "house"), "hourglass": ("time", "years", "year", "ages", "patience", "patient", "perseverance", "days", "age", "moment"),
    "earth": ("earth", "world", "land", "lands", "creation", "created", "create"), "house": ("home", "homes", "dwelling", "city", "town", "people", "tribe", "tribes"), "scale": ("justice", "balance", "weigh", "measure", "fair", "scales"),
    "coin": ("wealth", "money", "riches", "provision", "provide", "provided", "sustenance", "gold", "silver", "trade", "winter", "summer", "journeys"), "key": ("key", "keys", "unlock", "treasure", "secret"), "tent": ("tent", "tents", "camp", "desert"),
}
_WORD2ICON = {w: k for k, ws in KEYWORDS.items() for w in ws}

def icon_for(word: str) -> str | None:
    w = word.lower()
    return _WORD2ICON.get(w) or _WORD2ICON.get(w.rstrip("s")) or _WORD2ICON.get(w.rstrip("ed")) or _WORD2ICON.get(w.rstrip("ing"))

def plan(text: str, start: float, dur: float, scene_dur: float, hold: float = 1.3, gap: float = 0.9, max_n: int = 7) -> list[dict]:
    """[{icon, t, hold}] in scene time. Word position is estimated from character offset inside the spoken text."""
    words = list(re.finditer(r"[A-Za-z']+", text or "")); total = max(1, len(text or ""))
    out, last = [], -9.0
    for m in words:
        ic = icon_for(m.group(0))
        if not ic: continue
        t = start + dur * (m.start() / total)
        if t - last < gap or t + 0.5 > scene_dur: continue
        out.append({"icon": ic, "t": round(max(0.2, t), 2), "hold": min(hold, max(0.6, scene_dur - t - 0.1))}); last = t
        if len(out) >= max_n: break
    return out

def make_png(name: str, cache: Path, px: int = 280) -> Path:
    p = cache / "icons" / f"{name}_{px}.png"
    if p.exists(): return p
    p.parent.mkdir(parents=True, exist_ok=True)
    im, d = _canvas(); ICONS[name](d)
    im.resize((px, px), Image.LANCZOS).save(p); return p

def overlay(clip_in: Path, clip_out: Path, plans: list[dict], cache: Path, fps: int, W: int, H: int, y_frac: float = 0.80) -> Path:
    """Composite the timed icons onto a rendered scene clip (fade in/out, gentle rise). Falls back to the plain clip on any failure."""
    if not plans: return clip_in
    args = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip_in)]; chain = []; cur = "[0:v]"
    for k, pl in enumerate(plans, 1):
        png = make_png(pl["icon"], cache); args += ["-loop", "1", "-framerate", str(fps), "-i", str(png)]
        t0, h = pl["t"], pl["hold"]; fi = 0.22
        chain.append(f"[{k}:v]format=rgba,fade=t=in:st={t0:.2f}:d={fi}:alpha=1,fade=t=out:st={t0 + h - fi:.2f}:d={fi}:alpha=1[i{k}]")
        nxt = f"[o{k}]"
        chain.append(f"{cur}[i{k}]overlay=x=(W-w)/2:y='{int(H * y_frac)}-14*min(1\\,(t-{t0:.2f})/0.4)':enable='between(t,{t0:.2f},{t0 + h:.2f})':format=auto:eof_action=pass{nxt}"); cur = nxt
    args += ["-filter_complex", ";".join(chain), "-map", cur, "-an", "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(clip_out)]
    r = subprocess.run(args, capture_output=True, text=True)
    return clip_out if r.returncode == 0 and clip_out.exists() else clip_in
