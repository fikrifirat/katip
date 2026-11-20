import Foundation

// "What is masked and why", shown under each profile and each data type.
// General information for lawyers, not legal advice. Sources are linked so the lawyer can read the text itself.
// Checked 20 Nov 2026. Fine amounts under KVKK m.18 are raised every year by the revaluation rate, so the app
// links to the law instead of quoting amounts.

struct LegalSource: Hashable, Identifiable {
    var id: String { title }
    let title: String
    let url: URL?
}

enum Src {
    static let kvkk = LegalSource(title: "6698 sayılı Kişisel Verilerin Korunması Kanunu (KVKK)",
                                  url: URL(string: "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6698&MevzuatTur=1&MevzuatTertip=5"))
    static let tck = LegalSource(title: "5237 sayılı Türk Ceza Kanunu, m.135–140",
                                 url: URL(string: "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=5237&MevzuatTur=1&MevzuatTertip=5"))
    static let avukatlik = LegalSource(title: "1136 sayılı Avukatlık Kanunu, m.36 (sır saklama)",
                                       url: URL(string: "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=1136&MevzuatTur=1&MevzuatTertip=5"))
    static let guide = LegalSource(title: "KVKK, Avukatların Mesleki Faaliyetlerinde Kişisel Verilerin Korunmasına İlişkin Uygulama Rehberi (2026), s. 120–121 ve 146",
                                   url: URL(string: "https://www.kvkk.gov.tr/SharedFolderServer/CMSFiles/MTZhYjI0ZTE1NWIwMWM.pdf"))
    static let bench = LegalSource(title: "KVKK-Bench: Katip'in hangi verileri ne oranda bulduğu",
                                   url: URL(string: "https://huggingface.co/spaces/f1k/kvkk-bench"))
    static let privacy = LegalSource(title: L("Katip gizlilik açıklaması", "Katip privacy statement"),
                                     url: URL(string: appIsTurkish ? "https://github.com/fikrifirat/katip/blob/main/PRIVACY.tr.md" : "https://github.com/fikrifirat/katip/blob/main/PRIVACY.md"))
}

struct EntityInfo: Identifiable {
    let id: String
    let titleEN: String
    let group: Group
    let whyTR: String
    let whyEN: String
    var why: String { L(whyTR, whyEN) }

    enum Group: Int, CaseIterable {
        case direct, contact, financial, indirect, special, caseDetail
        var title: String {
            switch self {
            case .direct: return L("Kişiyi doğrudan belirleyenler", "Direct identifiers")
            case .contact: return L("İletişim ve adres", "Contact and address")
            case .financial: return L("Finansal veriler", "Financial data")
            case .indirect: return L("Kişiyi dolaylı belirleyenler", "Indirect identifiers")
            case .special: return L("Özel nitelikli veriler (KVKK m.6)", "Special categories (KVKK art. 6)")
            case .caseDetail: return L("Dosya ve bağlam bilgileri", "Case and context details")
            }
        }
        var basis: String {
            switch self {
            case .direct, .contact, .indirect:
                return L("KVKK m.3: kimliği belirli veya belirlenebilir gerçek kişiye ilişkin her bilgi kişisel veridir. m.4: işlenen veri amaçla bağlantılı, sınırlı ve ölçülü olmalıdır.",
                         "KVKK art. 3: any information about an identified or identifiable natural person is personal data. Art. 4: data must be relevant, limited and proportionate to the purpose.")
            case .financial:
                return L("KVKK m.3 ve m.12: veri sorumlusu, hukuka aykırı erişimi önlemek için her türlü teknik ve idari tedbiri almak zorundadır. Hesap ve kart numaraları dolandırıcılıkta doğrudan kullanılabilir.",
                         "KVKK arts. 3 and 12: the controller must take all technical and organisational measures to prevent unlawful access. Account and card numbers can be used directly for fraud.")
            case .special:
                return L("KVKK m.6: ırk, etnik köken, siyasi düşünce, felsefi inanç, din, mezhep, kılık kıyafet, dernek, vakıf ya da sendika üyeliği, sağlık, cinsel hayat, ceza mahkûmiyeti ve güvenlik tedbirleri ile biyometrik ve genetik veriler özel nitelikli kişisel veridir ve ancak m.6'da sayılan şartlarla işlenebilir.",
                         "KVKK art. 6: race, ethnic origin, political opinion, philosophical belief, religion, sect, dress, membership of associations, foundations or unions, health, sex life, criminal convictions and security measures, and biometric and genetic data are special categories and may be processed only under the conditions listed in art. 6.")
            case .caseDetail:
                return L("Tek başına kişiyi göstermeyen bilgiler bir araya gelince kişiyi belirlenebilir kılabilir. Bu yüzden KVKK m.3 anlamında hâlâ kişisel veri sayılabilirler.",
                         "Details that do not point to a person on their own can identify them together, so they can still be personal data under KVKK art. 3.")
            }
        }
    }
}

