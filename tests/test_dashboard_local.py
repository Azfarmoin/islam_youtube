import json, pytest
flask = pytest.importorskip("flask")
from pathlib import Path
from ivs.config import load_config
from ivs.db import DB
from ivs import dashboard

class Sel: stories_dir = None
class P: pass

@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "ROOT", tmp_path)
    p = P(); p.cfg = load_config(); p.db = DB(tmp_path / "d.sqlite3"); p.out_root = tmp_path / "out"; p.sel = Sel()
    work = p.out_root / "0001_x"; work.mkdir(parents=True)
    (work / "v.mp4").write_bytes(b"fakevideo"); (work / "metadata.json").write_text(json.dumps({"title": "Old", "description": "d", "tags": ["a"]}))
    (work / "qc_report.json").write_text(json.dumps({"passed": True, "checks": []}))
    p.db.conn.execute("INSERT INTO content_items(category,key,status,title,description,tags,video_path,religious_verification,content_quality,created_at,updated_at) VALUES('quran_ayah','quran:1:1','rendered','Old','d','[\"a\"]',?, 'VERIFIED','APPROVED','x','x')", (str(work / "v.mp4"),))
    p.db.conn.execute("INSERT INTO claims(claim_id,item_id,kind,source_title,translator,license,reviewer_status) VALUES('c1',1,'quran','Tanzil','Yusuf Ali','CC','automated_only')")
    p.db.conn.execute("INSERT INTO assets_used(item_id,name,kind,license) VALUES(1,'whoosh','sfx','CC0')"); p.db.conn.commit()
    return p, dashboard.create_app(p).test_client(), work

def test_all_pages_render(env):
    p, c, _ = env
    for url in ("/", "/?s=rendered", "/?q=quran", "/item/1", "/make", "/settings", "/history", "/history?l=info", "/credits"):
        r = c.get(url); assert r.status_code == 200, url
    assert b"Active settings" in c.get("/").data and b"Tanzil" in c.get("/item/1").data and b"Yusuf Ali" in c.get("/credits").data
    assert b"<video" in c.get("/item/1").data and c.get("/item/99").status_code == 404

def test_video_served_and_confined(env):
    p, c, work = env
    assert c.get("/media/1/video").data == b"fakevideo"
    p.db.conn.execute("UPDATE content_items SET video_path='/etc/hostname' WHERE id=1"); p.db.conn.commit()
    assert c.get("/media/1/video").status_code == 404

def test_edit_updates_db_and_metadata(env):
    p, c, work = env
    r = c.post("/item/1/edit", data={"title": "New title", "description": "New desc", "tags": "x, y"}); assert r.status_code == 302
    it = p.db.get_item(1); assert it["title"] == "New title" and json.loads(it["tags"]) == ["x", "y"]
    assert json.loads((work / "metadata.json").read_text())["title"] == "New title"
    assert c.post("/item/1/edit", data={"title": ""}).headers["Location"].endswith("empty")
    p.db.conn.execute("UPDATE content_items SET status='published' WHERE id=1"); p.db.conn.commit()
    assert c.post("/item/1/edit", data={"title": "z"}).status_code == 400

def test_settings_whitelist_and_zero_cost(env, tmp_path):
    p, c, _ = env
    r = c.post("/settings", data={"audio.narration.voice": "am_michael", "audio.narration.speed": "9", "video.pace": "normal", "audio.recitation.enabled": "1"}); assert r.status_code == 302
    assert p.cfg["audio"]["narration"]["voice"] == "am_michael" and p.cfg["audio"]["narration"]["speed"] == 1.3
    assert p.cfg["audio"]["copyright_free"] is False         # unchecked box = off
    assert (tmp_path / "data" / "overrides.yaml").exists()
    assert "Invalid" in c.post("/settings", data={"video.pace": "turbo"}).headers["Location"]

def test_make_approve_skip_and_guards(env, monkeypatch):
    p, c, _ = env
    called = {}
    p.make_next = lambda only=None: (called.update(only=only), 7)[1]
    import time
    assert c.post("/make", data={"only": "quran_ayah"}).status_code == 302; time.sleep(0.3)
    assert called["only"] == "quran_ayah" and b"item 7" in c.get("/make").data
    p.approve = lambda i: p.db.set_status(i, "approved"); p.skip = lambda i: p.db.set_status(i, "skipped")
    c.post("/approve/1"); assert p.db.get_item(1)["status"] == "approved"
    c.post("/skip/1"); assert p.db.get_item(1)["status"] == "skipped"
    assert c.post("/pause").status_code == 302 and p.db.setting("paused") == "1"
    assert c.post("/pause", headers={"Origin": "https://evil.example"}).status_code == 403
    assert c.get("/", headers={"Host": "evil.example"}).status_code == 403

def test_next_run():
    import datetime as dt
    assert dashboard.next_run_utc(dt.datetime(2026, 1, 1, 1, 30, tzinfo=dt.timezone.utc)).hour == 2

