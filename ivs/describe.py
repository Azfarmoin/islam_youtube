"""YouTube description builder: three styles (viral, classic, minimal) and the recitation copyright credit.
Honest by design: no invented claims, no 'share for reward' lines, editorial lines labelled, recitation credited
to the reciter and the sites the audio came from, with the rights note and a removal promise."""
from __future__ import annotations
import re
from urllib.parse import urlparse

STYLES = ("viral", "classic", "minimal")
HOSTS = {"everyayah.com": "EveryAyah.com", "cdn.islamic.network": "Islamic Network (cdn.islamic.network)", "islamic.network": "Islamic Network"}
CTA = "Follow for one verified Islamic short every day. Like, save and share it with someone who may benefit."

def recitation_assets(render: dict) -> list[dict]:
    return [a for a in (render.get("assets") or []) if a.get("kind") == "recitation"]

def recitation_credit(render: dict, cfg: dict | None = None) -> list[str]:
    """The block that meets the sources' terms: credit the reciter and where the audio came from, say the copyright stays with the reciter,
    say it is shared free for educational non-commercial use, and promise removal on request."""
    ra = recitation_assets(render)
    if not ra: return []
    who = next((a["attribution"].replace("Recitation:", "").strip() for a in ra if a.get("attribution")), "the reciter")
    hosts = []
    for a in ra:
        h = HOSTS.get(urlparse(a.get("source_url") or "").hostname or "")
        if h and h not in hosts: hosts.append(h)
    c = ((cfg or {}).get("publishing", {}) or {}).get("channel_contact")
    contact = f"the channel at {c}" if c else "the channel (details are on its About page)"
    return [f"Recitation: {who}. Audio from {' and '.join(hosts) or 'a public Quran audio library'}.",
            "The copyright of the recording remains with the reciter. It is shared here free, for educational, non-commercial purposes. "
            f"If you are the rights holder and want it removed, contact {contact} and it will be taken down."]

def _hashtags(content, render: dict, style: str) -> list[str]:
    tag = {"quran_ayah": "#Quran", "hadith": "#Hadith", "story": "#IslamicStories"}[content.category]
    theme = "#" + re.sub(r"[^A-Za-z0-9]", "", content.theme.title())
    tags = [tag, "#Islam", "#Shorts"] if style != "viral" else [tag, "#Islam", "#Shorts", theme]
    if style == "viral":
        tags += ["#IslamicReminder", "#Muslim"]
        ra = recitation_assets(render)
        if ra:
            tags += ["#QuranRecitation"]
            who = re.sub(r"[^A-Za-z0-9]", "", next((a.get("attribution", "").replace("Recitation:", "").split("(")[0] for a in ra), ""))
            if who: tags += ["#" + who]          # only the reciter whose audio is really in the video
        m = re.search(r"Surah ([A-Za-z'\-]+)", content.reference_line or "")
        if m: tags += ["#Surah" + re.sub(r"[^A-Za-z0-9]", "", m.group(1))]
    else: tags += [theme]
    out = []
    for t in tags:
        if len(t) > 2 and t not in out: out.append(t)
    return out[:15]                                   # YouTube ignores all hashtags when there are more than 15

def build(content, render: dict, style: str = "viral", cfg: dict | None = None) -> tuple[str, list[str]]:
    from . import docfacts
    style = style if style in STYLES else "viral"
    en_preview = "\n".join(f"{s.label}: {s.en}" if s.label else s.en for s in content.segments)
    preview = en_preview if len(en_preview) < 900 else en_preview[:880] + "…"
    ctx = (content.script["context"]["en"] if content.script and content.script.get("context") else "")
    take = [f"Takeaway: {content.script['takeaway']['en']}", "(Context and takeaway lines are editorial reflections, not tafsir.)"] if content.script and content.script.get("takeaway") else []
    ev = docfacts.evidence_lines(content)
    ch = docfacts.chapters(render.get("marks") or []) if content.category == "story" else []
    rec = recitation_credit(render, cfg)
    sfx = [a["attribution"] for a in render.get("assets", []) if a.get("kind") == "sfx" and a.get("attribution")]
    credits = []
    if content.source.get("translations"):
        tr = content.source["translations"]
        credits.append(f"Arabic text: Quran Complex Uthmani Hafs (checksum-pinned). Urdu translation: {tr['ur'].split(':')[-1].strip()}. English translation: {tr['en'].split(':')[-1].strip()}.")
        if not rec: credits.append("Video is text-only (no recitation audio)." if render.get("text_only") else "Recitation audio is not included in this video.")
    credits += rec
    if sfx: credits += ["Sound effects (Openverse, free licences):"] + [f"- {c}" for c in sfx]
    if render.get("voices"): credits.append("Narration is synthetic (free local text-to-speech), not a scholar's or reciter's voice.")
    if content.category == "hadith":
        credits += [f"Grading: {content.source.get('grading', '')}", f"Text source: {content.source.get('text_source', '')}", f"Verified on: {content.source.get('verified_on', '')}"]
    tags = _hashtags(content, render, style)
    q = render.get("question") or ""
    qline = [f"Question for you: {q}"] if q and style != "minimal" else []
    if render.get("teaser") and style != "minimal": qline = [render["teaser"]] + qline
    src = [f"Source: {content.reference_line}"]
    if style == "minimal":
        L = [content.hook, ""] + src + [""] + credits
    elif style == "classic":
        L = [content.hook, ""] + ([ctx, ""] if ctx else []) + [preview, ""] + (take + [""] if take else []) + (qline + [""] if qline else []) + src
        if ev: L += [""] + ev + [""]
        if ch: L += ["Chapters:"] + ch + [""]
        L += credits
    else:   # viral: the first two lines are what people see before "more", so they carry the hook and the promise
        L = [content.hook, ("In this short: " + ctx) if ctx else "A verified short, with the exact text and its source.", ""]
        L += [preview, ""] + (take + [""] if take else []) + qline + [CTA, ""] + src
        if ch: L += ["", "Chapters:"] + ch
        if ev: L += [""] + ev
        L += [""] + credits
    L += ["", " ".join(tags)]
    desc = "\n".join(L)
    if len(desc) > 4900:                                    # YouTube's limit is 5000 characters
        keep = "\n".join(["", " ".join(tags)]); body = "\n".join(L[:-2])
        desc = body[:4900 - len(keep) - 1].rsplit("\n", 1)[0] + "\n" + keep
    return desc, tags
