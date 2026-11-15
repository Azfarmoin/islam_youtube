"""Finishing 'look' pass applied to EVERY video after assembly: colour grade, light, camera motion, cut punch, progress bar.
Pure FFmpeg filters (free, local, no stock footage). Each effect is a switch under `look:` in config.yaml and on the dashboard Look & Story page.
Effects never touch the audio and never alter the Quran text; they only dress the picture."""
from __future__ import annotations
import re
from pathlib import Path
from . import grade as GR
from .audio import run

LOOK_DEFAULTS = {"enabled": True, "grade": "auto", "grain": True, "vignette": True, "sharpen": True, "bloom": True, "flicker": False,
                 "push_in": True, "handheld": False, "cut_punch": True, "cut_flash": True, "progress_bar": True, "edge_fades": True, "comment_question": True}
GRADES = ["auto", "none"] + sorted(GR.PROFILES)
MOODS = [   # theme keyword -> grade profile (first match wins); gentle, never teal-orange or HDR
    (("night", "dua", "prayer", "tahajjud", "dark", "silence", "stars", "moon"), "deep_night"),
    (("mercy", "hope", "ease", "relief", "patience", "gratitude", "dawn", "forgive", "light", "joy", "kind"), "warm_dawn"),
    (("death", "loss", "warning", "reckoning", "judgment", "grave", "hell", "fear", "pride", "arrogan"), "cool_dusk"),
    (("knowledge", "learn", "read", "wisdom", "intellect", "think"), "high_clarity"),
    (("history", "ancient", "past", "nation", "people of"), "sepia_archive"),
]
QUESTIONS = [   # one reflective, non-clickbait comment prompt per mood; never a claim, never 'share for reward'
    (("mercy", "hope", "ease", "relief", "patience", "gratitude"), "Which hardship taught you the most? Tell us below."),
    (("death", "loss", "warning", "reckoning", "judgment", "fear"), "What reminder keeps you steady? Tell us below."),
    (("knowledge", "learn", "read", "wisdom"), "What is one thing you learned today? Tell us below."),
    (("night", "dua", "prayer"), "What dua is on your heart tonight? Tell us below."),
]
DEFAULT_QUESTION = "What does this change for your day? Tell us below."

ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-maxrate", "6M", "-bufsize", "12M"]   # grain makes noisy frames expensive: cap the bitrate so files stay small

def cfg_look(cfg: dict | None) -> dict:
    out = dict(LOOK_DEFAULTS); out.update(((cfg or {}).get("look") or {})); return out

def pick_grade(theme: str, choice: str) -> str | None:
    if choice == "none": return None
    if choice != "auto": return choice if choice in GR.PROFILES else None
    t = (theme or "").lower()
    for keys, prof in MOODS:
        if any(k in t for k in keys): return prof
    return "filmic_natural"

def question_for(theme: str) -> str:
    t = (theme or "").lower()
    for keys, q in QUESTIONS:
        if any(k in t for k in keys): return q
    return DEFAULT_QUESTION

def _no_vig(profile_filter: str) -> str:
    return re.sub(r",?vignette=[^,]*$", "", profile_filter)          # the look pass owns the vignette so it can be switched off

def build_graph(look: dict, theme: str, cuts: list[float], total: float, fps: int, W: int, H: int, graded_already: bool = False) -> tuple[str, dict]:
    """Returns (filter_complex, applied) where applied lists the effects switched on. Pure function: easy to test."""
    L = cfg_look({"look": look}); on = {}
    if not L["enabled"]: return "", on
    pre, post = [], []
    prof = None if graded_already else pick_grade(theme, L["grade"])
    if prof: pre.append(_no_vig(GR.filter_for(prof))); on["grade"] = prof
    if L["sharpen"]: pre.append("unsharp=5:5:0.45:5:5:0.0"); on["sharpen"] = True
    cuts = sorted(c for c in cuts if 0.3 < c < total - 0.3)[:14]
    z = []
    if L["handheld"]: pre.append("rotate=a='0.0035*sin(2*PI*t/5.2)+0.002*sin(2*PI*t/2.3)':ow=iw:oh=ih:c=black:bilinear=1"); on["handheld"] = True
    if L["push_in"] or L["handheld"] or L["cut_punch"]:
        n = max(1, int(total * fps)); base = 1.045 if L["handheld"] else 1.0
        expr = f"{base}"
        if L["push_in"]: expr += f"+0.05*on/{n}"; on["push_in"] = True
        if L["cut_punch"] and cuts:
            expr += "".join(f"+0.035*gt(on/{fps},{c:.2f})*max(0,1-(on/{fps}-{c:.2f})/0.35)" for c in cuts); on["cut_punch"] = True
        pre.append(f"zoompan=z='{expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={fps}")
    bl = L["bloom"]
    if bl: on["bloom"] = True
    br = []
    if L["flicker"]: br.append("0.012*sin(2*PI*t*3.1)+0.008*sin(2*PI*t*7.3)"); on["flicker"] = True
    if L["cut_flash"] and cuts: br += [f"0.09*gt(t,{c:.2f})*max(0,1-(t-{c:.2f})/0.16)" for c in cuts]; on["cut_flash"] = True
    if br: post.append("eq=brightness='" + "+".join(br) + "':eval=frame")
    if L["grain"]: post.append("noise=alls=3:allf=t"); on["grain"] = True
    if L["vignette"]: post.append("vignette=PI/5"); on["vignette"] = True
    if L["edge_fades"]: post.append(f"fade=t=in:st=0:d=0.2,fade=t=out:st={max(0.1, total - 0.3):.2f}:d=0.3"); on["edge_fades"] = True
    g = "[0:v]" + (",".join(pre) + "," if pre else "") + "format=yuv420p"
    if bl: g += ",split[a][b];[b]scale=iw/4:ih/4,gblur=sigma=5,scale=%d:%d[c];[a][c]blend=c0_mode=screen:c0_opacity=0.2:c1_opacity=0:c2_opacity=0" % (W, H)
    g += ("," + ",".join(post) if post else "")
    if L["progress_bar"]:
        on["progress_bar"] = True
        g += f"[v];color=c=0xd9b36a:s={W}x8:r={fps}[bar];[v][bar]overlay=x='-w+w*t/{total:.2f}':y=28:shortest=1"
    return g + ",format=yuv420p[out]", on

def apply(src: Path, dst: Path, cfg: dict, theme: str, cuts: list[float], total: float, fps: int, W: int, H: int, graded_already: bool = False) -> tuple[Path, dict]:
    g, on = build_graph(cfg_look(cfg), theme, cuts, total, fps, W, H, graded_already)
    if not g or not on: return src, {}
    run(["ffmpeg", "-y", "-i", str(src), "-filter_complex", g, "-map", "[out]", "-r", str(fps), *ENC, "-an", str(dst)])
    return dst, on
