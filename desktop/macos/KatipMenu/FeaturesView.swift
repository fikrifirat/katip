import AppKit
import SwiftUI

/// What each feature is, in the lawyer's words: what it does, and exactly what leaves this Mac.
struct FeatureText {
    let title: String
    let icon: String
    let does: String
    let sends: String

    static func of(_ id: String) -> FeatureText {
        switch id {
        case "mevzuat":
            return FeatureText(title: L("Mevzuat kontrolü", "Statute check"), icon: "book.closed",
                               does: L("Claude bir maddeye atıf yapınca Katip onu bu Mac'teki mevzuat metniyle karşılaştırır.",
                                       "When Claude cites an article, Katip checks it against the statute text on this Mac."),
                               sends: L("Hiçbir şey. Mevzuat dizini uygulamanın içinde, çevrimdışı.",
                                        "Nothing. The statute index is inside the app, offline."))
        case "emsal":
            return FeatureText(title: L("Emsal karar arama", "Precedent search"), icon: "building.columns",
                               does: L("Claude Yargıtay ve Danıştay kararlarını arar, sonuçları kaynak bağlantısıyla gösterir.",
                                       "Claude searches Yargıtay and Danıştay decisions and shows each with its source link."),
                               sends: L("Yalnızca kısa arama kelimeleri bedesten.adalet.gov.tr'ye (Adalet Bakanlığı) gider. Belge metni ve adlar asla gitmez.",
                                        "Only short search keywords go to bedesten.adalet.gov.tr (Ministry of Justice). Document text and names never do."))
        case "dd_masak":
            return FeatureText(title: L("MASAK taraması", "MASAK screening"), icon: "checkmark.shield",
                               does: L("Bir kişiyi ya da şirketi MASAK malvarlığı dondurma listelerinde bu Mac'te tarar (6415 m.5/6/7, 7262).",
                                       "Screens a person or company against MASAK's asset-freeze lists, on this Mac (6415 art. 5/6/7, 7262)."),
                               sends: L("Katip dört kamu listesini masak.hmb.gov.tr'den indirir (yaklaşık 10 istek). Taradığınız adlar hiçbir yere gönderilmez.",
                                        "Katip downloads the four public lists from masak.hmb.gov.tr (about 10 requests). The names you screen are never sent anywhere."))
        case "dd_ilan":
            return FeatureText(title: L("ilan.gov.tr araması", "ilan.gov.tr lookup"), icon: "megaphone",
                               does: L("Seçtiğiniz tek bir adı ilan.gov.tr'de arar ve çıkan ilanları DD taramasına ekler.",
                                       "Searches ilan.gov.tr for one name you choose and adds the notices it finds to DD screening."),
                               sends: L("Bu Mac'teki tarayıcı ilan.gov.tr'yi açar ve o adı sitenin kendi arama kutusuna yazar, sizin arayacağınız gibi, insan hızında.",
                                        "The browser on this Mac opens ilan.gov.tr and types that name into the site's own search box, as you would, at a human pace."))
        default:
            return FeatureText(title: L("Ticaret Sicili Gazetesi", "Trade Registry Gazette"), icon: "newspaper",
                               does: L("Bir şirketi Türkiye Ticaret Sicili Gazetesi'nde arar; ilanların tam listesini ve ücretsiz gazete sayfalarından en fazla 3'ünü okur.",
                                       "Searches the Türkiye Ticaret Sicili Gazetesi for one company; lists every notice and reads up to 3 of the free gazette pages."),
                               sends: L("Tarayıcı ticaretsicil.gov.tr'yi açar; e-Devlet ile kendiniz giriş yaparsınız. Katip şifrenizi asla görmez, güvenlik kodunu asla çözmez, ücretli sayfaya asla basmaz.",
                                        "The browser opens ticaretsicil.gov.tr and you log in with e-Devlet yourself. Katip never sees your password, never solves a security code and never presses a paid button."))
        }
    }
}

struct StateBadge: View {
    let f: E.Feature
    var body: some View {
        switch f.state {
        case "ready": Tag(text: L("Hazır", "Ready"), color: .green)
        case "working": Tag(text: L("Kuruluyor…", "Setting up…"), color: .accentColor)
        case "needs_setup": Tag(text: L("Kurulum gerekli", "Needs setup"), color: .orange)
        case "problem": Tag(text: L("Sorun var", "Problem"), color: .red)
        default: Tag(text: L("Kapalı", "Off"), color: .secondary)
        }
    }
}

