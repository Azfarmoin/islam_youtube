"""Static dashboard website (GitHub Pages, free). Reads the SQLite history and writes site/index.html + site/data.json.
PUBLIC-SAFE: only published videos (title, link, date, category, views if collected) and aggregate counts are included. No review items, no errors, no paths, no keys."""
from __future__ import annotations
import datetime as dt, html, json
from pathlib import Path

CSS = """:root{--bg:#0b1020;--card:#141b34;--ink:#f3ecd9;--mute:#a9b0c8;--gold:#e8c872;--line:#26304f}
@media (prefers-color-scheme:light){:root{--bg:#f6f1e4;--card:#fffaf0;--ink:#1c2340;--mute:#5c6482;--gold:#9a6f12;--line:#e2d8bd}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:24px 16px 64px}h1{font-size:clamp(1.5rem,4vw,2.2rem);margin:.2em 0;color:var(--gold)}
.sub{color:var(--mute);margin:0 0 24px}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}.kpi b{display:block;font-size:1.8rem;color:var(--gold)}.kpi span{color:var(--mute);font-size:.85rem}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:20px}h2{font-size:1.05rem;margin:0 0 10px}
.bars{display:flex;align-items:flex-end;gap:6px;height:110px}.bars div{flex:1;background:linear-gradient(var(--gold),#b58d36);border-radius:4px 4px 0 0;min-height:2px;position:relative}
.bars div i{position:absolute;bottom:-20px;left:0;right:0;text-align:center;font-style:normal;font-size:.62rem;color:var(--mute)}.bars{padding-bottom:22px}
.tools{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}input,button{font:inherit;border-radius:10px;border:1px solid var(--line);background:var(--bg);color:var(--ink);padding:8px 12px}
button.on{background:var(--gold);color:#1c1c1c;border-color:var(--gold)}input{flex:1;min-width:180px}
.list{display:grid;gap:10px}.item{display:grid;grid-template-columns:1fr auto;gap:4px 12px;background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.item a{color:var(--ink);text-decoration:none;font-weight:600}.item a:hover{color:var(--gold)}.meta{color:var(--mute);font-size:.82rem}.pill{color:var(--gold);font-size:.8rem;align-self:center;white-space:nowrap}
footer{color:var(--mute);font-size:.8rem;margin-top:28px}"""

def collect(db, cfg: dict) -> dict:
    c = db.conn; now = dt.datetime.now(dt.timezone.utc)
    rows = c.execute("SELECT id,category,key,title,published_at,platform_url,platform_id FROM content_items WHERE status='published' ORDER BY published_at DESC").fetchall()
    vids = []
    for r in rows:
        st = {}
        try: st = json.loads(db.setting(f"stats:{r['platform_id']}") or "{}")
        except Exception: pass
        vids.append({"title": r["title"] or r["key"], "category": r["category"], "key": r["key"], "published_at": r["published_at"], "url": r["platform_url"],
                     "views": st.get("viewCount"), "likes": st.get("likeCount")})
    counts = {k: v for k, v in c.execute("SELECT status,COUNT(*) FROM content_items GROUP BY status").fetchall()}
    day = {}
    for v in vids:
        d = (v["published_at"] or "")[:10]
        if d: day[d] = day.get(d, 0) + 1
    last14 = [((now - dt.timedelta(days=i)).date().isoformat()) for i in range(13, -1, -1)]
    units = c.execute("SELECT COALESCE(SUM(units),0) FROM quota_log WHERE platform='youtube' AND ts>=?", ((now - dt.timedelta(hours=24)).isoformat(),)).fetchone()[0]
    nz = lambda x: int(x) if str(x or "").isdigit() else 0
    bycat = {}
    for v in vids: bycat[v["category"]] = bycat.get(v["category"], 0) + 1
    top = sorted((v for v in vids if v["views"] is not None), key=lambda v: -nz(v["views"]))[:5]
    a, n = cfg.get("audio", {}), cfg.get("audio", {}).get("narration", {}); vd = cfg.get("video", {})
    feats = [("English voice", f'Kokoro {n.get("voice", "")} (humanised, free licence)' if n.get("enabled") else "off"),
             ("Pace", f'{vd.get("pace", "normal")}, max {vd.get("max_seconds", "")} s'), ("Word-synced icons", "on" if vd.get("word_icons") else "off"),
             ("Copyright-free mode", "on" if a.get("copyright_free") else "off"), ("Quran recitation", "authentic reciter audio" if a.get("recitation", {}).get("enabled", True) else "off (text only)"),
             ("Faces / prophets depicted", "never"), ("Human review", "stories, hadith and AI drafts")]
    today = now.date().isoformat()
    tv, tl = sum(nz(v["views"]) for v in vids), sum(nz(v["likes"]) for v in vids)
    if any(v["views"] is not None for v in vids):
        db.put_setting(f"hist:{today}", json.dumps({"views": tv, "likes": tl, "videos": len(vids)}))
    hist = []
    for d in last14:
        try: h = json.loads(db.setting(f"hist:{d}") or "null")
        except Exception: h = None
        hist.append({"d": d[5:], "views": (h or {}).get("views")})
    credits = [dict(r) for r in c.execute("""SELECT DISTINCT cl.source_title AS source, cl.translator AS translator, cl.license AS license FROM claims cl
        JOIN content_items i ON i.id=cl.item_id WHERE i.status='published' AND cl.source_title IS NOT NULL ORDER BY 1""")]
    return {"hist": hist, "credits": credits, "generated": now.strftime("%Y-%m-%d %H:%M UTC"), "total_published": len(vids), "today": day.get(now.date().isoformat(), 0),
            "week": sum(day.get(d, 0) for d in last14[-7:]), "in_pipeline": sum(counts.get(k, 0) for k in ("queued", "verified", "generating", "rendered", "approved", "needs_review")),
            "per_day": [{"d": d[5:], "n": day.get(d, 0)} for d in last14], "quota_units_24h": units, "quota_limit": int(cfg.get("publishing", {}).get("youtube_daily_quota", 10000)),
            "videos": vids[:300], "total_views": sum(nz(v["views"]) for v in vids), "total_likes": sum(nz(v["likes"]) for v in vids), "by_category": bycat, "top": top, "features": feats, "categories": sorted({v["category"] for v in vids})}

