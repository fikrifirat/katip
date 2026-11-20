import UIKit
import UniformTypeIdentifiers

/// Sends masked text to ChatGPT or Claude. Only the masked text leaves Katip; the placeholder map never does.
///
/// The masked text is put on the clipboard as local-only (not synced to the lawyer's Mac by Universal Clipboard)
/// and expires after 10 minutes. Short documents are also pre-filled through the providers' `?q=` web links,
/// which open the app when it is installed. Long ones are pasted by the lawyer.
enum AIHandoff {
    enum Target: String, CaseIterable, Identifiable {
        case chatgpt, claude
        var id: String { rawValue }
        var name: String { self == .chatgpt ? "ChatGPT" : "Claude" }
        var base: String { self == .chatgpt ? "https://chatgpt.com/" : "https://claude.ai/new" }
    }

    /// Longest URL we pre-fill. Longer prompts are pasted from the clipboard instead.
    static let maxPrefill = 6000
    static let clipboardLifetime: TimeInterval = 600

    static func prompt(task: String, masked: String) -> String {
        let ask = task.trimmingCharacters(in: .whitespacesAndNewlines)
        let note = L("Not: Bu metindeki kişisel veriler [AD SOYAD-1] gibi yer tutucularla maskelendi. Cevabında yer tutucuları aynen, köşeli parantezleriyle koru; gerçek değerleri tahmin etmeye çalışma.",
                     "Note: personal data in this text was replaced with placeholders such as [AD SOYAD-1]. Keep the placeholders exactly as they are, with their brackets, and do not try to guess the real values.")
        return [ask.isEmpty ? nil : ask, note, "---", masked].compactMap { $0 }.joined(separator: "\n\n")
    }

    static func copy(_ text: String) {
        UIPasteboard.general.setItems([[UTType.utf8PlainText.identifier: text]],
                                      options: [.localOnly: true, .expirationDate: Date().addingTimeInterval(clipboardLifetime)])
    }

    /// Copies the prompt and opens the provider. Returns true if the prompt was pre-filled (no paste needed).
    @MainActor @discardableResult
    static func send(_ prompt: String, to target: Target) async -> Bool {
        copy(prompt)
        var comps = URLComponents(string: target.base)!
        var prefilled = false
        if let q = prompt.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed), q.count <= maxPrefill {
            comps.queryItems = [URLQueryItem(name: "q", value: prompt)]
            prefilled = true
        }
        _ = await UIApplication.shared.open(comps.url!)
        return prefilled
    }
}
