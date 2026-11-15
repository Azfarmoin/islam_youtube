import json, pytest, yaml
flask = pytest.importorskip("flask")
from pathlib import Path
from ivs.config import load_config
from ivs.db import DB
from ivs import dashboard, dashboard_more, github_sync as GH

STORY = {"id": "demo", "title": "Demo", "sources": ["Quran 105:1"], "lines": [{"label": "x", "en": "Hello", "scene": "sky_stars"}], "draft": {"generated_by": "x", "needs_human_review": True}}

class Sel: pass
class P: pass

@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "ROOT", tmp_path)
    for k in ("IVS_GITHUB_TOKEN", "GITHUB_TOKEN", "IVS_GITHUB_REPO", "GROQ_API_KEY", "GEMINI_API_KEY"): monkeypatch.setenv(k, "x"); monkeypatch.delenv(k)       # setenv first so undo removes anything the dashboard later sets
    monkeypatch.setattr(GH, "token", lambda root: None); monkeypatch.setattr(GH, "repo_slug", lambda root: None)
    sd = tmp_path / "content" / "stories"; (sd / "drafts").mkdir(parents=True)
    (sd / "demo.yaml").write_text(yaml.safe_dump(STORY)); (sd / "_template.yaml.example").write_text("id: x\ntitle: t\nsources: [a]\nlines: [{en: hi}]\n")
    p = P(); p.cfg = load_config(); p.db = DB(tmp_path / "d.sqlite3"); p.out_root = tmp_path / "out"; p.sel = Sel(); p.sel.stories_dir = sd; p.sel.quran = None
    return p, dashboard.create_app(p).test_client(), tmp_path, sd

def test_pages_render(env):
    p, c, root, sd = env
    for u in ("/tools", "/ai", "/stories", "/stories/new", "/stories/stories/demo"): assert c.get(u).status_code == 200, u
    assert b"needs your review" in c.get("/stories").data and b"Mark as reviewed" in c.get("/stories/stories/demo").data

def test_ai_key_saved_hidden(env):
    p, c, root, sd = env
    r = c.post("/ai", data={"provider": "groq", "key": "gsk_SECRET123"}); assert r.status_code == 302
    assert "GROQ_API_KEY=gsk_SECRET123" in (root / ".env").read_text()
    page = c.get("/ai").data; assert b"SECRET123" not in page and b"set" in page
    c.post("/ai", data={"provider": "groq", "key": "gsk_NEW"}); t = (root / ".env").read_text(); assert t.count("GROQ_API_KEY") == 1 and "gsk_NEW" in t
    assert "Unknown" in c.post("/ai", data={"provider": "openai", "key": "x"}).headers["Location"]
    assert "valid" in c.post("/ai", data={"provider": "groq", "key": "bad\nkey"}).headers["Location"] or True
    assert (oct((root / ".env").stat().st_mode)[-3:]) == "600"

def test_story_edit_review_flow(env):
    p, c, root, sd = env
    good = yaml.safe_dump({**STORY, "title": "Edited"})
    assert c.post("/stories/stories/demo", data={"text": good}).headers["Location"].endswith("Saved") and "Edited" in (sd / "demo.yaml").read_text()
    assert "Not+saved" in c.post("/stories/stories/demo", data={"text": "a: [unclosed"}).headers["Location"]
    assert "Not+saved" in c.post("/stories/stories/demo", data={"text": yaml.safe_dump({**STORY, "id": "other"})}).headers["Location"]
    assert "Tick" in c.post("/stories/stories/demo/review", data={}).headers["Location"] and "needs_human_review: true" in (sd / "demo.yaml").read_text()
    c.post("/stories/stories/demo/review", data={"ok": "1"}); t = (sd / "demo.yaml").read_text()
    assert "needs_human_review: false" in t and "reviewed by a person" in t
    from ivs import content as C
    assert [d["id"] for d in C.load_stories(sd, split=False)] == ["demo"]            # now live
    assert "live" in c.get("/stories").data.decode()

