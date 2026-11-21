import SwiftUI
import UniformTypeIdentifiers

struct HomeView: View {
    @Binding var incoming: URL?
    @EnvironmentObject private var engine: MaskEngine
    @EnvironmentObject private var store: SessionStore
    @AppStorage("profile") private var profile = "ai"
    @AppStorage("model") private var model: KatipModel = .mini

    @State private var importing = false
    @State private var scanning = false
    @State private var busy: String?
    @State private var error: String?
    @State private var path: [MaskSession] = []
    @State private var showSettings = false
    @State private var showLetter = false

    var body: some View {
        NavigationStack(path: $path) {
            List {
                Section {
                    StepsHeader()
                }
                .listRowBackground(Color.clear)
                .listRowInsets(EdgeInsets())

                Section {
                    Picker(L("Ne için maskeliyorsunuz?", "What is it for?"), selection: $profile) {
                        ForEach(ProfileSpec.order, id: \.self) { Text(ProfileSpec.shared.title($0)).tag($0) }
                    }
                    .pickerStyle(.segmented)
                    .listRowSeparator(.hidden)
                    Text(LegalInfo.profile(profile).useFor)
                        .font(.footnote).foregroundStyle(.secondary)
                    DisclosureGroup(L("Neyi maskeler, neden?", "What it masks, and why")) {
                        ProfileDetails(profile: profile)
                    }
                } header: {
                    Text(L("1 · Ne için?", "1 · What for?"))
                }

                Section {
                    Button { importing = true } label: {
                        Label(L("Belge seç", "Choose a document"), systemImage: "doc.badge.plus")
                    }
                    if DocumentScanner.isAvailable {
                        Button { scanning = true } label: {
                            Label(L("Kâğıt belgeyi tara", "Scan a paper document"), systemImage: "doc.viewfinder")
                        }
                    }
                    PasteButton(payloadType: String.self) { texts in
                        guard let t = texts.first else { return }
                        Task { await run(ReadResult(text: t, title: Masking.defaultTitle(.paste), ocr: false), source: .paste) }
                    }
                    .labelStyle(.titleAndIcon)
                    Button { Task { await sample() } } label: {
                        Label(L("Örnek dilekçeyle dene", "Try a sample petition"), systemImage: "wand.and.stars")
                    }
                } header: {
                    Text(L("2 · Belge", "2 · Document"))
                } footer: {
                    Text(L("PDF, Word (.docx), UYAP (.udf), metin veya fotoğraf. Belge bu telefonda okunur ve maskelenir; hiçbir yere yüklenmez.",
                           "PDF, Word (.docx), UYAP (.udf), text or photo. The document is read and masked on this phone and is not uploaded anywhere."))
                }

                Section {
                    Button { showLetter = true } label: {
                        Label(L("Hollanda'dan gelen bir mektubu anla", "Understand a letter from the Netherlands"), systemImage: "envelope.open")
                    }
                } header: {
                    Text(L("Test · Mektup açıklaması", "Test · Letter explained"))
                } footer: {
                    Text(L("IND, belediye veya işveren mektubu: türü, süresi ve kaynağı, sade bir açıklama ve yardım alabileceğiniz yerler. Hukuki danışmanlık değildir.",
                           "A letter from the IND, gemeente or employer: its type, deadline and source, a plain explanation, and where to get help. Not legal advice."))
                }

                if !store.sessions.isEmpty {
                    Section {
                        ForEach(store.sessions) { s in
                            NavigationLink(value: s) { SessionRow(session: s) }
                        }
                        .onDelete { idx in idx.map { store.sessions[$0].id }.forEach(store.delete) }
                    } header: {
                        Text(L("Son belgeler", "Recent documents"))
                    } footer: {
                        Text(L("Belgeler ve eşleme tabloları şifreli olarak yalnızca bu telefonda tutulur ve \(SessionStore.keepDays) gün sonra silinir.",
                               "Documents and their maps are kept encrypted on this phone only and deleted after \(SessionStore.keepDays) days."))
                    }
                }
            }
            .navigationTitle("Katip")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { showSettings = true } label: { Image(systemName: "gearshape") }
                        .accessibilityLabel(L("Ayarlar", "Settings"))
                }
            }
            .navigationDestination(for: MaskSession.self) { SessionView(sessionID: $0.id) }
            .fileImporter(isPresented: $importing, allowedContentTypes: DocumentReader.importable) { result in
                if case let .success(url) = result { Task { await open(url) } }
            }
            .fullScreenCover(isPresented: $scanning) {
                DocumentScanner(onDone: { pages in
                    scanning = false
                    Task { await scanned(pages) }
                }, onCancel: { scanning = false })
                .ignoresSafeArea()
            }
            .sheet(isPresented: $showSettings) { SettingsView() }
            .fullScreenCover(isPresented: $showLetter) {
                LetterView()
                    .environmentObject(engine)
                    .tint(Theme.accent)
            }
            .overlay { if let busy { BusyOverlay(text: busy) } }
            .alert(L("Olmadı", "Something went wrong"), isPresented: Binding(get: { error != nil }, set: { if !$0 { error = nil } })) {
                Button("OK", role: .cancel) {}
            } message: { Text(error ?? "") }
            .onChange(of: incoming) { _, url in
                guard let url else { return }
                incoming = nil
                Task { await open(url) }
            }
            .task { await engine.warm(model: model) }
        }
    }

    private func open(_ url: URL) async {
        busy = L("Belge okunuyor…", "Reading the document…")
        do {
            let r = try await DocumentReader.read(url: url, engine: engine)
            await run(r, source: .file)
        } catch {
            busy = nil
            self.error = error.localizedDescription
        }
    }

    private func scanned(_ pages: [CGImage]) async {
        guard !pages.isEmpty else { return }
        busy = L("Metin tanınıyor…", "Recognising text…")
        do {
            let (t, note) = try await DocumentReader.ocr(pages)
            await run(ReadResult(text: t, title: Masking.defaultTitle(.scan), ocr: true, note: note), source: .scan)
        } catch {
            busy = nil
            self.error = error.localizedDescription
        }
    }

    private func sample() async {
        guard let url = Bundle.main.url(forResource: "ornek_dilekce", withExtension: "txt", subdirectory: "Samples")
            ?? Bundle.main.url(forResource: "ornek_dilekce", withExtension: "txt"),
            let t = try? String(contentsOf: url) else { return }
        await run(ReadResult(text: t, title: Masking.defaultTitle(.sample), ocr: false), source: .sample)
    }

    private func run(_ r: ReadResult, source: MaskSession.Source) async {
        busy = L("Bu telefonda maskeleniyor…", "Masking on this phone…")
        defer { busy = nil }
        do {
            let s = try await Masking.start(r, source: source, profile: profile, model: model, engine: engine, store: store)
            path = [s]
        } catch {
            self.error = error.localizedDescription
        }
    }
}

