"""Downloads the pinned Quran editions (Arabic Uthmani Hafs + Simple, Urdu, English) into assets/data and writes MANIFEST.json.
Run once: python scripts/fetch_quran.py"""
import sys, urllib.request
from pathlib import Path
BASE = "https://cdn.jsdelivr.net/gh/fawazahmed0/quran-api@1/editions/"
EDITIONS = ["ara-quranuthmanihaf", "ara-quransimple", "urd-fatehmuhammadja", "eng-abdullahyusufal"]
ROOT = Path(__file__).resolve().parent.parent
dest = ROOT / "assets" / "data"; dest.mkdir(parents=True, exist_ok=True)
for name in EDITIONS:
    p = dest / f"{name}.json"
    if p.exists(): print("have", name); continue
    print("downloading", name); urllib.request.urlretrieve(BASE + name + ".json", p)
sys.path.insert(0, str(ROOT))
from ivs.quran import build_manifest
build_manifest(dest)
print("done")