// MARK: Features screen
struct FeaturesScreen: View {
    @EnvironmentObject var model: AppModel
    @State private var setup: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                ScreenHeader(title: L("Özellikler", "Features"),
                             subtitle: L("Katip'in maskelemenin yanında yapabildikleri. Her birini siz açarsınız; internete çıkanlar ne gönderdiğini açıkça söyler. Claude yalnızca açık ve hazır olanları görür.",
                                         "What Katip can do besides masking. You switch each one on; the ones that go online say exactly what they send. Claude only sees the ones that are on and ready."))
                ForEach(model.features?.features ?? []) { f in
                    FeatureCard(f: f) { setup = f.id }
                }
                if model.features == nil { ProgressView().frame(maxWidth: .infinity) }
                if let note = model.note { Label(note, systemImage: "exclamationmark.triangle").foregroundStyle(.orange) }
            }
            .padding(22)
        }
        .task { await model.refreshFeatures() }
        .sheet(item: Binding(get: { setup.map { SheetID(id: $0) } }, set: { setup = $0?.id })) { s in
            FeatureSetup(id: s.id) { setup = nil }.environmentObject(model)
        }
        .onReceive(NotificationCenter.default.publisher(for: .katipTourSetup)) { n in setup = n.object as? String }
    }
}

struct SheetID: Identifiable { let id: String }

struct FeatureCard: View {
    @EnvironmentObject var model: AppModel
    let f: E.Feature
    let openSetup: () -> Void
    var t: FeatureText { .of(f.id) }

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            Tile(symbol: t.icon, color: f.enabled ? featureTint(f.id) : .gray, size: 34)
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 8) {
                    Text(t.title).font(.headline)
                    StateBadge(f: f)
                    if f.online { Tag(text: L("İnternet", "Online"), color: .blue) }
                }
                Text(t.does).font(.callout).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                if let line = statusLine { Text(line).font(.caption).foregroundStyle(.secondary) }
                if f.enabled && f.state != "ready" && f.state != "working" {
                    Button(L("Kurulumu tamamla…", "Finish setup…"), action: openSetup).buttonStyle(.borderedProminent).controlSize(.small)
                }
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 8) {
                Toggle("", isOn: Binding(get: { f.enabled }, set: { on in
                    if on && f.online { openSetup() }  // anything that goes online starts with its setup and consent
                    else { Task { await model.setFeature(f.id, on: on) } }
                }))
                .toggleStyle(.switch).labelsHidden()
                .accessibilityLabel(t.title)
                if f.enabled && f.id != "mevzuat" {
                    Button(L("Ayarlar…", "Settings…"), action: openSetup).buttonStyle(.borderless).font(.callout)
                }
            }
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: 10).fill(Color.primary.opacity(0.035)))
        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color.primary.opacity(0.08)))
    }

    var statusLine: String? {
        switch f.id {
        case "dd_masak":
            guard let n = f.detail.records, n > 0 else { return nil }
            return L("\(n) kayıt · \(shortDate(f.detail.dataAsOf)) tarihli", "\(n) records · as of \(shortDate(f.detail.dataAsOf))")
        case "dd_gazette":
            guard f.enabled else { return nil }
            if let u = f.detail.sessionUntil {
                return L("Oturum açık: \(timeText(u)) saatine kadar", "Logged in until \(timeText(u))")
            }
            return L("İlk aramada tarayıcı açılır, e-Devlet ile giriş yaparsınız.", "The first lookup opens the browser for your e-Devlet login.")
        case "dd_ilan" where f.enabled:
            return browserLine(model.features?.browser)
        default: return nil
        }
    }
}

func shortDate(_ iso: String?) -> String {
    guard let iso, iso.count >= 10 else { return "?" }
    let p = iso.prefix(10).split(separator: "-")
    return p.count == 3 ? "\(p[2]).\(p[1]).\(p[0])" : String(iso.prefix(10))
}

func timeText(_ t: Double) -> String {
    let f = DateFormatter()
    f.dateStyle = .none
    f.timeStyle = .short
    return f.string(from: Date(timeIntervalSince1970: t))
}

func browserLine(_ b: E.Browser?) -> String {
    switch b?.kind {
    case "chrome": return L("Tarayıcı: bu Mac'teki Google Chrome", "Browser: this Mac's Google Chrome")
    case "chromium": return L("Tarayıcı: Katip için indirilen Chromium", "Browser: the Chromium downloaded for Katip")
    default: return L("Tarayıcı yok: Google Chrome kurun ya da Chromium indirin.", "No browser: install Google Chrome or download Chromium.")
    }
}

