import SwiftUI
import UniformTypeIdentifiers

/// "Letter explained" (private test, same flow as docs/cep.html): a letter, mostly a Dutch one from the IND,
/// the gemeente or an employer, is read and masked on this phone. Katip names the kind of letter and the deadline
/// rule it knows, with the official source; the masked letter goes to ChatGPT or Claude for a plain explanation;
/// the names come back on the phone; and the screen ends with people who can help.
/// Nothing is stored: the letter and its map live only while this screen is open.
struct LetterView: View {
    @EnvironmentObject private var engine: MaskEngine
    @Environment(\.dismiss) private var dismiss
    @AppStorage("model") private var model: KatipModel = .mini
    @AppStorage("letterAnswerLang") private var answerLang = appIsTurkish ? "tr" : "en"

    @State private var info: LetterInfo?
    @State private var original: String?
    @State private var ocrNote: String?
    @State private var out: LetterOutput?
    @State private var type = "other"
    @State private var allow: [String] = []
    @State private var deny: [String] = []
    @State private var addTerm = ""
    @State private var prompt = ""
    @State private var sentTo: String?
    @State private var answer = ""
    @State private var restored: RestoreOutput?
    @State private var busy: String?
    @State private var error: String?
    @State private var importing = false
    @State private var scanning = false

