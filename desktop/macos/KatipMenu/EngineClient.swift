import Foundation

/// Speak Turkish on a Turkish Mac, English elsewhere. Every string the lawyer sees goes through this.
let isTurkish: Bool = (Locale.preferredLanguages.first ?? "en").hasPrefix("tr")
func L(_ tr: String, _ en: String) -> String { isTurkish ? tr : en }

/// Talks to the Katip engine on 127.0.0.1. The port and token come from ~/.katip/engine.json, which only this
/// user can read. Starting and stopping go through launchd, so the engine runs (and exits when idle) on its own.
struct EngineClient {
    static let label = "com.fikrifirat.katip.engine"

    // MARK: what the engine sends back (snake_case in JSON, converted on decode)
    struct State: Decodable { let port: Int; let token: String; let pid: Int }

    struct Status: Decodable {
        let version: String
        let pid: Int
        let uptimeS: Double
        let served: Int
        let rssPeakMb: Double
        let model: String
        let vault: String
    }

    struct Settings: Decodable, Equatable {
        var model: String
        var defaultProfile: String
        var emsalOnline: Bool
        var documentsFolder: String
        var includeDownloads: Bool
        var firstRunDone: Bool
    }

    struct ModelInfo: Decodable, Identifiable, Equatable {
        let name: String
        let sizeMb: Double
        let downloaded: Bool
        let included: Bool
        let recommended: Bool
        let current: Bool
        var id: String { name }
    }

    struct Download: Decodable, Equatable {
        let name: String
        let state: String
        let done: Int
        let total: Int
        let error: String?
        var fraction: Double { total > 0 ? Double(done) / Double(total) : 0 }
    }

    struct Models: Decodable, Equatable {
        let current: String
        let models: [ModelInfo]
        let download: Download?
    }

    struct Matter: Decodable, Identifiable, Equatable {
        let matter: String
        let lastUsed: Double
        let expires: Double
        var id: String { matter }
    }

    struct Matters: Decodable { let matters: [Matter] }

    struct ClaudeState: Decodable, Equatable {
        struct Desktop: Decodable, Equatable {
            let installed: Bool
            let connected: Bool
            let stale: Bool
            let brokenConfig: Bool
            let `extension`: Bool
        }
        struct Code: Decodable, Equatable { let installed: Bool; let connected: Bool; let stale: Bool }
        let desktop: Desktop
        let code: Code
    }

    struct ClaudeChange: Decodable { let app: String; let connected: Bool; let restartNeeded: Bool }

    struct Masked: Decodable {
        let maskedText: String
        let placeholders: [String]
        let page: Int?
        let pages: Int?
        let fileName: String?
    }

    struct Restored: Decodable { let text: String; let placeholdersRestored: Int }

    enum Failure: LocalizedError {
        case notRunning, refused(String), didNotStart, busy
        var errorDescription: String? {
            switch self {
            case .notRunning: return L("Katip motoru çalışmıyor.", "The Katip engine is not running.")
            case .refused(let why): return why
            case .busy: return L("Katip hâlâ çalışıyor (büyük ya da taranmış belgeler birkaç dakika sürebilir). Biraz sonra yeniden deneyin.",
                                 "Katip is still working (large or scanned documents can take a few minutes). Try again shortly.")
            case .didNotStart: return L("Katip motoru başlamadı. Ayrıntı için motor kaydına bakın.",
                                        "The Katip engine did not start. The engine log says why.")
            }
        }
    }

