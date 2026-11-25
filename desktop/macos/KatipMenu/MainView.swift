import AppKit
import SwiftUI
import UniformTypeIdentifiers

/// The Katip window: first run until it's done, then the everyday screens.
struct RootView: View {
    @EnvironmentObject var model: AppModel
    @State private var loaded = false
    @State private var loadError: String?

    var body: some View {
        Group {
            if let s = model.settings, s.firstRunDone {
                MainView()
            } else if model.settings != nil || loadError != nil {
                OnboardingView()
            } else {
                VStack(spacing: 10) {
                    ProgressView()
                    Text(L("Katip açılıyor…", "Opening Katip…")).foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .frame(minWidth: 760, minHeight: 560)
        .task {
            guard !loaded else { return }
            loaded = true
            do { try await model.loadAll() } catch { loadError = error.localizedDescription }
        }
    }
}

enum Screen: String, CaseIterable, Identifiable {
    case mask, restore, cases, connections, settings
    var id: String { rawValue }
    var title: String {
        switch self {
        case .mask: return L("Maskele", "Mask")
        case .restore: return L("Geri çevir", "Restore")
        case .cases: return L("Davalar", "Cases")
        case .connections: return L("Bağlantılar", "Connections")
        case .settings: return L("Ayarlar", "Settings")
        }
    }
    var icon: String {
        switch self {
        case .mask: return "eye.slash"
        case .restore: return "arrow.uturn.backward"
        case .cases: return "folder"
        case .connections: return "link"
        case .settings: return "gearshape"
        }
    }
}

struct MainView: View {
    @EnvironmentObject var model: AppModel
    @State private var section: Screen = .mask

    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 8) {
                    Image(systemName: "checkmark.shield.fill").foregroundStyle(Color.accentColor)
                    Text("Katip").font(.title3.weight(.semibold))
                }
                .padding(.horizontal, 10).padding(.bottom, 14).padding(.top, 4)
                ForEach(Screen.allCases) { s in
                    SidebarItem(screen: s, selected: section == s) { section = s }
                }
                Spacer()
                EngineFooter().padding(.horizontal, 10)
            }
            .padding(12)
            .frame(width: 200)
            .background(Color.primary.opacity(0.035))
            Divider()
            ZStack(alignment: .topLeading) {  // every screen stays alive, so switching never loses your text
                MaskScreen().screen(section == .mask)
                RestoreScreen().screen(section == .restore)
                CasesScreen().screen(section == .cases)
                ConnectionsScreen().screen(section == .connections)
                SettingsScreen().screen(section == .settings)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
        .onReceive(NotificationCenter.default.publisher(for: .katipShow)) { n in
            if let s = n.object as? Screen { section = s }
        }
    }
}

extension View {
    func screen(_ shown: Bool) -> some View {
        opacity(shown ? 1 : 0).allowsHitTesting(shown).accessibilityHidden(!shown)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}

struct SidebarItem: View {
    let screen: Screen
    let selected: Bool
    let action: () -> Void
    @State private var hover = false
    var body: some View {
        Button(action: action) {
            Label(screen.title, systemImage: screen.icon)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.vertical, 6).padding(.horizontal, 10)
                .background(RoundedRectangle(cornerRadius: 7).fill(selected ? Color.accentColor.opacity(0.16)
                                                                   : hover ? Color.primary.opacity(0.05) : .clear))
                .foregroundStyle(selected ? Color.accentColor : Color.primary)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hover = $0 }
        .accessibilityAddTraits(selected ? .isSelected : [])
    }
}

extension Notification.Name {
    static let katipShow = Notification.Name("katip.show")
    static let katipTourStep = Notification.Name("katip.tourStep")
    static let katipTourMask = Notification.Name("katip.tourMask")
}

struct EngineFooter: View {
    @EnvironmentObject var model: AppModel
    var body: some View {
        HStack(spacing: 6) {
            Circle().fill(model.running ? Color.green : Color.secondary.opacity(0.5)).frame(width: 7, height: 7)
            Text(model.running ? L("Motor çalışıyor", "Engine running") : L("Motor beklemede", "Engine idle"))
                .font(.caption).foregroundStyle(.secondary)
            Spacer()
        }
        .help(model.running ? (model.status?.model ?? "") : L("İlk işte kendiliğinden başlar.", "Starts by itself on the next task."))
    }
}

// MARK: shared pieces
struct ScreenHeader: View {
    let title: String
    let subtitle: String
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.system(size: 22, weight: .semibold))
            Text(subtitle).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
        }
    }
}

