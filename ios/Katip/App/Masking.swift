import Foundation

/// The one flow every input goes through: read text -> mask on the device -> save.
@MainActor
enum Masking {
    static func start(_ read: ReadResult, source: MaskSession.Source, profile: String, model: KatipModel,
                      engine: MaskEngine, store: SessionStore) async throws -> MaskSession {
        let out = try await engine.mask(read.text, profile: profile, model: model, ocr: read.ocr)
        let s = MaskSession(title: read.title, source: source, profile: profile, model: model, original: read.text,
                            masked: out.text ?? "", mapping: out.mapping ?? [:], spans: out.spans ?? [],
                            engineModel: out.model, ocrNote: read.note, ocr: read.ocr)
        store.upsert(s)
        return s
    }

    /// Mask again after the lawyer changed the profile or the keep/add lists.
    static func redo(_ s: MaskSession, engine: MaskEngine, store: SessionStore) async throws -> MaskSession {
        let out = try await engine.mask(s.original, profile: s.profile, model: s.model, allow: s.allow, deny: s.deny, ocr: s.ocr)
        var n = s
        n.masked = out.text ?? ""
        n.mapping = out.mapping ?? [:]
        n.spans = out.spans ?? []
        n.engineModel = out.model
        store.upsert(n)
        return n
    }

    static func defaultTitle(_ source: MaskSession.Source) -> String {
        let d = Date().formatted(date: .abbreviated, time: .shortened)
        switch source {
        case .scan: return L("Tarama", "Scan") + " · " + d
        case .paste: return L("Yapıştırılan metin", "Pasted text") + " · " + d
        case .sample: return L("Örnek dilekçe (uydurma kişiler)", "Sample petition (made-up people)")
        case .file: return d
        }
    }
}
