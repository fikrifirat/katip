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
    @Published var loginItem = SMAppService.mainApp.status == .enabled

    let client = EngineClient()
    var running: Bool { status != nil }

    func refreshStatus() async { status = await client.status() }

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
    default: return "Base"
    }
}

func modelDetail(_ m: E.ModelInfo) -> String {
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
