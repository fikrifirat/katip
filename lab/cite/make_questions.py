"""Write the Cite-Bench-TR question set (data/questions.jsonl). Run once; the file is committed.

Each question is asked twice, in Turkish and in English (an expat or foreign client asking about Turkish law).
  expect  articles a good answer should cite (any one of them counts). Checked by hand against the article text in
          the statute index (build_index.py), see `check_questions()`. These are Claude-written and NEED a lawyer's
          review before publication: status "draft" until then.
  must    optional key fact (a period, a share, a threshold) as regexes on the folded answer; any one matches.
  risk    high = a wrong answer can lose a case or a right (deadlines, liberty, residence); medium = money or compliance.
  trap    the law changed recently, so a model trained on older text is likely to be wrong.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TWO_WEEKS = [r"(iki|2)\s*hafta", r"two\s*weeks", r"2\s*weeks", r"(14|on dört)\s*gün", r"(14|fourteen)\s*days"]
def P(tr, en):  # period helper: Turkish words + English words
    return [rf"\b({tr})", rf"\b({en})"]   # no trailing \\b: Turkish suffixes follow ("otuz gündür")

Q = [
 # ---- İş hukuku (labour) -------------------------------------------------------------------------------------------
 ("is", "high", "Belirsiz süreli iş sözleşmesini feshetmek isteyen işveren, işçiye ne kadar önceden bildirimde bulunmalıdır?",
  "How much notice must an employer give before terminating an indefinite-term employment contract in Turkey?",
  ["4857:17"], [r"(iki|dört|altı|sekiz|2|4|6|8)\s*hafta", r"(two|four|six|eight|2|4|6|8)\s*weeks"], None),
 ("is", "high", "Kıdem tazminatına hak kazanmak için işçinin en az ne kadar çalışmış olması gerekir ve bu hak hangi kanunda düzenlenir?",
  "How long must an employee have worked to be entitled to severance pay (kıdem tazminatı) in Turkey, and which law governs it?",
  ["1475:14"], P(r"bir yil|1 yil|bir sene", r"one year|1 year|12 months"), "old-law: still in 1475, a law otherwise repealed"),
 ("is", "high", "İş sözleşmesi geçerli sebep gösterilmeden feshedilen işçi işe iade için ne kadar süre içinde başvurmalıdır?",
  "An employee in Turkey was dismissed without a valid reason. Within what period must they apply for reinstatement?",
  ["4857:20", "7036:3"], P(r"bir ay|1 ay", r"one month|1 month"), None),
 ("is", "high", "Ücreti ödenmeyen işçi iş sözleşmesini haklı nedenle derhal feshedebilir mi? Dayanağı nedir?",
  "Can an employee in Turkey whose wages are not paid terminate the contract immediately for just cause? On what legal basis?",
  ["4857:24"], None, None),
 ("is", "medium", "İş sözleşmesine konulabilecek deneme süresi en fazla ne kadardır?",
  "What is the maximum probation period that can be agreed in a Turkish employment contract?",
  ["4857:15"], P(r"iki ay|2 ay", r"two months|2 months"), None),
 ("is", "high", "Ücret, fazla mesai ve yıllık izin ücreti gibi işçilik alacakları kaç yılda zamanaşımına uğrar?",
  "What is the limitation period for employee claims such as unpaid wages, overtime and annual leave pay in Turkey?",
  ["4857:ek 3"], P(r"beş yil|5 yil", r"five years|5 years"), None),
 # ---- Kira (rent) --------------------------------------------------------------------------------------------------
 ("kira", "medium", "Konut kirasında yenilenen kira döneminde kira artışı en fazla ne kadar olabilir?",
  "How much can residential rent be increased at renewal in Turkey?",
  ["6098:344"], [r"tüfe", r"tüketici fiyat", r"consumer price", r"\bcpi\b", r"inflation"], "the 25% cap (TBK geçici 1 and 2) covered renewals up to 1 July 2024 only"),
 ("kira", "high", "Kiracı kirayı ödemezse kiraya veren tahliye için hangi yolu izlemeli, kiracıya ne kadar süre vermelidir?",
  "If a tenant in Turkey does not pay rent, how can the landlord evict them and how much time must the tenant be given?",
  ["6098:315", "2004:269"], P(r"otuz gün|30 gün", r"thirty days|30 days"), None),
 ("kira", "medium", "Ev sahibi kendisi oturmak için kiracıyı çıkarabilir mi? Şartları nelerdir?",
  "Can a landlord in Turkey evict a tenant because they need the home for themselves? Under what conditions?",
  ["6098:350"], None, None),
 ("kira", "medium", "Kira sözleşmesinde alınabilecek depozito (güvence) en fazla ne kadar olabilir?",
  "What is the maximum security deposit a landlord in Turkey may require?",
  ["6098:342"], P(r"üç aylik|3 aylik|üç ay|3 ay", r"three months|3 months"), None),
 ("kira", "high", "Kira bedelinin tespiti veya tahliye davası açmadan önce arabulucuya gitmek zorunlu mu?",
  "In Turkey, is mediation mandatory before filing a rent or eviction lawsuit?",
  ["6325:18/B"], [r"zorunlu", r"dava şart", r"mandatory", r"compulsory", r"required"], "added in 2023 (Law 7445)"),
 ("kira", "medium", "Konut kirasında ev sahibi on yıllık uzama süresi dolunca sözleşmeyi sebep göstermeden sona erdirebilir mi?",
  "Can a landlord in Turkey end a residential lease without cause after the ten-year extension period?",
  ["6098:347"], P(r"on yil|10 yil", r"ten years|10 years|ten-year|10-year"), None),
 # ---- Aile (family) ------------------------------------------------------------------------------------------------
 ("aile", "medium", "Anlaşmalı boşanmanın şartları nelerdir?",
  "What are the conditions for an uncontested (agreed) divorce in Turkey?",
  ["4721:166"], P(r"bir yil|1 yil", r"one year|1 year"), None),
 ("aile", "high", "Eşinin zina ettiğini öğrenen kişi boşanma davasını ne kadar süre içinde açmalıdır?",
  "Within what period must a spouse in Turkey file for divorce after learning of adultery?",
  ["4721:161"], P(r"alti ay|6 ay", r"six months|6 months"), None),
 ("aile", "medium", "Boşanma sonrası yoksulluk nafakası hangi şartlarla ve ne kadar süre için verilir?",
  "Under what conditions and for how long is post-divorce spousal support (yoksulluk nafakası) granted in Turkey?",
  ["4721:175"], None, None),
 ("aile", "medium", "Evlilik içinde edinilen mallar boşanmada nasıl paylaşılır?",
  "How is property acquired during marriage divided on divorce in Turkey?",
  ["4721:202", "4721:219", "4721:231", "4721:236"], None, None),
 ("aile", "medium", "Boşanmada çocuğun velayeti ve iştirak nafakası nasıl belirlenir?",
  "How are child custody and child support decided in a Turkish divorce?",
  ["4721:182", "4721:327", "4721:330"], None, None),
 ("aile", "medium", "Boşanma davası sürerken eşlerden biri tedbir nafakası isteyebilir mi?",
  "Can a spouse claim interim maintenance while a divorce case is pending in Turkey?",
  ["4721:169"], None, None),
 # ---- Miras (inheritance) ------------------------------------------------------------------------------------------
 ("miras", "high", "Mirası reddetmek için süre nedir ve ne zaman başlar?",
  "What is the deadline to renounce an inheritance in Turkey, and when does it start?",
  ["4721:605", "4721:606"], P(r"üç ay|3 ay", r"three months|3 months"), None),
 ("miras", "medium", "Çocukların (altsoyun) saklı payı ne kadardır?",
  "What is the reserved (forced) share of children in Turkish inheritance law?",
  ["4721:506"], [r"yari", r"\bhalf\b", r"1/2", r"%\s?50", r"50\s?%"], "changed in 2007: siblings no longer have a reserved share"),
 ("miras", "medium", "Çocuklarla birlikte mirasçı olan sağ kalan eşin miras payı nedir?",
  "What share of the estate does a surviving spouse receive when inheriting together with children in Turkey?",
  ["4721:499"], [r"dörtte bir", r"1/4", r"quarter", r"one[- ]fourth", r"%\s?25", r"25\s?%"], None),
 ("miras", "medium", "Saklı payı zedelenen mirasçı tenkis davasını ne kadar süre içinde açmalıdır?",
  "Within what period must an heir whose reserved share was violated file a reduction action (tenkis) in Turkey?",
  ["4721:571"], P(r"bir yil|1 yil", r"one year|1 year"), None),
 ("miras", "medium", "Vasiyetname hangi şekillerde yapılabilir?",
  "In what forms can a will be made under Turkish law?",
  ["4721:531"], None, None),
 ("miras", "high", "Yabancı uyruklu bir kişi öldüğünde Türkiye'deki taşınmazlarına hangi ülkenin miras hukuku uygulanır?",
  "A foreign national dies owning an apartment in Turkey. Which country's inheritance law applies to that apartment?",
  ["5718:20"], [r"türk hukuku", r"turkish law"], None),
 # ---- İcra (enforcement) -------------------------------------------------------------------------------------------
 ("icra", "high", "İlamsız icra takibinde ödeme emrine itiraz süresi kaç gündür?",
  "How many days does a debtor in Turkey have to object to a payment order in enforcement proceedings without a judgment?",
  ["2004:62"], P(r"yedi gün|7 gün", r"seven days|7 days"), None),
 ("icra", "high", "Borçlu itiraz ettikten sonra alacaklı itirazın iptali davasını ne kadar sürede açmalıdır?",
  "After a debtor objects, within what period must the creditor in Turkey file an action to annul the objection (itirazın iptali)?",
  ["2004:67"], P(r"bir yil|1 yil|bir sene|1 sene", r"one year|1 year"), None),
 ("icra", "high", "Alacaklı itirazın kaldırılmasını ne kadar süre içinde icra mahkemesinden isteyebilir?",
  "Within what period can a creditor in Turkey ask the enforcement court to lift the debtor's objection (itirazın kaldırılması)?",
  ["2004:68"], P(r"alti ay|6 ay", r"six months|6 months"), None),
 ("icra", "medium", "Borçlu olmadığını düşünen kişi icra takibine karşı hangi davayı açabilir?",
  "What lawsuit can a person in Turkey file if they believe they do not owe the debt being enforced?",
  ["2004:72"], [r"menfi tespit", r"negative declaratory"], None),
 ("icra", "high", "Kambiyo senetlerine dayalı takipte borçlunun şikayet ve itiraz süresi kaç gündür?",
  "In Turkish enforcement based on a bill of exchange or cheque, how many days does the debtor have to object?",
  ["2004:168", "2004:169"], P(r"beş gün|5 gün", r"five days|5 days"), None),
 ("icra", "high", "Kira alacağı için tahliye talepli icra takibinde kiracının itiraz süresi nedir?",
  "In an enforcement proceeding for unpaid rent with eviction, how long does the tenant in Turkey have to object?",
  ["2004:269"], P(r"yedi gün|7 gün", r"seven days|7 days"), None),
 # ---- Ceza (criminal) ----------------------------------------------------------------------------------------------
 ("ceza", "high", "Bireysel suçlarda gözaltı süresi en fazla ne kadardır?",
  "What is the maximum police custody period for individual offences in Turkey?",
  ["5271:91"], [r"(yirmi dört|24)\s*saat", r"(twenty[- ]four|24)\s*hours"], None),
 ("ceza", "high", "Tutuklama kararı verilebilmesi için hangi şartlar aranır?",
  "What conditions must be met for pre-trial detention (tutuklama) in Turkey?",
  ["5271:100"], None, None),
 ("ceza", "high", "Şüphelinin ifade verirken hangi hakları vardır? Avukat isteyebilir mi?",
  "What rights does a suspect in Turkey have during questioning? Can they ask for a lawyer?",
  ["5271:147", "5271:150"], None, None),
 ("ceza", "high", "Ceza davasında verilen hükme karşı istinaf süresi nedir?",
  "What is the deadline to appeal (istinaf) a criminal judgment in Turkey?",
  ["5271:273"], TWO_WEEKS, "Law 7499 (2 Mar 2024) changed 'seven days from pronouncement' to 'two weeks from service of the reasoned judgment'"),
 ("ceza", "medium", "Hükmün açıklanmasının geri bırakılması (HAGB) hangi cezalarda uygulanabilir?",
  "When can a Turkish court defer the announcement of a verdict (HAGB)?",
  ["5271:231"], P(r"iki yil|2 yil", r"two years|2 years"), None),
 ("ceza", "medium", "Dolandırıcılık suçunun cezası nedir?",
  "What is the penalty for fraud (dolandırıcılık) under Turkish criminal law?",
  ["5237:157", "5237:158"], [r"bir yildan beş yila", r"1\s*(ila|-|–)\s*5\s*yil", r"one to five years", r"1\s*(to|-|–)\s*5\s*years"], None),
 # ---- Usul ve süreler (civil procedure and deadlines) ---------------------------------------------------------------
 ("usul", "high", "Hukuk mahkemesi kararına karşı istinaf süresi nedir ve ne zaman başlar?",
  "What is the deadline to appeal a civil court judgment in Turkey (istinaf), and when does it start?",
  ["6100:345"], TWO_WEEKS, None),
 ("usul", "high", "Bölge adliye mahkemesi kararına karşı temyiz süresi nedir?",
  "What is the deadline to appeal a regional court of appeal decision to the Court of Cassation (temyiz) in a civil case?",
  ["6100:361"], TWO_WEEKS, None),
 ("usul", "high", "Davalı cevap dilekçesini ne kadar süre içinde vermelidir?",
  "How long does a defendant in a Turkish civil case have to file a statement of defence?",
  ["6100:127", "6100:317"], TWO_WEEKS, None),
 ("usul", "high", "Bir süre adli tatile denk gelirse ne olur?",
  "What happens to a procedural deadline in Turkey that ends during the judicial recess (adli tatil)?",
  ["6100:104"], P(r"bir hafta|1 hafta", r"one week|1 week"), None),
 ("usul", "high", "Elektronik tebligat ne zaman yapılmış sayılır?",
  "When is an electronic notification (e-tebligat) deemed served in Turkey?",
  ["7201:7/A"], [r"beşinci gün", r"5\.? gün", r"fifth day", r"5th day", r"five days"], None),
 ("usul", "medium", "Genel yetkili mahkeme hangisidir?",
  "Which court generally has territorial jurisdiction in a Turkish civil case?",
  ["6100:6"], [r"yerleşim yeri", r"domicile", r"residence"], None),
 # ---- KVKK (data protection) ---------------------------------------------------------------------------------------
 ("kvkk", "medium", "Kişisel veriler açık rıza olmadan hangi hallerde işlenebilir?",
  "When can personal data be processed without explicit consent under Turkey's data protection law (KVKK)?",
  ["6698:5"], None, None),
 ("kvkk", "medium", "Sağlık verisi gibi özel nitelikli kişisel veriler hangi şartlarla işlenebilir?",
  "Under what conditions can special categories of personal data, such as health data, be processed under KVKK?",
  ["6698:6"], None, "amended by Law 7499 (2 Mar 2024)"),
 ("kvkk", "medium", "Kişisel veriler yurt dışına hangi şartlarla aktarılabilir?",
  "Under what conditions can personal data be transferred abroad under KVKK?",
  ["6698:9"], [r"yeterlilik", r"standart sözleşme", r"adequacy", r"standard contract"], "rewritten by Law 7499 (2 Mar 2024): adequacy decisions, standard contracts, binding corporate rules"),
 ("kvkk", "medium", "Veri sorumlusunun aydınlatma yükümlülüğü neleri kapsar?",
  "What must a data controller tell people when collecting their personal data under KVKK?",
  ["6698:10"], None, None),
 ("kvkk", "medium", "İlgili kişinin veri sorumlusuna başvurusu ne kadar sürede cevaplanmalıdır?",
  "Within how many days must a data controller in Turkey answer a data subject's request?",
  ["6698:11", "6698:13"], P(r"otuz gün|30 gün", r"thirty days|30 days"), None),
 ("kvkk", "medium", "Aydınlatma yükümlülüğünü yerine getirmeyen veri sorumlusuna hangi yaptırım uygulanır?",
  "What sanction applies to a data controller that fails to meet the duty to inform under KVKK?",
  ["6698:18"], [r"idari para ceza", r"administrative fine"], None),
 # ---- Yabancılar (foreigners and expats) ---------------------------------------------------------------------------
 ("yabanci", "high", "Türkiye'de kaç günden fazla kalacak yabancının ikamet izni alması gerekir?",
  "How long can a foreigner stay in Turkey before they need a residence permit?",
  ["6458:19", "6458:11"], P(r"doksan gün|90 gün", r"ninety days|90 days"), None),
 ("yabanci", "high", "Türkiye'de ikamet izni türleri nelerdir?",
  "What types of residence permit exist in Turkey?",
  ["6458:30"], None, None),
 ("yabanci", "high", "Türkiye'de ev satın alan yabancı kısa dönem ikamet izni alabilir mi?",
  "Can a foreigner who buys a home in Turkey get a short-term residence permit?",
  ["6458:31"], None, None),
 ("yabanci", "high", "Türk vatandaşıyla evli yabancı eş aile ikamet izni alabilir mi? Şartları nelerdir?",
  "Can the foreign spouse of a Turkish citizen get a family residence permit? What are the conditions?",
  ["6458:34", "6458:35"], None, None),
 ("yabanci", "high", "Uzun dönem ikamet izni için Türkiye'de kaç yıl kesintisiz ikamet gerekir?",
  "How many years of uninterrupted residence are needed for a long-term residence permit in Turkey?",
  ["6458:42"], P(r"sekiz yil|8 yil", r"eight years|8 years"), None),
 ("yabanci", "high", "Hangi durumlarda bir yabancı hakkında sınır dışı etme kararı alınabilir?",
  "When can a foreigner be deported from Turkey?",
  ["6458:54"], None, None),
 ("yabanci", "high", "Yabancı bir çalışan Türkiye'de çalışma izni için nereye başvurur?",
  "Where does a foreign employee apply for a work permit in Turkey?",
  ["6735:7"], [r"bakanlik", r"ministry", r"konsolosluk", r"consulate"], None),
 ("yabanci", "high", "Türk vatandaşıyla evlenen yabancı ne zaman Türk vatandaşlığına başvurabilir?",
  "When can a foreigner married to a Turkish citizen apply for Turkish citizenship?",
  ["5901:16"], P(r"üç yil|3 yil", r"three years|3 years"), None),
 ("yabanci", "medium", "Yatırım yoluyla Türk vatandaşlığı hangi kanuna dayanır?",
  "What is the legal basis for Turkish citizenship by investment?",
  ["5901:12"], None, None),
 # ---- Tüketici ve taşınmaz (consumer and property) ----------------------------------------------------------------
 ("tuketici", "medium", "Ayıplı mal alan tüketicinin hangi seçimlik hakları vardır?",
  "What remedies does a consumer in Turkey have after buying a defective product?",
  ["6502:11"], None, None),
 ("tuketici", "medium", "Ayıplı maldan sorumluluk süresi nedir?",
  "How long is a seller in Turkey liable for defects in goods sold to a consumer?",
  ["6502:12"], P(r"iki yil|2 yil", r"two years|2 years"), None),
 ("tuketici", "medium", "İnternetten alışverişte cayma hakkı süresi nedir?",
  "How long is the right of withdrawal for online purchases in Turkey?",
  ["6502:48"], P(r"on dört gün|14 gün", r"fourteen days|14 days"), None),
 ("tuketici", "medium", "Tüketici uyuşmazlığında tüketici hakem heyetine mi yoksa mahkemeye mi başvurulmalı?",
  "Should a consumer dispute in Turkey go to the consumer arbitration committee or to court?",
  ["6502:68", "6502:73"], None, "the money threshold is updated every year"),
 ("tuketici", "medium", "Apartmanda aidat ödemeyen kat malikine karşı ne yapılabilir?",
  "What can be done against an apartment owner in Turkey who does not pay the building's common charges?",
  ["634:20", "634:22"], None, None),
 ("tuketici", "medium", "Tüketiciye satılan mallar için garanti belgesi zorunlu mu?",
  "Is a warranty certificate mandatory for goods sold to consumers in Turkey?",
  ["6502:56"], None, None),
]

AREAS = {"is": "Labour", "kira": "Rent", "aile": "Family", "miras": "Inheritance", "icra": "Enforcement",
         "ceza": "Criminal", "usul": "Civil procedure and deadlines", "kvkk": "Data protection (KVKK)",
         "yabanci": "Foreigners and expats", "tuketici": "Consumer and property"}


STALE = {"ceza-04": [r"(yedi|7)\s*gün", r"(seven|7)\s*days"],
         "kira-01": [r"%\s?25", r"25\s?%", r"yüzde yirmi beş", r"yüzde 25", r"25 percent", r"25 per cent"]}


def rows():
    n = {}
    for area, risk, tr, en, expect, must, trap in Q:
        n[area] = n.get(area, 0) + 1
        yield {"id": f"{area}-{n[area]:02d}", "area": area, "risk": risk, "q_tr": tr, "q_en": en, "expect": expect,
               "must": must or [], "trap": trap, "stale": STALE.get(f"{area}-{n[area]:02d}", []), "status": "draft"}


def check_questions(rs, checker):
    """Every expected article must exist and be in force in the index; print its first words for a human check."""
    bad = 0
    for r in rs:
        for e in r["expect"]:
            no, art = e.split(":")
            kind, num = ("ek", art[3:]) if art.startswith("ek ") else ("madde", art)
            v, note, a, slug = checker.verify(no, kind, num, "", None)
            if v != "OK":
                bad += 1
            print(f"{r['id']:<11} {e:<11} {v:<8} {((a or {}).get('t') or '')[:90]}")
    return bad


if __name__ == "__main__":
    import sys; sys.path.insert(0, str(HERE))
    from katip_cite import Checker
    rs = list(rows())
    bad = check_questions(rs, Checker())
    (HERE / "data").mkdir(exist_ok=True)
    with open(HERE / "data" / "questions.jsonl", "w") as f:
        for r in rs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n{len(rs)} questions x 2 languages, {sum(len(r['expect']) for r in rs)} expected articles, {bad} not OK")
