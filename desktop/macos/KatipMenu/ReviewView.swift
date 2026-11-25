import AppKit
import SwiftUI

/// The review queue: words Katip wasn't sure about, one at a time. The lawyer strikes the gavel; Katip remembers.
struct ReviewScreen: View {
    @EnvironmentObject var model: AppModel
    @Environment(\.screenShown) private var shown
    @State private var striking: String?   // the verdict being stamped, for the animation
    @State private var showLearned = false
    @State private var confirmAllow: E.Candidate?

    var queue: [E.Candidate] { model.review?.open ?? [] }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack(alignment: .top) {
                    ScreenHeader(title: L("İnceleme", "Review"),
                                 subtitle: L("Katip'in emin olamadığı sözcükler. Kararı siz verin: Katip bu Mac'te bundan sonra ona göre maskeler. Hiçbiri bu Mac'ten çıkmaz.",
                                             "Words Katip wasn't sure about. You decide; from then on Katip masks accordingly on this Mac. None of this leaves the Mac."))
                    Spacer()
                    if let r = model.review {
                        let later = r.open.count - model.reviewWaiting
                        VStack(alignment: .trailing, spacing: 2) {
                            Text("\(model.reviewWaiting)").font(.system(size: 28, weight: .semibold, design: .rounded))
                            Text(L("bekliyor", "waiting") + (later > 0 ? L(" · \(later) sonraya", " · \(later) later") : "")
                                 + L(" · \(r.judged) karar", " · \(r.judged) decided")).font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
                if model.review?.unreadable == true {
                    VStack(alignment: .leading, spacing: 8) {
                        Label(L("Katip öğrendiği listeleri okuyamıyor (Anahtar Zinciri izin vermedi). Güvenlik için maskeleme durdu.",
                                "Katip can't read its learned lists (the Keychain refused). Masking has stopped to be safe."),
                              systemImage: "lock.trianglebadge.exclamationmark").foregroundStyle(.red)
                        Text(L("Mac'inize giriş yaptığınızdan emin olun ve Katip'i yeniden açın. Olmazsa listeleri yeniden başlatın: eski dosya silinmez, kenara konur; maskelemeyi öğrettiğiniz sözcükleri yeniden öğretmeniz gerekir.",
                               "Make sure you're logged in to your Mac and reopen Katip. If that doesn't help, start the lists again: the old file is kept aside, not deleted, and you'll need to teach Katip those words again."))
                            .font(.callout).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                        Button(L("Listeleri yeniden başlat", "Start the lists again")) { Task { await model.resetReview() } }
                    }
                    .padding(12).background(RoundedRectangle(cornerRadius: 10).fill(Color.red.opacity(0.07)))
                }
                if let c = queue.first {
                    CandidateCard(c: c, striking: striking) { v in decide(c, v) }
                        .id(c.id)
                        .transition(.asymmetric(insertion: .move(edge: .trailing).combined(with: .opacity),
                                                removal: .move(edge: .leading).combined(with: .opacity)))
                    if queue.count > 1 { upNext }
                } else if model.review != nil {
                    EmptyDocket()
                }
                if let v = model.lastVerdict {
                    HStack {
                        Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                        Text(verdictLine(v.verdict, v.text)).font(.callout)
                        Spacer()
                        Button(L("Geri al", "Undo")) { Task { await model.undoVerdict() } }.shortcut("z", .command, when: shown)
                    }
                    .padding(10).background(RoundedRectangle(cornerRadius: 8).fill(Color.green.opacity(0.08)))
                }
                learned
                if let note = model.note { Label(note, systemImage: "exclamationmark.triangle").foregroundStyle(.orange) }
            }
            .padding(22)
            .animation(.spring(response: 0.45, dampingFraction: 0.82), value: queue.first?.id)
        }
        .task { await model.refreshReview() }
        .onReceive(NotificationCenter.default.publisher(for: .katipTourJudge)) { _ in
            if let c = queue.first { decide(c, "mask") }
        }
        .onReceive(Timer.publish(every: 8, on: .main, in: .common).autoconnect()) { _ in
            // Claude may have masked something meanwhile; only while this screen shows, so the engine can idle
            if shown && NSApp.isActive { Task { await model.refreshReview() } }
        }
        .onChange(of: shown) { _, now in if now { Task { await model.refreshReview() } } }
        .confirmationDialog(L("“\(confirmAllow?.text ?? "")” hiçbir belgede maskelenmesin mi?", "Never mask “\(confirmAllow?.text ?? "")” in any document?"),
                            isPresented: Binding(get: { confirmAllow != nil }, set: { if !$0 { confirmAllow = nil } }),
                            presenting: confirmAllow) { c in
            Button(L("Evet, kişisel veri değil", "Yes, it isn't personal data"), role: .destructive) { strike(c, "allow") }
        } message: { _ in
            Text(L("Bu sözcük bu Mac'teki tüm davalarda açık kalır ve Claude'a gider. Bir kişinin adıysa Maskele'yi seçin.",
                   "This word then stays readable in every case on this Mac and goes to Claude. If it is a person's name, choose Mask."))
        }
    }

