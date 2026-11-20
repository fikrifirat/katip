import CryptoKit
import Foundation
import WebKit

/// Serves the offline engine (index.html, engine.js, onnxruntime-web, models) from the app bundle under
/// `katip-engine://app/`. Nothing else is reachable: the page's CSP allows only this origin, and model files are
/// served only when their SHA-256 matches `models/manifest.json` (built from sdk/spec/models.json).
final class EngineSchemeHandler: NSObject, WKURLSchemeHandler {
    static let scheme = "katip-engine"
    static let indexURL = URL(string: "\(scheme)://app/index.html")!

    private let root: URL
    private var verified = Set<String>()
    private let manifest: [String: [String: String]]
    private let lock = NSLock()

    override init() {
        root = Bundle.main.resourceURL!.appendingPathComponent("Engine", isDirectory: true).standardizedFileURL
        let data = (try? Data(contentsOf: root.appendingPathComponent("models/manifest.json"))) ?? Data("{}".utf8)
        manifest = (try? JSONDecoder().decode([String: [String: String]].self, from: data)) ?? [:]
        super.init()
    }

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        guard let url = task.request.url else { return fail(task, 400) }
        let file = root.appendingPathComponent(String(url.path.drop(while: { $0 == "/" }))).standardizedFileURL
        guard file.path.hasPrefix(root.path + "/"), let data = try? Data(contentsOf: file, options: .mappedIfSafe) else {
            return fail(task, 404)
        }
        let rel = String(file.path.dropFirst(root.path.count + 1))
        if rel.hasPrefix("models/"), rel != "models/manifest.json", !check(rel, data) { return fail(task, 403) }
        let headers = [
            "Content-Type": Self.mime(file.pathExtension),
            "Content-Length": String(data.count),
            "Cache-Control": "no-store",
        ]
        let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: headers)!
        task.didReceive(response)
        task.didReceive(data)
        task.didFinish()
    }

    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {}

    /// models/<name>/<file> must match the pinned hash. Checked once per file per launch.
    private func check(_ rel: String, _ data: Data) -> Bool {
        lock.lock(); defer { lock.unlock() }
        if verified.contains(rel) { return true }
        let parts = rel.split(separator: "/", maxSplits: 2).map(String.init)
        guard parts.count == 3, let want = manifest[parts[1]]?[parts[2]] else { return false }
        let got = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        guard got == want else { return false }
        verified.insert(rel)
        return true
    }

    private func fail(_ task: WKURLSchemeTask, _ status: Int) {
        let r = HTTPURLResponse(url: task.request.url ?? Self.indexURL, statusCode: status, httpVersion: "HTTP/1.1", headerFields: [:])!
        task.didReceive(r)
        task.didReceive(Data())
        task.didFinish()
    }

    private static func mime(_ ext: String) -> String {
        switch ext {
        case "html": return "text/html; charset=utf-8"
        case "js", "mjs": return "text/javascript; charset=utf-8"
        case "wasm": return "application/wasm"
        case "json": return "application/json"
        default: return "application/octet-stream"
        }
    }
}
