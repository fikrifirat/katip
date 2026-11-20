"""Offline tests for Katip Emsal (no network). Run: python -m pytest lab/emsal -q   (or python lab/emsal/test_emsal.py)"""
import io, sys, zipfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import emsal, blind  # noqa: E402

# A made-up petition in the same shape as a real one: masked identity, readable argument.
PETITION = """Şüpheli : ████ ████ (TC: ███████████)
Müdafi : Av. ████ ███████ (UETS: 12345-67890-11111)
Müvekkil Ahmet evinde kenevir yetiştirmiştir; ele geçirilen 40 gram esrar kişisel kullanım sınırındadır.
Hassas terazi bulunmamıştır. Eylem TCK md. 188/3 kapsamında değil, TCK 191 kapsamında kullanmak için
bulundurmadır. Ceza Muhakemesi Kanunu "Tutuklama nedenleri" başlıklı 100. Madde koşulları yoktur.
Kenevir ve esrar miktarı ticareti göstermez; kullanım amacı açıktır. Ankara'da ikamet etmektedir."""

def test_unmask_drops_blocks_and_placeholders():
    t = emsal.unmask("Ad: ████ [AD SOYAD] kaldı")
    assert "█" not in t and "[AD SOYAD]" not in t and "kaldı" in t

def test_read_udf(tmp_path):
    p = tmp_path / "x.udf"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("content.xml", "<template><content><![CDATA[Merhaba ████ dünya]]></content></template>")
    assert emsal.read_petition(p) == "Merhaba ████ dünya"

def test_statutes():
    s = emsal.statutes(PETITION)
    assert s[:2] == ["TCK 188", "TCK 191"] and "CMK 100" in s
    assert emsal.domain(s) == "ceza"
    assert emsal.statutes("hukuka aykırılık ay 97") == []          # lowercase words are not law names

def test_candidate_terms_never_capitalised_or_short():
    words = [t.word for t in emsal.candidate_terms(emsal.unmask(PETITION))]
    assert "kenevir" in words
    assert not any(w[0].isupper() for w in words)               # 'Ahmet', 'Ankara' cannot qualify
    assert not any(len(w) < 4 for w in words)
    assert "müvekkil" not in words                               # boilerplate

def test_safe_query_is_the_only_door():
    text = emsal.unmask(PETITION)
    assert emsal.safe_query(["kenevir", "esrar"], text) == "kenevir esrar"
    for bad in (["Ahmet"], ["ankara"], ["12345"], ["kenevir", "UETS"], ["ka"], ["heroin"]):
        try:
            emsal.safe_query(bad, text)
        except ValueError:
            continue
        raise AssertionError(f"leaked {bad}")
    # statute heading words are public and allowed only when passed as public text
    assert emsal.safe_query(["imal"], text, public="uyuşturucu imal ticareti") == "imal"

def test_weight_terms_filters_by_document_frequency():
    terms = [emsal.Term("kenevir", "kenev", 5), emsal.Term("nadirkelime", "nadir", 9), emsal.Term("olarak", "olara", 9)]
    out = emsal.weight_terms(terms, {"kenevir": 12000, "nadirkelime": 12, "olarak": 9_000_000}, 10_000_000)
    assert [t.word for t in out] == ["kenevir"]                 # too rare and too common both dropped

def test_query_design_covers_terms():
    terms = [emsal.Term(w, w[:5], 1) for w in ["kenevir", "esrar", "gram", "terazi", "dikili", "kullanım", "internet"]]
    text = " ".join(t.word for t in terms)
    qs = emsal.write_queries(terms, text)
    assert len(qs) == 6 and all(len(q.split()) == 3 for q in qs)
    used = Counter(w for q in qs for w in q.split())
    assert set(used) == {t.word for t in terms}

def test_heading_contrast_query():
    if "TCK" not in emsal.HEADINGS:
        return
    qs, public = emsal.statute_queries(["TCK 188", "TCK 191"], {}, 10_000_000, emsal.unmask(PETITION))
    assert qs == ["ticareti kullanmak"]
    assert "imal" in public

def test_verify_numbers():
    h = {"esas": "2017/378", "karar": "2018/618"}
    assert emsal.verify(h, "Ceza Genel Kurulu 2017/378 E. , 2018/618 K.")
    assert emsal.verify({"esas": "2012/1335", "karar": "2013/423"}, "Ceza Genel Kurulu 2012/10-1335 E. , 2013/423 K.")
    assert not emsal.verify(h, "Ceza Genel Kurulu 2017/3781 E. , 2018/618 K.")
    assert not emsal.verify({"esas": "", "karar": "2018/618"}, "2018/618")

def test_bm25_prefers_matching_paragraph():
    docs = [emsal.tokens("kenevir esrar kişisel kullanım sınırı hassas terazi"), emsal.tokens("kira bedeli tespit davası")]
    bm = emsal.BM25(docs)
    q = Counter(emsal.tokens("kenevir kullanım"))
    assert bm.score(q, 0) > bm.score(q, 1) == 0

def test_outcome():
    assert emsal.outcome("... hükmün BOZULMASINA, oy birliğiyle karar verildi.") == "bozma"
    assert emsal.outcome("... hükmün ONANMASINA ...") == "onama"

def test_ndcg():
    assert blind.ndcg([2, 2, 0]) == 1.0
    assert 0 < blind.ndcg([0, 2, 2]) < 1

if __name__ == "__main__":
    import tempfile
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(Path(tempfile.mkdtemp())) if fn.__code__.co_argcount else fn()
                print("ok  ", name)
            except Exception as e:
                fails += 1; print("FAIL", name, e)
    sys.exit(1 if fails else 0)