    func decide(_ c: E.Candidate, _ v: String) {
        guard striking == nil else { return }
        if v == "later" { Task { await model.judge(c, v) }; return }
        if v == "allow" && c.kind == "unsure" { confirmAllow = c; return }  // unmasking a name everywhere: ask first
        strike(c, v)
    }

    func strike(_ c: E.Candidate, _ v: String) {
        withAnimation(.easeIn(duration: 0.12)) { striking = v }
        NSSound(named: "Pop")?.play()
        Task {
            try? await Task.sleep(nanoseconds: 550_000_000)
            await model.judge(c, v)
            striking = nil
        }
    }

    var upNext: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(L("Sırada", "Up next")).font(.caption.weight(.semibold)).foregroundStyle(.secondary)
            ForEach(queue.dropFirst().prefix(4)) { c in
                HStack(spacing: 8) {
                    KindTag(kind: c.kind)
                    Text(c.text).font(.system(.body, design: .serif)).lineLimit(1)
                    if c.seen > 1 { Text("×\(c.seen)").font(.caption).foregroundStyle(.secondary) }
                    Spacer()
                    Text(c.matter == "default" ? L("Genel", "General") : c.matter).font(.caption).foregroundStyle(.secondary)
                }
            }
            if queue.count > 5 { Text(L("ve \(queue.count - 5) tane daha", "and \(queue.count - 5) more")).font(.caption).foregroundStyle(.secondary) }
        }
        .padding(12).background(RoundedRectangle(cornerRadius: 10).fill(Color.primary.opacity(0.03)))
    }

    @ViewBuilder var learned: some View {
        if let l = model.review?.learned, !(l.mask.isEmpty && l.allow.isEmpty) {
            DisclosureGroup(isExpanded: $showLearned) {
                VStack(alignment: .leading, spacing: 10) {
                    LearnedList(title: L("Her zaman maskele", "Always mask"), items: l.mask, color: .blue) { t in
                        Task { await model.removeLearned("mask", t) }
                    }
                    LearnedList(title: L("Asla maskeleme", "Never mask"), items: l.allow, color: .secondary) { t in
                        Task { await model.removeLearned("allow", t) }
                    }
                }.padding(.top, 6)
            } label: {
                Label(L("Katip'in öğrendikleri (\(l.mask.count + l.allow.count))", "What Katip learned (\(l.mask.count + l.allow.count))"),
                      systemImage: "brain").font(.headline)
            }
        }
    }
}

func verdictLine(_ v: String, _ text: String) -> String {
    switch v {
    case "mask": return L("“\(text)” artık bu Mac'te her zaman maskelenecek.", "“\(text)” will now always be masked on this Mac.")
    case "allow": return L("“\(text)” artık maskelenmeyecek.", "“\(text)” will no longer be masked.")
    default: return L("Sona bırakıldı.", "Moved to the end.")
    }
}

struct KindTag: View {
    let kind: String
    var body: some View {
        kind == "missed" ? Tag(text: L("Kaçmış olabilir", "Possibly missed"), color: .orange)
                         : Tag(text: L("Emin değildi", "Unsure"), color: .blue)
    }
}

struct CandidateCard: View {
    @Environment(\.screenShown) private var shown
    let c: E.Candidate
    let striking: String?
    let decide: (String) -> Void

