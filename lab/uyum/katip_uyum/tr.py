"""Turkish documents: summary for the lawyer, KVKK inventory, and the aydınlatma metni (KVKK m.10).

Turkish text comes from the questionnaire's *_tr fields (name_tr, purpose_tr, label_tr, service_tr,
retention_tr). Where one is missing the document says so with [AÇIK: ...] instead of mixing in English.
"""
from __future__ import annotations

from . import law
from .model import effective_role, activity_data, activity_subjects, by_id, receives, review_state, sources
from .rules import SEVERITY_TR, THEMES_TR, Analysis


def A(what: str) -> str:
    return f"**[AÇIK: {what}]**"


def t(x: dict, key: str, what: str) -> str:
    val = x.get(f"{key}_tr")
    return val if val else A(what)


def table(head, rows):
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", "<br>")  # noqa: E731
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] +
                     ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows])


ULKE = {"TR": "Türkiye", "US": "ABD", "DE": "Almanya", "FR": "Fransa", "NL": "Hollanda", "IE": "İrlanda",
        "BE": "Belçika", "GB": "Birleşik Krallık", "CH": "İsviçre", "IN": "Hindistan", "LOCAL": "kendi bilgisayarımız"}
ROTA = {"EEA": "AB/AEA içinde", "adequacy": "AB yeterlilik kararı", "DPF": "AB-ABD Veri Gizliliği Çerçevesi",
        "SCC": "standart sözleşme maddeleri", "BCR": "bağlayıcı şirket kuralları", "same country": "aynı ülke",
        "onward (client SCCs)": "AB müvekkilleriyle yapılan SCC'ler kapsamında ileri aktarım",
        "missing": "araç yok", "unknown": "belirtilmemiş"}
GDPR_TR = {"6(1)(a)": "rıza", "6(1)(b)": "sözleşmenin ifası", "6(1)(c)": "hukuki yükümlülük",
           "6(1)(d)": "hayati menfaat", "6(1)(e)": "kamu yararı", "6(1)(f)": "meşru menfaat"}


def ulke(cc):
    return ULKE.get(cc, law.country(cc)) if cc else A("ülke")


def kvkk_sebep(a) -> str:
    if a.get("kvkk_basis"):
        return law.KVKK_ONLY.get(a["kvkk_basis"], a["kvkk_basis"])
    b = a.get("lawful_basis")
    s = law.KVKK_BASIS.get(b, A("KVKK m.5 hukuki sebebi")) if b else A("KVKK m.5 hukuki sebebi")
    if b and b in law.KVKK_BASIS:
        s += " " + A("teyit edin; müvekkil işi için m.5/2-e daha uygun olabilir")
    if a.get("art9_condition"):
        s += "; " + law.KVKK_ART9.get(a["art9_condition"], A("KVKK m.6/3 şartı"))
    return s


def header(an, title):
    s, c = an.q["system"], an.q["controller"]
    return (f"# {title}\n\n**Sistem:** {s['name']} · **Veri sorumlusu:** {c['name']} · **Anket tarihi:** "
            f"{s.get('date') or A('tarih')}\n\n> **Avukat incelemesi için TASLAK.** Katip bu metni yukarıdaki ankete "
            "göre hazırladı. Hukuki görüş değildir; sistemin KVKK'ya, GDPR'a veya AB Yapay Zekâ Tüzüğü'ne uygun olduğu "
            "anlamına gelmez. **[AÇIK: ...]** ile işaretli yerler eksik bilgidir.\n")


