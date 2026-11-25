import AppKit
import SwiftUI

/// Name models: pick the default, swap, download, delete, or add a model folder. Masking always runs on this Mac.
struct ModelsScreen: View {
    @EnvironmentObject var model: AppModel
    @State private var downloading: String?
    @State private var confirmDelete: E.ModelInfo?

    var list: [E.ModelInfo] { model.models?.models ?? [] }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                ScreenHeader(title: L("Modeller", "Models"),
                             subtitle: L("Adları bulan model. Maskeleme her zaman bu Mac'te çalışır; internet yalnızca bir modeli ilk kez indirirken kullanılır.",
                                         "The model that finds names. Masking always runs on this Mac; the internet is only used to download a model the first time."))
                ForEach(list) { m in row(m) }
                HStack(spacing: 10) {
                    Button(L("Model klasörü ekle…", "Add model folder…")) { pickFolder() }
                    RevealButton(key: \.models)
                    Text(L("Kendi eğittiğiniz ya da büronuzun verdiği bir Katip modeli (config.json, tokenizer.json, onnx/).",
                           "A Katip model you trained or your firm gave you (config.json, tokenizer.json, onnx/)."))
                        .font(.caption).foregroundStyle(.secondary)
                }
                .padding(.top, 4)
                Label(L("Mini ve Base, Hugging Face'ten sabitlenmiş bir sürümle indirilir; her dosya parmak iziyle (SHA-256) kontrol edilir. Kontrolü geçmeyen model kullanılmaz.",
                        "Mini and Base are downloaded from Hugging Face at a pinned version, and every file is checked against its fingerprint (SHA-256). A model that fails the check is never used."),
                      systemImage: "lock.shield").font(.callout).foregroundStyle(.secondary)
                if let note = model.note { Label(note, systemImage: "exclamationmark.triangle").foregroundStyle(.orange) }
            }
            .padding(22)
        }
        .task { await model.refreshModels() }
        .confirmationDialog(L("Bu model silinsin mi?", "Delete this model?"),
                            isPresented: Binding(get: { confirmDelete != nil }, set: { if !$0 { confirmDelete = nil } }),
                            presenting: confirmDelete) { m in
            Button(m.custom ? L("Listeden çıkar", "Remove from list") : L("Sil", "Delete"), role: .destructive) {
                Task { if m.custom { await model.removeModelFolder(m.name) } else { await model.deleteModel(m.name) } }
            }
        } message: { m in
            Text(m.custom ? L("Klasörünüz silinmez; yalnızca Katip'in listesinden çıkar.", "Your folder isn't deleted; it only leaves Katip's list.")
                          : L("\(Int(m.sizeMb)) MB yer açılır. İstediğinizde yeniden indirebilirsiniz.", "Frees \(Int(m.sizeMb)) MB. You can download it again any time."))
        }
    }

    @ViewBuilder func row(_ m: E.ModelInfo) -> some View {
        HStack(alignment: .center, spacing: 14) {
            Image(systemName: m.custom ? "folder" : "cpu").font(.title2)
                .foregroundStyle(m.current ? Color.accentColor : .secondary).frame(width: 30)
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(modelTitle(m.name)).font(.headline)
                    if m.current { Tag(text: L("Varsayılan", "Default"), color: .green) }
                    if m.recommended { Tag(text: L("Önerilen", "Recommended"), color: .accentColor) }
                    if m.included { Tag(text: L("Uygulamayla gelir", "Included"), color: .secondary) }
                    else if m.downloaded && !m.custom { Tag(text: L("Bu Mac'te", "On this Mac"), color: .secondary) }
                }
                Text(modelDetail(m)).font(.callout).foregroundStyle(.secondary).lineLimit(2).truncationMode(.middle)
            }
            Spacer()
            if downloading == m.name, let d = model.models?.download {
                VStack(alignment: .trailing, spacing: 2) {
                    ProgressView(value: d.fraction).frame(width: 120)
                    Text("\(Int(Double(d.done) / 1e6)) / \(Int(Double(d.total) / 1e6)) MB").font(.caption2).foregroundStyle(.secondary)
                }
            } else if !m.downloaded && !m.custom {
                Button(L("İndir", "Download")) {
                    downloading = m.name
                    Task { await model.download(m.name); downloading = nil }
                }
                .disabled(downloading != nil)
            } else if !m.current && m.downloaded {
                Button(L("Varsayılan yap", "Make default")) { Task { await model.useModel(m.name) } }
            }
            if !m.current && !m.included && (m.downloaded || m.custom) {
                Button { confirmDelete = m } label: { Image(systemName: "trash") }
                    .buttonStyle(.borderless).help(m.custom ? L("Listeden çıkar", "Remove from list") : L("Sil", "Delete"))
            }
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: 10).fill(m.current ? Color.accentColor.opacity(0.06) : Color.primary.opacity(0.035)))
        .overlay(RoundedRectangle(cornerRadius: 10).stroke(m.current ? Color.accentColor.opacity(0.4) : Color.primary.opacity(0.08)))
    }

    func pickFolder() {
        let p = NSOpenPanel()
        p.canChooseDirectories = true
        p.canChooseFiles = false
        p.prompt = L("Ekle", "Add")
        NSApp.activate(ignoringOtherApps: true)
        if p.runModal() == .OK, let u = p.url { Task { await model.addModelFolder(u) } }
    }
}