enum LegalInfo {
    static let entities: [EntityInfo] = [
        .init(id: "PERSON", titleEN: "Name", group: .direct,
              whyTR: "Ad soyad kişiyi doğrudan belirler. Yabancı müvekkil isimleri de bulunur. Mahkeme ve kurum adları isim sayılmaz.",
              whyEN: "A full name identifies a person directly. Foreign client names are found too. Court and institution names are not treated as names."),
        .init(id: "TCKN", titleEN: "Turkish ID no.", group: .direct,
              whyTR: "T.C. kimlik numarası tek başına kişiyi belirler ve kişinin devletteki bütün kayıtlarını birbirine bağlar. Bütün profillerde her zaman maskelenir.",
              whyEN: "The Turkish ID number identifies a person on its own and links all of their state records. It is masked in every profile."),
        .init(id: "YKN", titleEN: "Foreigner ID no.", group: .direct,
              whyTR: "Yabancı kimlik numarası (99 ile başlar), T.C. kimlik numarasının yabancılar için olanıdır. Her zaman maskelenir.",
              whyEN: "The foreigner ID number (starts with 99) is the equivalent of the Turkish ID number for foreigners. Always masked."),
        .init(id: "PASSPORT", titleEN: "Passport no.", group: .direct,
              whyTR: "Pasaport numarası kişiyi doğrudan belirler. Yabancı müvekkillerin dosyalarında sık geçer. Her zaman maskelenir.",
              whyEN: "A passport number identifies a person directly and is common in foreign clients' files. Always masked."),
        .init(id: "FOREIGN_ID", titleEN: "Foreign ID no.", group: .direct,
              whyTR: "Başka ülkelerin kimlik numaraları da kişiyi doğrudan belirler. Her zaman maskelenir.",
              whyEN: "Other countries' ID numbers identify a person directly too. Always masked."),
        .init(id: "VKN", titleEN: "Tax ID", group: .direct,
              whyTR: "Gerçek kişinin vergi numarası kişiyi belirler. Şirketlerinki kişisel veri değildir, ama metinden ayırt etmek güvenilir olmadığı için hepsi maskelenir.",
              whyEN: "A natural person's tax number identifies them. A company's is not personal data, but the two cannot be told apart reliably, so all are masked."),
        .init(id: "BAR_NO", titleEN: "Bar registration no.", group: .direct,
              whyTR: "Baro sicil numarası avukatın kimliğini belirler. Avukat da bir gerçek kişidir.",
              whyEN: "A bar registration number identifies the lawyer, who is also a natural person."),
        .init(id: "PHONE", titleEN: "Phone", group: .contact,
              whyTR: "Telefon numarası kişiye doğrudan ulaştırır ve çoğu zaman kimlikle eşleştirilmiştir.",
              whyEN: "A phone number reaches the person directly and is usually registered to their identity."),
        .init(id: "EMAIL", titleEN: "E-mail", group: .contact,
              whyTR: "E-posta adresi çoğu zaman adı soyadı içerir ve kişiye doğrudan ulaştırır.",
              whyEN: "An e-mail address often contains the person's name and reaches them directly."),
        .init(id: "ADDRESS", titleEN: "Address", group: .contact,
              whyTR: "Ev adresi kişinin yaşadığı yeri gösterir. Mahkemeye sunum profilinde tarafların kendi adresleri tümüyle, diğer adreslerin bina ve kapı numaraları maskelenir; dava konusu taşınmazın adresi mahkeme için okunur kalır. Yapay zekâ ve tam anonim profillerinde bütün adresler maskelenir.",
              whyEN: "A home address shows where a person lives. In the court profile, parties' own addresses are masked in full and other addresses lose building and door numbers; the address of the property in dispute stays readable for the court. In the AI and anonymous profiles every address is masked."),
        .init(id: "UETS", titleEN: "UETS (e-notification) address", group: .contact,
              whyTR: "UETS (e-Tebligat) adresi kişiye ya da avukata özgü bir tebligat adresidir ve onu belirler.",
              whyEN: "A UETS (electronic notification) address belongs to one person or lawyer and identifies them."),
        .init(id: "IP_ADDRESS", titleEN: "IP address", group: .contact,
              whyTR: "IP adresi, internet sağlayıcısının kayıtlarıyla birlikte kişiyi belirleyebilir.",
              whyEN: "Together with the internet provider's records, an IP address can identify a person."),
        .init(id: "IBAN", titleEN: "IBAN", group: .financial,
              whyTR: "IBAN hesap sahibini belirler ve ödeme dolandırıcılığında kullanılabilir.",
              whyEN: "An IBAN identifies the account holder and can be used in payment fraud."),
        .init(id: "CREDIT_CARD", titleEN: "Card number", group: .financial,
              whyTR: "Kart numarası hem kişiyi belirler hem de doğrudan para kaybına yol açabilir.",
              whyEN: "A card number identifies the holder and can lead directly to financial loss."),
        .init(id: "PLATE", titleEN: "Licence plate", group: .indirect,
              whyTR: "Araç plakası, ruhsat kayıtlarından araç sahibine götürür.",
              whyEN: "A licence plate leads to the owner through registration records."),
        .init(id: "BIRTH_DATE", titleEN: "Date of birth", group: .indirect,
              whyTR: "Doğum tarihi, isim ya da yer bilgisiyle birleşince kişiyi büyük ölçüde belirler.",
              whyEN: "A date of birth largely identifies a person when combined with a name or place."),
        .init(id: "HEALTH", titleEN: "Health data", group: .special,
              whyTR: "Teşhis, rapor, ilaç, engellilik oranı gibi sağlık bilgileri özel nitelikli veridir. İş, tazminat ve sigorta dosyalarında sık geçer.",
              whyEN: "Diagnoses, medical reports, medication and disability ratings are special-category data, and common in employment, damages and insurance files."),
        .init(id: "RELIGION", titleEN: "Religion / belief", group: .special,
              whyTR: "Din, mezhep ve felsefi inanç özel nitelikli veridir.",
              whyEN: "Religion, sect and philosophical belief are special-category data."),
        .init(id: "POLITICAL", titleEN: "Political opinion", group: .special,
              whyTR: "Siyasi düşünce ve parti üyeliği özel nitelikli veridir.",
              whyEN: "Political opinion and party membership are special-category data."),
        .init(id: "UNION", titleEN: "Union membership", group: .special,
              whyTR: "Sendika, dernek ve vakıf üyeliği özel nitelikli veridir. İşçilik davalarında sık geçer.",
              whyEN: "Membership of a union, association or foundation is special-category data, and common in employment cases."),
        .init(id: "ETHNICITY", titleEN: "Race / ethnic origin", group: .special,
              whyTR: "Irk ve etnik köken özel nitelikli veridir.",
              whyEN: "Race and ethnic origin are special-category data."),
        .init(id: "SEXUAL_LIFE", titleEN: "Sex life", group: .special,
              whyTR: "Cinsel hayata ilişkin bilgiler özel nitelikli veridir. Aile hukuku dosyalarında sık geçer.",
              whyEN: "Information about sex life is special-category data, and common in family-law files."),
        .init(id: "BIOMETRIC_GENETIC", titleEN: "Biometric / genetic", group: .special,
              whyTR: "Parmak izi, yüz tanıma ve DNA (ör. babalık testi) sonuçları özel nitelikli veridir.",
              whyEN: "Fingerprints, face recognition and DNA results (e.g. paternity tests) are special-category data."),
        .init(id: "CRIMINAL_RECORD", titleEN: "Criminal record", group: .special,
              whyTR: "Ceza mahkûmiyeti ve güvenlik tedbirleri özel nitelikli veridir. Mahkemeye sunumda dosyanın konusu olduğu için okunur kalır; yapay zekâ ile paylaşımda maskelenir.",
              whyEN: "Criminal convictions and security measures are special-category data. They stay readable for court use, where they are the subject of the file, and are masked when sharing with AI."),
        .init(id: "CASE_NO", titleEN: "Case no.", group: .caseDetail,
              whyTR: "Esas, karar ve UYAP numaraları mahkemeye sunumda okunur kalır, çünkü mahkemenin işine yarar. Yapay zekâ ile paylaşımda maskelenir: numarayla dosyaya ve taraflara ulaşılabilir.",
              whyEN: "Docket, decision and UYAP numbers stay readable for the court, which needs them. They are masked when sharing with AI, because the number leads to the file and its parties."),
        .init(id: "DATE", titleEN: "Date", group: .caseDetail,
              whyTR: "Olay, işe giriş, kaza gibi tarihler başka bilgilerle birleşince kişiyi belirleyebilir. Yalnızca tam anonim profilde maskelenir.",
              whyEN: "Dates of events, hiring or accidents can identify a person together with other details. Masked only in the fully anonymous profile."),
        .init(id: "PLACE", titleEN: "Place", group: .caseDetail,
              whyTR: "İl ve ilçe adları küçük yerlerde kişiyi belirleyebilir. Yalnızca tam anonim profilde maskelenir.",
              whyEN: "Province and district names can identify a person in small places. Masked only in the fully anonymous profile."),
        .init(id: "INSTITUTION", titleEN: "Institution", group: .caseDetail,
              whyTR: "Mahkeme, şirket ve kurum adları işvereni ya da dosyayı gösterebilir. Yalnızca tam anonim profilde maskelenir.",
              whyEN: "Court, company and institution names can point to an employer or the file. Masked only in the fully anonymous profile."),
    ]

