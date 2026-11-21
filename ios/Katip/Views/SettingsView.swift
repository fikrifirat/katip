import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var engine: MaskEngine
    @EnvironmentObject private var store: SessionStore
    @EnvironmentObject private var feedback: FeedbackStore
    @Environment(\.dismiss) private var dismiss
    @AppStorage("model") private var model: KatipModel = .mini
    @State private var confirmWipe = false

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Picker(L("İsim modeli", "Name model"), selection: $model) {
                        ForEach(KatipModel.allCases) { m in
                            VStack(alignment: .leading) {
                                Text(m.title)
                                Text(m.detail).font(.caption).foregroundStyle(.secondary)
                            }.tag(m)
                        }
                    }
                    .pickerStyle(.inline)
                    .labelsHidden()
                } header: {
                    Text(L("Model", "Model"))
                } footer: {
                    Text(L("Modeller uygulamanın içindedir ve bu telefonda çalışır. İnternet gerekmez.",
                           "The models ship inside the app and run on this phone. No internet needed."))
                }

                Section(L("Maskeleme profilleri", "Masking profiles")) {
                    ForEach(ProfileSpec.order, id: \.self) { p in
                        DisclosureGroup(ProfileSpec.shared.title(p)) { ProfileDetails(profile: p) }
                    }
                    NavigationLink(L("Hukuki notlar", "Legal notes")) { LegalNotesView() }
                }

                Section {
                    if let file = try? feedback.exportFile(), !feedback.records.isEmpty {
                        ShareLink(item: file) {
                            Label(L("Hükümleri dışa aktar (\(feedback.records.count))", "Export verdicts (\(feedback.records.count))"), systemImage: "square.and.arrow.up")
                        }
                    } else {
                        Text(L("Henüz hüküm yok.", "No verdicts yet.")).foregroundStyle(.secondary)
                    }
                } header: {
                    Text(L("Geri bildirim", "Feedback"))
                } footer: {
                    Text(L("Hükümler yalnızca veri türünü, nasıl bulunduğunu ve kararınızı içerir; değeri ya da metni içermez. Siz paylaşmadıkça hiçbir yere gönderilmez.",
                           "Verdicts hold only the data type, how it was found and your verdict, never the value or text. Nothing is sent unless you share it."))
                }

                Section {
                    Button(L("Bütün belgeleri ve eşleme tablolarını sil", "Delete all documents and maps"), role: .destructive) { confirmWipe = true }
                } footer: {
                    Text(L("Belgeler \(SessionStore.keepDays) gün sonra kendiliğinden silinir.", "Documents are deleted automatically after \(SessionStore.keepDays) days."))
                }

                Section(L("Hakkında", "About")) {
                    LabeledContent(L("Motor", "Engine"), value: "katip-mask")
                    Link(L("Gizlilik açıklaması", "Privacy statement"), destination: Src.privacy.url!)
                    Link(L("KVKK-Bench sonuçları", "KVKK-Bench results"), destination: Src.bench.url!)
                    Link(L("Kaynak kodu (AGPL-3.0)", "Source code (AGPL-3.0)"), destination: URL(string: "https://github.com/fikrifirat/katip")!)
                    Text(L("Katip Mask modelleri CC BY-SA 4.0 lisanslıdır ve BERTurk (MIT, dbmdz) üzerine kuruludur. ONNX Runtime (MIT) ile çalışır.",
                           "Katip Mask models are licensed CC BY-SA 4.0 and built on BERTurk (MIT, dbmdz). They run with ONNX Runtime (MIT)."))
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            .navigationTitle(L("Ayarlar", "Settings"))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button(L("Bitti", "Done")) { dismiss() } } }
            .confirmationDialog(L("Bütün belgeler ve eşleme tabloları bu telefondan silinsin mi?", "Delete all documents and maps from this phone?"),
                                isPresented: $confirmWipe, titleVisibility: .visible) {
                Button(L("Hepsini sil", "Delete all"), role: .destructive) { store.deleteAll() }
            }
            .onChange(of: model) { _, m in Task { await engine.warm(model: m) } }
        }
    }
}
