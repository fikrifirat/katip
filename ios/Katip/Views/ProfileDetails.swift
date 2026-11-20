import SwiftUI

/// What a profile masks and why, with the legal text behind it. Each data type expands to its own reason.
struct ProfileDetails: View {
    let profile: String

    var body: some View {
        let why = LegalInfo.profile(profile)
        let entities = Set(ProfileSpec.shared.profiles[profile]?.entities ?? [])
        VStack(alignment: .leading, spacing: 12) {
            Text(why.why).font(.footnote)
            LabeledBlock(title: L("Okunur kalanlar", "Stays readable"), text: why.keeps)

            ForEach(EntityInfo.Group.allCases, id: \.rawValue) { g in
                let items = LegalInfo.entities.filter { $0.group == g && entities.contains($0.id) }
                if !items.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(g.title).font(.subheadline.weight(.semibold))
                        Text(g.basis).font(.caption).foregroundStyle(.secondary)
                        ForEach(items) { e in
                            DisclosureGroup(ProfileSpec.shared.label(e.id)) {
                                Text(e.why).font(.footnote).frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .font(.callout)
                        }
                    }
                }
            }

            SourcesView(sources: why.sources)
            NavigationLink(L("Maskelenmiş metin hâlâ kişisel veri mi? Yaptırımlar", "Is masked text still personal data? Sanctions")) {
                LegalNotesView()
            }
            .font(.footnote)
        }
        .padding(.vertical, 4)
    }
}

struct LabeledBlock: View {
    let title: String
    let text: String
    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title).font(.caption.weight(.semibold)).foregroundStyle(.secondary)
            Text(text).font(.footnote)
        }
    }
}

struct SourcesView: View {
    let sources: [LegalSource]
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(L("Kaynaklar", "Sources")).font(.caption.weight(.semibold)).foregroundStyle(.secondary)
            ForEach(sources) { s in
                if let url = s.url { Link(s.title, destination: url).font(.caption) } else { Text(s.title).font(.caption) }
            }
        }
    }
}

/// The general notes: pseudonymised text is still personal data, what Katip does about it, and the sanctions.
struct LegalNotesView: View {
    var body: some View {
        List {
            Section(LegalInfo.stillPersonalData.title) {
                Text(LegalInfo.stillPersonalData.body).font(.callout)
            }
            Section(LegalInfo.consequences.title) {
                ForEach(LegalInfo.consequences.items, id: \.self) { Text($0).font(.callout) }
                SourcesView(sources: LegalInfo.consequences.sources + [Src.guide])
            }
            Section {
                Text(LegalInfo.disclaimer).font(.footnote)
                SourcesView(sources: [Src.bench, Src.privacy])
            }
        }
        .navigationTitle(L("Hukuki notlar", "Legal notes"))
        .navigationBarTitleDisplayMode(.inline)
    }
}