    static func entity(_ id: String) -> EntityInfo? { entities.first { $0.id == id } }

    struct ProfileWhy {
        let useFor: String
        let keeps: String
        let why: String
        let sources: [LegalSource]
    }

    static func profile(_ id: String) -> ProfileWhy {
        switch id {
        case "court":
            return .init(
                useFor: L("Delil, dilekçe eki ve mahkemeye sunulacak belgeler.", "Evidence, petition attachments and documents for the court."),
                keeps: L("Dosya numaraları, emsal kararlar, mahkeme adları, tarihler, sokak ve mahalle adları ve dava konusu taşınmazın adresi okunur kalır: mahkeme bunlara ihtiyaç duyar.",
                         "Case numbers, precedent citations, court names, dates, street and neighbourhood names and the address of the property in dispute stay readable: the court needs them."),
                why: L("KVKK m.4 ölçülülük ilkesi gereği mahkemeye yalnızca davayla ilgili veri sunulmalıdır. Kimlik numaraları, telefon, e-posta, banka bilgileri ve tarafların ev adresleri çoğu zaman davanın konusu değildir. Bu kurallar çalışan avukatların geri bildirimiyle belirlendi.",
                       "Under the proportionality principle of KVKK art. 4, only data relevant to the case should go to the court. ID numbers, phone, e-mail, bank details and parties' home addresses are rarely what the case is about. These rules were set with feedback from practising lawyers."),
                sources: [Src.kvkk, Src.avukatlik])
        case "ai":
            return .init(
                useFor: L("ChatGPT, Claude gibi yapay zekâ araçlarına göndermek için.", "For sending to AI tools such as ChatGPT or Claude."),
                keeps: L("Mahkeme adları, tarihler, il ve ilçeler ve olayların akışı okunur kalır, böylece yapay zekâ işe yarar bir cevap verebilir.",
                         "Court names, dates, provinces and districts and the course of events stay readable, so the AI can still give a useful answer."),
                why: L("KVKK'nın avukatlar rehberi, müvekkil belgelerinin üretken yapay zekâ araçlarına yüklenmesinin yurt dışına veri aktarımı sayılabileceğini belirtir (s. 120–121) ve paylaşmadan önce maskeleme ya da anonimleştirme önerir (s. 146). Yurt dışına aktarım KVKK m.9'daki şartlara bağlıdır (7499 sayılı Kanunla değişik). Dosya numaraları da maskelenir, çünkü numarayla taraflara ulaşılabilir.",
                       "The Board's guide for lawyers says that uploading client documents to generative AI tools can be a transfer of personal data abroad (pp. 120–121) and recommends masking or anonymising before sharing (p. 146). Transfers abroad are subject to KVKK art. 9 (as amended by Law 7499). Case numbers are masked too, because they lead to the parties."),
                sources: [Src.guide, Src.kvkk, Src.avukatlik])
        default:
            return .init(
                useFor: L("Yayın, eğitim, makale veya emsal paylaşımı: kimin olduğunun hiç çıkmaması gereken metinler.", "Publications, training material, articles or sharing a precedent: texts where nobody should be identifiable."),
                keeps: L("Yalnızca olayların akışı ve hukuki değerlendirme okunur kalır.", "Only the course of events and the legal reasoning stay readable."),
                why: L("Tarih, yer ve kurum gibi dolaylı bilgiler bir araya gelince kişiyi belirleyebilir. Bu profil onları da maskeler. Yine de bağlamdan kişi çıkarılabiliyorsa metin anonim sayılmaz.",
                       "Indirect details such as dates, places and institutions can identify a person together, so this profile masks them too. If the person can still be inferred from the context, the text is not anonymous."),
                sources: [Src.kvkk, Src.guide])
        }
    }