    var question: String {
        c.kind == "missed"
            ? L("Katip bunu maskelemedi. Bu bir kişinin adı mı?", "Katip didn't mask this. Is it a person's name?")
            : L("Katip bunu ad sayıp maskeledi ama emin değildi. Doğru mu?", "Katip masked this as a name but wasn't sure. Was it right?")
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 8) {
                KindTag(kind: c.kind)
                if c.source == "claude" {
                    AppIcon(path: Apps.claude, fallback: "sparkle", size: 16)
                    Text(L("Claude için maskelenirken", "While masking for Claude")).font(.caption).foregroundStyle(.secondary)
                } else {
                    Text(L("Katip penceresinde", "In the Katip window")).font(.caption).foregroundStyle(.secondary)
                }
                Text("·").foregroundStyle(.secondary)
                Text(c.matter == "default" ? L("Genel", "General") : L("Dava \(c.matter)", "Case \(c.matter)")).font(.caption).foregroundStyle(.secondary)
                if c.seen > 1 { Text(L("· \(c.seen) kez görüldü", "· seen \(c.seen) times")).font(.caption).foregroundStyle(.secondary) }
                Spacer()
            }
            Text(question).font(.title3.weight(.semibold))
            (Text(c.before.isEmpty ? "" : c.before + " ").foregroundColor(.secondary)
             + Text(c.text).bold().foregroundColor(.primary).underline(true, color: .accentColor)
             + Text(c.after.isEmpty ? "" : " " + c.after).foregroundColor(.secondary))
                .font(.system(size: 17, design: .serif)).lineSpacing(4).textSelection(.enabled)
                .padding(14).frame(maxWidth: .infinity, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: 8).fill(Color(nsColor: .textBackgroundColor)))
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.primary.opacity(0.08)))
            HStack(spacing: 8) {
                Text(L("Katip'in eminliği", "Katip's confidence")).font(.caption).foregroundStyle(.secondary)
                ProgressView(value: c.score).frame(width: 120).tint(c.score < 0.5 ? .orange : .accentColor)
                Text(L("%\(Int((c.score * 100).rounded()))", "\(Int((c.score * 100).rounded()))%")).font(.caption.monospacedDigit()).foregroundStyle(.secondary)
                Spacer()
                Text(L("Diğer değerler ••• olarak gizlendi.", "Other values are hidden as •••.")).font(.caption).foregroundStyle(.tertiary)
            }
            HStack(alignment: .center, spacing: 14) {
                Button { decide("mask") } label: {
                    HStack(spacing: 10) {
                        Gavel(down: striking == "mask", size: 40)
                        VStack(alignment: .leading, spacing: 1) {
                            Text(L("Kişisel veri, maskele", "Personal data, mask it")).font(.headline)
                            Text(L("Bundan sonra hep maskelenir", "Always masked from now on")).font(.caption).opacity(0.85)
                        }
                    }
                    .padding(.horizontal, 14).padding(.vertical, 8)
                }
                .buttonStyle(GavelButtonStyle())
                .shortcut(.return, when: shown)
                .help(L("Return", "Return"))
                Button { decide("allow") } label: {
                    VStack(alignment: .leading, spacing: 1) {
                        Text(L("Kişisel veri değil", "Not personal data")).font(.headline)
                        Text(L("Bir daha maskelenmez", "Never masked again")).font(.caption).foregroundStyle(.secondary)
                    }.padding(.horizontal, 6).padding(.vertical, 4)
                }
                .controlSize(.large)
                .shortcut("n", when: shown)
                Spacer()
                Button(L("Sonra", "Later")) { decide("later") }.buttonStyle(.borderless).shortcut("l", when: shown)
            }
            Text(L("Kısayollar: Return maskele · N maskeleme · L sonra · ⌘Z geri al", "Shortcuts: Return mask · N don't mask · L later · ⌘Z undo"))
                .font(.caption2).foregroundStyle(.tertiary)
        }
        .padding(18)
        .background(RoundedRectangle(cornerRadius: 14).fill(Color.primary.opacity(0.035)))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.primary.opacity(0.08)))
        .overlay(alignment: .topTrailing) {
            if let s = striking { VerdictStamp(verdict: s).padding(18).transition(.scale(scale: 1.6).combined(with: .opacity)) }
        }
    }
}