private struct StepsHeader: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(L("Belgeyi bu telefonda maskeleyin, yapay zekâya yalnızca maskeli metni gönderin, cevaptaki isimleri geri koyun.",
                   "Mask the document on this phone, send only the masked text to the AI, then put the names back into its answer."))
                .font(.callout)
            HStack(spacing: 8) {
                StepChip(n: "1", text: L("Maskele", "Mask"))
                Image(systemName: "chevron.right").font(.caption2).foregroundStyle(.secondary)
                StepChip(n: "2", text: L("Gönder", "Send"))
                Image(systemName: "chevron.right").font(.caption2).foregroundStyle(.secondary)
                StepChip(n: "3", text: L("Geri koy", "Restore"))
            }
        }
        .padding(.vertical, 8)
        .padding(.horizontal, 20)
    }
}

struct StepChip: View {
    let n: String
    let text: String
    var body: some View {
        HStack(spacing: 6) {
            Text(n).font(.caption.bold()).frame(width: 20, height: 20)
                .background(Theme.lime, in: Circle()).foregroundStyle(Theme.ink)
            Text(text).font(.subheadline.weight(.medium))
        }
    }
}

private struct SessionRow: View {
    let session: MaskSession
    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(session.title).lineLimit(1)
            Text("\(ProfileSpec.shared.title(session.profile)) · \(L("\(session.spans.count) değer maskelendi", "\(session.spans.count) values masked")) · \(session.created.formatted(.relative(presentation: .named)))")
                .font(.caption).foregroundStyle(.secondary).lineLimit(1)
        }
    }
}

struct BusyOverlay: View {
    let text: String
    var body: some View {
        ZStack {
            Color.black.opacity(0.25).ignoresSafeArea()
            VStack(spacing: 12) {
                ProgressView()
                Text(text).font(.callout)
            }
            .padding(24)
            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
        }
    }
}
