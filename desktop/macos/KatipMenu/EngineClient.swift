import Foundation

/// Talks to the Katip engine on 127.0.0.1. The port and token come from ~/.katip/engine.json, which only this
/// user can read. Starting and stopping go through launchd, so the engine runs (and exits when idle) on its own.
struct EngineClient {
    static let label = "com.fikrifirat.katip.engine"

    struct State: Decodable { let port: Int; let token: String; let pid: Int }

    struct Status: Decodable {
        let version: String
        let pid: Int
        let uptime_s: Double
        let served: Int
        let rss_peak_mb: Double
        let model: String
        let vault: String
    }

    struct Masked: Decodable {
        let masked_text: String
        let placeholders: [String]
        let ms: Double
    }

    struct Restored: Decodable { let text: String; let placeholders_restored: Int }

    enum Failure: LocalizedError {
        case notRunning, refused(String), didNotStart
        var errorDescription: String? {
            switch self {
            case .notRunning: return "The Katip engine is not running."
            case .refused(let why): return why
            case .didNotStart: return "The Katip engine did not start. Run `katip-engine install` once, then try again."
            }
        }
    }

    static var home: URL {
        if let h = ProcessInfo.processInfo.environment["KATIP_HOME"] { return URL(fileURLWithPath: h) }
        return FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".katip")
    }

    static var logURL: URL {
        FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Logs/Katip/engine.log")
    }

    func state() -> State? {
        guard let data = try? Data(contentsOf: Self.home.appendingPathComponent("engine.json")) else { return nil }
        return try? JSONDecoder().decode(State.self, from: data)
    }

    private func call<T: Decodable>(_ path: String, body: [String: Any]? = nil, timeout: TimeInterval = 60) async throws -> T {
        guard let st = state() else { throw Failure.notRunning }
        var req = URLRequest(url: URL(string: "http://127.0.0.1:\(st.port)\(path)")!, timeoutInterval: timeout)
        req.setValue("Bearer \(st.token)", forHTTPHeaderField: "Authorization")
        if let body {
            req.httpMethod = "POST"
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try JSONSerialization.data(withJSONObject: body)
        }
        let (data, resp) : (Data, URLResponse)
        do { (data, resp) = try await URLSession.shared.data(for: req) } catch { throw Failure.notRunning }
        guard let http = resp as? HTTPURLResponse, http.statusCode == 200 else {
            let msg = (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["error"] as? String
            throw Failure.refused(msg ?? "The engine refused the request.")
        }
        return try JSONDecoder().decode(T.self, from: data)
    }

    func status() async -> Status? { try? await call("/v1/status", timeout: 3) }

    func mask(_ text: String, profile: String = "ai", matter: String = "default") async throws -> Masked {
        try await call("/v1/mask", body: ["text": text, "profile": profile, "matter": matter])
    }

    func restore(_ text: String, matter: String = "default") async throws -> Restored {
        try await call("/v1/restore", body: ["text": text, "matter": matter])
    }

    /// `launchctl kickstart` the agent, then wait until it answers.
    func start() async throws {
        if await status() != nil { return }
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/launchctl")
        p.arguments = ["kickstart", "gui/\(getuid())/\(Self.label)"]
        try p.run()
        p.waitUntilExit()
        for _ in 0..<100 {
            if await status() != nil { return }
            try await Task.sleep(nanoseconds: 200_000_000)
        }
        throw Failure.didNotStart
    }

    func stop() async {
        struct Ack: Decodable { let stopping: Bool }
        let _: Ack? = try? await call("/v1/shutdown", body: [:], timeout: 3)
    }
}