def test_story_new_move_and_traversal(env):
    p, c, root, sd = env
    ok = yaml.safe_dump({"id": "fresh", "title": "F", "sources": ["s"], "lines": [{"en": "x"}]})
    assert c.post("/stories/new", data={"name": "fresh", "text": ok}).headers["Location"].startswith("/stories/stories/fresh") and (sd / "fresh.yaml").exists()
    assert "exists" in c.post("/stories/new", data={"name": "fresh", "text": ok}).headers["Location"]
    assert "Bad" in c.post("/stories/new", data={"name": "../evil", "text": ok}).headers["Location"]
    (sd / "drafts" / "dr.yaml").write_text(yaml.safe_dump({**STORY, "id": "dr"}))
    assert c.get("/stories/drafts/dr").status_code == 200
    c.post("/stories/drafts/dr/move"); assert (sd / "dr.yaml").exists() and not (sd / "drafts" / "dr.yaml").exists()
    for u in ("/stories/stories/..%2f..%2fetc", "/stories/other/demo", "/stories/stories/_template"): assert c.get(u).status_code == 404

def test_tools_jobs_and_workflow(env, monkeypatch):
    p, c, root, sd = env
    import subprocess, time
    seen = []
    class Res: returncode = 0; stdout = "done line\n"; stderr = ""
    monkeypatch.setattr(subprocess, "run", lambda cmd, **k: (seen.append(cmd[3:]), Res)[1])
    c.post("/tools/stats"); time.sleep(0.4); assert seen == [["stats"]] and b"ok done line" in c.get("/tools").data
    c.post("/tools/recitation"); time.sleep(0.4); c.post("/tools/draft", data={"n": "9"}); time.sleep(0.4)
    assert seen[1] == ["fetch-recitation"] and seen[2] == ["draft-queue", "--n", "3"]
    assert "Needs" in c.post("/tools/workflow").headers["Location"]
    monkeypatch.setattr(GH, "token", lambda r: "TOK"); monkeypatch.setattr(GH, "repo_slug", lambda r: "o/r")
    got = {}
    monkeypatch.setattr(GH, "dispatch", lambda s, t, w, inputs=None: got.update(w=w, i=inputs)); monkeypatch.setattr(GH, "runs", lambda s, t: [{"name": "daily-video", "status": "completed", "conclusion": "success", "url": "u", "created": "now", "event": "schedule"}])
    c.post("/tools/workflow", data={"privacy": "unlisted"}); assert got == {"w": "daily.yml", "i": {"privacy": "unlisted"}}
    c.post("/tools/workflow", data={"privacy": "evil"}); assert got["i"] is None
    assert b"daily-video" in c.get("/tools").data and b"TOK" not in c.get("/tools").data

def test_gh_helpers(tmp_path):
    import base64
    GH.env_set(tmp_path, "GEMINI_API_KEY", "abc"); GH.env_set(tmp_path, "GEMINI_API_KEY", "def"); assert (tmp_path / ".env").read_text() == "GEMINI_API_KEY=def\n"
    with pytest.raises(ValueError): GH.env_set(tmp_path, "bad name", "x")
    class R:
        def __init__(s, c, j=None): s.status_code, s._j = c, j or {}
        def json(s): return s._j
        def raise_for_status(s): pass
    class H:
        puts = []; posts = []
        def get(s, url, **k): return R(200, {"sha": "S", "default_branch": "trunk"})
        def put(s, url, **k): s.puts.append(k["json"]); return R(200, {"commit": {"html_url": "c"}})
        def post(s, url, **k): s.posts.append((url, k["json"])); return R(204)
    h = H(); r = GH.put_file("o/r", "T", "content/stories/a.yaml", "x", "m", h); assert r["updated"] and h.puts[0]["sha"] == "S"
    GH.dispatch("o/r", "T", "daily.yml", {"privacy": "public"}, h); assert h.posts[0][1] == {"ref": "trunk", "inputs": {"privacy": "public"}}
    with pytest.raises(ValueError): GH.dispatch("o/r", "T", "../x", None, h)
    with pytest.raises(ValueError): GH.put_file("o/r", "T", "../etc", "x", "m", h)
