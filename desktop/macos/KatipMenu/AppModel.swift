import AppKit
import ServiceManagement
import SwiftUI

typealias E = EngineClient

/// Everything the windows and the menu show, kept in one place and refreshed from the engine.
@MainActor
final class AppModel: ObservableObject {
    static let shared = AppModel()
    @Published var status: E.Status?
    @Published var settings: E.Settings?
    @Published var models: E.Models?
    @Published var matters: [E.Matter] = []
    @Published var claude: E.ClaudeState?
    @Published var claudeError: String?
    @Published var busy = false
    @Published var note: String?
    @Published var paths: E.Paths?
    @Published var loginItem = SMAppService.mainApp.status == .enabled

    let client = EngineClient()
    var running: Bool { status != nil }

    func refreshStatus() async { status = await client.status() }
    func refreshPaths() async { if let p: E.Paths = try? await client.call("/v1/paths") { paths = p } }

    /// Start the engine if needed and read everything the screens need.
    func loadAll() async throws {
        try await client.start()
        async let s: E.Settings = client.call("/v1/settings")
        async let m: E.Models = client.call("/v1/models")
        async let mt: E.Matters = client.call("/v1/matters")
        settings = try await s
        models = try await m
        matters = try await mt.matters
        status = await client.status()
        await refreshClaude()
        await refreshFeatures()
        await refreshPaths()
    }

    func refreshClaude() async {
        do { claude = try await client.call("/v1/claude", timeout: 40); claudeError = nil } catch {
            claudeError = error.localizedDescription
        }
    }

    /// macOS runs a downloaded app from a temporary, read-only place until it's moved; Claude can't use that path.
    static var inApplications: Bool { Bundle.main.bundlePath.hasPrefix("/Applications/") }

    func moveToApplications() {
        let dst = URL(fileURLWithPath: "/Applications/Katip.app")
        let fm = FileManager.default
        do {
            if fm.fileExists(atPath: dst.path) { try fm.trashItem(at: dst, resultingItemURL: nil) }
            try fm.copyItem(at: Bundle.main.bundleURL, to: dst)
            removexattr(dst.path, "com.apple.quarantine", XATTR_NOFOLLOW)  // the copy is ours; no translocation again
            let cfg = NSWorkspace.OpenConfiguration()
            cfg.createsNewApplicationInstance = true
            NSWorkspace.shared.openApplication(at: dst, configuration: cfg) { _, _ in
                DispatchQueue.main.async { NSApp.terminate(nil) }
            }
        } catch {
            note = L("Taşınamadı. Katip'i Finder'da Uygulamalar klasörüne sürükleyin.",
                     "Couldn't move it. Drag Katip to the Applications folder in Finder.")
        }
    }

    func refreshMatters() async {
        if let m: E.Matters = try? await client.call("/v1/matters") { matters = m.matters }
    }

    @discardableResult
    func save(_ changes: [String: Any]) async -> Bool {
        do {
            settings = try await client.call("/v1/settings", body: changes)
            return true
        } catch {
            note = error.localizedDescription
            return false
        }
    }

    /// Download a model and switch to it, updating `models.download` as the bytes arrive.
    func download(_ name: String) async {
        do {
            struct Started: Decodable { let download: E.Download }
            let _: Started = try await client.call("/v1/models/download", body: ["name": name, "use": true])
            while true {
                let m: E.Models = try await client.call("/v1/models")
                models = m
                if m.download?.state != "running" || m.download?.name != name { break }
                try await Task.sleep(nanoseconds: 300_000_000)
            }
            if models?.download?.name != name || models?.download?.state != "done" {
                note = L("İndirilemedi. İnternet bağlantınızı kontrol edip yeniden deneyin; Katip bu arada Nano ile çalışır.",
                         "Couldn't download. Check your internet connection and try again; Katip keeps working with Nano meanwhile.")
            }
            settings = try await client.call("/v1/settings")
        } catch {
            note = error.localizedDescription
        }
    }

    func useModel(_ name: String) async { await save(["model": name]) }

    func refreshModels() async {
        if let m: E.Models = try? await client.call("/v1/models") { models = m }
    }

    func deleteModel(_ name: String) async {
        do { models = try await client.call("/v1/models/delete", body: ["name": name]) } catch { note = error.localizedDescription }
    }

    func addModelFolder(_ url: URL) async {
        do {
            models = try await client.call("/v1/models/custom", body: ["path": url.path])
            settings = try await client.call("/v1/settings")
        } catch { note = error.localizedDescription }
    }

