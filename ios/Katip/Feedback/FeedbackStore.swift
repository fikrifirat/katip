import Foundation

/// Verdicts on masked documents, kept on this phone until the lawyer exports them (feedback-block/SPEC.md,
/// "Masking block"). A record holds types, counts and corrections, never a value or any document text.
@MainActor
final class FeedbackStore: ObservableObject {
    struct Record: Codable, Hashable {
        struct Corrections: Codable, Hashable { let acilan: Int; let eklenen: Int; let baglam: Int }
        let result_id: String
        let gorev: String           // "maskeleme"
        let puan: Int
        let profil: String
        let model: String
        let turler: [String: Int]
        let duzeltme: Corrections
        let t: Date
    }

    static let format = "katip-mask-feedback/1"
    @Published private(set) var records: [String: Record] = [:]   // latest verdict per result_id wins
    private let url: URL

    init() {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("Katip", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        url = dir.appendingPathComponent("feedback.json")
        let dec = JSONDecoder(); dec.dateDecodingStrategy = .iso8601
        if let d = try? Data(contentsOf: url), let r = try? dec.decode([String: Record].self, from: d) { records = r }
    }

    func save(_ r: Record) throws {
        var next = records
        next[r.result_id] = r
        let enc = JSONEncoder(); enc.dateEncodingStrategy = .iso8601
        try enc.encode(next).write(to: url, options: [.atomic, .completeFileProtection])
        records = next
    }

    /// JSON Lines file for the lawyer to share when they choose; nothing is uploaded automatically.
    func exportFile() throws -> URL {
        let enc = JSONEncoder(); enc.dateEncodingStrategy = .iso8601; enc.outputFormatting = .sortedKeys
        var lines = [#"{"format":"\#(Self.format)"}"#]
        for r in records.values.sorted(by: { $0.t < $1.t }) { lines.append(String(decoding: try enc.encode(r), as: UTF8.self)) }
        let out = FileManager.default.temporaryDirectory.appendingPathComponent("katip-mask-feedback.jsonl")
        try lines.joined(separator: "\n").appending("\n").write(to: out, atomically: true, encoding: .utf8)
        return out
    }
}

enum MaskVerdicts {
    /// Masking verdicts from SPEC.md, same 0/1/2 scale and colours as the precedent block.
    static let all: [Verdict] = [
        Verdict(puan: 0, label: L("Eksik", "Missed some")),
        Verdict(puan: 1, label: L("Fazla", "Too much")),
        Verdict(puan: 2, label: L("Doğru", "Correct")),
    ]
}