# ------------------------------------------------------------------------------------------- 00 özet
def ozet(an: Analysis) -> str:
    out = [header(an, "Özet ve yapılacaklar")]
    if an.q.get("assumptions"):
        out.append("## Varsayılan cevaplar (doğrulanmadı)\n\nAşağıdaki cevaplar tahmindir. Bunlara dayanan her bulgu "
                   "ancak tahmin kadar doğrudur; paketi kullanmadan önce her birini doğrulayın.\n\n" +
                   table(["Alan", "Varsayılan cevap", "Neden"],
                         [[a.get("field", ""), a.get("value_tr") or a.get("value", ""), a.get("basis_tr") or a.get("basis", "")]
                          for a in an.q["assumptions"]]) + "\n")
    top = an.top(5)
    if top:
        out.append("## Önce bunlar\n\nÖnem ve verinin hassasiyetine göre sıralandı.\n\n" +
                   "\n".join(f"{i}. **{f.title_tr or f.title}** *({f.cite})*" for i, f in enumerate(top, 1)) + "\n")
    counts = {}
    for f in an.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    out.append("## Tüm bulgular\n\n" + ", ".join(f"{counts.get(k, 0)} {SEVERITY_TR[k].lower()}"
                                                for k in ("action", "risk", "open", "info")) + ". Ayrıntılı açıklamalar "
               "İngilizce belgelerde (00-overview.md ve ilgili belge).\n")
    for th, label in THEMES_TR.items():
        fs = [f for f in an.findings if f.theme == th]
        if fs:
            out.append(f"### {label}\n\n" + table(["Tür", "Bulgu", "Dayanak", "Belge"],
                                                   [[SEVERITY_TR[f.severity], f.title_tr or f.title, f.cite, ", ".join(f.docs)]
                                                    for f in fs]) + "\n")
    out.append("## Belgeler\n\nİngilizce belgeler AB müvekkilleri ve denetim otoriteleri içindir. Türkçe belgeler: "
               "[kişisel veri işleme envanteri](01-envanter.tr.md) ve [aydınlatma metni](03-aydinlatma-metni.tr.md).\n")
    return "\n".join(out)


# ------------------------------------------------------------------------------------------- 01 envanter
def envanter(an: Analysis) -> str:
    q = an.q
    out = [header(an, "Kişisel veri işleme envanteri (KVKK)")]
    out.append("VERBİS kaydına (KVKK m.16) ve saklama ve imha politikasına temel olan envanter. Kurul, 2018'den beri "
               "bazı meslek gruplarını kayıt yükümlülüğünden muaf tuttu; avukatların güncel listede olup olmadığı "
               "kontrol edilmeli " + A("karar numarası, doğrulanmış") + ". Kayıt muafiyeti diğer yükümlülükleri "
               "kaldırmaz.\n")
    stor = by_id(q, "storage")
    rows = []
    for a in q.get("activities", []):
        rows.append([
            t(a, "name", "faaliyet adı"),
            t(a, "purpose", "amaç"),
            kvkk_sebep(a),
            ", ".join(s.get("label_tr") or A("kişi grubu") for s in activity_subjects(q, a)),
            ", ".join(d.get("label_tr") or A("veri kategorisi") for d in activity_data(q, a)),
            ", ".join(stor[s].get("what_tr") or A("saklama yeri") for s in a.get("storage", []) if s in stor) or A("saklama yeri"),
            a.get("retention_tr") or A("saklama süresi"),
        ])
    out.append(table(["Faaliyet", "Amaç", "Hukuki sebep (KVKK)", "İlgili kişi grubu", "Veri kategorisi",
                      "Saklama yeri", "Saklama süresi"], rows) + "\n")
    xf = [tr for tr in an.transfers if tr.kvkk_transfer]
    out.append("## Yurt dışına aktarım (KVKK m.9)\n\n" + (table(["Alıcı", "Ülke", "Ne gidiyor", "Aktarım aracı (KVKK)"], [
        [tr.vendor["name"], ulke(tr.country), {"raw": "maskelenmemiş metin", "masked": "maskeli metin",
                                               "metadata": "arama terimi"}.get(tr.receives, A("ne gidiyor")),
         A("standart sözleşme (5 iş günü içinde Kurula bildirim) veya diğer m.9 aracı")] for tr in xf]) if xf else "Yok.") + "\n")
    return "\n".join(out)


