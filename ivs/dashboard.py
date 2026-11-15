"""Local dashboard (Flask, 127.0.0.1 only; the CLI works without it).
Pages: Home, Video detail (player, QC, sources, credits, edit), Make now, Settings, History, Credits.
Nothing here can publish by itself: approving only marks an item approved; the scheduler/workflow uploads."""
from __future__ import annotations
import datetime as dt, html, json, shutil, threading
from pathlib import Path
import yaml
from .audit import run_audit
from .publish_youtube import YouTubePublisher
from . import site as SITE, github_sync as GH, features as FEAT
from .config import ROOT, load_config, deep_update, enforce_zero_cost

from urllib.parse import quote_plus as _qp
def _q(x): return _qp(str(x).replace("\n", " ")[:200])

CSS = """body{font:15px system-ui;margin:0;background:#0f1b22;color:#e8e4da}main{max-width:1100px;margin:0 auto;padding:16px 20px 60px}
nav{background:#142631;border-bottom:1px solid #2c4350;padding:10px 20px;display:flex;gap:16px;flex-wrap:wrap}nav a{text-decoration:none}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #2c4350;padding:6px 8px;text-align:left;vertical-align:top}
a,button{color:#d9b36a}button,input[type=submit]{background:none;border:1px solid #d9b36a;border-radius:4px;padding:3px 10px;cursor:pointer;font:inherit}
input,select,textarea{background:#0b141a;color:#e8e4da;border:1px solid #2c4350;border-radius:4px;padding:5px;font:inherit}textarea{width:100%;min-height:110px}
h2{margin-top:26px;color:#d9b36a}.pass,.VERIFIED,.APPROVED{color:#7bd88f}.fail,.REJECTED{color:#ff7b72}.warn{color:#e3b341}
.ks{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px}.k{border:1px solid #2c4350;border-radius:8px;padding:10px}.k b{font-size:24px;color:#d9b36a}
.cols{display:grid;grid-template-columns:minmax(220px,340px) 1fr;gap:20px}@media(max-width:760px){.cols{grid-template-columns:1fr}}
video{width:100%;max-height:70vh;background:#000;border-radius:8px}pre{white-space:pre-wrap;background:#0b141a;padding:10px;border-radius:6px;overflow:auto;max-height:340px}
.bars{display:flex;align-items:flex-end;gap:5px;height:90px;padding-bottom:18px}.bars div{flex:1;background:#d9b36a;border-radius:3px 3px 0 0;min-height:2px;position:relative}.bars i{position:absolute;bottom:-17px;left:0;right:0;text-align:center;font:10px system-ui;color:#9aa}
.msg{background:#1d3340;border:1px solid #d9b36a;border-radius:6px;padding:8px 12px;margin:10px 0}"""

# Settings the page may change (nothing else is writable from the browser). (path, label, kind, choices/range)
VOICES = {"bm_george": "British male, calm and clear (default)", "bm_fable": "British male, storyteller", "bm_lewis": "British male, steady",
          "am_michael": "American male, warm", "am_adam": "American male, deep", "af_heart": "American female, warm", "af_bella": "American female, bright"}
SAMPLE = "Peace be upon you. Here is a short story worth telling, spoken slowly where it matters, and quickly where it does not."

SETTINGS = [
    (("audio", "narration", "enabled"), "English voice on", "bool", None),
    (("audio", "narration", "voice"), "English voice", "choice", ["bm_george", "bm_fable", "bm_lewis", "am_michael", "am_adam", "af_heart", "af_bella"]),
    (("audio", "narration", "speed"), "Voice speed", "float", (0.85, 1.3)),
    (("audio", "narration", "humanize"), "Humanised pauses", "bool", None),
    (("audio", "copyright_free"), "Copyright-free mode", "bool", None),
    (("audio", "recitation", "enabled"), "Real Quran recitation", "bool", None),
    (("video", "pace"), "Pace", "choice", ["fast", "normal"]),
    (("video", "word_icons"), "Word-synced icons", "bool", None),
    (("publishing", "platforms", "youtube", "privacy"), "YouTube privacy", "choice", ["private", "unlisted", "public"]),
    (("publishing", "description_style"), "Description style", "choice", ["viral", "classic", "minimal"]),
]

def _get(d, path):
    for k in path:
        d = (d or {}).get(k) if isinstance(d, dict) else None
    return d

def _set(d, path, v):
    for k in path[:-1]: d = d.setdefault(k, {})
    d[path[-1]] = v

def next_run_utc(now=None):
    """Next tick of the workflow cron '5 */2 * * *'."""
    now = now or dt.datetime.now(dt.timezone.utc)
    t = now.replace(minute=5, second=0, microsecond=0)
    while t <= now or t.hour % 2: t += dt.timedelta(hours=1 if t.hour % 2 == 0 or t <= now else 1)
    return t