struct GavelButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(.white)
            .background(RoundedRectangle(cornerRadius: 10, style: .continuous)
                .fill(LinearGradient(colors: [Color(red: 0.42, green: 0.25, blue: 0.13), Color(red: 0.3, green: 0.17, blue: 0.08)],
                                     startPoint: .top, endPoint: .bottom)))
            .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).stroke(Color(red: 0.86, green: 0.68, blue: 0.3).opacity(0.7)))
            .scaleEffect(configuration.isPressed ? 0.97 : 1)
            .shadow(color: .black.opacity(0.18), radius: 3, y: 2)
    }
}

/// The court stamp that lands on the card when the gavel strikes.
struct VerdictStamp: View {
    let verdict: String
    var body: some View {
        let mask = verdict == "mask"
        Text(mask ? L("MASKELENDİ", "MASKED") : L("SERBEST", "CLEARED"))
            .font(.system(size: 20, weight: .heavy, design: .serif)).tracking(2)
            .foregroundStyle(mask ? Color.red.opacity(0.85) : Color.green.opacity(0.85))
            .padding(.horizontal, 12).padding(.vertical, 6)
            .overlay(RoundedRectangle(cornerRadius: 6).stroke(mask ? Color.red.opacity(0.8) : Color.green.opacity(0.8), lineWidth: 3))
            .rotationEffect(.degrees(-12))
    }
}

struct EmptyDocket: View {
    var body: some View {
        VStack(spacing: 12) {
            Gavel(down: true, size: 72)
            Text(L("Masa temiz", "The docket is clear")).font(.title2.weight(.semibold))
            Text(L("Katip bir sözcükten emin olamadığında burada görürsünüz. Belge maskeledikçe yenileri gelir.",
                   "When Katip isn't sure about a word, it shows here. New ones arrive as you mask documents."))
                .multilineTextAlignment(.center).foregroundStyle(.secondary).frame(maxWidth: 420)
        }
        .frame(maxWidth: .infinity).padding(.vertical, 40)
    }
}

struct LearnedList: View {
    let title: String
    let items: [String]
    let color: Color
    let remove: (String) -> Void
    var body: some View {
        if !items.isEmpty {
            VStack(alignment: .leading, spacing: 6) {
                Text(title).font(.caption.weight(.semibold)).foregroundStyle(.secondary)
                FlowRow(items: items) { t in
                    HStack(spacing: 4) {
                        Text(t).font(.callout)
                        Button { remove(t) } label: { Image(systemName: "xmark.circle.fill") }
                            .buttonStyle(.borderless).foregroundStyle(.secondary).help(L("Unut", "Forget"))
                    }
                    .padding(.horizontal, 8).padding(.vertical, 3)
                    .background(Capsule().fill(color.opacity(0.12)))
                }
            }
        }
    }
}

/// Chips that wrap onto new lines.
struct FlowRow<Content: View>: View {
    let items: [String]
    @ViewBuilder let content: (String) -> Content
    var body: some View {
        FlowLayout(spacing: 6) { ForEach(items, id: \.self) { content($0) } }
    }
}

struct FlowLayout: Layout {
    var spacing: CGFloat = 6
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let w = proposal.width ?? 600
        var x: CGFloat = 0, y: CGFloat = 0, row: CGFloat = 0
        for s in subviews {
            let z = s.sizeThatFits(.unspecified)
            if x + z.width > w, x > 0 { x = 0; y += row + spacing; row = 0 }
            x += z.width + spacing; row = max(row, z.height)
        }
        return CGSize(width: w, height: y + row)
    }
    func placeSubviews(in b: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = b.minX, y = b.minY, row: CGFloat = 0
        for s in subviews {
            let z = s.sizeThatFits(.unspecified)
            if x + z.width > b.maxX, x > b.minX { x = b.minX; y += row + spacing; row = 0 }
            s.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(z))
            x += z.width + spacing; row = max(row, z.height)
        }
    }
}

extension Notification.Name {
    static let katipTourJudge = Notification.Name("katip.tourJudge")
}