struct TextPane: View {
    let title: String
    @Binding var text: String
    var editable = true
    var placeholder = ""
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.caption.weight(.semibold)).foregroundStyle(.secondary)
            ZStack(alignment: .topLeading) {
                if editable {
                    TextEditor(text: $text).font(.system(.body, design: .serif)).scrollContentBackground(.hidden)
                } else {
                    ScrollView { Text(text).font(.system(.body, design: .serif)).textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .topLeading) }
                }
                if text.isEmpty && !placeholder.isEmpty {
                    Text(placeholder).foregroundStyle(.tertiary).padding(.top, editable ? 0 : 0).padding(.leading, 5)
                        .allowsHitTesting(false)
                }
            }
            .padding(10)
            .background(RoundedRectangle(cornerRadius: 8).fill(Color(nsColor: .textBackgroundColor)))
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.primary.opacity(0.1)))
        }
    }
}

func copyToClipboard(_ s: String) {
    NSPasteboard.general.clearContents()
    NSPasteboard.general.setString(s, forType: .string)
}

func saveText(_ s: String, name: String) {
    let p = NSSavePanel()
    p.nameFieldStringValue = name
    p.allowedContentTypes = [.plainText]
    NSApp.activate(ignoringOtherApps: true)
    if p.runModal() == .OK, let u = p.url { try? s.write(to: u, atomically: true, encoding: .utf8) }
}

struct CaseField: View {
    @Binding var matter: String
    var body: some View {
        HStack(spacing: 6) {
            Text(L("Dava", "Case")).foregroundStyle(.secondary)
            TextField(L("ör. 2026/123", "e.g. 2026/123"), text: $matter)
                .textFieldStyle(.roundedBorder).frame(width: 160)
                .help(L("Aynı davanın belgeleri aynı yer tutucuları alır. Müvekkil adı değil, dosya numarası yazın.",
                        "Documents of one case share placeholders. Use a file number, not a client's name."))
        }
    }
}

func matterOrDefault(_ s: String) -> String {
    let t = s.trimmingCharacters(in: .whitespaces)
    return t.isEmpty ? "default" : t
}