    func removeModelFolder(_ path: String) async {
        do {
            models = try await client.call("/v1/models/custom/remove", body: ["path": path])
            settings = try await client.call("/v1/settings")
        } catch { note = error.localizedDescription }
    }

    // MARK: review queue
    @Published var review: E.Review?
    @Published var lastVerdict: (id: String, verdict: String, text: String)?

    func refreshReview() async {
        if let r: E.Review = try? await client.call("/v1/review") { review = r }
    }

    func judge(_ c: E.Candidate, _ verdict: String) async {
        do {
            review = try await client.call("/v1/review/judge", body: ["id": c.id, "verdict": verdict])
            lastVerdict = (c.id, verdict, c.text)
        } catch { note = error.localizedDescription; await refreshReview() }
    }

    func undoVerdict() async {
        guard let v = lastVerdict else { return }
        do { review = try await client.call("/v1/review/undo", body: ["id": v.id]) } catch { note = error.localizedDescription }
        lastVerdict = nil
    }

    func resetReview() async {
        do { review = try await client.call("/v1/review/reset", body: [:]) } catch { note = error.localizedDescription }
    }

    var reviewWaiting: Int { review?.open.filter { !$0.later }.count ?? 0 }

    func removeLearned(_ list: String, _ text: String) async {
        do { review = try await client.call("/v1/review/learned/remove", body: ["list": list, "text": text]) } catch {
            note = error.localizedDescription
        }
    }

    // MARK: features
    @Published var features: E.Features?

    func refreshFeatures() async {
        if let f: E.Features = try? await client.call("/v1/features") { features = f }
    }

    func feature(_ id: String) -> E.Feature? { features?.features.first { $0.id == id } }

    /// Switch a feature on or off; switching MASAK on also fetches its lists, so wait for that.
    func setFeature(_ id: String, on: Bool) async {
        do {
            features = try await client.call("/v1/features", body: ["id": id, "enabled": on])
            if id == "emsal" { settings = try await client.call("/v1/settings") }
            await followJob(id)
        } catch { note = error.localizedDescription }
    }

    /// refresh (MASAK lists), install_browser, test_browser, logout; waits until a background job ends.
    func featureAction(_ id: String, _ action: String) async {
        do {
            features = try await client.call("/v1/features/action", body: ["id": id, "action": action], timeout: 60)
            await followJob(id)
        } catch { note = error.localizedDescription }
    }

    private func followJob(_ id: String) async {
        var misses = 0
        for _ in 0..<3600 where feature(id)?.job?.state == "running" {  // 30 minutes at most
            try? await Task.sleep(nanoseconds: 500_000_000)
            if let f: E.Features = try? await client.call("/v1/features") { features = f; misses = 0 } else {
                misses += 1
                if misses >= 6 { note = L("Katip motoruna ulaşılamıyor.", "Can't reach the Katip engine."); return }
            }
        }
    }

    func connect(_ app: String, on: Bool) async -> E.ClaudeChange? {
        do {
            let r: E.ClaudeChange = try await client.call(on ? "/v1/claude/connect" : "/v1/claude/disconnect",
                                                          body: ["app": app], timeout: 60)
            await refreshClaude()
            return r
        } catch {
            note = error.localizedDescription
            return nil
        }
    }

    func forget(_ matter: String) async {
        struct Done: Decodable { let deleted: Bool }
        do { let _: Done = try await client.call("/v1/forget", body: ["matter": matter]) } catch {
            note = error.localizedDescription
        }
        await refreshMatters()
    }

    func toggleEngine() async {
        busy = true
        defer { busy = false }
        if running {
            await client.stop()
            try? await Task.sleep(nanoseconds: 400_000_000)
        } else {
            do { try await client.start() } catch { note = error.localizedDescription }
        }
        await refreshStatus()
    }

    func setLoginItem(_ on: Bool) {
        do {
            if on { try SMAppService.mainApp.register() } else { try SMAppService.mainApp.unregister() }
        } catch {
            note = L("Mac bunu reddetti. Sistem Ayarları > Genel > Giriş Öğeleri'nden açabilirsiniz.",
                     "macOS refused. You can switch it on in System Settings > General > Login Items.")
        }
        loginItem = SMAppService.mainApp.status == .enabled
    }

