import base64, json, pytest, yaml
from pathlib import Path
from ivs import github_sync as G

CH = {("audio", "narration", "voice"): "am_michael", ("audio", "narration", "speed"): 1.05, ("audio", "copyright_free"): False,
      ("audio", "recitation", "enabled"): False, ("video", "pace"): "normal", ("publishing", "platforms", "youtube", "privacy"): "unlisted", ("publishing", "description_style"): "minimal"}

def test_patch_keeps_comments_and_only_targets():
    t = Path(__file__).resolve().parent.parent.joinpath("config.yaml").read_text()
    n, sk = G.apply(t, CH); assert sk == []
    y = yaml.safe_load(n); o = yaml.safe_load(t)
    assert y["audio"]["narration"]["voice"] == "am_michael" and y["publishing"]["platforms"]["youtube"]["privacy"] == "unlisted" and y["video"]["pace"] == "normal"
    assert y["publishing"]["description_style"] == "minimal" and y["audio"]["recitation"]["enabled"] is False and y["audio"]["copyright_free"] is False
    assert y["publishing"]["platforms"]["youtube"]["category_id"] == o["publishing"]["platforms"]["youtube"]["category_id"]
    assert y["audio"]["narration"]["humanize"] == o["audio"]["narration"]["humanize"] and y["video"]["width"] == o["video"]["width"]
    assert n.count("# ") == t.count("# ") and len(n.splitlines()) == len(t.splitlines())
    n2, _ = G.apply(n, CH); assert n2 == n                                           # idempotent
    other = [k for k in y["audio"] if k not in ("narration", "recitation", "copyright_free")]
    assert all(y["audio"][k] == o["audio"][k] for k in other)

def test_missing_key_is_skipped():
    n, sk = G.apply("a:\n  b: 1\n", {("a", "zzz"): 2, ("q", "r"): 3}); assert n == "a:\n  b: 1\n" and sk == ["a.zzz", "q.r"]

class R:
    def __init__(s, code, j=None): s.status_code, s._j = code, j or {}
    def json(s): return s._j
    def raise_for_status(s): assert s.status_code < 400

class FakeHTTP:
    def __init__(s, text): s.text, s.puts, s.auth = text, [], []
    def get(s, url, headers=None, timeout=0): s.auth.append(headers["Authorization"]); return R(200, {"content": base64.b64encode(s.text.encode()).decode(), "sha": "abc"})
    def put(s, url, headers=None, timeout=0, json=None):
        s.puts.append(json); return R(200, {"commit": {"html_url": "https://github.com/x/y/commit/1"}})

def test_preview_and_push():
    h = FakeHTTP("audio:\n  narration:\n    voice: bm_george   # v\n")
    pv = G.preview("o/r", "TOK", {("audio", "narration", "voice"): "af_heart"}, h); assert pv["changed"] and "af_heart" in pv["diff"] and not h.puts
    r = G.push("o/r", "TOK", {("audio", "narration", "voice"): "af_heart"}, http=h); assert r["pushed"] and len(h.puts) == 1
    assert base64.b64decode(h.puts[0]["content"]).decode().count("af_heart") == 1 and h.puts[0]["sha"] == "abc"
    h2 = FakeHTTP("audio:\n  narration:\n    voice: af_heart\n"); assert G.push("o/r", "TOK", {("audio", "narration", "voice"): "af_heart"}, http=h2)["pushed"] is False and not h2.puts

def test_errors_do_not_leak_token():
    class Deny(FakeHTTP):
        def get(s, *a, **k): return R(403)
    with pytest.raises(RuntimeError) as e: G.fetch_remote("o/r", "SECRETTOKEN", Deny(""))
    assert "SECRETTOKEN" not in str(e.value)

def test_token_and_slug_from_env(tmp_path, monkeypatch):
    for k in ("IVS_GITHUB_TOKEN", "GITHUB_TOKEN", "IVS_GITHUB_REPO"): monkeypatch.delenv(k, raising=False)
    (tmp_path / ".env").write_text('IVS_GITHUB_TOKEN="tok123"\nIVS_GITHUB_REPO=me/project\n')
    assert G.token(tmp_path) == "tok123" and G.repo_slug(tmp_path) == "me/project"
