import AppKit
import SwiftUI

/// The first run: five short screens, each doing one thing, so a lawyer is set up without help.
struct OnboardingView: View {
    @EnvironmentObject var model: AppModel
    @State var step: Step = .welcome

    enum Step: Int, CaseIterable { case welcome, prepare, model, claude, ready }

    var body: some View {
        VStack(spacing: 0) {
            StepDots(current: step.rawValue, count: Step.allCases.count)
                .padding(.top, 22)
            Group {
                switch step {
                case .welcome: WelcomeStep { step = .prepare }
                case .prepare: PrepareStep { step = .model }
                case .model: ModelStep { step = .claude }
                case .claude: ClaudeStep { step = .ready }
                case .ready: ReadyStep()
                }
            }
            .frame(maxWidth: 560)
            .padding(.horizontal, 40)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .transition(.asymmetric(insertion: .move(edge: .trailing).combined(with: .opacity),
                                    removal: .opacity))
            .id(step)
        }
        .animation(.easeInOut(duration: 0.25), value: step)
        .onReceive(NotificationCenter.default.publisher(for: .katipTourStep)) { n in
            if let i = n.object as? Int, let s = Step(rawValue: i) { step = s }
        }
    }
}

struct StepDots: View {
    let current: Int
    let count: Int
    var body: some View {
        HStack(spacing: 8) {
            ForEach(0..<count, id: \.self) { i in
                Capsule().fill(i == current ? Color.accentColor : Color.secondary.opacity(0.25))
                    .frame(width: i == current ? 22 : 8, height: 8)
            }
        }
        .accessibilityLabel(L("Adım \(current + 1) / \(count)", "Step \(current + 1) of \(count)"))
    }
}

/// Title, one-line explanation, content, and the main button at the bottom right.
struct StepFrame<Content: View>: View {
    let icon: String
    let title: String
    let subtitle: String
    let button: String
    var buttonEnabled = true
    var secondary: (String, () -> Void)?
    let action: () -> Void
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Spacer(minLength: 10)
            Image(systemName: icon).font(.system(size: 38, weight: .regular)).foregroundStyle(Color.accentColor)
            VStack(alignment: .leading, spacing: 6) {
                Text(title).font(.system(size: 26, weight: .semibold))
                Text(subtitle).font(.title3).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }
            content
            Spacer(minLength: 10)
            HStack {
                if let secondary {
                    Button(secondary.0, action: secondary.1).buttonStyle(.borderless)
                }
                Spacer()
                Button(button, action: action)
                    .buttonStyle(.borderedProminent)
                    .keyboardShortcut(.defaultAction)
                    .controlSize(.large)
                    .disabled(!buttonEnabled)
            }
            .padding(.bottom, 26)
        }
    }
}

// MARK: 1. Welcome
struct WelcomeStep: View {
    let next: () -> Void
    var body: some View {
        StepFrame(icon: "checkmark.shield",
                  title: L("Katip'e hoş geldiniz", "Welcome to Katip"),
                  subtitle: L("Belgelerdeki kişisel verileri, yapay zekâya göndermeden önce bu Mac'te gizler; cevaptaki adları geri koyar.",
                              "Hides the personal data in your documents on this Mac before they go to an AI, and puts the names back into the answer."),
                  button: L("Başlayalım", "Get started"), action: next) {
            VStack(alignment: .leading, spacing: 12) {
                Promise(icon: "laptopcomputer", text: L("Her şey bu Mac'te çalışır. Belgeleriniz hiçbir yere yüklenmez.",
                                                        "Everything runs on this Mac. Your documents are never uploaded."))
                Promise(icon: "key", text: L("Gerçek adları geri getiren anahtar yalnızca sizde, Anahtar Zinciri'nde durur.",
                                             "The key that brings real names back stays with you, in your Keychain."))
                Promise(icon: "eye", text: L("Son kontrol sizde: Katip bir değeri kaçırabilir, göndermeden önce bakın.",
                                             "You have the last look: Katip can miss a value, so check before you send."))
                if !AppModel.inApplications { MoveBanner() }
            }
            .padding(.top, 6)
        }
    }
}

struct MoveBanner: View {
    @EnvironmentObject var model: AppModel
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "arrow.down.app").font(.title2).foregroundStyle(Color.accentColor)
            VStack(alignment: .leading, spacing: 2) {
                Text(L("Katip'i Uygulamalar klasörüne taşıyın", "Move Katip to your Applications folder")).font(.headline)
                Text(L("Böylece güncellemeler ve Claude bağlantısı çalışır.", "So updates and the Claude connection keep working."))
                    .font(.callout).foregroundStyle(.secondary)
            }
            Spacer()
            Button(L("Taşı ve yeniden aç", "Move and reopen")) { model.moveToApplications() }
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 10).fill(Color.accentColor.opacity(0.08)))
        .padding(.top, 8)
    }
}

