from types import SimpleNamespace as N
from ivs.topics import TopicSelector as T

def test_topic_ids():
    assert T.topic_id("quran:94:5-6") == "quran:94" and T.topic_id("quran:94:1") == "quran:94"
    assert T.topic_id("story:al-fil-p2") == "story:al-fil" and T.topic_id("story:al-fil") == "story:al-fil"
    assert T.topic_id("hadith:bukhari:6018") == "hadith:bukhari:6018"

def test_recent_window_and_relax():
    class C:
        def __init__(s, keys): s.keys = keys
        def execute(s, q, a): return N(fetchall=lambda: [{"key": k} for k in s.keys[-a[0]:][::-1]])
    sel = T.__new__(T); sel.cfg = {"dedupe": {"recent_topic_window": 3}}; sel.db = N(conn=C(["quran:94:1", "story:al-fil-p1", "quran:2:153", "quran:14:7"]))
    assert sel._recent_topics() == {"story:al-fil", "quran:2", "quran:14"}
    calls = []
    sel._pick = lambda only, avoid: (calls.append(bool(avoid)) or (None if avoid else "x"))
    sel.db.log = lambda *a, **k: None
    assert sel.next_content() == "x" and calls == [True, False]       # relaxes once instead of skipping the day

def test_hard_cap_config_and_copyright_free():
    import yaml
    c = yaml.safe_load(open("config.yaml"))
    assert c["video"]["max_seconds"] <= 59 and c["video"]["target_seconds"][1] <= 59 and c["video"]["length_seconds"] < 59
    assert c["audio"]["copyright_free"] is True and c["audio"]["narration"]["allow_edge"] is False
    from ivs import openverse
    openverse.set_mode(True); assert set(openverse.ALLOWED) == {"cc0", "pdm"}
    openverse.set_mode(False); assert "by" in openverse.ALLOWED
    from ivs import tts_engines as T
    T.available = lambda: {"chatterbox": False, "qwen3": False, "fish": True}
    T.BACKENDS["fish"] = lambda *a, **k: 3.0
    from pathlib import Path
    assert T.try_engines("x", "en", Path("a.wav"), {"engines": ["fish"]}, copyfree=True) is None
    assert T.try_engines("x", "en", Path("a.wav"), {"engines": ["fish"]}, copyfree=False)[0] == 3.0

def test_word_icons_plan():
    from ivs import icons
    p = icons.plan("Do they not look at the birds in the sky, and the ships on the sea?", 0.5, 8, 10)
    assert [x["icon"] for x in p][:3] == ["bird", "stars", "ship"] and all(0 < x["t"] < 10 for x in p)
    assert icons.icon_for("mountains") == "mountain" and icons.icon_for("the") is None
    assert set(icons.ICONS) >= {"sun", "mountain", "ship", "bird", "heart", "book"} and not any(w in icons.KEYWORDS for w in ("prophet", "angel", "allah"))