// MARK: Mask
struct MaskScreen: View {
    @EnvironmentObject var model: AppModel
    @State private var input = ""
    @State private var output = ""
    @State private var placeholders: [String] = []
    @State private var profile: Profile = .ai
    @State private var matter = ""
    @State private var working = false
    @State private var error: String?
    @State private var dropping = false
    @State private var source: String?
    @State private var copied = false

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            ScreenHeader(title: L("Maskele", "Mask"),
                         subtitle: L("Metni yapıştırın ya da bir belgeyi buraya sürükleyin. Kişisel veriler yer tutucuya döner; gerçek değerler bu Mac'te kalır.",
                                     "Paste text or drag a document here. Personal data becomes placeholders; the real values stay on this Mac."))
            HStack(spacing: 14) {
                Picker(L("Profil", "Profile"), selection: $profile) {
                    ForEach(Profile.allCases) { p in Text(p.title).tag(p) }
                }
                .frame(width: 270)
                .help(profile.detail)
                CaseField(matter: $matter)
                Spacer()
            }
            Text(profile.detail).font(.callout).foregroundStyle(.secondary)
            HStack(spacing: 14) {
                VStack(spacing: 8) {
                    TextPane(title: source.map { L("Belge: \($0)", "Document: \($0)") } ?? L("Orijinal", "Original"),
                             text: $input,
                             placeholder: L("Metni buraya yapıştırın ya da PDF, Word, UDF veya fotoğraf sürükleyin…",
                                            "Paste text here, or drop a PDF, Word, UDF or photo…"))
                    HStack {
                        Button(L("Belge seç…", "Choose document…")) { pickFile() }
                        Spacer()
                        Button(L("Maskele", "Mask")) { Task { await maskText() } }
                            .keyboardShortcut(.return, modifiers: .command)
                            .buttonStyle(.borderedProminent)
                            .disabled(input.isEmpty || working || source != nil)
                    }
                }
                VStack(spacing: 8) {
                    TextPane(title: L("Maskeli: yapay zekâya bu gider", "Masked: this is what goes to the AI"),
                             text: $output, editable: false,
                             placeholder: working ? L("Maskeleniyor…", "Masking…") : "")
                    HStack {
                        if !placeholders.isEmpty {
                            Text(summarize(placeholders)).font(.caption).foregroundStyle(.secondary).lineLimit(2)
                        }
                        Spacer()
                        Button(copied ? L("Kopyalandı", "Copied") : L("Kopyala", "Copy")) {
                            copyToClipboard(output); copied = true
                            Task { try? await Task.sleep(nanoseconds: 1_500_000_000); copied = false }
                        }
                        .disabled(output.isEmpty)
                        Button(L("Kaydet…", "Save…")) { saveText(output, name: L("maskeli.txt", "masked.txt")) }.disabled(output.isEmpty)
                    }
                }
            }
            if working { ProgressView().controlSize(.small) }
            if let error { Label(error, systemImage: "exclamationmark.triangle").foregroundStyle(.orange) }
            Label(L("Göndermeden önce maskeli metne bir göz atın: Katip bir değeri kaçırabilir.",
                    "Glance over the masked text before you send it: Katip can miss a value."),
                  systemImage: "eye").font(.callout).foregroundStyle(.secondary)
        }
        .padding(22)
        .overlay {
            if dropping {
                RoundedRectangle(cornerRadius: 14).stroke(Color.accentColor, style: StrokeStyle(lineWidth: 3, dash: [8]))
                    .background(Color.accentColor.opacity(0.06)).padding(8)
                    .overlay(Text(L("Bırakın, maskeleyeyim", "Drop to mask")).font(.title2.weight(.medium)))
            }
        }
        .dropDestination(for: URL.self) { urls, _ in
            guard let u = urls.first else { return false }
            Task { await maskFile(u) }
            return true
        } isTargeted: { dropping = $0 }
        .onChange(of: input) { _, new in if new.isEmpty { source = nil } }
        .onReceive(NotificationCenter.default.publisher(for: .katipTourMask)) { n in
            if let t = n.object as? String { input = t; Task { await maskText() } }
        }
        .onAppear { profile = Profile(rawValue: model.settings?.defaultProfile ?? "ai") ?? .ai }
    }

    func pickFile() {
        let p = NSOpenPanel()
        p.allowedContentTypes = [.pdf, .plainText, .rtf, .image, UTType(filenameExtension: "docx")!, UTType(filenameExtension: "udf") ?? .data, .data]
        p.allowsMultipleSelection = false
        NSApp.activate(ignoringOtherApps: true)
        if p.runModal() == .OK, let u = p.url { Task { await maskFile(u) } }
    }

    func maskText() async {
        working = true; error = nil
        defer { working = false }
        do {
            let m = try await model.client.mask(input, profile: profile.rawValue, matter: matterOrDefault(matter))
            output = m.maskedText; placeholders = m.placeholders
        } catch { self.error = error.localizedDescription }
        await model.refreshMatters()
    }

    func maskFile(_ u: URL) async {
        working = true; error = nil; output = ""; placeholders = []
        defer { working = false }
        do {
            let m = try await model.client.maskFile(u, profile: profile.rawValue, matter: matterOrDefault(matter))
            source = m.fileName ?? u.lastPathComponent
            input = L("(Belge bu Mac'te okundu; orijinali burada gösterilmez.)", "(The document was read on this Mac; the original isn't shown here.)")
            output = m.maskedText; placeholders = m.placeholders
        } catch { self.error = error.localizedDescription }
        await model.refreshMatters()
    }
}