struct Promise: View {
    let icon: String
    let text: String
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon).frame(width: 22).foregroundStyle(Color.accentColor)
            Text(text).fixedSize(horizontal: false, vertical: true)
        }
    }
}

// MARK: 2. Getting ready
struct PrepareStep: View {
    @EnvironmentObject var model: AppModel
    let next: () -> Void
    @State private var checks: [Check] = [
        Check(title: L("Katip motoru başlatılıyor", "Starting the Katip engine")),
        Check(title: L("Dava anahtarları korunuyor", "Protecting case keys")),
        Check(title: L("Örnek bir cümle maskeleniyor", "Masking a sample sentence")),
    ]
    @State private var failed = false
    @State private var running = false

    struct Check: Identifiable {
        let id = UUID()
        let title: String
        var state: State = .waiting
        var detail: String?
        enum State { case waiting, working, ok, warn, failed }
    }

    var done: Bool { checks.allSatisfy { $0.state == .ok || $0.state == .warn } }

    var body: some View {
        StepFrame(icon: "gearshape.2",
                  title: L("Hazırlanıyor", "Getting ready"),
                  subtitle: L("Katip arka planda küçük bir motor çalıştırır. Kullanmadığınızda 15 dakika sonra kendiliğinden durur.",
                              "Katip runs a small engine in the background. When you're not using it, it stops by itself after 15 minutes."),
                  button: L("Devam", "Continue"), buttonEnabled: done,
                  secondary: failed ? (L("Kaydı göster", "Show log"), { NSWorkspace.shared.activateFileViewerSelecting([E.logURL]) }) : nil,
                  action: next) {
            VStack(alignment: .leading, spacing: 12) {
                ForEach(checks) { c in
                    HStack(alignment: .top, spacing: 10) {
                        Group {
                            switch c.state {
                            case .waiting: Image(systemName: "circle").foregroundStyle(.tertiary)
                            case .working: ProgressView().controlSize(.small)
                            case .ok: Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                            case .warn: Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.orange)
                            case .failed: Image(systemName: "xmark.octagon.fill").foregroundStyle(.red)
                            }
                        }
                        .frame(width: 20)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(c.title)
                            if let d = c.detail { Text(d).font(.callout).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true) }
                        }
                    }
                }
                if failed {
                    Button(L("Yeniden dene", "Try again")) { Task { await run() } }.padding(.top, 4)
                }
            }
            .padding(.top, 6)
        }
        .task { await run() }
    }

    func run() async {
        guard !running else { return }
        running = true
        defer { running = false }
        failed = false
        for i in checks.indices { checks[i].state = .waiting; checks[i].detail = nil }
        let t0 = Date()
        checks[0].state = .working
        do {
            try await model.loadAll()
            checks[0].state = .ok
            let secs = Date().timeIntervalSince(t0)
            checks[0].detail = secs < 0.3 ? L("Çalışıyor.", "Running.")
                : L(String(format: "%.1f saniyede hazır.", secs), String(format: "Ready in %.1f seconds.", secs))
        } catch {
            checks[0].state = .failed
            checks[0].detail = error.localizedDescription
            failed = true
            return
        }
        checks[1].state = .working
        if model.status?.vault.hasPrefix("encrypted") == true {
            checks[1].state = .ok
            checks[1].detail = L("Şifreli, yalnızca bu Mac'te.", "Encrypted, on this Mac only.")
        } else {
            checks[1].state = .warn
            checks[1].detail = L("Anahtarlar yalnızca bellekte; motor durunca adlar geri getirilemez.",
                                 "Keys are in memory only; names can't be brought back after the engine stops.")
        }
        checks[2].state = .working
        do {
            let m = try await model.client.mask(SampleText.sentence, matter: SampleText.matter)
            let ok = !m.maskedText.contains("DEMİRCİ")
            checks[2].state = ok ? .ok : .failed
            checks[2].detail = ok ? summarize(m.placeholders) : L("Örnek ad gizlenmedi.", "The sample name was not hidden.")
            failed = !ok
        } catch {
            checks[2].state = .failed
            checks[2].detail = error.localizedDescription
            failed = true
        }
    }
}

