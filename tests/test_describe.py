import pytest
from ivs.config import load_config
from ivs.quran import Quran
from ivs import content as C, describe
from ivs.catalog import QURAN
from ivs.pipeline import make_metadata

REC = {"name": "x.mp3", "kind": "recitation", "source_url": "https://everyayah.com/data/Alafasy_128kbps/094005.mp3", "license": "x", "attribution": "Recitation: Mishary Rashid Alafasy"}
REC2 = {**REC, "source_url": "https://cdn.islamic.network/quran/audio/128/ar.alafasy/6000.mp3"}

@pytest.fixture(scope="module")
def ayah():
    q = Quran(load_config(None)); return C.build_quran(q, QURAN[0])[0]

def render(assets): return {"assets": assets, "text_only": not assets, "voices": ["bm_george"], "marks": []}

def test_recitation_credit_block_meets_terms(ayah):
    d, tags = describe.build(ayah, render([REC, REC2]), "viral", {})
    assert "Mishary Rashid Alafasy" in d and "EveryAyah.com" in d and "Islamic Network" in d
    assert "copyright of the recording remains with the reciter" in d and "educational, non-commercial" in d and "taken down" in d
    d2, _ = describe.build(ayah, render([REC]), "classic", {"publishing": {"channel_contact": "me@example.org"}})
    assert "the channel at me@example.org" in d2 and "Islamic Network" not in d2                  # only the mirror really used is credited

def test_no_recitation_no_recitation_claims(ayah):
    for st in describe.STYLES:
        d, tags = describe.build(ayah, render([]), st, {})
        assert "copyright of the recording" not in d and "#QuranRecitation" not in tags and not any("Alafasy" in t for t in tags)
        assert "text-only" in d or "not included" in d

@pytest.mark.parametrize("style", describe.STYLES)
def test_styles_valid_and_limits(ayah, style):
    d, tags = describe.build(ayah, render([REC]), style, {})
    assert d.splitlines()[0] == ayah.hook and len(d) <= 4900 and len(tags) <= 15 and all(t.startswith("#") for t in tags)
    assert tags[0] in ("#Quran",) and "#Shorts" in tags
    assert "Source:" in d and d.rstrip().endswith(" ".join(tags))

def test_viral_has_cta_and_honest_labels_minimal_is_short(ayah):
    v, vt = describe.build(ayah, render([REC]), "viral", {}); m, _ = describe.build(ayah, render([REC]), "minimal", {}); c, _ = describe.build(ayah, render([REC]), "classic", {})
    assert describe.CTA in v and describe.CTA not in c and describe.CTA not in m and len(m) < len(v)
    assert "#QuranRecitation" in vt and "#MisharyRashidAlafasy" in vt
    low = v.lower()
    for bad in ("guaranteed", "you will be rewarded if you share", "share to get", "miracle"): assert bad not in low

def test_make_metadata_uses_config_style_and_keeps_title(ayah):
    a = make_metadata(ayah, render([REC]), {"publishing": {"description_style": "minimal"}}); b = make_metadata(ayah, render([REC]), {})
    assert a["description_style"] == "minimal" and b["description_style"] == "viral" and a["title"] == b["title"] and "#Shorts" in a["title"]
    assert make_metadata(ayah, render([REC]), {}, style="classic")["description_style"] == "classic"