# ------------------------------------------------------------------------------------------- 03 aydınlatma
def aydinlatma(an: Analysis) -> str:
    q, c = an.q, an.q["controller"]
    acts = q.get("activities", [])
    out = [header(an, "Aydınlatma metni (KVKK m.10)")]
    out.append("Bu metin, kişisel veriler elde edilirken verilir ve açık rıza metninden ayrı tutulur (Aydınlatma "
               "Yükümlülüğünün Yerine Getirilmesinde Uyulacak Usul ve Esaslar Hakkında Tebliğ). Amaç ve hukuki sebepler "
               "genel ifadelerle değil, faaliyet bazında yazılmalıdır.\n")
    out.append("## Veri sorumlusu\n\n" + f"{c['name']}, {c.get('address') or A('adres')}. Kişisel verilerle ilgili "
               f"başvurular için: {c.get('contact') or A('iletişim adresi')}.\n")
    out.append("## Kişisel verileriniz hangi amaçla ve hangi hukuki sebeple işleniyor\n\n" + table(
        ["Amaç", "Hukuki sebep", "Saklama süresi"],
        [[t(a, "purpose", "amaç"), kvkk_sebep(a), a.get("retention_tr") or A("saklama süresi")] for a in acts]) + "\n")
    yontem = []
    for a in acts:
        src = sources(a)
        kaynak = {"data_subject": "doğrudan sizden", "client": "müvekkilimizin bize ilettiği belgelerden",
                  "public": "kamuya açık kaynaklardan", "third_party": "üçüncü kişilerden",
                  "generated": "sistemlerimizin kayıtlarından"}
        yontem.append(f"- {t(a, 'name', 'faaliyet adı')}: " + (", ".join(kaynak.get(s, s) for s in src) or A("kaynak")) +
                      (f" ({a['source_detail_tr']})" if a.get("source_detail_tr") else ""))
    out.append("## Verilerinizi nasıl topluyoruz\n\nElektronik ortamda (e-posta, belge yükleme, kamuya açık "
               "kayıtlarda arama) ve gerektiğinde fiziki belgelerden:\n\n" + "\n".join(yontem) + "\n")
    vend = [x for x in q.get("vendors", []) if receives(q, x) not in ("none", None) and x.get("country") != "LOCAL"]
    alici = []
    for x in vend:
        er = effective_role(x)
        rol = ("hizmet sağlayıcı (veri işleyen)" if er in ("processor", "sub_processor")
               else "kendi adına hareket eden kurum" if er in ("controller", "joint_controller") else A("rolü"))
        ne = {"raw": "maskelenmemiş", "masked": "maskeli (maskeleme aracının tespit ettiği adlar ve kimlik numaraları yer tutucularla değiştirilmiş)",
              "metadata": "yalnızca arama terimi"}.get(receives(q, x), A("ne aktarılıyor"))
        alici.append([x["name"], x.get("service_tr") or A("hizmetin Türkçe tanımı"), rol, ulke(x.get("country")), ne])
    for p in q.get("partners", []):
        alici.append([p["name"], p.get("service_tr") or "birlikte çalıştığımız hukuk bürosu",
                      {"joint_controller": "ortak veri sorumlusu", "controller": "veri sorumlusu",
                       "processor": "veri işleyen"}.get(p.get("role"), A("rolü")), ulke(p.get("country")), "dosyaya göre"])
    if any(ag.get("output") == "client" for ag in q.get("agents", [])):
        alici.append(["Müvekkillerimiz", "hazırladığımız rapor ve görüşler", "veri sorumlusu", "müvekkilin ülkesi", "rapor içeriği"])
    out.append("## Verileriniz kimlere ve hangi amaçla aktarılıyor\n\n" + (table(
        ["Alıcı", "Ne için", "Rolü", "Ülke", "Ne aktarılıyor"], alici) if alici else "Aktarım yok.") + "\n")
    xf = [tr for tr in an.transfers if tr.kvkk_transfer]
    if xf:
        out.append("## Yurt dışına aktarım (KVKK m.9)\n\n" + "; ".join(
            f"{tr.vendor['name']} ({ulke(tr.country)})" for tr in xf) + ". Bu aktarımlar KVKK m.9'daki araçlardan "
            "birine dayanır: " + A("her alıcı için standart sözleşme veya diğer uygun güvence") + ". Maskeli metin de "
            "bizim için kişisel veridir; bu nedenle aynı kurallar uygulanır.\n")
    ajanlar = [ag for ag in q.get("agents", []) if ag.get("output") in ("client", "court", "published")]
    if ajanlar and all(review_state(ag) == "always" for ag in ajanlar):
        yz = ("Belgeleri sınıflandırmak, araştırma yapmak ve taslak hazırlamak için yapay zekâ sistemleri kullanıyoruz. "
              "Her sonuç, büromuzdan çıkmadan önce bir avukat tarafından incelenir.")
    else:
        yz = ("Belgeleri sınıflandırmak, araştırma yapmak ve taslak hazırlamak için yapay zekâ sistemleri kullanıyoruz. " +
              A("hangi çıktıların gönderilmeden önce avukat tarafından okunduğunu doğru biçimde yazın; ankete göre bazı "
                "çıktılar incelenmeden gönderiliyor"))
    out.append("## Yapay zekâ kullanımı\n\n" + yz + " Hakkınızda yalnızca otomatik sistemlerle yapılan analiz sonucunda "
               "aleyhinize bir sonuç çıkmasına itiraz edebilirsiniz (KVKK m.11/1-g).\n")
    out.append("## Haklarınız (KVKK m.11)\n\nBize başvurarak; kişisel verilerinizin işlenip işlenmediğini öğrenme, "
               "işlenmişse bilgi talep etme, işlenme amacını ve amacına uygun kullanılıp kullanılmadığını öğrenme, yurt "
               "içinde veya yurt dışında aktarıldığı üçüncü kişileri bilme, eksik veya yanlış işlenmişse düzeltilmesini "
               "isteme, KVKK m.7'deki şartlar çerçevesinde silinmesini veya yok edilmesini isteme, bu işlemlerin "
               "aktarıldığı üçüncü kişilere bildirilmesini isteme, münhasıran otomatik sistemlerle analiz sonucu "
               "aleyhinize bir sonucun ortaya çıkmasına itiraz etme ve kanuna aykırı işleme nedeniyle zarara uğramanız "
               "hâlinde zararın giderilmesini talep etme haklarına sahipsiniz.\n\nBaşvurunuzu yazılı olarak veya "
               "Veri Sorumlusuna Başvuru Usul ve Esasları Hakkında Tebliğ'de sayılan yöntemlerle " + (c.get("contact") or A("iletişim adresi")) +
               " adresine iletebilirsiniz. Başvurular en geç otuz gün içinde ücretsiz olarak sonuçlandırılır (KVKK m.13/2). "
               "Avukatlık Kanunu m.36'daki sır saklama yükümlülüğü, başka kişilere ait bilgilerin size verilmesini "
               "sınırlayabilir.\n")
    if not an.eea_controller and an.q.get("scope", {}).get("eu_clients"):
        out.append("## AB'de bulunan kişiler\n\nAB'de bulunan kişiler için ayrıca GDPR kapsamındaki bilgilendirme "
                   "metni geçerlidir (03-privacy-notice.md).\n")
    return "\n".join(out)


def render_tr(an: Analysis) -> dict[str, str]:
    return {"00-ozet.tr.md": ozet(an).rstrip() + "\n", "01-envanter.tr.md": envanter(an).rstrip() + "\n",
            "03-aydinlatma-metni.tr.md": aydinlatma(an).rstrip() + "\n"}