enum SampleText {
    static let matter = "katip-ornek"
    static let sentence = "Davacı Ayşe DEMİRCİ (T.C. Kimlik No: 10000000146) vekili Av. Mehmet KARA, müvekkiline 0532 111 22 33 numaralı telefondan ulaşılabileceğini bildirmiştir."
}

// MARK: 3. Name model
struct ModelStep: View {
    @EnvironmentObject var model: AppModel
    let next: () -> Void
    @State private var choice = "base"
    @State private var working = false

    var current: String { model.settings?.model ?? "nano" }
    var chosen: E.ModelInfo? { model.models?.models.first { $0.name == choice } }
    var downloading: E.Download? {
        guard let d = model.models?.download, d.state == "running" else { return nil }
        return d
    }

    var body: some View {
        StepFrame(icon: "person.text.rectangle",
                  title: L("Ad tanıma modeli", "Name model"),
                  subtitle: L("Kimlik numarası, telefon, IBAN gibi değerleri kurallar bulur. Adları bu küçük model bulur ve o da bu Mac'te çalışır.",
                              "Rules find ID numbers, phones and IBANs. Names are found by this small model, which also runs on this Mac."),
                  button: buttonTitle, buttonEnabled: !working,
                  secondary: (L("Şimdilik Nano kalsın", "Keep Nano for now"), { next() }),
                  action: { Task { await go() } }) {
            VStack(spacing: 10) {
                ForEach((model.models?.models ?? []).filter { !$0.custom }) { m in
                    ModelCard(info: m, selected: choice == m.name, active: current == m.name)
                        .onTapGesture { if !working { choice = m.name } }
                }
                if let d = downloading {
                    VStack(alignment: .leading, spacing: 4) {
                        ProgressView(value: d.fraction)
                        Text(L("\(modelTitle(d.name)) indiriliyor: \(mb(d.done)) / \(mb(d.total)) MB. Her dosya parmak iziyle doğrulanır.",
                               "Downloading \(modelTitle(d.name)): \(mb(d.done)) of \(mb(d.total)) MB. Each file is checked against its fingerprint."))
                            .font(.callout).foregroundStyle(.secondary)
                    }
                }
                if let note = model.note {
                    Text(note).font(.callout).foregroundStyle(.orange).fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    var buttonTitle: String {
        guard let c = chosen else { return L("Devam", "Continue") }
        if c.name == current { return L("Devam", "Continue") }
        return c.downloaded ? L("\(modelTitle(c.name)) kullan", "Use \(modelTitle(c.name))")
                            : L("İndir ve kullan (\(Int(c.sizeMb)) MB)", "Download and use (\(Int(c.sizeMb)) MB)")
    }

    func mb(_ b: Int) -> String { String(format: "%.0f", Double(b) / 1e6) }

    func go() async {
        guard let c = chosen else { return next() }
        model.note = nil
        if c.name == current { return next() }
        working = true
        defer { working = false }
        if c.downloaded {
            if await model.save(["model": c.name]) { next() }
        } else {
            await model.download(c.name)
            if model.settings?.model == c.name { next() }
        }
    }
}

struct ModelCard: View {
    let info: E.ModelInfo
    let selected: Bool
    let active: Bool
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: selected ? "largecircle.fill.circle" : "circle")
                .foregroundStyle(selected ? Color.accentColor : .secondary).font(.title3)
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(modelTitle(info.name)).font(.headline)
                    if info.recommended { Tag(text: L("Önerilen", "Recommended"), color: .accentColor) }
                    if active { Tag(text: L("Kullanılıyor", "In use"), color: .green) }
                    else if info.downloaded && !info.included { Tag(text: L("İndirildi", "Downloaded"), color: .secondary) }
                }
                Text(modelDetail(info)).font(.callout).foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 10).fill(Color.primary.opacity(selected ? 0.06 : 0.025)))
        .overlay(RoundedRectangle(cornerRadius: 10).stroke(selected ? Color.accentColor : Color.primary.opacity(0.08),
                                                           lineWidth: selected ? 1.5 : 1))
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }
}

struct Tag: View {
    let text: String
    let color: Color
    var body: some View {
        Text(text).font(.caption.weight(.medium)).padding(.horizontal, 6).padding(.vertical, 2)
            .background(Capsule().fill(color.opacity(0.15))).foregroundStyle(color)
    }
}

// MARK: 4. Connect Claude
struct ClaudeStep: View {
    @EnvironmentObject var model: AppModel
    let next: () -> Void