    // MARK: places on disk
    static var home: URL {
        if let h = ProcessInfo.processInfo.environment["KATIP_HOME"] { return URL(fileURLWithPath: h) }
        return FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".katip")
    }

    static var logURL: URL {
        FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Logs/Katip/engine.log")
    }

    /// The engine that ships inside Katip.app (Contents/Resources/engine), with its own Python.
    static var bundledEngine: URL? {
        guard let u = Bundle.main.resourceURL?.appendingPathComponent("engine/katip-engine"),
              FileManager.default.isExecutableFile(atPath: u.path) else { return nil }
        return u
    }

    static var agentPlist: URL {
        FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/LaunchAgents/\(label).plist")
    }

    func state() -> State? {
        guard let data = try? Data(contentsOf: Self.home.appendingPathComponent("engine.json")) else { return nil }
        return try? JSONDecoder().decode(State.self, from: data)
    }

    // MARK: HTTP
    private static let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()

    private func raw<T: Decodable>(_ path: String, body: [String: Any]?, timeout: TimeInterval) async throws -> T {
        guard let st = state() else { throw Failure.notRunning }
        var req = URLRequest(url: URL(string: "http://127.0.0.1:\(st.port)\(path)")!, timeoutInterval: timeout)
        req.setValue("Bearer \(st.token)", forHTTPHeaderField: "Authorization")
        if let body {
            req.httpMethod = "POST"
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try JSONSerialization.data(withJSONObject: body)
        }
        let (data, resp): (Data, URLResponse)
        do { (data, resp) = try await URLSession.shared.data(for: req) } catch let e as URLError {
            switch e.code {
            case .cannotConnectToHost, .cannotFindHost, .networkConnectionLost, .notConnectedToInternet:
                throw Failure.notRunning  // nothing listening: the engine stopped
            case .timedOut:
                throw Failure.busy
            default:
                throw Failure.refused(e.localizedDescription)
            }
        }
        guard let http = resp as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            let msg = (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["error"] as? String
            throw Failure.refused(msg ?? L("Motor isteği reddetti.", "The engine refused the request."))
        }
        return try Self.decoder.decode(T.self, from: data)
    }

    /// A call that starts the engine first if it went idle and stopped.
    func call<T: Decodable>(_ path: String, body: [String: Any]? = nil, timeout: TimeInterval = 120) async throws -> T {
        do { return try await raw(path, body: body, timeout: timeout) } catch Failure.notRunning {
            try await start()
            return try await raw(path, body: body, timeout: timeout)
        }
    }

    /// Status without starting anything: a stopped engine stays stopped.
    func status() async -> Status? { try? await raw("/v1/status", body: nil, timeout: 3) }

    func mask(_ text: String, profile: String? = nil, matter: String = "default") async throws -> Masked {
        var b: [String: Any] = ["text": text, "matter": matter]
        if let profile { b["profile"] = profile }
        return try await call("/v1/mask", body: b)
    }

    /// Every page of a file, joined (the engine pages long documents).
    func maskFile(_ url: URL, profile: String? = nil, matter: String = "default") async throws -> Masked {
        var b: [String: Any] = ["path": url.path, "matter": matter]
        if let profile { b["profile"] = profile }
        let first: Masked = try await call("/v1/mask_file", body: b, timeout: 600)
        guard let pages = first.pages, pages > 1 else { return first }
        var text = first.maskedText
        var ph = Set(first.placeholders)
        for p in 2...pages {
            b["page"] = p
            let next: Masked = try await call("/v1/mask_file", body: b, timeout: 600)
            text += next.maskedText
            ph.formUnion(next.placeholders)
        }
        return Masked(maskedText: text, placeholders: ph.sorted(), page: 1, pages: pages, fileName: first.fileName)
    }

    func restore(_ text: String, matter: String = "default") async throws -> Restored {
        try await call("/v1/restore", body: ["text": text, "matter": matter])
    }

    // MARK: launchd
    /// Register the bundled engine with launchd when no agent points at it yet: on first start, and again after
    /// the app was moved or updated, or runs with another KATIP_HOME. An agent installed from the repo is replaced.
    func ensureAgent() throws {
        guard let engine = Self.bundledEngine else { return }
        if let data = try? Data(contentsOf: Self.agentPlist),
           let plist = try? PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any],
           let args = plist["ProgramArguments"] as? [String], args.first == engine.path,
           (plist["EnvironmentVariables"] as? [String: String])?["KATIP_HOME"] == ProcessInfo.processInfo.environment["KATIP_HOME"] {
            return
        }
        let p = Process()
        p.executableURL = engine
        p.arguments = ["install"]
        p.standardOutput = FileHandle.nullDevice
        try p.run()
        p.waitUntilExit()
    }

    /// Make sure the agent exists, `launchctl kickstart` it, then wait until it answers.
    func start() async throws {
        if await status() != nil { return }
        try ensureAgent()
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/launchctl")
        // -k: an engine that is running but can't be reached (its state file is gone) is restarted, not waited on
        p.arguments = ["kickstart", "-k", "gui/\(getuid())/\(Self.label)"]
        p.standardError = FileHandle.nullDevice
        try p.run()
        p.waitUntilExit()
        for _ in 0..<150 {
            if await status() != nil { return }
            try await Task.sleep(nanoseconds: 200_000_000)
        }
        throw Failure.didNotStart
    }

    func stop() async {
        struct Ack: Decodable { let stopping: Bool }
        let _: Ack? = try? await raw("/v1/shutdown", body: [:], timeout: 3)
    }
}