// MARK: one feature's setup, step by step
struct FeatureSetup: View {
    @EnvironmentObject var model: AppModel
    let id: String
    let close: () -> Void
    @State private var agreed = false
    @State private var testing = false
    @State private var confirmLogout = false
    var f: E.Feature? { model.feature(id) }
    var t: FeatureText { .of(id) }
    var browser: E.Browser? { model.features?.browser }
    var needsBrowser: Bool { f?.needs == "browser" }
    var browserOK: Bool { browser?.kind != nil }
    var testedOK: Bool { f?.job?.action == "test_browser" && f?.job?.state == "done" || f?.job?.action == "install_browser" && f?.job?.state == "done" }
    var running: Bool { f?.job?.state == "running" }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 10) {
                Tile(symbol: t.icon, color: featureTint(id), size: 40)
                Text(t.title).font(.title2.weight(.semibold))
                if let f { StateBadge(f: f) }
            }
            Text(t.does).fixedSize(horizontal: false, vertical: true)

            SetupStep(n: 1, title: L("Ne gönderilir", "What leaves this Mac"), done: agreed || (f?.enabled ?? false)) {
                Text(t.sends).font(.callout).fixedSize(horizontal: false, vertical: true)
                if id == "emsal" { RevealButton(key: \.precedents, label: L("Kaydedilen kararlar", "Saved decisions")) }
                if !(f?.enabled ?? false) {
                    Toggle(L("Anladım, bu özelliği kullanmak istiyorum", "I understand and want to use this"), isOn: $agreed)
                }
            }

            if needsBrowser {
                SetupStep(n: 2, title: L("Tarayıcı", "Browser"), done: browserOK && testedOK) {
                    if !(f?.enabled ?? false) {
                        Text(L("Önce özelliği açın; tarayıcı adımı ondan sonra.", "Switch the feature on first; the browser step comes next."))
                            .font(.callout).foregroundStyle(.secondary)
                    } else {
                    HStack(spacing: 8) {
                        if browser?.kind == "chrome" { AppIcon(path: Apps.chrome, fallback: "globe", size: 22) }
                        Text(browserLine(browser)).font(.callout)
                    }
                    HStack {
                        if !browserOK {
                            Button(L("Chromium'u indir (yaklaşık 150 MB)", "Download Chromium (about 150 MB)")) {
                                Task { await model.featureAction(id, "install_browser") }
                            }.disabled(running)
                        } else {
                            Button(L("Tarayıcıyı dene", "Test the browser")) {
                                Task { await model.featureAction(id, "test_browser") }
                            }.disabled(running)
                        }
                        if running { ProgressView().controlSize(.small) }
                        if testedOK { Label(L("Çalışıyor", "Works"), systemImage: "checkmark.circle.fill").foregroundStyle(.green) }
                    }
                    if let j = f?.job, j.state == "failed", j.action != "refresh" {
                        Label(j.action == "install_browser"
                              ? L("İndirilemedi. İnternet bağlantınızı kontrol edip yeniden deneyin.", "Couldn't download. Check your internet connection and try again.")
                              : L("Tarayıcı başlamadı. Google Chrome'u güncelleyin ya da Chromium indirin.", "The browser didn't start. Update Google Chrome or download Chromium."),
                              systemImage: "exclamationmark.triangle").foregroundStyle(.orange).font(.callout)
                    }
                    Text(L("Arama sırasında pencere açılabilir; kendiliğinden kapanır. Chromium, Playwright'ın (Microsoft) indirme sunucusundan gelir.",
                           "A window may open during a lookup; it closes by itself. Chromium comes from Playwright's (Microsoft) download server."))
                        .font(.caption).foregroundStyle(.secondary)
                    }
                }
            }

            if id == "dd_masak" {
                SetupStep(n: 2, title: L("Listeler", "Lists"), done: (f?.detail.records ?? 0) > 0) {
                    if let n = f?.detail.records, n > 0 {
                        Text(L("\(n) kayıt, \(shortDate(f?.detail.dataAsOf)) tarihli. Haftada bir yenileyin.",
                               "\(n) records, as of \(shortDate(f?.detail.dataAsOf)). Refresh once a week."))
                            .font(.callout)
                    } else {
                        Text(L("Açınca Katip listeleri indirir (bir dakika kadar).", "When you switch it on, Katip downloads the lists (about a minute)."))
                            .font(.callout)
                    }
                    HStack {
                        RevealButton(key: \.masak)
                        if f?.enabled ?? false {
                            Button(L("Listeleri yenile", "Refresh lists")) { Task { await model.featureAction(id, "refresh") } }
                                .disabled(running)
                        }
                        if running { ProgressView().controlSize(.small); Text(L("İndiriliyor…", "Downloading…")).font(.callout) }
                    }
                    if let j = f?.job, j.state == "failed" {
                        Label(L("Listeler indirilemedi (\(j.error ?? "?")). Bağlantınızı kontrol edip yeniden deneyin.",
                                "Couldn't download the lists (\(j.error ?? "?")). Check your connection and try again."),
                              systemImage: "exclamationmark.triangle").foregroundStyle(.orange).font(.callout)
                    }
                }
            }

            if id == "dd_gazette" {
                SetupStep(n: 3, title: L("Giriş", "Login"), done: f?.detail.sessionUntil != nil) {
                    Text(L("İlk aramada tarayıcı ticaretsicil.gov.tr giriş sayfasında açılır. e-Devlet ile kendiniz giriş yapın; sonra Katip aramayı arka planda yapar.",
                           "On the first lookup the browser opens at ticaretsicil.gov.tr's login page. Log in with e-Devlet yourself; Katip then searches in the background."))
                        .font(.callout).fixedSize(horizontal: false, vertical: true)
                    Picker(L("Girişi sakla", "Keep the login"),
                           selection: Binding(get: { model.settings?.tsgSessionHours ?? 8.0 },
                                              set: { h in Task { await model.save(["tsg_session_hours": h]); await model.refreshFeatures() } })) {
                        Text(L("Her seferinde çıkış yap", "Log out after every lookup")).tag(0.0)
                        Text(L("1 saat", "1 hour")).tag(1.0)
                        Text(L("4 saat", "4 hours")).tag(4.0)
                        Text(L("8 saat (iş günü)", "8 hours (a working day)")).tag(8.0)
                    }
                    .frame(maxWidth: 360)
                    Text(L("Giriş bilgisi bu Mac'te şifreli durur, süre dolunca Katip sitede çıkış yapar ve siler.",
                           "The login is kept encrypted on this Mac; when the time is up Katip logs out on the site and deletes it."))
                        .font(.caption).foregroundStyle(.secondary)
                    RevealButton(key: \.gazette, label: L("Okunan gazete sayfaları", "Gazette pages read"))
                    if let u = f?.detail.sessionUntil {
                        HStack {
                            Text(L("Şu an giriş açık: \(timeText(u)) saatine kadar.", "Logged in now, until \(timeText(u)).")).font(.callout)
                            Button(L("Şimdi çıkış yap", "Log out now")) { confirmLogout = true }
                        }
                    }
                }
            }

            Spacer(minLength: 0)
            HStack {
                if f?.enabled ?? false {
                    Button(L("Özelliği kapat", "Turn off"), role: .destructive) {
                        Task { await model.setFeature(id, on: false); close() }
                    }
                }
                Spacer()
                Button(L("Kapat", "Close"), action: close).keyboardShortcut(.cancelAction)
                if !(f?.enabled ?? false) {
                    Button(id == "dd_masak" ? L("Aç ve listeleri indir", "Turn on and download lists") : L("Aç", "Turn on")) {
                        Task {
                            await model.setFeature(id, on: true)
                            if !needsBrowser && id != "dd_masak" { close() }
                        }
                    }
                    .buttonStyle(.borderedProminent).keyboardShortcut(.defaultAction)
                    .disabled(!agreed || running)
                }
            }
        }
        .padding(24)
        .frame(width: 560)
        .frame(minHeight: 380)
        .task { await model.refreshFeatures() }
        .confirmationDialog(L("Ticaret Sicili Gazetesi'nden çıkış yapılsın mı?", "Log out of the Trade Registry Gazette?"),
                            isPresented: $confirmLogout) {
            Button(L("Çıkış yap", "Log out")) { Task { await model.featureAction(id, "logout") } }
        } message: { Text(L("Bir sonraki aramada yeniden giriş yaparsınız.", "You'll log in again on the next lookup.")) }
        .onReceive(NotificationCenter.default.publisher(for: .katipTourAgree)) { _ in agreed = true }
    }
}

struct SetupStep<Content: View>: View {
    let n: Int
    let title: String
    let done: Bool
    @ViewBuilder let content: Content
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            ZStack {
                Circle().fill(done ? Color.green : Color.accentColor.opacity(0.15)).frame(width: 24, height: 24)
                if done { Image(systemName: "checkmark").font(.caption.weight(.bold)).foregroundStyle(.white) }
                else { Text("\(n)").font(.caption.weight(.semibold)).foregroundStyle(Color.accentColor) }
            }
            VStack(alignment: .leading, spacing: 8) {
                Text(title).font(.headline)
                content
            }
            Spacer(minLength: 0)
        }
    }
}

extension Notification.Name {
    static let katipTourSetup = Notification.Name("katip.tourSetup")
    static let katipTourAgree = Notification.Name("katip.tourAgree")
}
