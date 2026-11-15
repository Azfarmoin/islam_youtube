import json, re
from ivs import site as S
from ivs.db import DB

def test_site_builds_public_safe(tmp_path):
    db = DB(tmp_path / "t.sqlite3")
    c = db.conn
    c.execute("INSERT INTO content_items(category,key,status,title,published_at,platform_url,platform_id,error,created_at,updated_at) VALUES('quran_ayah','1:1','published','Al-Fatiha','2026-11-14T08:00:00+00:00','https://youtu.be/abc','abc',NULL,'x','x')")
    c.execute("INSERT INTO content_items(category,key,status,title,error,created_at,updated_at) VALUES('story','secret-story','needs_review','Hidden draft','boom /home/claude/x','x','x')")
    c.commit()
    r = S.build(db, {}, tmp_path / "site")
    page = (tmp_path / "site" / "index.html").read_text(); data = json.loads((tmp_path / "site" / "data.json").read_text())
    assert r["videos"] == 1 and "Al-Fatiha" in page and "<title>" in page
    assert "Hidden draft" not in page and "secret-story" not in page and "boom" not in page and "/home/" not in page
    assert data["total_published"] == 1 and data["in_pipeline"] == 1

def test_site_has_all_sections_and_local_dashboard(tmp_path):
    db = DB(tmp_path / "t.sqlite3")
    db.conn.execute("INSERT INTO content_items(category,key,status,title,published_at,platform_url,platform_id,created_at,updated_at) VALUES('story','s1','published','Story One','2026-11-14T08:00:00+00:00','https://youtu.be/z','z','x','x')"); db.conn.commit()
    db.put_setting("stats:z", json.dumps({"viewCount": "120", "likeCount": "9"}))
    cfg = {"audio": {"copyright_free": True, "narration": {"enabled": True, "voice": "bm_george"}}, "video": {"pace": "fast", "max_seconds": 59}}
    S.build(db, cfg, tmp_path / "s"); page = (tmp_path / "s" / "index.html").read_text()
    for t in ("Top videos", "Mix by category", "How these are made", "bm_george", "total views"): assert t in page
    assert json.loads((tmp_path / "s" / "data.json").read_text())["total_views"] == 120
