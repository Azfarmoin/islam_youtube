import json, subprocess, pytest, yaml
from pathlib import Path
from ivs import looks as LK, features as FEAT, describe
from ivs.config import load_config

def test_registry_is_exactly_100_and_honest():
    assert len(FEAT.FEATURES) == 100 and len({f["id"] for f in FEAT.FEATURES}) == 100
    assert all(f["status"] in ("done", "planned") for f in FEAT.FEATURES) and all(len([f for f in FEAT.FEATURES if f["category"] == c]) == 10 for c in FEAT.CATEGORIES)
    assert all(f["cfg"] is None for f in FEAT.FEATURES if f["status"] == "planned")             # planned items have no switch
    cfg = load_config(None)
    for f in FEAT.FEATURES:                                                                         # every switch points at a real config key
        if f["cfg"]:
            d = cfg
            for k in f["cfg"]: assert isinstance(d, dict) and k in d, f["id"]; d = d[k]
    for n, p in FEAT.PRESETS.items(): assert set(p) <= set(LK.LOOK_DEFAULTS), n

def test_grade_and_question_choice():
    assert LK.pick_grade("mercy and relief", "auto") == "warm_dawn" and LK.pick_grade("night dua", "auto") == "deep_night" and LK.pick_grade("warning", "auto") == "cool_dusk"
    assert LK.pick_grade("anything", "auto") == "filmic_natural" and LK.pick_grade("x", "none") is None and LK.pick_grade("x", "sepia_archive") == "sepia_archive" and LK.pick_grade("x", "bogus") is None
    assert "Tell us below" in LK.question_for("patience") and LK.question_for("zzz") == LK.DEFAULT_QUESTION
    for _, q in LK.QUESTIONS + [(0, LK.DEFAULT_QUESTION)]: assert len(q) < 70 and "share" not in q.lower() and "guarantee" not in q.lower()

def test_graph_switches():
    off = {k: False for k in LK.LOOK_DEFAULTS}; off["enabled"] = True; off["grade"] = "none"
    assert LK.build_graph({**off}, "t", [2, 4], 10, 24, 1080, 1920)[1] == {}
    g, on = LK.build_graph({**off, "cut_punch": True, "cut_flash": True, "progress_bar": True}, "t", [2.0, 4.0, 0.1, 99], 10, 24, 1080, 1920)
    assert on == {"cut_punch": True, "cut_flash": True, "progress_bar": True} and g.count("gt(on/24") == 2 and "0.10" not in g.split("zoompan")[1][:400]       # cuts near the ends are ignored
    assert LK.build_graph({**LK.LOOK_DEFAULTS, "enabled": False}, "t", [], 10, 24, 1080, 1920) == ("", {})
    g2, on2 = LK.build_graph({**off, "grade": "auto"}, "mercy", [], 10, 24, 1080, 1920, graded_already=True); assert "grade" not in on2            # stories already graded by the Director are not graded twice
    g3, on3 = LK.build_graph({**off, "handheld": True}, "t", [], 10, 24, 1080, 1920); assert "rotate=" in g3 and "1.045" in g3 and on3["push_in"] is False if "push_in" in on3 else True
    assert "vignette=PI/6" not in LK.build_graph({**off, "grade": "warm_dawn"}, "t", [], 10, 24, 1080, 1920)[0]                                   # grade profile's own vignette is removed

def test_real_ffmpeg_graph_runs(tmp_path):
    src = tmp_path / "s.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=270x480:r=12:d=4", "-pix_fmt", "yuv420p", str(src)], check=True)
    out, on = LK.apply(src, tmp_path / "o.mp4", {"look": {"handheld": True, "flicker": True, "grade": "auto"}}, "mercy", [1.5, 2.8], 4.0, 12, 270, 480)
    assert out != src and len(on) >= 10
    d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)]))
    assert 3.8 < d < 4.2
    same, none = LK.apply(src, tmp_path / "n.mp4", {"look": {"enabled": False}}, "x", [], 4.0, 12, 270, 480); assert same == src and none == {}

def test_question_in_description():
    from ivs.quran import Quran
    from ivs import content as C
    from ivs.catalog import QURAN
    c = C.build_quran(Quran(load_config(None)), QURAN[0])[0]
    r = {"assets": [], "text_only": True, "voices": [], "marks": [], "question": "What does this change for your day? Tell us below."}
    for st in ("viral", "classic"): assert "Question for you: What does this change" in describe.build(c, r, st, {})[0]
    assert "Question for you" not in describe.build(c, r, "minimal", {})[0] and "Question for you" not in describe.build(c, {**r, "question": ""}, "viral", {})[0]