    // MARK: - General notes

    static var stillPersonalData: (title: String, body: String) {
        (L("Maskelenmiş metin hâlâ kişisel veri mi?", "Is masked text still personal data?"),
         L("""
           Çoğu zaman evet. Yer tutucularla değiştirmek takma adlandırmadır (pseudonymisation), anonimleştirme değildir: eşleme tablosu sizde durduğu ve olaylar, tarihler, yerler kişiyi gösterebildiği sürece KVKK uygulanmaya devam eder. Maskeleme riski ve paylaşılan veri miktarını azaltır; bu KVKK m.4 (ölçülülük) ve m.12'ye (veri güvenliği) uymanıza yardım eder, ama yapay zekâya göndermeyi tek başına hukuka uygun hâle getirmez.

           Katip bu riski şöyle küçültür:
           • Eşleme tablosu (ör. [AD SOYAD-1] → gerçek isim) bu telefondan hiç çıkmaz. Şifreli saklanır, yedeğe girmez, 30 gün sonra silinir.
           • Yapay zekâ profili adresleri, dosya numaralarını ve sabıka bilgisini de maskeler; tam anonim profil tarih, yer ve kurum adlarını da.
           • Bulunan bir değer metinde hâlâ okunur kalacaksa Katip metni vermez.
           • Pano yalnızca bu cihazda kalır ve 10 dakika sonra silinir.

           Sizin yapmanız gerekenler:
           • Göndermeden önce maskeli metni okuyun. Katip bazı değerleri kaçırabilir.
           • Yurt dışına aktarım için KVKK m.9'daki şartları sağlayın (ör. sağlayıcının standart sözleşmesi ve Kurula bildirim).
           • Yapay zekâ hesabınızda sohbetlerin eğitimde kullanılmasını kapatın; mümkünse kurumsal (Team/Enterprise) plan kullanın.
           • Olaylar kişiyi tek başına gösteriyorsa (ör. bilinen bir dava), metni anonim saymayın.
           """,
           """
           Usually, yes. Replacing values with placeholders is pseudonymisation, not anonymisation: while the map exists and the events, dates and places can point to a person, KVKK still applies. Masking reduces the risk and the amount of data shared, which helps you meet KVKK art. 4 (proportionality) and art. 12 (security), but it does not by itself make sending the text to an AI lawful.

           How Katip reduces the risk:
           • The map (e.g. [AD SOYAD-1] → real name) never leaves this phone. It is encrypted, kept out of backups and deleted after 30 days.
           • The AI profile also masks addresses, case numbers and criminal records; the anonymous profile also masks dates, places and institutions.
           • If a detected value would still be readable, Katip refuses to give out the text.
           • The clipboard stays on this device and clears after 10 minutes.

           What you still need to do:
           • Read the masked text before sending it. Katip can miss values.
           • Meet the conditions of KVKK art. 9 for the transfer abroad (e.g. the provider's standard contract, notified to the Board).
           • Turn off training on your chats in the AI account, and use a business plan (Team/Enterprise) where you can.
           • If the events alone identify the person (e.g. a well-known case), do not treat the text as anonymous.
           """))
    }