// MARK: Restore
struct RestoreScreen: View {
    @EnvironmentObject var model: AppModel
    @State private var input = ""
    @State private var output = ""
    @State private var matter = ""
    @State private var count: Int?
    @State private var error: String?
    @State private var copied = false

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            ScreenHeader(title: L("Geri çevir", "Restore"),
                         subtitle: L("Yapay zekânın cevabını yapıştırın. [AD SOYAD-1] gibi yer tutucular gerçek değerlere döner; bu metni yapay zekâya geri vermeyin.",
                                     "Paste the AI's answer. Placeholders like [AD SOYAD-1] turn back into the real values; don't give this text back to an AI."))
            HStack {
                CaseField(matter: $matter)
                if !model.matters.isEmpty {
                    Menu(L("Son davalar", "Recent cases")) {
                        ForEach(model.matters.filter { $0.matter != SampleText.matter }.prefix(10)) { m in
                            Button(m.matter == "default" ? L("Genel", "General") : m.matter) { matter = m.matter == "default" ? "" : m.matter }
                        }
                    }
                    .frame(width: 150)
                }
                Spacer()
            }
            HStack(spacing: 14) {
                VStack(spacing: 8) {
                    TextPane(title: L("Yapay zekânın cevabı", "The AI's answer"), text: $input,
                             placeholder: L("Cevabı buraya yapıştırın…", "Paste the answer here…"))
                    HStack {
                        Button(L("Panodan yapıştır", "Paste from clipboard")) { input = NSPasteboard.general.string(forType: .string) ?? "" }
                        Spacer()
                        Button(L("Geri çevir", "Restore")) { Task { await restore() } }
                            .keyboardShortcut(.return, modifiers: .command)
                            .buttonStyle(.borderedProminent).disabled(input.isEmpty)
                    }
                }
                VStack(spacing: 8) {
                    TextPane(title: L("Gerçek adlarla", "With the real names"), text: $output, editable: false)
                    HStack {
                        if let count { Text(L("\(count) değer geri kondu", "\(count) values put back")).font(.caption).foregroundStyle(.secondary) }
                        Spacer()
                        Button(copied ? L("Kopyalandı", "Copied") : L("Kopyala", "Copy")) {
                            copyToClipboard(output); copied = true
                            Task { try? await Task.sleep(nanoseconds: 1_500_000_000); copied = false }
                        }.disabled(output.isEmpty)
                        Button(L("Kaydet…", "Save…")) { saveText(output, name: L("cevap.txt", "answer.txt")) }.disabled(output.isEmpty)
                    }
                }
            }
            if let error { Label(error, systemImage: "exclamationmark.triangle").foregroundStyle(.orange) }
            if count == 0 {
                Label(L("Hiç yer tutucu bulunamadı. Doğru davayı seçtiniz mi?", "No placeholders found. Is this the right case?"),
                      systemImage: "questionmark.circle").foregroundStyle(.orange)
            }
        }
        .padding(22)
    }

    func restore() async {
        error = nil
        do {
            let r = try await model.client.restore(input, matter: matterOrDefault(matter))
            output = r.text; count = r.placeholdersRestored
        } catch { self.error = error.localizedDescription }
    }
}

// MARK: Cases
struct CasesScreen: View {
    @EnvironmentObject var model: AppModel
    @State private var confirm: E.Matter?
    var visible: [E.Matter] { model.matters.filter { $0.matter != SampleText.matter } }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            ScreenHeader(title: L("Davalar", "Cases"),
                         subtitle: L("Her dava için adları geri getiren anahtar bu Mac'te şifreli durur ve son kullanımdan bir süre sonra kendiliğinden silinir.",
                                     "Each case's key, which brings names back, is kept encrypted on this Mac and deletes itself a while after last use."))
            if visible.isEmpty {
                ContentUnavailableView(L("Henüz dava yok", "No cases yet"), systemImage: "folder",
                                       description: Text(L("Bir belge maskelediğinizde burada görünür.", "A case shows here once you mask a document.")))
            } else {
                Table(visible) {
                    TableColumn(L("Dava", "Case")) { m in Text(m.matter == "default" ? L("Genel", "General") : m.matter) }
                    TableColumn(L("Son kullanım", "Last used")) { m in Text(Date(timeIntervalSince1970: m.lastUsed), style: .date) }
                    TableColumn(L("Silinecek", "Deletes on")) { m in Text(Date(timeIntervalSince1970: m.expires), style: .date) }
                    TableColumn("") { m in
                        Button(L("Unut…", "Forget…")) { confirm = m }.buttonStyle(.borderless).foregroundStyle(.red)
                    }.width(80)
                }
            }
        }
        .padding(22)
        .task { await model.refreshMatters() }
        .confirmationDialog(L("Bu davanın anahtarı silinsin mi?", "Delete this case's key?"),
                            isPresented: Binding(get: { confirm != nil }, set: { if !$0 { confirm = nil } }),
                            presenting: confirm) { m in
            Button(L("Anahtarı sil", "Delete key"), role: .destructive) { Task { await model.forget(m.matter) } }
        } message: { _ in
            Text(L("Bu davanın maskeli metinlerindeki adlar artık geri getirilemez. Bu geri alınamaz.",
                   "Names in this case's masked texts can no longer be brought back. This can't be undone."))
        }
    }
}

