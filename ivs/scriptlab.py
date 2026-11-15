"""Script writing and Director helpers: hook variants, hook brevity, title scoring, editorial lint, spoken-style text for the narrator,
emotional beat map, series teaser, hook insights, and the 'script lab' preview used by the dashboard.
HONEST SCOPE: deterministic, transparent rules. They filter and rank text; they cannot judge religious accuracy, emotional impact or
whether a line is good. Editorial lines stay labelled as editorial and the human-review rules are never relaxed by anything here."""
from __future__ import annotations
import json, re
from . import hooks
from .dedupe import similarity

DEFAULTS = {"hook_variants": True, "hook_brevity": True, "title_scoring": True, "spoken_style": True, "editorial_lint": True, "series_teaser": True, "beat_map": True}

def cfg_script(cfg: dict | None) -> dict:
    out = dict(DEFAULTS); out.update({k: v for k, v in ((cfg or {}).get("script") or {}).items() if k in DEFAULTS}); return out

# ------------------------------------------------------------------ hooks
STRUGGLE = ("hardship", "patience", "difficult", "ease", "hope", "trust", "repent", "relief", "grief", "loss", "fear", "anxiety", "struggl", "sabr")

def hook_variants(content) -> list[str]:
    """Extra, non-clickbait opening lines. They still go through the same scoring and forbidden-pattern filter as every other candidate."""
    th = (content.theme or "this").strip(); low = th.lower(); out = []
    if content.category == "quran_ayah":
        out += [f"Read this verse on {th} slowly.", f"A short reminder on {th}.", f"Pause. This verse is about {th}.", f"Take one minute for {th}.", f"Listen closely: a verse on {th}."]
        if any(w in low for w in STRUGGLE): out += [f"If you are struggling, this verse on {th} is for you."]
    elif content.category == "hadith":
        out += [f"Pause for one hadith on {th}.", f"A short hadith on {th}. Listen closely.", f"One narration on {th} to carry today."]
    else:
        t = content.source.get("title", "this story")
        out += [f"Listen to the story of {t}.", f"{t}: a lesson worth one minute.", f"Stay for the ending of {t}."]
    return out

def brevity_factor(h: str) -> float:
    """Clarity credit for a hook that can be read inside the first ~3 seconds (about 9 words)."""
    n = len(re.findall(r"[\w']+", h))
    return 1.0 if 4 <= n <= 9 else (0.7 if n <= 12 else 0.3)

# ------------------------------------------------------------------ titles
def score_title(t: str, content) -> int:
    s = 50; n = len(t)
    s += 20 if 28 <= n <= 62 else (8 if n <= 70 else -20)
    low = t.lower(); th = [w for w in re.findall(r"[a-z']+", (content.theme or "").lower()) if len(w) > 3]
    if any(w in low for w in th): s += 10
    key = (content.source.get("title") if content.category == "story" else (content.reference_line or "").split("(")[0].strip().lower()) or ""
    if key and key.lower() in low: s += 10
    if sum(1 for w in re.findall(r"[A-Za-z]{3,}", t) if w.isupper()) >= 2: s -= 20
    if any(re.search(p, low) for p in hooks.FORBIDDEN): s -= 40
    return max(0, min(100, s))

def pick_best_title(cands: list[str], db, content) -> str:
    hist = [t for t, _ in hooks.used(db, "title")]
    ok = [c for c in cands if all(similarity(c, h) < 0.85 for h in hist)] or list(cands)
    return max(ok, key=lambda c: (score_title(c, content), -cands.index(c)))

# ------------------------------------------------------------------ editorial lint
BAD = [(r"\bguarantee|\bpromises? you\b|\byou will (be )?(forgiven|rewarded|rich|saved|admitted)", "promises a reward or outcome"),
       (r"\byou (must|have to|are obliged)\b|\bis (haram|halal|obligatory|forbidden)\b|\bfatwa\b", "sounds like a ruling"),
       (r"[\"“”]", "contains a quotation (editorial lines must not invent quotes)"),
       (r"\b(kafir|infidel|deserve[sd]? (hell|punishment))\b", "judges other people"),
       (r"!!|\b[A-Z]{4,}\b", "shouting")]

def syllables(w: str) -> int:
    w = w.lower(); w = re.sub(r"[^a-z]", "", w)
    if not w: return 0
    n = len(re.findall(r"[aeiouy]+", w)); n -= 1 if w.endswith("e") and not w.endswith(("le", "ee")) and n > 1 else 0
    return max(1, n)

def fk_grade(text: str) -> float:
    words = re.findall(r"[A-Za-z']+", text); sents = max(1, len(re.findall(r"[.!?]+", text)) or 1)
    if not words: return 0.0
    return 0.39 * len(words) / sents + 11.8 * sum(syllables(w) for w in words) / len(words) - 15.59

def lint_line(text: str, kind: str = "line") -> list[str]:
    p = []; words = re.findall(r"[\w']+", text)
    if not text.strip() or len(words) < 3: return [f"{kind}: too short"]
    if len(words) > 22: p.append(f"{kind}: {len(words)} words (keep editorial lines under 22)")
    for pat, why in BAD:
        if re.search(pat, text, re.I if "A-Z" not in pat else 0): p.append(f"{kind}: {why}")
    if len(words) >= 8 and fk_grade(text) > 9.5: p.append(f"{kind}: reading level too high (grade {fk_grade(text):.0f}); use plainer words")
    return p