    var body: some View {
        StepFrame(icon: "link",
                  title: L("Claude'a bağlayın", "Connect Claude"),
                  subtitle: L("İsterseniz Claude belgelerinizi Katip üzerinden açar: Claude yalnızca maskeli metni görür. İsteğe bağlıdır; sonra da yapabilirsiniz.",
                              "If you like, Claude can open your documents through Katip: Claude only ever sees the masked text. Optional; you can do it later."),
                  button: L("Devam", "Continue"),
                  secondary: (L("Daha sonra", "Later"), { next() }),
                  action: next) {
            VStack(alignment: .leading, spacing: 14) {
                FolderRow()
                Divider()
                ClaudeRows()
                if let note = model.note {
                    Text(note).font(.callout).foregroundStyle(.orange).fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .task { await model.refreshClaude() }
    }
}

/// The folder Claude may search, and Downloads.
struct FolderRow: View {
    @EnvironmentObject var model: AppModel
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(L("Claude'un belge arayabileceği yerler", "Where Claude may look for documents")).font(.headline)
            HStack {
                Image(systemName: "folder").foregroundStyle(.secondary)
                Text(prettyPath(model.settings?.documentsFolder ?? "")).lineLimit(1).truncationMode(.middle)
                Spacer()
                Button(L("Değiştir…", "Change…")) { pick() }
                Button { reveal(model.settings?.documentsFolder, create: false) } label: { Image(systemName: "arrow.up.forward.square") }
                    .buttonStyle(.borderless).help(L("Finder'da göster", "Show in Finder"))
            }
            Toggle(L("İndirilenler klasörü de (UYAP ve e-posta ekleri)", "Also the Downloads folder (UYAP and e-mail attachments)"),
                   isOn: Binding(get: { model.settings?.includeDownloads ?? true },
                                 set: { v in Task { await model.save(["include_downloads": v]) } }))
            Text(L("Belgeler kopyalanmaz; olduğu yerde kalır. Değişiklikler birkaç saniyede Claude'a da geçer.",
                   "Nothing is copied; documents stay where they are. Changes reach Claude within seconds."))
                .font(.callout).foregroundStyle(.secondary)
        }
    }

    func pick() {
        let p = NSOpenPanel()
        p.canChooseDirectories = true
        p.canChooseFiles = false
        p.canCreateDirectories = true
        p.prompt = L("Seç", "Choose")
        if let cur = model.settings?.documentsFolder { p.directoryURL = URL(fileURLWithPath: cur) }
        NSApp.activate(ignoringOtherApps: true)
        if p.runModal() == .OK, let u = p.url {
            Task { await model.save(["documents_folder": u.path]) }  // Claude's Katip follows the settings live
        }
    }
}

func prettyPath(_ p: String) -> String {
    let home = FileManager.default.homeDirectoryForCurrentUser.path
    return p.hasPrefix(home) ? "~" + p.dropFirst(home.count) : p
}

struct ClaudeRows: View {
    @EnvironmentObject var model: AppModel
    @State private var working: String?
    @State private var restartHint = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let c = model.claude {
                AppRow(icon: "macwindow", appPath: Apps.claude, name: "Claude Desktop",
                       state: c.desktop.stale ? L("Katip taşınmış; yeniden bağlayın.", "Katip has moved; connect again.")
                           : c.desktop.extension && !c.desktop.connected
                           ? L("Katip uzantısı zaten kurulu: ek bir şey gerekmez.", "The Katip extension is already installed: nothing else needed.")
                           : c.desktop.brokenConfig ? L("Claude'un ayar dosyası okunamıyor; Katip ona dokunmadı.", "Claude's settings file can't be read; Katip left it alone.")
                           : !c.desktop.installed ? L("Bu Mac'te kurulu değil.", "Not installed on this Mac.")
                           : c.desktop.connected ? L("Bağlı.", "Connected.") : L("Bağlı değil.", "Not connected."),
                       connected: c.desktop.connected,
                       available: c.desktop.installed && !c.desktop.brokenConfig && !(c.desktop.extension && !c.desktop.connected),
                       working: working == "desktop") { on in
                    working = "desktop"
                    if let r = await model.connect("desktop", on: on), r.restartNeeded { restartHint = true }
                    working = nil
                }
                AppRow(icon: "terminal", appPath: Apps.terminal, name: "Claude Code",
                       state: !c.code.installed ? L("Bu Mac'te kurulu değil.", "Not installed on this Mac.")
                           : c.code.stale ? L("Katip taşınmış; yeniden bağlayın.", "Katip has moved; connect again.")
                           : c.code.connected ? L("Bağlı (tüm projelerde).", "Connected (in every project).") : L("Bağlı değil.", "Not connected."),
                       connected: c.code.connected, available: c.code.installed, working: working == "code") { on in
                    working = "code"
                    _ = await model.connect("code", on: on)
                    working = nil
                }
                if restartHint {
                    Label(L("Claude Desktop'tan çıkıp yeniden açın; Katip araçları sohbet kutusundaki araç menüsünde görünür.",
                            "Quit and reopen Claude Desktop; Katip's tools then show in the chat box's tools menu."),
                          systemImage: "arrow.clockwise").font(.callout).foregroundStyle(.secondary)
                }
            } else if let err = model.claudeError {
                HStack {
                    Label(err, systemImage: "exclamationmark.triangle").foregroundStyle(.orange)
                    Spacer()
                    Button(L("Yeniden dene", "Try again")) { Task { await model.refreshClaude() } }
                }
            } else {
                HStack { ProgressView().controlSize(.small); Text(L("Claude aranıyor…", "Looking for Claude…")) }
            }
        }
    }
}