// MARK: Connections
struct ConnectionsScreen: View {
    @EnvironmentObject var model: AppModel
    var body: some View {
        Form {
            Section {
                ClaudeRows()
            } header: { Text("Claude") } footer: {
                Text(L("Claude belgeleri Katip üzerinden açar ve yalnızca maskeli metni görür.",
                       "Claude opens documents through Katip and only ever sees the masked text.")).foregroundStyle(.secondary)
            }
            Section(L("Belge klasörü", "Documents folder")) { FolderRow() }
            Section {
                Toggle(L("Emsal karar arama (Yargıtay, Danıştay)", "Precedent search (Yargıtay, Danıştay)"),
                       isOn: Binding(get: { model.settings?.emsalOnline ?? false },
                                     set: { v in Task { await model.save(["emsal_online": v]) } }))
                Text(L("Açıkken yalnızca arama kelimeleri bedesten.adalet.gov.tr'ye gider, belge metni asla gitmez.",
                       "When on, only search keywords go to bedesten.adalet.gov.tr, never document text."))
                    .font(.callout).foregroundStyle(.secondary)
                LabeledContent(L("Mevzuat", "Legislation")) { Text(L("Bu Mac'te, çevrimdışı", "On this Mac, offline")).foregroundStyle(.secondary) }
                LabeledContent(L("Resmî Gazete ve ilanlar", "Official Gazette and notices")) { Tag(text: L("Yakında", "Coming soon"), color: .secondary) }
            } header: { Text(L("Kaynaklar", "Sources")) }
            if let note = model.note { Text(note).foregroundStyle(.orange) }
        }
        .formStyle(.grouped)
        .task { await model.refreshClaude() }
    }
}

// MARK: Settings
struct SettingsScreen: View {
    @EnvironmentObject var model: AppModel
    @State private var downloading: String?

    var body: some View {
        Form {
            Section(L("Ad tanıma modeli", "Name model")) {
                ForEach(model.models?.models ?? []) { m in
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            HStack(spacing: 6) {
                                Text(modelTitle(m.name))
                                if m.recommended { Tag(text: L("Önerilen", "Recommended"), color: .accentColor) }
                            }
                            Text(modelDetail(m)).font(.callout).foregroundStyle(.secondary)
                        }
                        Spacer()
                        if m.name == model.settings?.model {
                            Label(L("Kullanılıyor", "In use"), systemImage: "checkmark").foregroundStyle(.green)
                        } else if downloading == m.name, let d = model.models?.download {
                            ProgressView(value: d.fraction).frame(width: 110)
                        } else if m.downloaded {
                            Button(L("Kullan", "Use")) { Task { await model.useModel(m.name) } }
                        } else {
                            Button(L("İndir", "Download")) {
                                downloading = m.name
                                Task { await model.download(m.name); downloading = nil }
                            }.disabled(downloading != nil)
                        }
                    }
                }
            }
            Section(L("Varsayılan profil", "Default profile")) {
                Picker(L("Yeni belgeler için", "For new documents"),
                       selection: Binding(get: { Profile(rawValue: model.settings?.defaultProfile ?? "ai") ?? .ai },
                                          set: { p in Task { await model.save(["default_profile": p.rawValue]) } })) {
                    ForEach(Profile.allCases) { p in Text(p.title).tag(p) }
                }
            }
            Section(L("Mac", "Mac")) {
                Toggle(L("Girişte Katip'i aç (menü çubuğunda)", "Open Katip at login (in the menu bar)"),
                       isOn: Binding(get: { model.loginItem }, set: { model.setLoginItem($0) }))
                LabeledContent(L("Motor", "Engine")) {
                    HStack {
                        Text(model.running ? L("Çalışıyor · \(Int(model.status?.rssPeakMb ?? 0)) MB", "Running · \(Int(model.status?.rssPeakMb ?? 0)) MB")
                                           : L("Beklemede", "Idle")).foregroundStyle(.secondary)
                        Button(model.running ? L("Durdur", "Stop") : L("Başlat", "Start")) { Task { await model.toggleEngine() } }
                    }
                }
                LabeledContent(L("Kayıt", "Log")) {
                    Button(L("Finder'da göster", "Show in Finder")) { NSWorkspace.shared.activateFileViewerSelecting([E.logURL]) }
                }
                LabeledContent(L("Kurulum", "Setup")) {
                    Button(L("Kurulumu yeniden göster", "Show setup again")) { Task { await model.save(["first_run_done": false]) } }
                }
            }
            if let note = model.note { Text(note).foregroundStyle(.orange) }
            Section {
                Text(L("Katip açık kaynaklıdır (AGPL-3.0). Sürüm \(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "")",
                       "Katip is open source (AGPL-3.0). Version \(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "")"))
                    .font(.callout).foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .task {
            if let m: E.Models = try? await model.client.call("/v1/models") { model.models = m }
            await model.refreshStatus()
        }
    }
}