    static var consequences: (title: String, items: [String], sources: [LegalSource]) {
        (L("Neden önemli: yaptırımlar", "Why it matters: sanctions"),
         [
            L("KVKK m.18: veri güvenliği (m.12) ve yurt dışına aktarım (m.9) yükümlülüklerine aykırılık için idari para cezası. Tutarlar her yıl yeniden değerleme oranında artırılır.",
              "KVKK art. 18: administrative fines for breaching the security (art. 12) and transfer abroad (art. 9) duties. Amounts rise every year with the revaluation rate."),
            L("TCK m.135–136: kişisel verileri hukuka aykırı kaydetmek 1–3 yıl, başkasına vermek veya yaymak 2–4 yıl hapis. TCK m.137: suç bir meslek veya sanatın sağladığı kolaylıktan yararlanılarak işlenirse ceza yarı oranında artırılır.",
              "Turkish Criminal Code arts. 135–136: unlawfully recording personal data, 1–3 years; unlawfully giving or disseminating it, 2–4 years in prison. Art. 137: the penalty rises by half when the offence uses the advantages of a profession."),
            L("Avukatlık Kanunu m.36: avukat, mesleği sırasında öğrendiklerini açıklayamaz; aykırılık disiplin sorumluluğu doğurur.",
              "Attorneys' Act art. 36: a lawyer may not disclose what they learn in their work; a breach leads to disciplinary liability."),
            L("Müvekkilin kişilik haklarının ihlali nedeniyle maddi ve manevi tazminat istenebilir.",
              "The client can claim material and moral damages for a breach of personality rights."),
         ],
         [Src.kvkk, Src.tck, Src.avukatlik])
    }

    static var disclaimer: String {
        L("Bu bilgiler geneldir, hukuki görüş değildir. Katip değerlerin çoğunu bulur ama hepsini bulduğunu garanti etmez; KVKK-Bench sonuçlarına bakın.",
          "This is general information, not legal advice. Katip finds most values but does not guarantee it finds all of them; see the KVKK-Bench results.")
    }
}
