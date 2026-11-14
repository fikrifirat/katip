"""Tests for Katip Cite, which double as a small extraction eval:  python lab/cite/test_katip_cite.py
Each case: text, expected [(law, article, verdict)] in order. Written by hand to cover the forms Turkish lawyers,
Turkish LLM answers and English (expat) answers use, plus near-misses that must NOT be read as citations."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from katip_cite import Checker

CASES = [
    # Turkish abbreviations and article forms
    ("TBK m. 344 uyarınca", [("6098", "344", "OK")]),
    ("TBK md. 344/1 gereğince", [("6098", "344", "OK")]),
    ("TBK'nın 315. maddesi", [("6098", "315", "OK")]),
    ("TBK’nın 350 nci maddesi", [("6098", "350", "OK")]),
    ("TMK 166/3 hükmü", [("4721", "166", "OK")]),
    ("TMK m.166/III", [("4721", "166", "OK")]),
    ("HMK m. 345", [("6100", "345", "OK")]),
    ("HMK 345. madde", [("6100", "345", "OK")]),
    ("İİK 62", [("2004", "62", "OK")]),
    ("İİK m. 168/5", [("2004", "168", "OK")]),
    ("İş K. m. 18", [("4857", "18", "OK")]),
    ("CMK m. 91", [("5271", "91", "OK")]),
    ("TCK 157", [("5237", "157", "OK")]),
    ("KVKK m. 11 ve 13", [("6698", "11", "OK"), ("6698", "13", "OK")]),
    ("KVKK'nın 5. ve 6. maddeleri", [("6698", "5", "OK")]),
    ("YUKK m. 54/1-d", [("6458", "54", "OK")]),
    ("AY m. 20", [("2709", "20", "OK")]),
    ("Anayasa'nın 36. maddesi", [("2709", "36", "OK")]),
    ("TTK m. 5/A", [("6102", "5/A", "OK")]),
    ("Tebligat Kanunu m. 7/a", [("7201", "7/A", "OK")]),
    ("İş Kanunu ek madde 3", [("4857", "ek 3", "OK")]),
    # number + name
    ("6098 sayılı Türk Borçlar Kanunu'nun 344. maddesi", [("6098", "344", "OK")]),
    ("4857 sayılı İş Kanunu'nun 18 inci maddesi", [("4857", "18", "OK")]),
    ("4857 sayılı Kanun m. 17", [("4857", "17", "OK")]),
    ("6325 sayılı Kanun'un 18/B maddesi", [("6325", "18/B", "OK")]),
    ("1475 sayılı İş Kanunu m. 14", [("1475", "14", "OK")]),
    ("5901 sayılı Türk Vatandaşlığı Kanunu'nun 16. maddesi", [("5901", "16", "OK")]),
    # anaphora and lists
    ("İş Kanunu'nun 18. maddesi ve aynı Kanunun 21. maddesi", [("4857", "18", "OK"), ("4857", "21", "OK")]),
    ("TMK m. 161, 162 ve 166", [("4721", "161", "OK"), ("4721", "162", "OK"), ("4721", "166", "OK")]),
    ("TBK m. 347-349", [("6098", "347", "OK"), ("6098", "348", "OK"), ("6098", "349", "OK")]),
    # English (expat-facing answers)
    ("Article 344 of the Turkish Code of Obligations", [("6098", "344", "OK")]),
    ("Art. 18 of the Labour Law", [("4857", "18", "OK")]),
    ("Article 54 of the Law on Foreigners and International Protection (Law No. 6458)", [("6458", "54", "OK")]),
    ("Law No. 6735, Article 7", [("6735", "7", "OK")]),
    ("Turkish Civil Code Article 166", [("4721", "166", "OK")]),
    ("Article 5 of the KVKK", [("6698", "5", "OK")]),
    ("Article 42 of the LFIP", [("6458", "42", "OK")]),
    # wrong citations
    ("TBK m. 712", [("6098", "712", "NO_SUCH_ARTICLE")]),
    ("Article 1500 of the Turkish Civil Code", [("4721", "1500", "NO_SUCH_ARTICLE")]),
    ("İş Kanunu md. 87", [("4857", "87", "ARTICLE_REPEALED")]),
    ("BK m. 248", [("818", "248", "LAW_REPEALED")]),
    ("743 sayılı Medeni Kanun m. 134", [("743", "134", "LAW_REPEALED")]),
    ("743 sayılı Türk Ticaret Kanunu m. 1", [("743", "1", "NUMBER_NAME_CLASH")]),
    ("6098 sayılı Türk Medeni Kanunu m. 2", [("6098", "2", "NUMBER_NAME_CLASH")]),
    ("9999 sayılı Kanun m. 3", [("9999", "3", "UNKNOWN_LAW")]),
    ("1475 sayılı İş Kanunu m. 17", [("1475", "17", "ARTICLE_REPEALED")]),
    ("HUMK m. 432", [("1086", "432", "LAW_REPEALED")]),
    ("TMK m. 166 ve 6098 sayılı Türk Medeni Kanunu m. 2", [("4721", "166", "OK"), ("6098", "2", "NUMBER_NAME_CLASH")]),
    ("İİK m. 62 ve 7 gün içinde itiraz", [("2004", "62", "OK")]),
    # regressions from the first real run (14 Nov 2026 audit)
    ("Law No. 4857 regulates notice periods.", [("4857", None, "OK")]),
    ("Law No. 6458", [("6458", None, "OK")]),
    ("Turkish Family Law No. 5837 governs forced heirship.", [("5837", None, "UNKNOWN_LAW")]),
    ("818 sayılı Borçlar Kanunu yürürlükten kalkmıştır.", [("818", None, "LAW_REPEALED")]),
    ("the Labour Law (Law No. 4857), Article 17", [("4857", "17", "OK")]),
    ("Turkish Code of Civil Procedure (TCC), Article 179", [("6100", "179", "OK")]),
    ("Law No. 6698 on the Protection of Personal Data, Article 12", [("6698", "12", "OK")]),
    ("Law No. 4857, Article 120", [("4857", "120", "OK")]),
    ("1475 sayılı Kanun m. 14 ve bu Kanunun 17 nci maddesi", [("1475", "14", "OK")]),
    ("1475 sayılı Kanun m. 14 ve aynı Kanunun 17 nci maddesi", [("1475", "14", "OK"), ("1475", "17", "UNVERIFIED")]),
    ("**Law No. 5906 on Enforcement**, **Article 24**", [("5906", "24", "UNKNOWN_LAW")]),
    ("Law No. 6573 on the Regulation of Electronic Notifications (e-tebligat), Article 5", [("6573", "5", "UNKNOWN_LAW")]),
    # not citations
    ("İtiraz yedi gün içinde yapılır.", []),
    ("2 hafta içinde 62 nci madde hükümleri dahilinde", []),
    ("Toplantı 18 Mart 2024 tarihinde yapıldı.", []),
    ("Dosya 2019/1234 Esas sayılıdır.", []),
    ("Bu oran %25'tir ve 344 kişi katıldı.", []),
]


def run():
    c = Checker()
    tp = fp = fn = vok = 0
    fails = []
    for text, gold in CASES:
        got = [(x.law_no, x.article, x.verdict) for x in c.extract(text) if x.kind == "statute"]
        g_cit = [(l, a) for l, a, _ in gold]
        p_cit = [(l, a) for l, a, _ in got]
        tp_i = sum(1 for x in p_cit if x in g_cit)
        tp += tp_i; fp += len(p_cit) - tp_i; fn += len(g_cit) - tp_i
        vok += sum(1 for x in got if x in gold)
        if got != gold:
            fails.append((text, gold, got))
    for t, g, p in fails:
        print(f"FAIL  {t!r}\n      want {g}\n      got  {p}")
    n_gold = sum(len(g) for _, g in CASES)
    print(f"\n{len(CASES) - len(fails)}/{len(CASES)} cases pass. Extraction precision {tp / max(1, tp + fp):.3f}, "
          f"recall {tp / max(1, n_gold):.3f}; verdict correct on {vok}/{n_gold} gold citations.")
    return not fails


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
