import Foundation
import PDFKit
import UIKit
import UniformTypeIdentifiers
import Vision

/// Text from what the lawyer brings in. Everything runs on the device: PDFKit for text PDFs, Apple's Vision
/// text recogniser for scans and photos, the engine's own reader for .docx and .udf.
struct ReadResult {
    var text: String
    var title: String
    var ocr: Bool              // text came from OCR: the engine also catches misread ID numbers there
    var note: String?          // shown to the lawyer, e.g. "OCR without Turkish support"
}

enum ReadError: LocalizedError {
    case unsupported(String), empty
    var errorDescription: String? {
        switch self {
        case let .unsupported(ext): return L("Bu dosya türü desteklenmiyor: .\(ext). PDF, Word (.docx), UYAP (.udf), metin veya fotoğraf seçin.",
                                             "This file type is not supported: .\(ext). Pick a PDF, Word (.docx), UYAP (.udf), text file or photo.")
        case .empty: return L("Belgede okunabilir metin bulunamadı.", "No readable text was found in the document.")
        }
    }
}

extension UTType {
    static let udf = UTType(importedAs: "com.fikrifirat.katip.udf", conformingTo: .data)
    static let docx = UTType("org.openxmlformats.wordprocessingml.document") ?? .data
}

enum DocumentReader {
    static let importable: [UTType] = [.pdf, .docx, .udf, .plainText, .utf8PlainText, .image]

    @MainActor
    static func read(url: URL, engine: MaskEngine, ocrLanguage: String = "tr") async throws -> ReadResult {
        let scoped = url.startAccessingSecurityScopedResource()
        defer {
            if scoped { url.stopAccessingSecurityScopedResource() }
            // Files opened from other apps are copied into our Documents/Inbox. Don't keep the unmasked copy.
            if url.path.contains("/Documents/Inbox/") { try? FileManager.default.removeItem(at: url) }
        }
        let title = url.deletingPathExtension().lastPathComponent
        let ext = url.pathExtension.lowercased()
        let data = try Data(contentsOf: url)
        var r: ReadResult
        switch ext {
        case "pdf": r = try await pdf(data, title: title, ocrLanguage: ocrLanguage)
        case "docx": r = ReadResult(text: try await engine.extract(data, kind: "docx"), title: title, ocr: false)
        case "udf": r = ReadResult(text: try await engine.extract(data, kind: "udf"), title: title, ocr: false)
        case "txt", "text", "md": r = ReadResult(text: decode(data), title: title, ocr: false)
        case "jpg", "jpeg", "png", "heic", "heif", "tif", "tiff":
            guard let img = UIImage(data: data)?.cgImage else { throw ReadError.empty }
            let (t, note) = try await ocr([img], language: ocrLanguage)
            r = ReadResult(text: t, title: title, ocr: true, note: note)
        default: throw ReadError.unsupported(ext)
        }
        if r.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { throw ReadError.empty }
        return r
    }

    /// UTF-8, else Windows-1254 (Turkish), which older Word/Notepad exports use.
    static func decode(_ data: Data) -> String {
        if let s = String(data: data, encoding: .utf8) { return s }
        let tr = String.Encoding(rawValue: CFStringConvertEncodingToNSStringEncoding(CFStringEncoding(CFStringEncodings.windowsLatin5.rawValue)))
        return String(data: data, encoding: tr) ?? String(decoding: data, as: UTF8.self)
    }

    /// Text layer if the PDF has one; otherwise each page is rendered and read with OCR.
    static func pdf(_ data: Data, title: String, ocrLanguage: String = "tr") async throws -> ReadResult {
        guard let doc = PDFDocument(data: data) else { throw ReadError.empty }
        let text = (0 ..< doc.pageCount).compactMap { doc.page(at: $0)?.string }.joined(separator: "\n\n")
        if text.filter({ $0.isLetter }).count > 20 * max(1, doc.pageCount) / 2 {
            return ReadResult(text: text, title: title, ocr: false)
        }
        var images: [CGImage] = []
        for i in 0 ..< doc.pageCount {
            guard let page = doc.page(at: i) else { continue }
            let box = page.bounds(for: .mediaBox)
            let scale: CGFloat = 2.5
            let img = UIGraphicsImageRenderer(size: CGSize(width: box.width * scale, height: box.height * scale)).image { ctx in
                UIColor.white.setFill()
                ctx.fill(CGRect(origin: .zero, size: CGSize(width: box.width * scale, height: box.height * scale)))
                ctx.cgContext.translateBy(x: 0, y: box.height * scale)
                ctx.cgContext.scaleBy(x: scale, y: -scale)
                page.draw(with: .mediaBox, to: ctx.cgContext)
            }
            if let cg = img.cgImage { images.append(cg) }
        }
        let (t, note) = try await ocr(images, language: ocrLanguage)
        return ReadResult(text: t, title: title, ocr: true, note: note)
    }

    /// Apple Vision OCR, on the device. Turkish ("tr", the default) or Dutch ("nl", for Letter explained) is used
    /// when this iOS version supports it.
    static func ocr(_ images: [CGImage], language: String = "tr") async throws -> (String, String?) {
        try await Task.detached(priority: .userInitiated) {
            var pages: [String] = []
            var note: String?
            for img in images {
                let req = VNRecognizeTextRequest()
                req.recognitionLevel = .accurate
                req.usesLanguageCorrection = true
                let supported = (try? req.supportedRecognitionLanguages()) ?? []
                if let lang = supported.first(where: { $0.hasPrefix(language) }) {
                    req.recognitionLanguages = [lang, "en-US"]
                } else if language != "tr" {
                    req.automaticallyDetectsLanguage = true
                } else {
                    req.automaticallyDetectsLanguage = true
                    note = L("Bu iOS sürümünde Türkçe metin tanıma yok; ç, ğ, ı, ş gibi harfler yanlış okunabilir. Maskeyi dikkatle kontrol edin.",
                             "This iOS version has no Turkish text recognition; letters such as ç, ğ, ı, ş may be misread. Check the masking carefully.")
                }
                try VNImageRequestHandler(cgImage: img).perform([req])
                let lines = (req.results ?? []).compactMap { $0.topCandidates(1).first?.string }
                pages.append(lines.joined(separator: "\n"))
            }
            return (pages.joined(separator: "\n\n"), note)
        }.value
    }
}