def test_voice_page_sample_and_choice(env, tmp_path, monkeypatch):
    p, c, _ = env
    r = c.get("/voice"); assert r.status_code == 200 and b"am_michael" in r.data and b"Use this voice" in r.data
    from ivs import tts
    calls = []
    def fake(text, out, voice="bm_george", speed=1.0, human=True): calls.append((voice, speed)); Path(out).write_bytes(b"RIFFwav"); return 1.0
    monkeypatch.setattr(tts, "speak_en", fake)
    assert c.get("/voice/sample/af_heart.wav?speed=1.1").data == b"RIFFwav" and calls == [("af_heart", 1.1)]
    c.get("/voice/sample/af_heart.wav?speed=1.1"); assert len(calls) == 1          # cached
    assert c.get("/voice/sample/../../etc.wav").status_code == 404 and c.get("/voice/sample/evil.wav").status_code == 404
    assert c.post("/voice", data={"voice": "am_adam", "speed": "1.0"}).status_code == 302
    assert p.cfg["audio"]["narration"]["voice"] == "am_adam"
    assert c.post("/voice", data={"voice": "evil", "speed": "1"}).headers["Location"].endswith("voice")
    c.post("/settings", data={"video.pace": "normal"})             # settings save must not wipe the voice override
    import yaml; assert yaml.safe_load((tmp_path / "data" / "overrides.yaml").read_text())["audio"]["narration"]["voice"] == "am_adam"

def test_github_pages(env, tmp_path, monkeypatch):
    p, c, _ = env
    from ivs import github_sync as GH
    monkeypatch.setattr(GH, "token", lambda root: "TOK"); monkeypatch.setattr(GH, "repo_slug", lambda root: "me/proj")
    assert b"No saved settings" in c.get("/github").data
    c.post("/voice", data={"voice": "am_adam", "speed": "1.0"})
    calls = {}
    monkeypatch.setattr(GH, "preview", lambda s, t, ch: {"changed": True, "diff": "-voice: bm_george\n+voice: am_adam\n", "skipped": [], "sha": "x"})
    monkeypatch.setattr(GH, "push", lambda s, t, ch, **k: calls.update(ch=ch) or {"pushed": True, "skipped": []})
    r = c.get("/github"); assert b"am_adam" in r.data and b"Push to GitHub" in r.data and b"TOK" not in r.data
    assert c.post("/github").status_code == 302 and calls["ch"][("audio", "narration", "voice")] == "am_adam"
    assert c.post("/github", headers={"Origin": "https://evil.example"}).status_code == 403

def test_description_style_setting_and_preview(env, monkeypatch):
    p, c, work = env
    assert b"Description style" in c.get("/settings").data and b"Preview this style" in c.get("/item/1").data
    assert c.post("/settings", data={"publishing.description_style": "minimal"}).status_code == 302 and p.cfg["publishing"]["description_style"] == "minimal"
    assert c.post("/settings", data={"publishing.description_style": "spammy"}).headers["Location"].startswith("/settings?m=Invalid")
    r = c.get("/item/1?style=viral"); assert r.status_code == 200 and b"Could not rebuild" in r.data          # fake pipeline cannot rebuild: fails soft, no crash
    from types import SimpleNamespace as NS
    seg = NS(label="Q 1:1", en="Hello", ur="")
    ct = NS(hook="Hook line", segments=[seg], script=None, source={}, reference_line="Surah Test (1:1)", category="quran_ayah", theme="mercy", key="quran:1:1")
    p._rebuild_content = lambda it: ct
    r = c.get("/item/1?style=viral"); assert b"Preview of the" in r.data and b"Follow for one verified Islamic short" in r.data
    p.db.conn.execute("INSERT INTO publish_log(item_id,platform,ts,ok,platform_id,url,detail) VALUES(1,'youtube','2026-11-15T00:00:00+00:00',1,'v','u','private')"); p.db.conn.commit()
    p.cfg["publishing"]["platforms"]["youtube"]["privacy"] = "public"
    h = c.get("/history").data; assert b"API audit" in h and b"ok, private" in h
    assert b"personal and educational use" in c.get("/credits").data

def test_looks_page_presets_save_and_preview(env, tmp_path, monkeypatch):
    p, c, work = env
    import yaml, time
    r = c.get("/looks"); assert r.status_code == 200 and b"100</b> improvements" in r.data and b"planned" in r.data and b"Film grain" in r.data
    assert c.post("/looks/preset", data={"preset": "clean"}).status_code == 302 and p.cfg["look"]["grain"] is False and p.cfg["look"]["bloom"] is False
    assert "Unknown" in c.post("/looks/preset", data={"preset": "evil"}).headers["Location"]
    c.post("/looks", data={"look.grain": "1", "look.grade": "deep_night", "video.word_icons": "1"})
    assert p.cfg["look"]["grain"] is True and p.cfg["look"]["vignette"] is False and p.cfg["look"]["grade"] == "deep_night" and p.cfg["video"]["word_icons"] is True and p.cfg["audio"]["copyright_free"] is False
    ov = yaml.safe_load((tmp_path / "data" / "overrides.yaml").read_text()); assert ov["look"]["grade"] == "deep_night"
    assert c.post("/looks", data={"look.grade": "evil"}).status_code == 302 and p.cfg["look"]["grade"] == "deep_night"          # invalid grade ignored
    from ivs import github_sync as GH
    monkeypatch.setattr(GH, "token", lambda r: "T"); monkeypatch.setattr(GH, "repo_slug", lambda r: "o/r")
    seen = {}
    monkeypatch.setattr(GH, "preview", lambda s, t, ch: seen.update(ch=ch) or {"changed": False, "diff": "", "skipped": [], "sha": "x"})
    c.get("/github"); assert ("look", "grain") in seen["ch"] and ("look", "grade") in seen["ch"]             # new switches flow into GitHub sync
    assert c.get("/looks/preview.mp4").status_code == 404