def create_app(pipe):
    from flask import Flask, redirect, request, send_file, abort
    app = Flask(__name__)
    db = pipe.db; E = html.escape
    job = {"state": "idle", "msg": "", "started": None}; lock = threading.Lock()

    @app.before_request
    def guard():            # local-only tool: refuse cross-site form posts (CSRF) and foreign Host headers
        h = (request.host or "").split(":")[0]
        if h not in ("127.0.0.1", "localhost", "::1", "[::1]", "testserver"): abort(403)
        if request.method == "POST":
            o = request.headers.get("Origin")
            if o and (o.split("//", 1)[-1].split(":")[0] not in ("127.0.0.1", "localhost", "[::1]", "testserver")): abort(403)

    def page(title, body, msg=""):
        nav = "".join(f'<a href="{u}">{n}</a>' for u, n in (("/", "Home"), ("/make", "Make now"), ("/voice", "Voice"), ("/looks", "Look & Story"), ("/script", "Script & Director"), ("/stories", "Stories"), ("/tools", "Tools"), ("/ai", "AI key"), ("/github", "GitHub sync"), ("/history", "History"), ("/credits", "Credits"), ("/settings", "Settings")))
        paused = db.setting("paused") == "1"
        pz = f'<form method=post action=/pause style=display:inline><button>{"Resume" if paused else "Pause"} automation</button></form>'
        m = f'<div class=msg>{E(msg)}</div>' if msg else ""
        return (f'<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>{E(title)} - IVS</title><style>{CSS}</style>'
                f'<nav><b>Islamic Video Studio</b>{nav}<span style="margin-left:auto">{"PAUSED" if paused else "running"} {pz}</span></nav><main>{m}{body}</main>')

    def act(path, label, i): return f'<form method=post action="{path}/{i}" style="display:inline"><button>{label}</button></form>'
    def bars(vals):
        mx = max([v for _, v in vals] + [1])
        return '<div class=bars>' + "".join(f'<div style="height:{max(2, int(100 * v / mx))}%" title="{v} on {E(d)}"><i>{E(d[-2:])}</i></div>' for d, v in vals) + '</div>'

    def media_path(item, kind):
        p = item["video_path"] if kind == "video" else item["thumbnail_path"]
        if not p: return None
        q = Path(p); q = q if q.is_absolute() else Path(pipe.out_root) / q
        try: q = q.resolve(); root = Path(pipe.out_root).resolve()
        except Exception: return None
        return q if q.exists() and (root in q.parents or ROOT.resolve() in q.parents) else None

    @app.get("/")
    def index():
        c = db.conn; d = SITE.collect(db, pipe.cfg); rows = db.items(); flt = request.args.get("s"); q = (request.args.get("q") or "").lower()
        if flt: rows = [r for r in rows if r["status"] == flt]
        if q: rows = [r for r in rows if q in ((r["title"] or "") + " " + r["key"]).lower()]
        kp = "".join(f"<div class=k><b>{v}</b><br>{k}</div>" for k, v in (("published", d["total_published"]), ("today", d["today"]), ("7 days", d["week"]), ("in pipeline", d["in_pipeline"]), ("views", f"{d['total_views']:,}"), ("likes", f"{d['total_likes']:,}")))
        sc = dict(c.execute("SELECT status,COUNT(*) FROM content_items GROUP BY status").fetchall())
        h = [f"<h1>Dashboard</h1><div class=ks>{kp}</div>", "<h2>Uploads, last 14 days</h2>" + bars([(p["d"], p["n"]) for p in d["per_day"]]),
             "<p>" + " | ".join(f"<a href='/?s={k}'>{k} {v}</a>" for k, v in sc.items()) + " | <a href='/'>all</a></p>",
             f"<form><input name=q placeholder=search value='{E(q)}'><input type=hidden name=s value='{E(flt or '')}'> <input type=submit value=Search></form>"]
        if job["state"] != "idle": h.append(f'<div class=msg>Job: {E(job["state"])} {E(job["msg"])}</div>')
        h.append("<h2>Items</h2><table><tr><th>#</th><th>Key</th><th>Status</th><th>Title</th><th>Notes</th><th>Actions</th></tr>")
        for r in rows:
            btn = ""
            if r["status"] in ("rendered", "needs_review"): btn += act("/approve", "Approve", r["id"])
            if r["status"] not in ("published", "skipped"): btn += act("/skip", "Skip", r["id"])
            if r["status"] in ("failed", "generating"): btn += act("/rerender", "Re-render", r["id"])
            link = f' <a href="{E(r["platform_url"])}">youtube</a>' if r["platform_url"] else ""
            h.append(f"<tr><td><a href='/item/{r['id']}'>{r['id']}</a></td><td>{E(r['key'])}</td><td>{r['status']}{link}</td><td><a href='/item/{r['id']}'>{E(r['title'] or '(open)')}</a></td>"
                     f"<td>{E((r['review_reason'] or r['error'] or ''))[:200]}</td><td>{btn}</td></tr>")
        h.append("</table>")
        rej = c.execute("SELECT ts,key,reason FROM rejections ORDER BY id DESC LIMIT 15").fetchall()
        h.append(f"<h2>Rejected candidates ({c.execute('select count(*) from rejections').fetchone()[0]})</h2><table>")
        h += [f"<tr><td>{r['ts']}</td><td>{E(r['key'] or '')}</td><td>{E(r['reason'])}</td></tr>" for r in rej]
        h.append("</table><h2>Active settings</h2><p>" + " &middot; ".join(f"{E(k)}: <b>{E(str(v))}</b>" for k, v in d["features"]) + " (<a href=/settings>change</a>)</p>")
        h.append("<h2>Quota & storage</h2>")
        try: used = YouTubePublisher(pipe.cfg, db).quota_used_today()
        except Exception: used = "?"
        du = shutil.disk_usage(pipe.out_root)
        h.append(f"<p>YouTube quota used today (local count): {used}/10000 units. Output dir free space: {du.free // 2**30} GiB.</p><h2>Zero-cost / environment audit</h2><table>")
        h += [f"<tr><td class={x['status']}>{x['status']}</td><td>{E(x['name'])}</td><td>{E(x['detail'])}</td></tr>" for x in run_audit(pipe.cfg)["checks"]]
        h.append("</table>")
        return page("Home", "".join(h), request.args.get("m", ""))

    @app.get("/item/<int:i>")
    def item(i):
        it = db.get_item(i)
        if not it: abort(404)
        c = db.conn; work = Path(it["video_path"]).parent if it["video_path"] else None
        def rd(name):
            try: return (work / name).read_text(encoding="utf-8") if work else ""
            except Exception: return ""
        try: qc = json.loads(rd("qc_report.json") or "null")
        except Exception: qc = None
        try: tags = ", ".join(json.loads(it["tags"] or "[]"))
        except Exception: tags = it["tags"] or ""
        vid = f'<video controls preload=metadata playsinline poster="/media/{i}/thumb" src="/media/{i}/video"></video>' if media_path(it, "video") else "<p>No rendered video file on this machine (re-render to preview).</p>"
        btn = ""
        if it["status"] in ("rendered", "needs_review"): btn += act("/approve", "Approve", i)
        if it["status"] not in ("published", "skipped"): btn += act("/skip", "Skip", i)
        btn += act("/rerender", "Re-render", i)
        yt = f' &middot; <a href="{E(it["platform_url"])}">YouTube</a>' if it["platform_url"] else ""
        meta = (f"<p>Status <b>{it['status']}</b>{yt}<br>Religious verification: <b class={it['religious_verification']}>{it['religious_verification'] or '-'}</b> &middot; Quality: <b class={it['content_quality']}>{it['content_quality'] or '-'}</b> &middot; Engagement score: {it['engagement_score'] if it['engagement_score'] is not None else '-'}</p>"
                f"<p>{E(it['review_reason'] or '')} {E(it['error'] or '')}</p><p>{btn}</p>")
        edit = ""; note = ""; st = request.args.get("style")
        if st in ("viral", "classic", "minimal") and it["status"] != "published":
            try:
                from .pipeline import make_metadata
                ri = json.loads(rd("render_info.json") or "null")
                if not isinstance(ri, dict):
                    rows_ = [dict(x) for x in c.execute("SELECT * FROM assets_used WHERE item_id=?", (i,)).fetchall()]
                    ri = {"assets": rows_, "text_only": not any(x.get("kind") == "recitation" for x in rows_), "voices": [], "marks": []}
                m_ = make_metadata(pipe._rebuild_content(it), ri, pipe.cfg, st)
                it = dict(it); it["description"] = m_["description"]; note = f"<p class=msg>Preview of the <b>{E(st)}</b> description. Press Save to keep it.</p>"
            except Exception as ex: note = f"<p class=fail>Could not rebuild the description here: {E(str(ex))[:160]}</p>"
        if it["status"] != "published":
            cur = _get(pipe.cfg, ("publishing", "description_style")) or "viral"
            sel = "".join(f"<option {'selected' if x == (st or cur) else ''}>{x}</option>" for x in ("viral", "classic", "minimal"))
            edit = (f"<h2>Description style</h2><form method=get action=/item/{i}><select name=style>{sel}</select> <input type=submit value='Preview this style'> <small>viral: hook, call to action, hashtags &middot; classic: plain and complete &middot; minimal: short. The recitation credit is always included.</small></form>{note}"
                    f"<form method=post action=/item/{i}/edit><h2>Edit before it goes out</h2><p>Title<br><input name=title style='width:100%' maxlength=100 value=\"{E(it['title'] or '', True)}\"></p>"
                    f"<p>Description<br><textarea name=description>{E(it['description'] or '')}</textarea></p><p>Tags (comma separated)<br><input name=tags style='width:100%' value=\"{E(tags, True)}\"></p>"
                    "<p><input type=submit value='Save changes'> <small>Editing a Quran verse's text is not possible here: the verse text always comes from the verified source.</small></p></form>")
        claims = c.execute("SELECT * FROM claims WHERE item_id=?", (i,)).fetchall()
        ct = "".join(f"<tr><td>{E(x['kind'])}</td><td>{E(x['reference'] or '')}</td><td>{E(x['source_title'] or '')}</td><td>{E(x['translator'] or '')}</td><td>{E(x['grade'] or '')}</td><td>{E(x['license'] or '')}</td><td>{E(x['reviewer_status'])}</td><td>{('<a href=' + chr(34) + E(x['source_url']) + chr(34) + '>link</a>') if x['source_url'] else ''}</td></tr>" for x in claims)
        assets = c.execute("SELECT * FROM assets_used WHERE item_id=?", (i,)).fetchall()
        at = "".join(f"<tr><td>{E(x['kind'] or '')}</td><td>{E(x['name'] or '')}</td><td>{E(x['license'] or '')}</td><td>{E(x['attribution'] or '')}</td></tr>" for x in assets)
        try: src = json.dumps(json.loads(it["source_json"] or "{}"), indent=1, ensure_ascii=False)
        except Exception: src = it["source_json"] or ""
        script = rd("script.json")
        body = (f"<h1>#{i} {E(it['key'])}</h1><div class=cols><div>{vid}</div><div>{meta}{edit}</div></div>"
                f"<h2>Verification claims</h2><table><tr><th>Kind</th><th>Ref</th><th>Source</th><th>Translator</th><th>Grade</th><th>Licence</th><th>Review</th><th></th></tr>{ct or '<tr><td>none recorded</td></tr>'}</table>"
                f"<h2>Assets and credits</h2><table><tr><th>Kind</th><th>Name</th><th>Licence</th><th>Credit</th></tr>{at or '<tr><td>none recorded</td></tr>'}</table>"
                f"<h2>Quality check</h2>" + (f"<p>Passed: <b class={'pass' if qc.get('passed') else 'fail'}>{qc.get('passed')}</b></p><pre>{E(json.dumps(qc, indent=1, ensure_ascii=False))}</pre>" if isinstance(qc, dict) else "<p>No QC report on this machine.</p>") +
                (f"<h2>Script</h2><pre>{E(script)}</pre>" if script else "") + f"<h2>Source record</h2><pre>{E(src)}</pre>")
        return page(f"Item {i}", body, request.args.get("m", ""))

    @app.get("/media/<int:i>/<kind>")
    def media(i, kind):
        it = db.get_item(i)
        if not it or kind not in ("video", "thumb"): abort(404)
        p = media_path(it, "video" if kind == "video" else "thumb")
        if not p: abort(404)
        return send_file(p, conditional=True)

    @app.post("/item/<int:i>/edit")
    def edit(i):
        it = db.get_item(i)
        if not it or it["status"] == "published": abort(400)
        title = (request.form.get("title") or "").strip()[:100]; desc = (request.form.get("description") or "").strip()[:5000]
        tags = [t.strip() for t in (request.form.get("tags") or "").split(",") if t.strip()][:30]
        if not title: return redirect(f"/item/{i}?m=Title+cannot+be+empty")
        db.conn.execute("UPDATE content_items SET title=?,description=?,tags=?,updated_at=? WHERE id=?", (title, desc, json.dumps(tags, ensure_ascii=False), dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), i)); db.conn.commit()
        if it["video_path"]:         # the uploader reads metadata.json, so keep it in step
            mp = Path(it["video_path"]).parent / "metadata.json"
            try: m = json.loads(mp.read_text(encoding="utf-8")); m.update(title=title, description=desc, tags=tags); mp.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception: pass
        db.log("info", "title/description/tags edited in the dashboard", i)
        return redirect(f"/item/{i}?m=Saved")

    @app.get("/make")
    def make():
        cats = list((pipe.cfg.get("schedule") or {}).get("categories") or [])
        opts = "<option value=''>Next automatic pick (balanced rotation)</option>" + "".join(f"<option value='{E(c)}'>Category: {E(c)}</option>" for c in cats)
        stories = sorted(p.stem for p in Path(pipe.sel.stories_dir).glob("*.json")) if getattr(pipe.sel, "stories_dir", None) and Path(pipe.sel.stories_dir).exists() else []
        opts += "".join(f"<option value='story:{E(s)}'>Story: {E(s)}</option>" for s in stories)
        st = f'<div class=msg>Job: <b>{E(job["state"])}</b> {E(job["msg"])} (page refreshes itself)</div><meta http-equiv=refresh content=10>' if job["state"] == "running" else (f'<div class=msg>Last job: {E(job["state"])} {E(job["msg"])}</div>' if job["state"] != "idle" else "")
        body = (f"<h1>Make a video now</h1>{st}<form method=post action=/make><p><select name=only>{opts}</select> <input type=submit value='Make it'></p></form>"
                "<p>It picks verified, non-duplicate content, renders, runs every check, and stops at <i>rendered</i> or <i>needs_review</i>. It never uploads by itself; approve it on its page, and the scheduler or workflow does the upload. "
                "A render takes several minutes on a normal PC. Only one job runs at a time.</p>")
        return page("Make now", body)

    @app.post("/make")
    def make_post():
        only = (request.form.get("only") or "").strip() or None
        with lock:
            if job["state"] == "running": return redirect("/make")
            job.update(state="running", msg=f"({only or 'next'})", started=dt.datetime.now().isoformat(timespec="seconds"))
        def run():
            try:
                i = pipe.make_next(only=only)
                job.update(state="done", msg=(f"-> item {i}" if i else "nothing eligible (see rejected candidates)"))
            except Exception as ex: job.update(state="failed", msg=str(ex)[:200])
        threading.Thread(target=run, daemon=True).start()
        return redirect("/make")

    synth_lock = threading.Lock()

    @app.get("/voice")
    def voice():
        cur = _get(pipe.cfg, ("audio", "narration", "voice")); sp = _get(pipe.cfg, ("audio", "narration", "speed")) or 1.0
        on = _get(pipe.cfg, ("audio", "narration", "enabled"))
        rows = "".join(f"<tr><td><b>{E(v)}</b>{' (in use)' if v == cur else ''}</td><td>{E(d)}</td><td><audio controls preload=none src='/voice/sample/{E(v)}.wav?speed={sp}'></audio></td>"
                       f"<td><form method=post action=/voice><input type=hidden name=voice value='{E(v)}'><input type=hidden name=speed value='{sp}'><button {'disabled' if v == cur else ''}>Use this voice</button></form></td></tr>" for v, d in VOICES.items())
        body = (f"<h1>Choose the English voice</h1><p>Narration is {'on' if on else '<b>off</b> (turn it on in Settings)'}. Press play to hear a short sample; the first play of each voice takes a few seconds to generate.</p>"
                f"<form method=post action=/voice><p>Speed <input type=range name=speed min=0.85 max=1.3 step=0.01 value='{sp}' oninput=\"this.nextElementSibling.textContent=this.value\"><output>{sp}</output> "
                f"<input type=hidden name=voice value='{E(cur or 'bm_george')}'> <input type=submit value='Save speed'> <small>0.95 calm, 1.12 brisk (current default).</small></p></form>"
                f"<table><tr><th>Voice</th><th>Style</th><th>Sample</th><th></th></tr>{rows}</table>"
                "<p>All seven are the free Kokoro model (Apache-2.0). They apply to new videos and to re-renders. The Quran itself is never read by these voices; it is always the real recitation. "
                "Samples use a neutral sentence, never Quran text.</p>")
        return page("Voice", body, request.args.get("m", ""))

    @app.get("/voice/sample/<name>.wav")
    def voice_sample(name):
        if name not in VOICES: abort(404)
        try: sp = round(min(max(float(request.args.get("speed", 1.0)), 0.85), 1.3), 2)
        except Exception: sp = 1.0
        f = ROOT / "data" / "cache" / "voice_samples" / f"{name}_{sp}.wav"
        if not f.exists():
            from . import tts
            f.parent.mkdir(parents=True, exist_ok=True)
            with synth_lock:
                try: tts.speak_en(SAMPLE, f, voice=name, speed=sp, human=bool(_get(pipe.cfg, ("audio", "narration", "humanize"))))
                except Exception: f.unlink(missing_ok=True); abort(503)
        return send_file(f, mimetype="audio/wav", conditional=True)

    @app.post("/voice")
    def voice_post():
        v = request.form.get("voice")
        if v not in VOICES: return redirect("/voice?m=Unknown+voice")
        try: sp = round(min(max(float(request.form.get("speed", 1.0)), 0.85), 1.3), 2)
        except Exception: return redirect("/voice?m=Invalid+speed")
        f = ROOT / "data" / "overrides.yaml"; ov = {}
        if f.exists():
            try: ov = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            except Exception: ov = {}
        new = {"audio": {"narration": {"voice": v, "speed": sp}}}
        deep_update(ov, new); f.parent.mkdir(parents=True, exist_ok=True); f.write_text(yaml.safe_dump(ov, sort_keys=False), encoding="utf-8")
        deep_update(pipe.cfg, new); db.log("info", f"voice set to {v} speed {sp} in the dashboard")
        return redirect(f"/voice?m=Saved:+{v}+at+{sp}.+New+renders+use+it.")

    def overrides_changes():
        f = ROOT / "data" / "overrides.yaml"
        try: ov = yaml.safe_load(f.read_text(encoding="utf-8")) or {} if f.exists() else {}
        except Exception: ov = {}
        paths = [p for p, *_ in SETTINGS] + [tuple(f['cfg']) for f in FEAT.FEATURES if f['cfg']] + [tuple(f['cfg']) for f in FEAT.SCRIPT_FEATURES if f['cfg']]
        return {path: _get(ov, path) for path in dict.fromkeys(paths) if _get(ov, path) is not None}

    @app.get("/github")
    def github():
        ch = overrides_changes(); slug = GH.repo_slug(ROOT); tok = GH.token(ROOT)
        st = (f"<p>Repository: <b>{E(slug) if slug else 'not found'}</b> &middot; Token: <b>{'found' if tok else 'not found'}</b></p>")
        if not slug: st += "<p>Set <code>IVS_GITHUB_REPO=owner/name</code> in <code>.env</code>, or run this from a folder cloned from your repo.</p>"
        if not tok: st += ("<p>No token. Create one at GitHub &gt; Settings &gt; Developer settings &gt; Fine-grained tokens: only this repository, permission <b>Contents: Read and write</b>. "
                           "Put it in <code>.env</code> as <code>IVS_GITHUB_TOKEN=...</code> (never share it), or log in with the GitHub CLI (<code>gh auth login</code>). Restart the dashboard.</p>")
        body = ["<h1>GitHub sync</h1><p>Saves your dashboard settings into <code>config.yaml</code> in your repo, so the cloud runs use them too. Only the settings listed on the Settings and Voice pages are touched; comments stay.</p>", st]
        if not ch: body.append("<p>No saved settings yet. Change something on the Settings or Voice page first.</p>")
        else:
            body.append("<h2>Settings to push</h2><table>" + "".join(f"<tr><td>{E('.'.join(k))}</td><td><b>{E(str(v))}</b></td></tr>" for k, v in ch.items()) + "</table>")
            if slug and tok:
                try:
                    pv = GH.preview(slug, tok, ch)
                    body.append("<h2>What will change on GitHub</h2>" + (f"<pre>{E(pv['diff'])}</pre>" if pv["changed"] else "<p>GitHub already has these settings.</p>"))
                    if pv["skipped"]: body.append(f"<p class=warn>Could not find these in config.yaml, so they are skipped: {E(', '.join(pv['skipped']))}</p>")
                    if pv["changed"]: body.append("<form method=post action=/github><button>Push to GitHub (creates one commit)</button></form>")
                except Exception as ex: body.append(f"<p class=fail>{E(str(ex))[:300]}</p>")
        body.append("<p>Pushing makes a normal commit on your repo's default branch. The next workflow run uses it; you can revert it in GitHub's history.</p>")
        return page("GitHub sync", "".join(body), request.args.get("m", ""))

    @app.post("/github")
    def github_push():
        ch = overrides_changes(); slug = GH.repo_slug(ROOT); tok = GH.token(ROOT)
        if not (ch and slug and tok): return redirect("/github?m=Nothing+to+push+or+missing+repo/token")
        try: r = GH.push(slug, tok, ch)
        except Exception as ex: return redirect("/github?m=" + _q(ex))
        db.log("info", "settings pushed to GitHub config.yaml" if r["pushed"] else "GitHub sync: nothing to change")
        return redirect("/github?m=" + ("Pushed.+The+next+workflow+run+uses+it." if r["pushed"] else "GitHub+already+has+these+settings."))

    @app.get("/settings")
    def settings():
        ov = {}; f = ROOT / "data" / "overrides.yaml"
        if f.exists():
            try: ov = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            except Exception: pass
        rows = []
        for path, label, kind, ch in SETTINGS:
            v = _get(pipe.cfg, path); n = ".".join(path)
            if kind == "bool": w = f"<input type=checkbox name='{n}' value=1 {'checked' if v else ''}>"
            elif kind == "choice": w = f"<select name='{n}'>" + "".join(f"<option {'selected' if o == v else ''}>{E(o)}</option>" for o in ch) + "</select>"
            else: w = f"<input type=number step=0.01 min={ch[0]} max={ch[1]} name='{n}' value='{v}'>"
            rows.append(f"<tr><td>{E(label)}</td><td>{w}</td><td><small>{E(n)}{' *' if _get(ov, path) is not None else ''}</small></td></tr>")
        body = ("<h1>Settings</h1><form method=post action=/settings><table>" + "".join(rows) + "</table><p><input type=submit value='Save'></p></form>"
                "<p>Saved to <code>data/overrides.yaml</code> and used by <b>local</b> runs (* = overridden). GitHub Actions reads <code>config.yaml</code> in your repo, so change it there too for the cloud runs. "
                "Safety rules (no faces, never synthetic voice over the Quran, human review of stories and hadith, zero cost) cannot be changed here.</p>"
                "<p>Turning off <b>Real Quran recitation</b> gives a fully copyright-free video with text only.</p>")
        return page("Settings", body, request.args.get("m", ""))

    @app.post("/settings")
    def settings_post():
        new = {}
        for path, label, kind, ch in SETTINGS:
            n = ".".join(path)
            if kind == "bool": v = request.form.get(n) == "1"
            elif n not in request.form: continue          # field not submitted: keep the current value
            elif kind == "choice":
                v = request.form.get(n)
                if v not in ch: return redirect(f"/settings?m=Invalid+value+for+{n}")
            else:
                try: v = round(min(max(float(request.form.get(n)), ch[0]), ch[1]), 2)
                except Exception: return redirect(f"/settings?m=Invalid+number+for+{n}")
            _set(new, path, v)
        trial = json.loads(json.dumps({k: v for k, v in pipe.cfg.items()}, default=str)); deep_update(trial, new)
        try: enforce_zero_cost(trial)
        except Exception as ex: return redirect("/settings?m=" + _q(ex))
        f = ROOT / "data" / "overrides.yaml"; f.parent.mkdir(parents=True, exist_ok=True)
        try: old = yaml.safe_load(f.read_text(encoding="utf-8")) or {} if f.exists() else {}
        except Exception: old = {}
        f.write_text(yaml.safe_dump(deep_update(old, new), sort_keys=False), encoding="utf-8")
        deep_update(pipe.cfg, new); db.log("info", "settings changed in the dashboard")
        return redirect("/settings?m=Saved.+New+renders+use+it.")

    @app.get("/history")
    def history():
        c = db.conn; now = dt.datetime.now(dt.timezone.utc); nx = next_run_utc(now); lvl = request.args.get("l")
        day = {}
        for r in c.execute("SELECT substr(ts,1,10) d, SUM(units) u FROM quota_log WHERE platform='youtube' AND ts>=? GROUP BY d", ((now - dt.timedelta(days=14)).isoformat(),)):
            day[r["d"]] = r["u"]
        qv = [((now - dt.timedelta(days=k)).date().isoformat(), int(day.get((now - dt.timedelta(days=k)).date().isoformat(), 0))) for k in range(13, -1, -1)]
        d = SITE.collect(db, pipe.cfg)
        pl = c.execute("SELECT * FROM publish_log ORDER BY id DESC LIMIT 30").fetchall()
        logs = c.execute("SELECT * FROM event_log" + (" WHERE level=?" if lvl else "") + " ORDER BY id DESC LIMIT 150", ((lvl,) if lvl else ())).fetchall()
        want = _get(pipe.cfg, ("publishing", "platforms", "youtube", "privacy")) or "public"
        lock = [r for r in pl if r["ok"] and r["detail"] and r["detail"] != want]
        warn = (f"<div class=msg><b>YouTube made {len(lock)} recent upload(s) not '{E(want)}'.</b> A new Google Cloud project can only upload private videos until it passes YouTube's API audit. "
                "Fix: submit the free <i>YouTube API Services - Audit and Quota Extension</i> form for your project (see docs/YOUTUBE_SETUP.md). Until then, set them public by hand in YouTube Studio.</div>") if lock else ""
        body = (f"<h1>History</h1>{warn}<p>Next scheduled workflow run: <b>{nx.strftime('%Y-%m-%d %H:%M')} UTC</b> ({(nx + dt.timedelta(hours=5)).strftime('%H:%M')} Karachi). The cron is every 2 hours; local runs follow your own scheduler.</p>"
                "<h2>YouTube quota used per day (units)</h2>" + bars(qv) + "<h2>Total views, last 14 days</h2>" + bars([(p["d"], int(p["views"] or 0)) for p in d["hist"]]) +
                "<h2>Uploads</h2><table><tr><th>When</th><th>Item</th><th>Result</th><th>Link</th></tr>" +
                "".join(f"<tr><td>{E(r['ts'])}</td><td><a href='/item/{r['item_id']}'>{r['item_id']}</a></td><td>{('ok, ' + E(r['detail'] or '')) if r['ok'] else 'failed: ' + E((r['detail'] or '')[:150])}</td><td>{('<a href=' + chr(34) + E(r['url']) + chr(34) + '>video</a>') if r['url'] else ''}</td></tr>" for r in pl) +
                "</table><h2>Event log</h2><p>" + " ".join(f"<a href='/history?l={x}'>{x}</a>" for x in ("info", "warn", "error")) + " <a href='/history'>all</a></p><table>" +
                "".join(f"<tr><td>{E(r['ts'])}</td><td>{E(r['level'])}</td><td>{E(str(r['item_id'] or ''))}</td><td>{E(r['msg'][:300])}</td></tr>" for r in logs) + "</table>")
        return page("History", body)

    @app.get("/credits")
    def credits():
        c = db.conn
        a = c.execute("SELECT kind,name,license,attribution,source_url,COUNT(*) n FROM assets_used GROUP BY kind,name,license ORDER BY kind,name").fetchall()
        s = c.execute("SELECT DISTINCT source_title,translator,license FROM claims WHERE source_title IS NOT NULL ORDER BY 1").fetchall()
        body = ("<h1>Credits and licences</h1><h2>Text sources</h2><table><tr><th>Source</th><th>Translator</th><th>Licence</th></tr>" +
                "".join(f"<tr><td>{E(x['source_title'])}</td><td>{E(x['translator'] or '')}</td><td>{E(x['license'] or '')}</td></tr>" for x in s) +
                "</table><h2>Assets used in videos</h2><table><tr><th>Kind</th><th>Name</th><th>Licence</th><th>Credit</th><th>Used</th></tr>" +
                "".join(f"<tr><td>{E(x['kind'] or '')}</td><td>{E(x['name'] or '')}</td><td>{E(x['license'] or '')}</td><td>{E(x['attribution'] or '')}</td><td>{x['n']}</td></tr>" for x in a) +
                "</table><h2>Recitation terms (what the sources say)</h2><ul>"
                "<li><a href='https://alquran.cloud/terms-and-conditions'>Islamic Network terms</a>: recitations may be streamed, embedded and downloaded for <b>personal and educational use</b>; they remain the copyright of the reciters; in a commercial product the reciters may ask you to remove them.</li>"
                "<li><a href='https://community.islamic.network/d/231-clarification-on-licensing-and-usage-rights-for-quran-recitation-api'>Islamic Network staff</a>: no explicit right is granted; copyright stays with the reciter; attribution asked where possible; do not charge for free recordings.</li>"
                "<li>EveryAyah.com publishes no written terms that I could find.</li></ul>"
                "<p><b>What this project does about it:</b> every description names the reciter and the site the audio came from, states that the copyright stays with the reciter, that it is shared free for educational non-commercial use, and promises removal on request. Do not monetize and do not paywall. Not legal advice; for certainty, ask the rights holders in writing. See docs/LICENSES.md.</p>")
        return page("Credits", body)

    @app.post("/approve/<int:i>")
    def approve(i):
        try: pipe.approve(i); m = "Approved"
        except Exception as ex: m = str(ex)
        return redirect("/?m=" + _q(m))
    @app.post("/skip/<int:i>")
    def skip(i): pipe.skip(i); return redirect("/")
    @app.post("/rerender/<int:i>")
    def rerender(i):
        with lock:
            if job["state"] == "running": return redirect("/make")
            job.update(state="running", msg=f"(re-render {i})")
        def run():
            try: pipe.render_item(i); job.update(state="done", msg=f"re-rendered {i}")
            except Exception as ex: job.update(state="failed", msg=str(ex)[:200])
        threading.Thread(target=run, daemon=True).start(); return redirect("/make")
    @app.post("/pause")
    def pause(): db.put_setting("paused", "0" if db.setting("paused") == "1" else "1"); return redirect(request.referrer or "/")
    from . import dashboard_more; dashboard_more.register(app, dict(page=page, E=E, pipe=pipe, db=db, job=job, lock=lock, root=ROOT))
    return app
