import Foundation
import SwiftUI
import WebKit

/// One detected value, as the engine returns it.
struct FoundSpan: Codable, Hashable {
    let type: String
    let start: Int   // UTF-16 offsets into the original text
    let end: Int
    let text: String
    let score: Double
    let recognizer: String
}

struct MaskOutput: Codable {
    let ok: Bool
    let text: String?
    let mapping: [String: String]?
    let model: String?
    let ms: Int?
    let spans: [FoundSpan]?
    let leak: Bool?
    let kinds: [String]?
    let lines: [Int]?
    let error: String?
}

struct RestoreOutput: Codable {
    let text: String
    /// Placeholder-looking tokens in the answer that are not in this document's map.
    let unknown: [String]
}

enum EngineError: LocalizedError {
    case notReady, leak(kinds: [String], lines: [Int]), js(String)
    var errorDescription: String? {
        switch self {
        case .notReady: return L("Maskeleme motoru açılamadı.", "The masking engine could not start.")
        case let .leak(kinds, lines):
            return L("Maskeleme durduruldu: bulunan bir değer (\(kinds.joined(separator: ", "))) satır \(lines.map(String.init).joined(separator: ", ")) içinde hâlâ okunur kalacaktı. Metin paylaşılmadı.",
                     "Masking stopped: a detected value (\(kinds.joined(separator: ", "))) would stay readable on line \(lines.map(String.init).joined(separator: ", ")). Nothing was shared.")
        case let .js(m): return m
        }
    }
}

/// The katip-mask engine (rules + Katip Mask Mini/Nano), running in a hidden, offline WKWebView.
/// It is the same code as the web app, the npm/PyPI packages and Katip Kalkan, so output matches them.
@MainActor
final class MaskEngine: ObservableObject {
    @Published private(set) var ready = false
    @Published private(set) var failure: String?

    let webView: WKWebView
    private let handler = EngineSchemeHandler()
    private var readyWaiters: [CheckedContinuation<Void, Error>] = []

    init() {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()          // no cookies, caches or storage on disk
        config.setURLSchemeHandler(handler, forURLScheme: EngineSchemeHandler.scheme)
        config.suppressesIncrementalRendering = true
        webView = WKWebView(frame: CGRect(x: 0, y: 0, width: 1, height: 1), configuration: config)
        webView.isHidden = true
        #if DEBUG
        if #available(iOS 16.4, *) { webView.isInspectable = true }
        #endif
        webView.load(URLRequest(url: EngineSchemeHandler.indexURL))
        Task { await waitForEngine() }
    }

    private func waitForEngine() async {
        for _ in 0 ..< 200 {
            if let ok = try? await webView.callAsyncJavaScript("return !!window.katip", contentWorld: .page) as? Bool, ok {
                ready = true
                readyWaiters.forEach { $0.resume() }
                readyWaiters.removeAll()
                return
            }
            try? await Task.sleep(nanoseconds: 50_000_000)
        }
        failure = EngineError.notReady.localizedDescription
        readyWaiters.forEach { $0.resume(throwing: EngineError.notReady) }
        readyWaiters.removeAll()
    }

    private func untilReady() async throws {
        if ready { return }
        if failure != nil { throw EngineError.notReady }
        try await withCheckedThrowingContinuation { readyWaiters.append($0) }
    }

    /// Calls `window.katip[fn](args)` and decodes its JSON result.
    private func call<T: Decodable>(_ fn: String, _ args: [String: Any], as: T.Type) async throws -> T {
        try await untilReady()
        do {
            let raw = try await webView.callAsyncJavaScript(
                "return JSON.stringify(await window.katip[fn](args))",
                arguments: ["fn": fn, "args": args], contentWorld: .page)
            guard let s = raw as? String else { throw EngineError.js("empty result from \(fn)") }
            return try JSONDecoder().decode(T.self, from: Data(s.utf8))
        } catch let e as EngineError {
            throw e
        } catch {
            throw EngineError.js((error as NSError).userInfo["WKJavaScriptExceptionMessage"] as? String ?? error.localizedDescription)
        }
    }

    func warm(model: KatipModel) async {
        guard model != .rules else { return }
        _ = try? await call("warm", ["model": model.rawValue], as: Bool.self)
    }

    func mask(_ text: String, profile: String, model: KatipModel, allow: [String] = [], deny: [String] = [], ocr: Bool = false) async throws -> MaskOutput {
        var args: [String: Any] = ["text": text, "profile": profile, "allow": allow, "deny": deny, "ocr": ocr]
        args["model"] = model == .rules ? NSNull() : model.rawValue
        let out = try await call("mask", args, as: MaskOutput.self)
        if out.leak == true { throw EngineError.leak(kinds: out.kinds ?? [], lines: out.lines ?? []) }
        return out
    }

    func restore(_ text: String, mapping: [String: String]) async throws -> RestoreOutput {
        try await call("restore", ["text": text, "mapping": mapping], as: RestoreOutput.self)
    }

    /// Plain text of a .docx or .udf file (same walk as the web app).
    func extract(_ data: Data, kind: String) async throws -> String {
        struct Out: Decodable { let text: String }
        return try await call("extract", ["base64": data.base64EncodedString(), "kind": kind], as: Out.self).text
    }
}

enum KatipModel: String, CaseIterable, Identifiable, Codable {
    case mini, nano, rules
    var id: String { rawValue }
    var title: String {
        switch self {
        case .mini: return "Katip Mask Mini"
        case .nano: return "Katip Mask Nano"
        case .rules: return L("Yalnızca kurallar", "Rules only")
        }
    }
    var detail: String {
        switch self {
        case .mini: return L("Önerilen. Gündelik metindeki isimleri de bulur. Sayfa başına yaklaşık 1 sn.", "Recommended. Also finds names in everyday text. About 1 s per page.")
        case .nano: return L("Hızlı mod. Mahkeme metninde iyi, dilekçe ve e-postada Mini'den fazla isim kaçırır.", "Fast mode. Good on court text, misses more names than Mini in petitions and e-mails.")
        case .rules: return L("Kimlik no, IBAN, telefon gibi kalıplar ve isim listeleri. İsim kaçırma riski en yüksek.", "Patterns such as ID numbers, IBAN and phone, plus name lists. Most likely to miss names.")
        }
    }
}

/// Keeps the engine's WKWebView inside the view hierarchy so WebKit does not suspend it.
struct EngineHost: UIViewRepresentable {
    let engine: MaskEngine
    func makeUIView(context: Context) -> WKWebView { engine.webView }
    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
