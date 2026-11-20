import Foundation

/// One masked document. The original text and the placeholder map stay on this device (see SessionStore).
struct MaskSession: Codable, Identifiable, Hashable {
    var id = UUID()
    var title: String
    var created = Date()
    var source: Source
    var profile: String
    var model: KatipModel
    var original: String
    var masked: String
    var mapping: [String: String]
    var spans: [FoundSpan]
    var allow: [String] = []
    var deny: [String] = []
    var engineModel: String?
    var ocrNote: String?
    var ocr = false
    var answers: [Answer] = []

    enum Source: String, Codable { case file, scan, paste, sample }

    struct Answer: Codable, Hashable, Identifiable {
        var id = UUID()
        var date = Date()
        var restored: String
    }

    /// How many values of each type were masked, most first.
    var counts: [TypeCount] {
        Dictionary(grouping: spans, by: \.type).map { TypeCount(type: $0.key, n: $0.value.count) }
            .sorted { $0.n > $1.n || ($0.n == $1.n && $0.type < $1.type) }
    }

    /// Distinct masked values with their placeholders, in document order.
    var values: [MaskedValue] {
        var seen = Set<String>(), out: [MaskedValue] = []
        let byValue = Dictionary(mapping.map { ($0.value, $0.key) }, uniquingKeysWith: { a, _ in a })
        for s in spans {
            let v = s.text.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !seen.contains(v) else { continue }
            seen.insert(v)
            out.append(MaskedValue(placeholder: byValue[v] ?? "", value: v, type: s.type))
        }
        return out
    }
}

struct TypeCount: Hashable { let type: String; let n: Int }
struct MaskedValue: Hashable { let placeholder: String; let value: String; let type: String }