    var body: some View {
        NavigationStack {
            List {
                if let out, let info { result(out, info) } else { input }
            }
            .navigationTitle(L("Mektup açıklaması", "Letter explained"))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) { Button(L("Kapat", "Close")) { dismiss() } }
                if out != nil {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button(L("Yeni mektup", "New letter")) { reset() }
                    }
                }
            }
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
            .overlay { if let busy { BusyOverlay(text: busy) } }
            .alert(L("Olmadı", "Something went wrong"), isPresented: Binding(get: { error != nil }, set: { if !$0 { error = nil } })) {
                Button("OK", role: .cancel) {}
            } message: { Text(error ?? "") }
            .task {
                if info == nil { info = try? await engine.letterInfo() }
            }
            .task(id: promptKey) { await makePrompt() }
        }
    }

    // MARK: input

    @ViewBuilder private var input: some View {
        Section {
            Text(L("Hollanda'dan gelen bir mektubu (IND, belediye, vergi dairesi, işveren, mahkeme) ekleyin. Katip mektubu bu telefonda okur ve maskeler, türünü ve bildiği süreyi kaynağıyla gösterir, sonra yapay zekâdan sade bir açıklama istersiniz.",
                   "Add a letter from the Netherlands (IND, gemeente, Belastingdienst, employer, court). Katip reads and masks it on this phone, shows its type and the deadline it knows with the source, then you ask the AI for a plain explanation."))
                .font(.callout)
            Label(L("Test sürümü. Hukuki danışmanlık değildir.", "Test version. Not legal advice."), systemImage: "testtube.2")
                .font(.footnote).foregroundStyle(.secondary)
        }
        Section {
            Button { importing = true } label: { Label(L("Mektup seç (PDF, foto, metin)", "Choose the letter (PDF, photo, text)"), systemImage: "doc.badge.plus") }
            if DocumentScanner.isAvailable {
                Button { scanning = true } label: { Label(L("Kâğıt mektubu tara", "Scan the paper letter"), systemImage: "doc.viewfinder") }
            }
            PasteButton(payloadType: String.self) { texts in
                guard let t = texts.first else { return }
                Task { await run(t, note: nil) }
            }
            .labelStyle(.titleAndIcon)
        } footer: {
            Text(L("Mektup ve eşleme tablosu yalnızca bu ekran açıkken telefonda tutulur, hiçbir yere kaydedilmez.",
                   "The letter and its map stay on this phone only while this screen is open and are not saved."))
        }
    }

    // MARK: result

    @ViewBuilder private func result(_ out: LetterOutput, _ info: LetterInfo) -> some View {
        let kind = info.types[type] ?? info.types["other"]
        // 1 · what kind of letter
        Section {
            if let kind {
                VStack(alignment: .leading, spacing: 4) {
                    Text(kind.name.app).font(.title3.weight(.semibold))
                    Text(kind.name.nl).font(.footnote).foregroundStyle(.secondary)
                }
                Text(kind.what.app).font(.callout)
                if out.lang == "nl" {
                    deadline(kind)
                    if !kind.law.isEmpty {
                        DisclosureGroup(L("Dayanağı nedir?", "Where does this come from?")) {
                            ForEach(kind.law, id: \.self) { key in
                                if let law = info.law[key] {
                                    VStack(alignment: .leading, spacing: 4) {
                                        if let url = URL(string: law.url) { Link(law.ref, destination: url).font(.callout.weight(.semibold)) }
                                        Text(law.quote).font(.caption).foregroundStyle(.secondary)
                                    }
                                }
                            }
                        }
                    }
                } else {
                    Text(L("Bu mektup Türkçe görünüyor: Türkçe modellerle maskelendi. Mektup türü (henüz) tanınmıyor.",
                           "This letter looks Turkish: it was masked with the Turkish models. Its type isn't recognised (yet)."))
                        .font(.footnote).foregroundStyle(.secondary)
                }
            }
            if out.lang == "nl" {
                Picker(L("Doğru değil mi? Türü seçin", "Not right? Pick the type"), selection: $type) {
                    ForEach(info.order, id: \.self) { k in Text(info.types[k]?.name.app ?? k).tag(k) }
                }
                if type == out.type, let why = out.why, !why.isEmpty {
                    Text(L("Tanındığı ifadeler: ", "Recognised by: ") + why.joined(separator: ", ")).font(.caption).foregroundStyle(.secondary)
                }
            }
        } header: {
            Text(L("1 · Bu nasıl bir mektup?", "1 · What kind of letter is this?"))
        }

        // 2 · what was hidden
        Section {
            if let ocrNote { Label(ocrNote, systemImage: "exclamationmark.triangle").font(.footnote).foregroundStyle(.orange) }
            Text(L("\(out.mapping?.count ?? 0) bilgi gizlendi. Bulunan bilgilerin hiçbiri metinde kalmadı.",
                   "\(out.mapping?.count ?? 0) details hidden. None of the details found is left in the text."))
                .font(.callout.weight(.semibold)).foregroundStyle(Theme.accent)
            ScrollView {
                Text(highlighted(out.text ?? "")).font(.callout).textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(maxHeight: 280)
            DisclosureGroup(L("Gizlenenler (\(values(out).count))", "Hidden (\(values(out).count))")) {
                ForEach(values(out), id: \.self) { h in
                    HStack(alignment: .firstTextBaseline) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(h.value).font(.callout)
                            Text("\(h.placeholder) · \(label(h.placeholder, out, info))").font(.caption).foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button(L("Okunur bırak", "Keep readable")) { allow.append(h.value); Task { await remask() } }
                            .font(.caption).buttonStyle(.bordered)
                    }
                }
            }
            HStack {
                TextField(L("Hâlâ görünen bir isim veya numara", "A name or number still visible"), text: $addTerm)
                    .textInputAutocapitalization(.never).autocorrectionDisabled()
                Button(L("Gizle", "Hide")) {
                    let t = addTerm.trimmingCharacters(in: .whitespacesAndNewlines)
                    guard !t.isEmpty else { return }
                    addTerm = ""
                    deny.append(t)
                    Task { await remask() }
                }
                .disabled(addTerm.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        } header: {
            Text(L("2 · Katip'in gizledikleri", "2 · What Katip hid"))
        } footer: {
            Text(L("Katip bir şey kaçırabilir. Göndermeden önce metni okuyun.", "Katip can miss something. Read the text before you send it."))
        }

        // 3 · ask for an explanation
        Section {
            Picker(L("Açıklama dili", "Explanation in"), selection: $answerLang) {
                Text("Türkçe").tag("tr"); Text("English").tag("en"); Text("Nederlands").tag("nl")
            }
            ForEach(AIHandoff.Target.allCases) { t in
                Button {
                    Task {
                        let prefilled = await AIHandoff.send(prompt, to: t)
                        sentTo = prefilled
                            ? L("\(t.name) açıldı, soru yazılı. Cevabı kopyalayıp buraya dönün.", "\(t.name) opened with the question filled in. Copy its answer and come back here.")
                            : L("Soru panoda. \(t.name)'de yapıştırın, sonra cevabı kopyalayıp buraya dönün.", "The question is on the clipboard. Paste it in \(t.name), then copy the answer and come back here.")
                    }
                } label: {
                    Label(L("\(t.name)'de açıkla", "Explain in \(t.name)"), systemImage: "paperplane")
                }
                .disabled(prompt.isEmpty)
            }
            ShareLink(item: prompt) { Label(L("Başka bir uygulamayla paylaş", "Share with another app"), systemImage: "square.and.arrow.up") }
                .disabled(prompt.isEmpty)
            if let sentTo { Text(sentTo).font(.footnote).foregroundStyle(.secondary) }
        } header: {
            Text(L("3 · Açıklama isteyin", "3 · Ask for an explanation"))
        } footer: {
            Text(L("Yalnızca maskeli mektup ve sade dille açıklama isteği gider. Katip'in süre kuralı da kaynağıyla birlikte eklenir; yapay zekâdan mektupla karşılaştırması istenir.",
                   "Only the masked letter and a request for a plain explanation go out. Katip's deadline rule goes with it, with its source, and the AI is asked to check it against the letter."))
        }

        // 4 · put names back
        Section {
            TextField(L("Cevabı buraya yapıştırın", "Paste the answer here"), text: $answer, axis: .vertical)
                .lineLimit(3 ... 8)
                .onChange(of: answer) { _, a in Task { await restore(a, out) } }
            if let r = restored {
                Text(r.text).font(.callout).textSelection(.enabled)
                if !r.unknown.isEmpty {
                    Text(L("Bu mektupta olmayan etiketler: ", "Labels not in this letter: ") + r.unknown.joined(separator: ", "))
                        .font(.caption).foregroundStyle(.orange)
                }
                Button { AIHandoff.copy(r.text) } label: { Label(L("Kopyala", "Copy"), systemImage: "doc.on.doc") }
            }
        } header: {
            Text(L("4 · İsimleri geri koyun", "4 · Put the names back"))
        }

        // 5 · ask a person
        Section {
            if out.lang == "nl" {
                ForEach(info.help, id: \.self) { h in
                    VStack(alignment: .leading, spacing: 2) {
                        if let url = URL(string: h.url) { Link(h.name, destination: url).font(.callout.weight(.semibold)) }
                        Text(h.what.app).font(.caption).foregroundStyle(.secondary)
                    }
                }
            } else {
                Text(L("Baronuzun adli yardım bürosunu veya bir avukatı arayın.", "Call your bar association's legal aid office (adli yardım), or a lawyer."))
            }
        } header: {
            Text(L("5 · Bir insana sorun", "5 · Ask a person"))
        } footer: {
            Text(L("Emin değilseniz veya bir süre varsa bir insana sorun. Katip hukuki danışmanlık vermez; bu bir testtir.",
                   "In doubt, or is there a deadline? Ask a person. Katip does not give legal advice; this is a test."))
        }
    }

    @ViewBuilder private func deadline(_ kind: LetterInfo.Kind) -> some View {
        let urgent = kind.urgent ?? false
        VStack(alignment: .leading, spacing: 6) {
            Text(L("Katip'e göre süre", "Deadline according to Katip")).font(.subheadline.weight(.semibold))
            if let d = kind.deadline {
                Text(d.app).font(.callout)
                Text(d.nl).font(.caption).foregroundStyle(.secondary)
            } else {
                Text(L("Katip bu mektup için süre belirtmiyor. Mektupta bir tarih veya süre olup olmadığına bakın.",
                       "Katip names no deadline for this letter. Look in the letter for a date or term.")).font(.callout)
            }
            if urgent {
                Text(L("Dikkat: burada kısa süreler geçerli olabilir. Hemen yardım alın.", "Careful: short deadlines can apply here. Get help soon."))
                    .font(.callout.weight(.semibold)).foregroundStyle(.red)
            }
            Text(L("Her zaman kendi mektubunuzdaki tarihi ve itiraz (bezwaar) paragrafını kontrol edin. Onlar esastır.",
                   "Always check the date and the objection (bezwaar) paragraph in your own letter. They come first."))
                .font(.caption).foregroundStyle(.secondary)
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background((urgent ? Color.red : Theme.accent).opacity(0.12), in: RoundedRectangle(cornerRadius: 10))
    }

    // MARK: actions

    private var promptKey: String { "\(type)|\(answerLang)|\(out?.text ?? "")" }

    private func makePrompt() async {
        guard let out, let text = out.text else { prompt = ""; return }
        prompt = (try? await engine.letterPrompt(type: type, docLang: out.lang ?? "tr", answerLang: answerLang, masked: text)) ?? ""
    }

    private func open(_ url: URL) async {
        busy = L("Mektup okunuyor…", "Reading the letter…")
        do {
            let r = try await DocumentReader.read(url: url, engine: engine, ocrLanguage: "nl")
            await run(r.text, note: r.note)
        } catch {
            busy = nil
            self.error = error.localizedDescription
        }
    }

    private func scanned(_ pages: [CGImage]) async {
        guard !pages.isEmpty else { return }
        busy = L("Metin tanınıyor…", "Recognising text…")
        do {
            let (t, note) = try await DocumentReader.ocr(pages, language: "nl")
            await run(t, note: note)
        } catch {
            busy = nil
            self.error = error.localizedDescription
        }
    }

    private func run(_ text: String, note: String?) async {
        original = text
        ocrNote = note
        allow = []
        deny = []
        await remask(first: true)
    }

    private func remask(first: Bool = false) async {
        guard let original else { return }
        busy = L("Bu telefonda maskeleniyor…", "Masking on this phone…")
        defer { busy = nil }
        do {
            if info == nil { info = try await engine.letterInfo() }
            let o = try await engine.letter(original, model: model, allow: allow, deny: deny)
            out = o
            if first { type = o.type ?? "other" }
            if !answer.isEmpty { await restore(answer, o) }
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func restore(_ a: String, _ out: LetterOutput) async {
        guard !a.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { restored = nil; return }
        restored = try? await engine.restore(a, mapping: out.mapping ?? [:])
    }

    private func reset() {
        original = nil; out = nil; ocrNote = nil; type = "other"; allow = []; deny = []
        answer = ""; restored = nil; prompt = ""; sentTo = nil
    }

    // MARK: helpers

    private struct Hidden: Hashable {
        let placeholder: String
        let value: String
    }

    /// Placeholder and value pairs, in document order.
    private func values(_ out: LetterOutput) -> [Hidden] {
        let text = out.text ?? ""
        return (out.mapping ?? [:]).sorted { a, b in
            (text.range(of: a.key)?.lowerBound ?? text.endIndex) < (text.range(of: b.key)?.lowerBound ?? text.endIndex)
        }.map { Hidden(placeholder: $0.key, value: $0.value) }
    }

    /// "Naam / Name" for a Dutch placeholder, the Turkish label otherwise.
    private func label(_ placeholder: String, _ out: LetterOutput, _ info: LetterInfo) -> String {
        let tag = placeholder.trimmingCharacters(in: CharacterSet(charactersIn: "[]")).replacingOccurrences(of: #"-\d+$"#, with: "", options: .regularExpression)
        if out.lang == "nl", let l = info.labels.values.first(where: { $0.tag == tag }) {
            return "\(appIsTurkish ? l.tr : l.en) / \(l.nl)"
        }
        return tag
    }

    private func highlighted(_ text: String) -> AttributedString {
        var a = AttributedString(text)
        for m in text.matches(of: #/\[[^\[\]\n]{1,40}-\d+\]/#) {
            guard let lo = AttributedString.Index(m.range.lowerBound, within: a),
                  let hi = AttributedString.Index(m.range.upperBound, within: a) else { continue }
            a[lo ..< hi].backgroundColor = Theme.placeholder
            a[lo ..< hi].font = Font.callout.weight(.semibold)
        }
        return a
    }
}
