import json, re, pytest
from ivs import scriptlab as SL, features as FEAT, hooks
from ivs.config import load_config
from ivs.content import Content, Segment
from ivs.db import DB

def mk(cat="quran_ayah", theme="patience", **kw):
    d = dict(category=cat, key="quran:94:5-6", theme=theme, hook="Read this slowly.", segments=[Segment(ar="x", en="With hardship comes ease", label="Ash-Sharh 94:5")], source={}, reference_line="Quran 94:5")
    d.update(kw); return Content(**d)

def test_registry_100_honest():
    S = FEAT.SCRIPT_FEATURES
    assert len(S) == 100 and len({f["id"] for f in S}) == 100 and all(len([f for f in S if f["category"] == c]) == 10 for c in FEAT.SCRIPT_CATEGORIES)
    assert all(f["cfg"] is None for f in S if f["status"] == "planned") and not {f["id"] for f in S} & {f["id"] for f in FEAT.FEATURES}
    cfg = load_config(None)
    for f in S:
        if f["cfg"]:
            d = cfg
            for k in f["cfg"]: assert k in d, f["id"]; d = d[k]
    c = FEAT.script_counts(); assert c["done"] + c["planned"] == 100
    for n, p in FEAT.SCRIPT_PRESETS.items(): assert set(p) <= set(cfg["script"]), n

def test_hook_variants_pass_filter_and_brevity():
    for cat in ("quran_ayah", "hadith", "story"):
        c = mk(cat, source={"title": "The Cave"})
        for h in SL.hook_variants(c): assert h and not any(re.search(p, h.lower()) for p in hooks.FORBIDDEN), h
    assert SL.brevity_factor("Read this verse slowly now") == 1.0 and SL.brevity_factor(" ".join(["w"] * 11)) == 0.7 and SL.brevity_factor(" ".join(["w"] * 20)) == 0.3

def test_title_scoring_prefers_plain():
    c = mk()
    assert SL.score_title("Patience in the Quran: Ash-Sharh 94:5", c) > SL.score_title("SHOCKING SECRET YOU MUST SEE!!!", c)

def test_lint_flags_and_passes():
    assert SL.lint_line("This is guaranteed to bring you reward", "x")
    assert SL.lint_line("You must do this, it is haram otherwise", "x")
    assert SL.lint_line("THIS IS ALL SHOUTING TEXT HERE", "x")
    assert not SL.lint_line("Ease comes after hardship, and hope stays near.", "x")
    assert SL.lint_content(mk(hook="Guaranteed forgiveness for all")) and not SL.lint_content(mk())

def test_spoken_style():
    s = SL.spoken_style("The Prophet (PBUH) said, see 94:5-6 & more ﷺ")
    assert "peace be upon him" in s and "chapter 94, verses 5 to 6" in s and "&" not in s and "(" not in s

def test_beats_arc_series():
    b = SL.beat_map(6); assert b[0]["intensity"] == 3 and max(x["intensity"] for x in b) == 5 and not SL.check_arc(b)
    assert SL.check_arc([{"intensity": 5}] * 4) and SL.beat_map(0) == []
    assert SL.series_line(mk("story", source={"part": [1, 3]})) == "Part 1 of 3: part 2 is next."
    assert "end of this story" in SL.series_line(mk("story", source={"part": [3, 3]})) and SL.series_line(mk()) == ""

def test_lab_and_insights(tmp_path):
    db = DB(tmp_path / "d.sqlite3"); cfg = load_config(None)
    out = SL.lab(mk(), db, cfg); assert out["hooks"] and out["titles"] and out["editorial"] and out["settings"]["hook_variants"]
    assert SL.hook_insights(db) == []

flask = pytest.importorskip("flask")
from ivs import dashboard, github_sync as GH

class P: pass
class Sel: pass

@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "ROOT", tmp_path); monkeypatch.setattr(GH, "token", lambda r: None); monkeypatch.setattr(GH, "repo_slug", lambda r: None)
    sd = tmp_path / "content" / "stories"; sd.mkdir(parents=True)
    p = P(); p.cfg = load_config(); p.db = DB(tmp_path / "d.sqlite3"); p.out_root = tmp_path / "out"; p.sel = Sel(); p.sel.stories_dir = sd; p.sel.quran = None
    return p, dashboard.create_app(p).test_client(), tmp_path

def test_dashboard_page_save_preset(env):
    p, c, root = env
    r = c.get("/script"); assert r.status_code == 200 and b"Script &amp; Director" in r.data and b"100" in r.data
    assert b"href=\"/script\"" in r.data
    c.post("/script", data={"script.hook_variants": "1"})
    ov = __import__("yaml").safe_load((root / "data" / "overrides.yaml").read_text())
    assert ov["script"]["hook_variants"] is True and ov["script"]["editorial_lint"] is False and p.cfg["script"]["editorial_lint"] is False
    c.post("/script/preset", data={"preset": "balanced"}); assert p.cfg["script"]["editorial_lint"] is True
    assert c.post("/script/preset", data={"preset": "zzz"}).status_code == 302

def test_title_chooser(env):
    p, c, root = env
    p.db.conn.execute("INSERT INTO content_items(category,key,topic,status,created_at,updated_at,title) VALUES('quran_ayah','quran:94:5-6','patience','published','x','x','old')"); p.db.conn.commit()
    c.post("/script/title", data={"item": 1, "title": "new"}); assert p.db.get_item(1)["title"] == "old"      # published items are locked
    p.db.conn.execute("UPDATE content_items SET status='rendered'"); p.db.conn.commit()
    c.post("/script/title", data={"item": 1, "title": "Chosen title"}); assert p.db.get_item(1)["title"] == "Chosen title"
    assert c.get("/script?item=1").status_code == 200