def render(data: dict, title: str = "Islamic Video Studio") -> str:
    e = html.escape; mx = max([p["n"] for p in data["per_day"]] + [1])
    bars = "".join(f'<div style="height:{max(2, int(100 * p["n"] / mx))}%" title="{p["n"]} on {p["d"]}"><i>{p["d"][-2:]}</i></div>' for p in data["per_day"])
    kp = "".join(f'<div class="kpi"><b>{v}</b><span>{e(k)}</span></div>' for k, v in (("videos published", data["total_published"]), ("today", data["today"]), ("last 7 days", data["week"]), ("in the pipeline", data["in_pipeline"]), ("total views", f'{data["total_views"]:,}'), ("total likes", f'{data["total_likes"]:,}'), ("API quota used (24h)", f'{data["quota_units_24h"]:,}/{data["quota_limit"]:,}')))
    cats = "".join(f'<button data-c="{e(c)}">{e(c.replace("_", " "))}</button>' for c in data["categories"])
    vm = max([int(p["views"] or 0) for p in data["hist"]] + [1])
    vb = "".join(f'<div style="height:{max(2, int(100 * int(p["views"] or 0) / vm))}%" title="{p["views"] if p["views"] is not None else "no data"} on {p["d"]}"><i>{p["d"][-2:]}</i></div>' for p in data["hist"])
    cr = "".join(f'<div class="meta">{e(str(x["source"]))}{(" - " + e(str(x["translator"]))) if x["translator"] else ""}{(" (" + e(str(x["license"])) + ")") if x["license"] else ""}</div>' for x in data["credits"]) or '<p class="meta">Listed once videos are published.</p>'
    tot = max(sum(data["by_category"].values()), 1)
    mix = "".join(f'<div class="meta">{e(k.replace("_", " "))} <b>{v}</b> ({100 * v // tot}%)</div>' for k, v in sorted(data["by_category"].items(), key=lambda x: -x[1])) or '<p class="meta">Nothing yet.</p>'
    top = "".join(f'<div class="item"><a href="{e(v["url"] or "#")}" target="_blank" rel="noopener">{e(v["title"])}</a><span class="pill">{e(str(v["views"]))} views</span></div>' for v in data["top"]) or '<p class="meta">Appears after the first stats run.</p>'
    feat = "".join(f'<div class="meta"><b>{e(k)}:</b> {e(str(v))}</div>' for k, v in data["features"])
    payload = json.dumps(data["videos"], ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title><style>{CSS}</style></head><body><div class="wrap">
<h1>{e(title)}</h1><p class="sub">Verified Quran and story shorts, made and published automatically. Updated {e(data["generated"])}.</p>
<div class="kpis">{kp}</div><div class="panel"><h2>Uploads, last 14 days</h2><div class="bars">{bars}</div></div>
<div class="panel"><h2>Total views, last 14 days</h2><div class="bars">{vb}</div></div><div class="panel"><h2>Mix by category</h2>{mix}</div><div class="panel"><h2>Top videos</h2>{top}</div><div class="panel"><h2>How these are made</h2>{feat}</div>
<div class="panel"><h2>Sources and credits</h2>{cr}</div><div class="panel"><h2>Videos</h2><div class="tools"><input id="q" placeholder="Search title or reference" aria-label="Search"><button data-c="" class="on">All</button>{cats}</div><div id="list" class="list"></div></div>
<footer>Made with free tools. Quran text: Tanzil. Recitation: Mishary Rashid Alafasy, audio from EveryAyah.com and Islamic Network; the recording's copyright remains with the reciter, shared free for educational, non-commercial use, and removed on request. English voice: Kokoro (Apache-2.0). Editorial lines are not scholarly tafsir.</footer></div>
<script>const V={payload};let c="",q="";const L=document.getElementById("list");
function esc(s){{return String(s??"").replace(/[&<>"]/g,m=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[m]))}}
function draw(){{const r=V.filter(v=>(!c||v.category===c)&&(!q||(v.title+" "+v.key).toLowerCase().includes(q)));
L.innerHTML=r.length?r.map(v=>`<div class="item"><a href="${{esc(v.url)}}" target="_blank" rel="noopener">${{esc(v.title)}}</a><span class="pill">${{v.views!=null?esc(v.views)+" views":""}}</span><span class="meta">${{esc(v.category.replace("_"," "))}} · ${{esc((v.published_at||"").slice(0,10))}} · ${{esc(v.key)}}</span></div>`).join(""):'<p class="meta">No videos yet.</p>'}}
document.getElementById("q").oninput=e=>{{q=e.target.value.toLowerCase();draw()}};
document.querySelectorAll("button[data-c]").forEach(b=>b.onclick=()=>{{c=b.dataset.c;document.querySelectorAll("button[data-c]").forEach(x=>x.classList.toggle("on",x===b));draw()}});draw();</script></body></html>"""

def build(db, cfg: dict, out: Path, title: str = "Islamic Video Studio") -> dict:
    out.mkdir(parents=True, exist_ok=True)
    data = collect(db, cfg)
    (out / "index.html").write_text(render(data, title), encoding="utf-8"); (out / "data.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / ".nojekyll").write_text("")
    return {"videos": len(data["videos"]), "out": str(out)}