    /// Mask (or restore) whatever text is on the clipboard and put the result back on it.
    func clipboard(restore: Bool) async {
        let pb = NSPasteboard.general
        guard let text = pb.string(forType: .string), !text.isEmpty else {
            note = L("Panoda metin yok.", "The clipboard has no text.")
            return
        }
        busy = true
        defer { busy = false }
        do {
            let out: String
            if restore {
                let r = try await client.restore(text)
                if r.placeholdersRestored == 0 {
                    note = L("Panodaki metinde bu Mac'in bildiği bir yer tutucu yok; pano değişmedi. Bir davaya aitse Katip penceresinde Geri çevir'i kullanın.",
                             "The clipboard has no placeholder this Mac knows; it's unchanged. If it belongs to a case, use Restore in the Katip window.")
                    return
                }
                out = r.text
                note = L("\(r.placeholdersRestored) değer geri kondu. Panoda artık gerçek adlar var.",
                         "Put back \(r.placeholdersRestored) values. The clipboard now holds the real names.")
            } else {
                let m = try await client.mask(text)
                out = m.maskedText
                note = L("\(m.placeholders.count) değer gizlendi. Panoda artık maskeli metin var.",
                         "Hid \(m.placeholders.count) values. The clipboard now holds the masked text.")
            }
            pb.clearContents()
            pb.setString(out, forType: .string)
        } catch {
            note = error.localizedDescription
        }
        await refreshStatus()
    }
}

/// What each masking profile is for, in the lawyer's words.
enum Profile: String, CaseIterable, Identifiable {
    case ai, court, anon, eu
    var id: String { rawValue }
    var title: String {
        switch self {
        case .ai: return L("Yapay zekâ ile paylaşım", "Sharing with AI")
        case .court: return L("Mahkemeye sunum", "Court filing")
        case .anon: return L("Tam anonim", "Full anonymisation")
        case .eu: return L("AB / GDPR", "EU / GDPR")
        }
    }
    var detail: String {
        switch self {
        case .ai: return L("Tüm kişisel veriler, adresler, dava ve baro numaraları gizlenir.",
                           "All personal data, addresses, case and bar numbers are hidden.")
        case .court: return L("Tarafların adres ve iletişim bilgileri gizlenir; dosya numarası ve tarihler kalır.",
                              "Parties' addresses and contact details are hidden; file numbers and dates stay.")
        case .anon: return L("Ek olarak tarihler, yerler ve kurumlar da gizlenir. Yayın ve makale için.",
                             "Also hides dates, places and institutions. For publishing.")
        case .eu: return L("Yapay zekâ profiline ek olarak AB kimlik ve KDV numaraları, yabancı adlar.",
                           "As for AI, plus EU ID and VAT numbers and non-Turkish names.")
        }
    }
}

/// The models in the lawyer's words.
func modelTitle(_ name: String) -> String {
    switch name {
    case "nano": return "Nano"
    case "mini": return "Mini"
    case "base": return "Base"
    default: return URL(fileURLWithPath: name).lastPathComponent  // a model folder the lawyer added
    }
}

func modelDetail(_ m: E.ModelInfo) -> String {
    if m.custom {
        return m.downloaded ? L("\(Int(m.sizeMb.rounded())) MB · eklediğiniz klasör: \(prettyPath(m.name))",
                                "\(Int(m.sizeMb.rounded())) MB · your folder: \(prettyPath(m.name))")
                            : L("Klasör bulunamadı ya da model eksik: \(prettyPath(m.name))",
                                "Folder missing or not a complete model: \(prettyPath(m.name))")
    }
    switch m.name {
    case "nano": return L("Uygulamayla gelir. En hızlısı; adları biraz daha sık kaçırır.",
                          "Comes with the app. Fastest; misses names a little more often.")
    case "mini": return L("\(Int(m.sizeMb)) MB. Eski bilgisayarlar için iyi bir denge.",
                          "\(Int(m.sizeMb)) MB. A good balance for older computers.")
    default: return L("\(Int(m.sizeMb)) MB. En doğrusu; çoğu Mac için önerilir.",
                      "\(Int(m.sizeMb)) MB. Most accurate; recommended for most Macs.")
    }
}

/// "[AD SOYAD-1]", "[AD SOYAD-2]", "[T.C. KİMLİK NO-1]" -> "2 AD SOYAD · 1 T.C. KİMLİK NO"
func summarize(_ placeholders: [String]) -> String {
    var counts: [String: Int] = [:]
    for p in placeholders {
        var s = p.trimmingCharacters(in: CharacterSet(charactersIn: "[]"))
        if let dash = s.lastIndex(of: "-"), Int(s[s.index(after: dash)...]) != nil { s = String(s[..<dash]) }
        counts[s, default: 0] += 1
    }
    return counts.sorted { $0.value > $1.value }.map { "\($0.value) \($0.key)" }.joined(separator: " · ")
}
