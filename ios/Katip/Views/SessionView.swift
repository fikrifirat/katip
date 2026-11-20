import SwiftUI

/// One document: check the masking, send it, put the names back into the answer.
struct SessionView: View {
    let sessionID: UUID
    @EnvironmentObject private var engine: MaskEngine
    @EnvironmentObject private var store: SessionStore
    @Environment(\.dismiss) private var dismiss

    @State private var task = ""
    @State private var addTerm = ""
    @State private var busy: String?
    @State private var error: String?
    @State private var sentTo: String?
    @State private var restored: RestoreOutput?
    @State private var showFull = false
    @State private var confirmDelete = false

    private var session: MaskSession? { store.sessions.first { $0.id == sessionID } }

    var body: some View {
        Group {
            if let s = session { content(s) } else { ContentUnavailableView(L("Belge silindi", "Document deleted"), systemImage: "trash") }
        }
        .navigationTitle(session?.title ?? "")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button(role: .destructive) { confirmDelete = true } label: { Image(systemName: "trash") }
                    .accessibilityLabel(L("Belgeyi sil", "Delete document"))
            }
        }
        .confirmationDialog(L("Belge ve eşleme tablosu bu telefondan silinsin mi? Sonra cevaplardaki isimler geri konamaz.",
                              "Delete the document and its map from this phone? Names can no longer be put back into answers."),
                            isPresented: $confirmDelete, titleVisibility: .visible) {
            Button(L("Sil", "Delete"), role: .destructive) { store.delete(sessionID); dismiss() }
        }
        .overlay { if let busy { BusyOverlay(text: busy) } }
        .alert(L("Olmadı", "Something went wrong"), isPresented: Binding(get: { error != nil }, set: { if !$0 { error = nil } })) {
            Button("OK", role: .cancel) {}
        } message: { Text(error ?? "") }
    }

    @ViewBuilder
    private func content(_ s: MaskSession) -> some View {
        List {
            // 1 · Check
            Section {
                if let note = s.ocrNote {
                    Label(note, systemImage: "exclamationmark.triangle").font(.footnote).foregroundStyle(.orange)
                }
                CountsView(session: s)
                ScrollView {
                    Text(highlighted(s.masked)).font(.callout).textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(maxHeight: 260)
                Button(L("Tamamını göster", "Show all")) { showFull = true }
                Picker(L("Profil", "Profile"), selection: Binding(get: { s.profile }, set: { p in update(s) { $0.profile = p } })) {
                    ForEach(ProfileSpec.order, id: \.self) { Text(ProfileSpec.shared.title($0)).tag($0) }
                }
            } header: {
                Text(L("1 · Kontrol edin", "1 · Check"))
            } footer: {
                Text(L("Göndermeden önce okuyun: Katip bazı değerleri kaçırabilir. Model: \(s.engineModel ?? KatipModel.rules.title).",
                       "Read it before sending: Katip can miss values. Model: \(s.engineModel ?? KatipModel.rules.title)."))
            }

            // "What Katip found" block. The shared feedback control (judge-hammer grade, designed in the precedent
            // finder thread for the MCP, web and mobile apps) goes on this block once that design lands.
            Section {
                DisclosureGroup(L("Maskelenenler (\(s.values.count))", "Masked values (\(s.values.count))")) {
                    ForEach(s.values, id: \.value) { v in
                        HStack(alignment: .firstTextBaseline) {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(v.value).font(.callout)
                                Text("\(v.placeholder) · \(ProfileSpec.shared.label(v.type))").font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Button(L("Okunur bırak", "Keep readable")) { update(s) { $0.allow.append(v.value) } }
                                .font(.caption).buttonStyle(.bordered)
                        }
                    }
                }
                if !s.allow.isEmpty {
                    DisclosureGroup(L("Okunur bırakılanlar (\(s.allow.count))", "Kept readable (\(s.allow.count))")) {
                        ForEach(s.allow, id: \.self) { a in
                            HStack {
                                Text(a)
                                Spacer()
                                Button(L("Yine maskele", "Mask again")) { update(s) { $0.allow.removeAll { $0 == a } } }
                                    .font(.caption).buttonStyle(.bordered)
                            }
                        }
                    }
                }
                HStack {
                    TextField(L("Kaçan bir isim veya ifade", "A missed name or phrase"), text: $addTerm)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                    Button(L("Maskele", "Mask")) {
                        let t = addTerm.trimmingCharacters(in: .whitespacesAndNewlines)
                        guard !t.isEmpty else { return }
                        addTerm = ""
                        update(s) { $0.deny.append(t) }
                    }
                    .disabled(addTerm.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            } footer: {
                Text(L("Eklediğiniz ifade belgede geçtiği her yerde maskelenir.", "A phrase you add is masked everywhere it appears."))
            }

            // 2 · Send
            Section {
                TextField(L("Yapay zekâdan ne istiyorsunuz? (isteğe bağlı)", "What do you want from the AI? (optional)"), text: $task, axis: .vertical)
                    .lineLimit(1 ... 4)
                ForEach(AIHandoff.Target.allCases) { t in
                    Button {
                        Task {
                            let prefilled = await AIHandoff.send(AIHandoff.prompt(task: task, masked: s.masked), to: t)
                            sentTo = prefilled
                                ? L("\(t.name) açıldı, metin yazılı. Cevabı kopyalayıp buraya dönün.", "\(t.name) opened with the text filled in. Copy its answer and come back here.")
                                : L("Metin panoda. \(t.name)'de yapıştırın, sonra cevabı kopyalayıp buraya dönün.", "The text is on the clipboard. Paste it in \(t.name), then copy the answer and come back here.")
                        }
                    } label: {
                        Label(L("\(t.name)'ye gönder", "Send to \(t.name)"), systemImage: "paperplane")
                    }
                }
                ShareLink(item: AIHandoff.prompt(task: task, masked: s.masked)) {
                    Label(L("Başka bir uygulamayla paylaş", "Share with another app"), systemImage: "square.and.arrow.up")
                }
                Button { AIHandoff.copy(AIHandoff.prompt(task: task, masked: s.masked)); sentTo = L("Kopyalandı (10 dakika sonra panodan silinir).", "Copied (cleared from the clipboard after 10 minutes).") } label: {
                    Label(L("Kopyala", "Copy"), systemImage: "doc.on.doc")
                }
                if let sentTo { Text(sentTo).font(.footnote).foregroundStyle(.secondary) }
            } header: {
                Text(L("2 · Gönderin", "2 · Send"))
            } footer: {
                Text(L("Yalnızca maskeli metin gider. Eşleme tablosu bu telefonda kalır. Hesabınızda sohbetlerin eğitimde kullanılmasını kapatın.",
                       "Only the masked text goes out. The map stays on this phone. Turn off training on your chats in your AI account."))
            }

            // 3 · Restore
            Section {
                PasteButton(payloadType: String.self) { texts in
                    guard let t = texts.first else { return }
                    Task { await restore(t, s) }
                }
                .labelStyle(.titleAndIcon)
                if let r = restored {
                    if !r.unknown.isEmpty {
                        Label(L("Bu belgeye ait olmayan yer tutucular: \(r.unknown.joined(separator: ", ")). Cevap başka bir belgeden olabilir ya da yapay zekâ yer tutucuyu değiştirmiş olabilir.",
                                "Placeholders not from this document: \(r.unknown.joined(separator: ", ")). The answer may be from another document, or the AI changed a placeholder."),
                              systemImage: "exclamationmark.triangle").font(.footnote).foregroundStyle(.orange)
                    }
                    Text(r.text).font(.callout).textSelection(.enabled)
                    HStack {
                        Button { AIHandoff.copy(r.text) } label: { Label(L("Kopyala", "Copy"), systemImage: "doc.on.doc") }
                        Spacer()
                        ShareLink(item: r.text) { Label(L("Paylaş", "Share"), systemImage: "square.and.arrow.up") }
                    }
                    .buttonStyle(.bordered)
                }
            } header: {
                Text(L("3 · İsimleri geri koyun", "3 · Put the names back"))
            } footer: {
                Text(L("Yapay zekânın cevabını kopyalayıp yapıştırın. [AD SOYAD-1] gibi yer tutucular bu telefonda gerçek değerlerle değiştirilir.",
                       "Copy the AI's answer and paste it here. Placeholders such as [AD SOYAD-1] are replaced with the real values on this phone."))
            }

            Section {
                DisclosureGroup(LegalInfo.stillPersonalData.title) {
                    Text(LegalInfo.stillPersonalData.body).font(.footnote)
                }
            }
        }
        .sheet(isPresented: $showFull) {
            NavigationStack {
                ScrollView { Text(highlighted(s.masked)).textSelection(.enabled).padding() }
                    .navigationTitle(L("Maskeli metin", "Masked text")).navigationBarTitleDisplayMode(.inline)
                    .toolbar { ToolbarItem(placement: .confirmationAction) { Button(L("Kapat", "Close")) { showFull = false } } }
            }
        }
    }

    private func update(_ s: MaskSession, _ change: (inout MaskSession) -> Void) {
        var n = s
        change(&n)
        Task {
            busy = L("Yeniden maskeleniyor…", "Masking again…")
            defer { busy = nil }
            do { _ = try await Masking.redo(n, engine: engine, store: store) } catch { self.error = error.localizedDescription }
        }
    }

    private func restore(_ text: String, _ s: MaskSession) async {
        do {
            let r = try await engine.restore(text, mapping: s.mapping)
            restored = r
            var n = s
            n.answers.insert(.init(restored: r.text), at: 0)
            store.upsert(n)
        } catch { self.error = error.localizedDescription }
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

private struct CountsView: View {
    let session: MaskSession
    var body: some View {
        if session.spans.isEmpty {
            Label(L("Kişisel veri bulunamadı. Yine de metni okuyun.", "No personal data found. Read the text anyway."), systemImage: "info.circle")
                .font(.footnote)
        } else {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ForEach(session.counts, id: \.type) { c in
                        Text("\(ProfileSpec.shared.label(c.type)) \(c.n)")
                            .font(.caption.weight(.medium))
                            .padding(.horizontal, 8).padding(.vertical, 4)
                            .background(Theme.placeholder, in: Capsule())
                    }
                }
            }
        }
    }
}
