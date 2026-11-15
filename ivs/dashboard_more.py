"""Extra dashboard pages: Tools (stats, recitation, drafts, GitHub workflow), AI key, Stories editor + review queue.
Registered onto the Flask app by dashboard.create_app. Local only; secrets are written, never shown."""
from __future__ import annotations
import datetime as dt, html, os, re, subprocess, sys, threading
from pathlib import Path
import yaml
from . import github_sync as GH, features as FEAT, looks as LK
from .config import ROOT

from urllib.parse import quote_plus as _qp
def _q(x): return _qp(str(x).replace("\n", " ")[:200])

FREE_AI = {   # only providers with a free tier; paid ones are left out to keep the project at $0
    "gemini": ("GEMINI_API_KEY", "Google Gemini (free tier; keep billing OFF)"),
    "groq": ("GROQ_API_KEY", "Groq (free tier)"),
    "openrouter": ("OPENROUTER_API_KEY", "OpenRouter (use :free models)"),
    "mistral": ("MISTRAL_API_KEY", "Mistral (free tier)"),
}
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{1,60}$")

def register(app, ctx):
    from flask import request, redirect, abort
    page, E, pipe, db, job, lock, ROOT = ctx["page"], ctx["E"], ctx["pipe"], ctx["db"], ctx["job"], ctx["lock"], ctx["root"]
    stories_dir = Path(getattr(pipe.sel, "stories_dir", None) or ROOT / "content" / "stories")

    def start(label, fn):
        with lock:
            if job["state"] == "running": return False
            job.update(state="running", msg=label, started=dt.datetime.now().isoformat(timespec="seconds"))
        def run():
            try: job.update(state="done", msg=f"{label}: {fn()}"[:400])
            except Exception as ex: job.update(state="failed", msg=f"{label}: {ex}"[:400])
        threading.Thread(target=run, daemon=True).start(); return True

    def cli(*args, timeout=1800):
        def f():
            env = dict(os.environ); env.update(GH._dotenv(ROOT))
            r = subprocess.run([sys.executable, "-m", "ivs", *args], cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=timeout)
            tail = (r.stdout.strip().splitlines() or r.stderr.strip().splitlines() or [""])[-1]
            return ("ok " if r.returncode == 0 else f"exit {r.returncode} ") + tail[:200]
        return f

    def jobbox():
        if job["state"] == "idle": return ""
        refresh = "<meta http-equiv=refresh content=8>" if job["state"] == "running" else ""
        return f'<div class=msg>Job: <b>{E(job["state"])}</b> {E(job["msg"])}</div>{refresh}'

    # ------------------------------------------------------------------ Tools
    @app.get("/tools")
    def tools():
        slug, tok = GH.repo_slug(ROOT), GH.token(ROOT); runs_html = ""
        if slug and tok:
            try:
                rs = GH.runs(slug, tok)
                runs_html = "<table><tr><th>Workflow</th><th>Status</th><th>When</th></tr>" + "".join(
                    f"<tr><td><a href='{E(r['url'] or '#')}'>{E(r['name'] or '')}</a> <small>{E(r['event'] or '')}</small></td><td class={'pass' if r['conclusion'] == 'success' else ('fail' if r['conclusion'] == 'failure' else 'warn')}>{E(str(r['conclusion'] or r['status']))}</td><td>{E(r['created'] or '')}</td></tr>" for r in rs) + "</table>"
            except Exception as ex: runs_html = f"<p class=fail>{E(str(ex))[:250]}</p>"
        else: runs_html = "<p>Needs a repo and token: see the <a href=/github>GitHub sync</a> page.</p>"
        b = lambda path, label, extra="": f"<form method=post action='{path}' style='display:inline'>{extra}<button>{label}</button></form> "
        body = (f"<h1>Tools</h1>{jobbox()}<p>These run on this computer, one at a time.</p>"
                "<h2>This computer</h2><p>" + b("/tools/stats", "Refresh view and like counts") + b("/tools/recitation", "Download all recitation audio") +
                b("/tools/draft", "Draft next story from the queue", "<select name=n><option>1</option><option>2</option><option>3</option></select> ") + "</p>"
                "<p><small>Stats need your YouTube login. Recitation downloads from EveryAyah / Islamic Network and takes a while the first time. Drafts need no key (an AI key makes them better) and always wait for your review on the Stories page.</small></p>"
                "<h2>GitHub Actions</h2><p>" + b("/tools/workflow", "Run the daily workflow now", "<select name=privacy><option value=''>privacy: default</option><option>private</option><option>unlisted</option><option>public</option></select> ") +
                b("/tools/workflow-pages", "Rebuild the dashboard website") + "</p><p><small>Needs a token with Actions: Read and write.</small></p>" + runs_html)
        return page("Tools", body, request.args.get("m", ""))

    @app.post("/tools/stats")
    def t_stats(): return redirect("/tools?m=" + ("Started" if start("refresh stats", cli("stats", timeout=300)) else "A+job+is+already+running"))
    @app.post("/tools/recitation")
    def t_rec(): return redirect("/tools?m=" + ("Started" if start("download recitation", cli("fetch-recitation")) else "A+job+is+already+running"))
    @app.post("/tools/draft")
    def t_draft():
        try: n = min(max(int(request.form.get("n", 1)), 1), 3)
        except Exception: n = 1
        return redirect("/tools?m=" + ("Started" if start(f"draft {n} stories", cli("draft-queue", "--n", str(n), timeout=1200)) else "A+job+is+already+running"))

    def wf(name, inputs=None):
        slug, tok = GH.repo_slug(ROOT), GH.token(ROOT)
        if not (slug and tok): return redirect("/tools?m=Needs+repo+and+token+(see+GitHub+sync)")
        try: GH.dispatch(slug, tok, name, inputs)
        except Exception as ex: return redirect("/tools?m=" + _q(str(ex)))
        db.log("info", f"workflow {name} started from the dashboard")
        return redirect("/tools?m=Started+" + name + ".+Watch+the+list+below.")
    @app.post("/tools/workflow")
    def t_wf():
        p = request.form.get("privacy") or ""
        return wf("daily.yml", {"privacy": p} if p in ("private", "unlisted", "public") else None)
    @app.post("/tools/workflow-pages")
    def t_pages(): return wf("pages.yml")

    # ------------------------------------------------------------------ AI key
    @app.get("/ai")
    def ai():
        rows = "".join(f"<tr><td>{E(label)}</td><td>{E(var)}</td><td>{'<b class=pass>set</b>' if GH.env_has(ROOT, var) else 'not set'}</td></tr>" for var, label in FREE_AI.values())
        opts = "".join(f"<option value='{k}'>{E(v[1])}</option>" for k, v in FREE_AI.items())
        gh = bool(GH.repo_slug(ROOT)) and bool(__import__("shutil").which("gh"))
        body = ("<h1>AI key (optional)</h1><p>Used only to draft story scripts from verified text; drafts always wait for your review. Without a key, a plain built-in drafter is used. "
                "Only providers with a free tier are listed, so the project stays at $0. Keep billing off at the provider.</p><table><tr><th>Provider</th><th>Variable</th><th>This computer</th></tr>" + rows + "</table>"
                f"<form method=post action=/ai><h2>Save a key</h2><p><select name=provider>{opts}</select></p><p><input type=password name=key autocomplete=off placeholder='paste key (hidden)' style='width:100%'></p>"
                f"<p><label><input type=checkbox name=gh value=1 {'checked' if gh else 'disabled'}> Also save as a GitHub secret for the cloud drafter (needs the GitHub CLI, logged in)</label></p><p><input type=submit value='Save key'></p></form>"
                "<p>The key is written to <code>.env</code> (private, not uploaded to git) and is never shown again. To remove it, delete its line from <code>.env</code>. Restart the dashboard after saving so it is picked up.</p>")
        return page("AI key", body, request.args.get("m", ""))

    @app.post("/ai")
    def ai_save():
        prov, key = request.form.get("provider"), (request.form.get("key") or "").strip()
        if prov not in FREE_AI: return redirect("/ai?m=Unknown+provider")
        var = FREE_AI[prov][0]
        try: GH.env_set(ROOT, var, key)
        except ValueError: return redirect("/ai?m=That+key+does+not+look+valid")
        os.environ[var] = key; msg = f"Saved+{var}+to+.env."
        if request.form.get("gh") == "1":
            slug = GH.repo_slug(ROOT); msg += "+GitHub+secret+saved." if slug and GH.gh_secret(slug, var, key) else "+GitHub+secret+could+NOT+be+saved+(is+gh+logged+in?)."
        db.log("info", f"AI key for {prov} saved")           # name only, never the value
        return redirect("/ai?m=" + msg)

    # ------------------------------------------------------------------ Script & Director
    sc_switch = [f for f in FEAT.SCRIPT_FEATURES if f["status"] == "done" and f["cfg"]]
    def _sc_cfg(): 
        from . import scriptlab as SL
        return SL.cfg_script(pipe.cfg)

    @app.get("/script")
    def script_page():
        from . import scriptlab as SL
        cnt = FEAT.script_counts(); S = _sc_cfg()
        presets = "".join(f"<form method=post action=/script/preset style=display:inline><input type=hidden name=preset value={n}><button>{n}</button></form> " for n in FEAT.SCRIPT_PRESETS)
        rows = ""
        for cat in FEAT.SCRIPT_CATEGORIES:
            rows += f"<tr><th colspan=3 style='color:#d9b36a;padding-top:18px'>{E(cat)}</th></tr>"
            for f in (x for x in FEAT.SCRIPT_FEATURES if x["category"] == cat):
                if f["status"] == "planned": st, c = "<span class=warn>planned</span>", "style='opacity:.6'"
                elif f["cfg"]: st, c = f"<input type=checkbox name='{'.'.join(f['cfg'])}' value=1 {'checked' if S.get(f['cfg'][1], pipe.cfg.get('script', {}).get(f['cfg'][1])) else ''}>", ""
                else: st, c = "<span class=pass>built, always on</span>", ""
                rows += f"<tr {c}><td style='width:170px'>{st}</td><td><b>{E(f['name'])}</b></td><td><small>{E(f['desc'])}</small></td></tr>"
        # hook insights
        try: ins = SL.hook_insights(db)
        except Exception: ins = []
        irows = "".join(f"<tr><td>{E(str(r['pattern']))}<br><small>{E(str(r.get('example', '')))}</small></td><td>{r['n']}</td><td>{r['avg']}</td></tr>" for r in (ins or [])[:15]) if isinstance(ins, list) else ""
        itab = f"<h2>Hook insights</h2><table><tr><th>Hook shape</th><th>Videos</th><th>Average views</th></tr>{irows}</table>" if irows else "<h2>Hook insights</h2><p><small>No view statistics yet. Run Tools &gt; Refresh stats after videos are public. Small samples prove nothing; treat this as a hint.</small></p>"
        # script lab
        iid = request.args.get("item", type=int); lab_html = ""
        items = db.items()
        opts = "".join(f"<option value={r['id']} {'selected' if r['id'] == iid else ''}>#{r['id']} {E(r['key'])} ({E(r['status'])})</option>" for r in items[-40:][::-1])
        if iid:
            it = db.get_item(iid)
            if it:
                try:
                    lb = SL.lab(pipe._rebuild_content(it), db, pipe.cfg, iid)
                    hr = "".join(f"<tr><td>{E(h['text'] if 'text' in h else h.get('hook',''))}</td><td>{h.get('score','')}</td><td>{'<span class=fail>rejected</span>' if h.get('rejected') else ''}</td></tr>" for h in lb["hooks"][:12])
                    tr_ = "".join(f"<tr><td>{E(t['title'])}</td><td>{t['score']}</td><td><form method=post action=/script/title><input type=hidden name=item value={iid}><input type=hidden name=title value='{E(t['title'])}'><button>Use</button></form></td></tr>" for t in lb["titles"])
                    er = "".join(f"<tr><td>{E(e['kind'])}</td><td>{E(e['text'])}<br><small>Spoken: {E(e['spoken'])}</small></td><td>grade {e['grade']}</td><td>{'<span class=fail>' + E('; '.join(map(str, e['problems']))) + '</span>' if e['problems'] else '<span class=pass>ok</span>'}</td></tr>" for e in lb["editorial"])
                    bt = ", ".join(f"{b['scene']}: {E(b['feel'])} ({b['intensity']})" for b in lb["beats"]) or "single-verse video: no beat map"
                    lab_html = (f"<h2>Lab for #{iid}</h2><h3>Hooks</h3><table>{hr}</table><h3>Titles</h3><table>{tr_}</table><h3>Editorial lines</h3><table>{er}</table>"
                                f"<p><b>Beats:</b> {bt}<br><b>Arc:</b> {E('; '.join(lb['arc_problems']) or 'ok')}<br><b>Series line:</b> {E(lb['series'] or '-')}</p>")
                except Exception as e: lab_html = f"<p class=fail>Lab failed: {E(str(e))}</p>"
        body = (f"<h1>Script &amp; Director</h1><p><b>{cnt['total']}</b> improvements to script writing and direction: <b class=pass>{cnt['done']} built</b> ({cnt['switchable']} with a switch), <b class=warn>{cnt['planned']} planned</b> (not built, no switch). "
                "These are rule-based checks and choices, not a judge of religious accuracy, and they do not guarantee views. Anything the lint flags goes to human review.</p>"
                f"<p>Presets: {presets}</p><form method=post action=/script><p><input type=submit value='Save switches'></p><table>{rows}</table><p><input type=submit value='Save switches'></p></form>"
                f"{itab}<h2>Script lab</h2><form method=get action=/script><select name=item>{opts}</select> <button>Preview hooks, titles, lint</button></form>{lab_html}")
        return page("Script & Director", body, request.args.get("m", ""))

    @app.post("/script")
    def script_save():
        new = {}
        for f in sc_switch: _set(new, tuple(f["cfg"]), request.form.get(".".join(f["cfg"])) == "1")
        _save_overrides(new); db.log("info", "script and director switches saved in the dashboard")
        return redirect("/script?m=Saved.+New+videos+and+re-renders+use+it.")

    @app.post("/script/preset")
    def script_preset():
        p = FEAT.SCRIPT_PRESETS.get(request.form.get("preset") or "")
        if not p: return redirect("/script?m=Unknown+preset")
        _save_overrides({"script": dict(p)}); db.log("info", f"script preset {request.form.get('preset')} applied")
        return redirect("/script?m=Preset+applied.")

    @app.post("/script/title")
    def script_title():
        import json
        i = request.form.get("item", type=int); title = (request.form.get("title") or "").strip()[:100]
        it = db.get_item(i) if i else None
        if not it or it["status"] == "published" or not title: return redirect("/script?m=Cannot+change+this+title")
        db.conn.execute("UPDATE content_items SET title=?,updated_at=? WHERE id=?", (title, dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), i)); db.conn.commit()
        if it["video_path"]:
            mp = Path(it["video_path"]).parent / "metadata.json"
            try: m = json.loads(mp.read_text(encoding="utf-8")); m["title"] = title; mp.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception: pass
        db.log("info", "title chosen from script lab", i)
        return redirect(f"/script?item={i}&m=Title+set")

    # ------------------------------------------------------------------ Look & Story
    def _get(d, path):
        for k in path:
            d = d.get(k) if isinstance(d, dict) else None
        return d
    def _set(d, path, v):
        for k in path[:-1]: d = d.setdefault(k, {})
        d[path[-1]] = v
    def _save_overrides(new):
        from .config import deep_update
        f = ROOT / "data" / "overrides.yaml"
        try: old = (yaml.safe_load(f.read_text(encoding="utf-8")) or {}) if f.exists() else {}
        except Exception: old = {}
        f.parent.mkdir(parents=True, exist_ok=True); f.write_text(yaml.safe_dump(deep_update(old, new), sort_keys=False), encoding="utf-8")
        deep_update(pipe.cfg, new)
    switchable = [f for f in FEAT.FEATURES if f["status"] == "done" and f["cfg"] and f["cfg"] != ("look", "grade")]
    preview_file = ROOT / "data" / "cache" / "look_preview.mp4"

    def form_look(form):
        """Read the whole Look & Story form: every switchable item posts, so an unticked box means off."""
        new = {}
        for f in switchable: _set(new, tuple(f["cfg"]), form.get(".".join(f["cfg"])) == "1")
        g = form.get("look.grade")
        if g in LK.GRADES: _set(new, ("look", "grade"), g)
        return new

    @app.get("/looks")
    def looks_page():
        cnt = FEAT.counts(); cur_grade = _get(pipe.cfg, ("look", "grade")) or "auto"
        presets = "".join(f"<form method=post action=/looks/preset style=display:inline><input type=hidden name=preset value={n}><button>{n}</button></form> " for n in FEAT.PRESETS)
        gopts = "".join(f"<option {'selected' if g == cur_grade else ''}>{g}</option>" for g in LK.GRADES)
        rows = ""
        for cat in FEAT.CATEGORIES:
            rows += f"<tr><th colspan=3 style='color:#d9b36a;padding-top:18px'>{E(cat)}</th></tr>"
            for f in (x for x in FEAT.FEATURES if x["category"] == cat):
                if f["status"] == "planned": st, c = "<span class=warn>planned</span>", "style='opacity:.6'"
                elif f["cfg"] and f["cfg"] != ("look", "grade"):
                    n = ".".join(f["cfg"]); st, c = f"<input type=checkbox name='{n}' value=1 {'checked' if _get(pipe.cfg, tuple(f['cfg'])) else ''}>", ""
                elif f["cfg"]: st, c = f"<select name='look.grade'>{gopts}</select>", ""
                else: st, c = "<span class=pass>built, always on</span>", ""
                rows += f"<tr {c}><td style='width:170px'>{st}</td><td><b>{E(f['name'])}</b></td><td><small>{E(f['desc'])}</small></td></tr>"
        pv = f"<h2>Preview</h2><video controls loop src='/looks/preview.mp4?{int(preview_file.stat().st_mtime)}' style='max-height:60vh'></video>" if preview_file.exists() else ""
        body = (f"<h1>Look &amp; Story</h1>{jobbox()}<p><b>{cnt['total']}</b> improvements for illustration and storytelling: <b class=pass>{cnt['done']} built</b> ({cnt['switchable']} with a switch here), <b class=warn>{cnt['planned']} planned</b>. "
                "Planned items are not built yet and have no switch. Effects only dress the picture: they never touch the audio or the Quran text.</p>"
                f"<p>Presets: {presets}</p>{pv}"
                "<form method=post action=/looks><p><input type=submit value='Save switches'> "
                "<button formaction=/looks/preview>Preview these switches on my latest video (8 s)</button> <small>Preview needs a rendered video on this computer. Saved switches apply to new videos and re-renders; use GitHub sync for cloud runs.</small></p>"
                f"<table>{rows}</table><p><input type=submit value='Save switches'></p></form>")
        return page("Look & Story", body, request.args.get("m", ""))

    @app.post("/looks")
    def looks_save():
        _save_overrides(form_look(request.form)); db.log("info", "look and story switches saved in the dashboard")
        return redirect("/looks?m=Saved.+New+videos+and+re-renders+use+it.")

    @app.post("/looks/preset")
    def looks_preset():
        p = FEAT.PRESETS.get(request.form.get("preset") or "")
        if not p: return redirect("/looks?m=Unknown+preset")
        _save_overrides({"look": dict(p)}); db.log("info", f"look preset {request.form.get('preset')} applied")
        return redirect("/looks?m=Preset+applied.")

    @app.post("/looks/preview")
    def looks_preview():
        new = form_look(request.form); look = dict(LK.cfg_look({"look": (pipe.cfg.get("look") or {})})); look.update(new.get("look", {}))
        src = None
        for it in db.items():
            if it["video_path"]:
                q = Path(it["video_path"]); q = q if q.is_absolute() else Path(pipe.out_root) / q
                if q.exists(): src = (q, it["title"] or it["key"]); break
        if not src: return redirect("/looks?m=No+rendered+video+on+this+computer+yet.+Make+one+first.")
        def run_preview():
            import subprocess, tempfile
            preview_file.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory() as td:
                cut = Path(td) / "c.mp4"
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src[0]), "-t", "8", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(cut)], check=True, timeout=120)
                from . import jsfx
                w, h = jsfx._size(cut)
                g, on = LK.build_graph(look, src[1], [2.5, 5.5], 8.0, int(pipe.cfg["video"]["fps"]), w, h)
                if not g or not on: raise RuntimeError("every effect is off: nothing to preview")
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(cut), "-filter_complex", g, "-map", "[out]", "-r", str(pipe.cfg["video"]["fps"]), *LK.ENC, "-an", "-movflags", "+faststart", str(preview_file)], check=True, timeout=300)
            return "preview ready (" + ", ".join(on) + ")"
        ok = start("look preview", run_preview)
        return redirect("/looks?m=" + ("Preview+is+rendering+(about+half+a+minute)" if ok else "A+job+is+already+running"))

    @app.get("/looks/preview.mp4")
    def looks_preview_file():
        from flask import send_file
        if not preview_file.exists(): abort(404)
        return send_file(preview_file, mimetype="video/mp4", conditional=True)

    # ------------------------------------------------------------------ Stories
    def story_files():
        out = []
        for d, tag in ((stories_dir, "stories"), (stories_dir / "drafts", "drafts")):
            if d.exists():
                for p in sorted(d.glob("*.yaml")):
                    if not p.name.startswith("_"): out.append((tag, p))
        return out

    def find(tag, name):
        if tag not in ("stories", "drafts") or not NAME.match(name): abort(404)
        p = (stories_dir if tag == "stories" else stories_dir / "drafts") / f"{name}.yaml"
        return p

    def flagged(text):
        try: d = yaml.safe_load(text) or {}
        except Exception: return None
        return bool((d.get("draft") or {}).get("needs_human_review")) if isinstance(d, dict) else None

    def check(text, name):
        """Returns (error_or_None, warnings). Errors block saving; verification warnings do not."""
        try: d = yaml.safe_load(text)
        except Exception as ex: return f"not valid YAML: {str(ex)[:200]}", []
        if not isinstance(d, dict): return "the file must be a YAML mapping", []
        miss = [k for k in ("id", "title", "sources", "lines") if not d.get(k)]
        if miss: return "missing: " + ", ".join(miss), []
        if str(d["id"]) != name: return f"id must equal the file name ('{name}')", []
        if not isinstance(d["lines"], list) or not all(isinstance(x, dict) for x in d["lines"]): return "lines must be a list of entries", []
        warns = []
        try:
            from . import content as C
            c, rep = C.build_story(d, pipe.sel.quran)
            warns = [str(p) for p in (rep.get("problems") or [])]
        except Exception as ex: warns = [f"could not run the full verification here ({str(ex)[:120]})"]
        return None, warns

    @app.get("/stories")
    def stories():
        rows = ""
        for tag, p in story_files():
            t = p.read_text(encoding="utf-8"); f = flagged(t)
            try: ttl = (yaml.safe_load(t) or {}).get("title", "")
            except Exception: ttl = "(unreadable)"
            st = "<b class=warn>AI draft: needs your review</b>" if f else ("<b class=pass>live</b>" if tag == "stories" else "draft folder")
            rows += f"<tr><td><a href='/stories/{tag}/{p.stem}'>{E(p.stem)}</a></td><td>{E(str(ttl))}</td><td>{st}</td></tr>"
        body = (f"<h1>Stories</h1>{jobbox()}<p>Stories are written by people. Only <b>live</b> stories are used for videos; AI drafts stay out until you review them and press the review button. Every video from a story still needs approval before upload.</p>"
                f"<table><tr><th>File</th><th>Title</th><th>Status</th></tr>{rows or '<tr><td>none</td></tr>'}</table><p><a href=/stories/new>+ New story</a> &middot; <a href=/tools>Draft from the queue</a></p>")
        return page("Stories", body, request.args.get("m", ""))

    @app.get("/stories/new")
    def story_new():
        tpl = (stories_dir / "_template.yaml.example"); text = tpl.read_text(encoding="utf-8") if tpl.exists() else "id: \ntitle: \nsources: []\nlines: []\n"
        body = ("<h1>New story</h1><form method=post action=/stories/new><p>File name / id (lowercase letters, numbers, dashes) <input name=name pattern='[a-z0-9][a-z0-9-]+' required></p>"
                f"<p><textarea name=text style='min-height:420px;font-family:monospace'>{E(text)}</textarea></p><p><input type=submit value='Create'> <small>Use the same id as the file name. Quote Quran verses as <code>quran: \"105:1-2\"</code>; the engine pulls the exact verified text.</small></p></form>")
        return page("New story", body, request.args.get("m", ""))

    @app.post("/stories/new")
    def story_new_post():
        name = (request.form.get("name") or "").strip(); text = request.form.get("text") or ""
        if not NAME.match(name): return redirect("/stories/new?m=Bad+name")
        p = stories_dir / f"{name}.yaml"
        if p.exists(): return redirect("/stories/new?m=That+file+already+exists")
        err, _ = check(text, name)
        if err: return redirect("/stories/new?m=" + _q(err))
        stories_dir.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8"); db.log("info", f"story {name} created in the dashboard")
        return redirect(f"/stories/stories/{name}?m=Created")

    @app.get("/stories/<tag>/<name>")
    def story_edit(tag, name):
        p = find(tag, name)
        if not p.exists(): abort(404)
        t = p.read_text(encoding="utf-8"); err, warns = check(t, name); f = flagged(t)
        slug, tok = GH.repo_slug(ROOT), GH.token(ROOT)
        w = "".join(f"<li>{E(x)}</li>" for x in warns)
        acts = ""
        if f: acts += (f"<form method=post action=/stories/{tag}/{name}/review><p class=warn>This is an AI draft. Check every line against its sources, fix anything wrong above, save, then confirm:</p>"
                       "<label><input type=checkbox name=ok value=1> I checked every claim and source myself</label> <button>Mark as reviewed</button></form>")
        if tag == "drafts": acts += f"<form method=post action=/stories/{tag}/{name}/move><button>Move into the live stories folder</button></form>"
        if slug and tok and tag == "stories": acts += f"<form method=post action=/stories/{tag}/{name}/github><button>Push this story to GitHub</button> <small>so the cloud runs can use it</small></form>"
        body = (f"<h1>{E(name)}</h1>{acts}<form method=post action=/stories/{tag}/{name}><p><textarea name=text style='min-height:480px;font-family:monospace'>{E(t)}</textarea></p><p><input type=submit value='Save'></p></form>"
                + (f"<h2>Verification notes</h2><ul>{w}</ul><p><small>These are warnings from the same checks the pipeline runs; fix them before the story can render.</small></p>" if w else "<p class=pass>Verification found no problems.</p>")
                + (f"<p class=fail>{E(err)}</p>" if err else ""))
        return page(name, body, request.args.get("m", ""))

    @app.post("/stories/<tag>/<name>")
    def story_save(tag, name):
        p = find(tag, name)
        if not p.exists(): abort(404)
        text = (request.form.get("text") or "").replace("\r\n", "\n")
        err, _ = check(text, name)
        if err: return redirect(f"/stories/{tag}/{name}?m=" + _q("Not saved: " + err))
        p.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8"); db.log("info", f"story {name} edited in the dashboard")
        return redirect(f"/stories/{tag}/{name}?m=Saved")

    @app.post("/stories/<tag>/<name>/review")
    def story_review(tag, name):
        p = find(tag, name)
        if not p.exists(): abort(404)
        if request.form.get("ok") != "1": return redirect(f"/stories/{tag}/{name}?m=Tick+the+box+to+confirm+you+checked+it")
        t = p.read_text(encoding="utf-8"); n, c = re.subn(r"(needs_human_review\s*:\s*)(true|True|yes)", r"\1false", t, count=1)
        if not c: return redirect(f"/stories/{tag}/{name}?m=No+review+flag+found")
        p.write_text(n.rstrip("\n") + f"\n# reviewed by a person in the dashboard on {dt.date.today().isoformat()}\n", encoding="utf-8")
        db.log("info", f"story {name} marked human-reviewed")
        return redirect(f"/stories/{tag}/{name}?m=Marked+as+reviewed.+It+can+now+be+used+for+videos.")

    @app.post("/stories/<tag>/<name>/move")
    def story_move(tag, name):
        p = find(tag, name)
        if tag != "drafts" or not p.exists(): abort(404)
        dest = stories_dir / p.name
        if dest.exists(): return redirect(f"/stories/{tag}/{name}?m=A+live+story+with+that+name+exists")
        p.rename(dest); return redirect(f"/stories/stories/{name}?m=Moved")

    @app.post("/stories/<tag>/<name>/github")
    def story_gh(tag, name):
        p = find(tag, name); slug, tok = GH.repo_slug(ROOT), GH.token(ROOT)
        if tag != "stories" or not p.exists() or not (slug and tok): abort(400)
        try: r = GH.put_file(slug, tok, f"content/stories/{name}.yaml", p.read_text(encoding="utf-8"), f"Update story {name} from the dashboard")
        except Exception as ex: return redirect(f"/stories/{tag}/{name}?m=" + _q(str(ex)))
        return redirect(f"/stories/{tag}/{name}?m=Pushed+to+GitHub")