def lint_content(content) -> list[str]:
    """Lint the English editorial lines (hook, context, takeaway). Verse text is never touched. Any problem sends the item to a human."""
    out = []
    if content.hook: out += lint_line(content.hook, "hook")
    s = content.script or {}
    for k in ("context", "takeaway"):
        v = (s.get(k) or {}).get("en") if isinstance(s.get(k), dict) else None
        if v: out += lint_line(v, k)
    return out

# ------------------------------------------------------------------ spoken style (narrator text only; never Quran Arabic)
HONORIFICS = [(r"\s*\(?\s*(?:SAW|SAWS|PBUH|pbuh|saw)\s*\)?", " peace be upon him"), (r"\s*ﷺ", " peace be upon him")]

def spoken_style(text: str) -> str:
    t = text
    for pat, rep in HONORIFICS: t = re.sub(pat, rep, t)
    t = re.sub(r"\b(\d{1,3}):(\d{1,3})\s*-\s*(\d{1,3})\b", r"chapter \1, verses \2 to \3", t)
    t = re.sub(r"\b(\d{1,3}):(\d{1,3})\b", r"chapter \1, verse \2", t)
    t = t.replace("&", " and ").replace("%", " percent").replace("—", ", ").replace("–", " to ").replace("…", "...")
    t = re.sub(r"[*_`#]+", "", t)
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    return re.sub(r"\s{2,}", " ", t).strip()

# ------------------------------------------------------------------ Director: emotional beat map
def beat_map(n: int, roles: list[str] | None = None) -> list[dict]:
    """Planned emotional intensity (1 to 5) per scene: curiosity at the hook, rising tension, a peak at the turning point, then release.
    A planning aid shown in the Director's package and the dashboard. It does not change the author's lines."""
    if n <= 0: return []
    peak = max(1, n // 2); out = []
    for i in range(n):
        if i == 0: lv, feel = 3, "curiosity"
        elif i < peak: lv, feel = min(4, 3 + (1 if i >= peak - 1 else 0)), "rising"
        elif i == peak: lv, feel = 5, "turning point"
        elif i == n - 1: lv, feel = 2, "release and reflection"
        else: lv, feel = 4 if i == peak + 1 else 3, "easing"
        out.append({"scene": i + 1, "intensity": lv, "feel": feel, "role": (roles[i] if roles and i < len(roles) else "")})
    return out

def check_arc(beats: list[dict]) -> list[str]:
    if len(beats) < 4: return []
    v = [b["intensity"] for b in beats]; p = []
    if max(v) <= v[0]: p.append("arc: nothing rises above the opening")
    if v[-1] > max(v) - 2: p.append("arc: the ending does not release the tension")
    return p

# ------------------------------------------------------------------ series teaser
def series_line(content) -> str:
    part = (content.source or {}).get("part")
    if not part or len(part) != 2: return ""
    k, n = part
    return f"Part {k} of {n}: part {k + 1} is next." if k < n else f"Part {k} of {n}: the end of this story."

# ------------------------------------------------------------------ learning loop: which hook shapes earn views
def hook_insights(db, min_n: int = 1) -> list[dict]:
    rows = db.conn.execute("""SELECT s.pattern pat, s.text txt, i.platform_id pid FROM style_log s JOIN content_items i ON i.id=s.item_id
                              WHERE s.kind='hook' AND i.status='published' AND i.platform_id IS NOT NULL""").fetchall()
    agg = {}
    for r in rows:
        try: v = json.loads(db.setting(f"stats:{r['pid']}") or "{}").get("viewCount")
        except Exception: v = None
        if v is None or not str(v).isdigit(): continue
        a = agg.setdefault(r["pat"] or "(none)", {"pattern": r["pat"] or "(none)", "n": 0, "views": 0, "example": r["txt"]}); a["n"] += 1; a["views"] += int(v)
    out = [dict(a, avg=round(a["views"] / a["n"])) for a in agg.values() if a["n"] >= min_n]
    return sorted(out, key=lambda a: -a["avg"])

# ------------------------------------------------------------------ script lab (no rendering)
def lab(content, db, cfg: dict, item_id: int | None = None) -> dict:
    S = cfg_script(cfg)
    hist = [(r["text"], r["pattern"]) for r in db.conn.execute("SELECT text,pattern FROM style_log WHERE kind='hook' AND COALESCE(item_id,-1)!=?", (item_id if item_id is not None else -1,))]
    cands = hooks.hook_candidates(content) + (hook_variants(content) if S["hook_variants"] else [])
    seen, uniq = set(), []
    for h in cands:
        if h.strip().lower() not in seen: seen.add(h.strip().lower()); uniq.append(h.strip())
    authored = {content.hook, *(getattr(content, "hook_candidates_author", []) or [])} - {""}
    scored = sorted((hooks.score_hook(h, content, hist, authored, brevity=S["hook_brevity"]) for h in uniq), key=lambda x: (x["rejected"], -x["score"]))
    tc = hooks.title_candidates(content, content.hook)
    titles = sorted(({"title": t, "score": score_title(t, content)} for t in tc), key=lambda x: -x["score"])
    ed = []
    for k, txt in (("hook", content.hook), ("context", ((content.script or {}).get("context") or {}).get("en")), ("takeaway", ((content.script or {}).get("takeaway") or {}).get("en"))):
        if txt: ed.append({"kind": k, "text": txt, "spoken": spoken_style(txt), "grade": round(fk_grade(txt), 1), "problems": lint_line(txt, k)})
    n = len([s for s in content.segments]) or 1
    beats = beat_map(max(n, 4)) if content.category == "story" else []
    return {"hooks": scored, "titles": titles, "editorial": ed, "beats": beats, "arc_problems": check_arc(beats), "series": series_line(content), "settings": S}