struct AppRow: View {
    let icon: String
    var appPath: String? = nil
    let name: String
    let state: String
    let connected: Bool
    let available: Bool
    let working: Bool
    let change: (Bool) async -> Void

    var body: some View {
        HStack(spacing: 12) {
            if let appPath { AppIcon(path: appPath, fallback: icon, size: 34) }
            else { Image(systemName: icon).font(.title2).frame(width: 30).foregroundStyle(.secondary) }
            VStack(alignment: .leading, spacing: 2) {
                Text(name).font(.headline)
                HStack(spacing: 5) {
                    if connected { Circle().fill(.green).frame(width: 7, height: 7) }
                    Text(state).font(.callout).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                }
            }
            Spacer()
            if working {
                ProgressView().controlSize(.small)
            } else if connected {
                Button(L("Bağlantıyı kes", "Disconnect")) { Task { await change(false) } }
            } else if available {
                Button(L("Bağla", "Connect")) { Task { await change(true) } }.buttonStyle(.borderedProminent)
            }
        }
    }
}

// MARK: 5. Ready
struct ReadyStep: View {
    @EnvironmentObject var model: AppModel
    @State private var masked: String?
    @State private var restored: String?

    var body: some View {
        StepFrame(icon: "checkmark.seal",
                  title: L("Hazırsınız", "You're set"),
                  subtitle: L("İşte Katip'in yaptığı: soldaki metin yapay zekâya gider, sağdaki cevabınıza geri döner.",
                              "Here's what Katip does: the left text goes to the AI, the right is what comes back into your answer."),
                  button: L("Katip'i kullanmaya başla", "Start using Katip"),
                  action: { Task { await finish() } }) {
            if let note = model.note { Text(note).font(.callout).foregroundStyle(.orange) }
            HStack(alignment: .top, spacing: 12) {
                SampleBox(title: L("Yapay zekânın gördüğü", "What the AI sees"), text: masked)
                Image(systemName: "arrow.right").foregroundStyle(.secondary).padding(.top, 34)
                SampleBox(title: L("Size dönen", "What you get back"), text: restored)
            }
            VStack(alignment: .leading, spacing: 8) {
                Label(L("Menü çubuğundaki kalkan simgesinden panodaki metni tek tıkla maskeleyebilirsiniz.",
                        "Use the shield in the menu bar to mask the clipboard in one click."), systemImage: "menubar.rectangle")
                Label(L("Belge maskelemek ve cevabı geri çevirmek için Katip penceresini kullanın.",
                        "Use the Katip window to mask documents and turn answers back."), systemImage: "macwindow")
            }
            .font(.callout).foregroundStyle(.secondary)
        }
        .task {
            if let m = try? await model.client.mask(SampleText.sentence, matter: SampleText.matter) {
                masked = m.maskedText
                restored = (try? await model.client.restore(m.maskedText, matter: SampleText.matter))?.text
            }
        }
    }

    func finish() async {
        struct Done: Decodable { let deleted: Bool }
        let _: Done? = try? await model.client.call("/v1/forget", body: ["matter": SampleText.matter])
        await model.save(["first_run_done": true])
        await model.refreshMatters()
    }
}

struct SampleBox: View {
    let title: String
    let text: String?
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.caption.weight(.semibold)).foregroundStyle(.secondary)
            Text(text ?? "…").font(.system(.callout, design: .serif)).textSelection(.enabled)
                .frame(maxWidth: .infinity, minHeight: 90, alignment: .topLeading)
                .padding(10)
                .background(RoundedRectangle(cornerRadius: 8).fill(Color.primary.opacity(0.04)))
        }
    }
}
