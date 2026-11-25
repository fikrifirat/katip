import AppKit
import SwiftUI

// MARK: Folders: where Katip keeps things, each with Show in Finder

extension EngineClient {
    /// GET /v1/paths: where models, cases, MASAK lists, gazette pages and the log are kept.
    struct Paths: Decodable, Equatable {
        let katip: String
        let cases: String
        let documents: String
        let downloads: String
        let models: String
        let masak: String
        let gazette: String
        let precedents: String
        let log: String
        let claudeDesktop: String
    }
}

/// Opens a folder in Finder, or shows a file selected in its folder. Katip's own folders are made if missing, so the
/// button never opens nothing; the lawyer's folders (documents, Downloads) are never created.
@MainActor func reveal(_ path: String?, create: Bool = true) {
    guard let path, !path.isEmpty else { return }
    let url = URL(fileURLWithPath: (path as NSString).expandingTildeInPath)
    let fm = FileManager.default
    var dir: ObjCBool = false
    if fm.fileExists(atPath: url.path, isDirectory: &dir) {
        if dir.boolValue { NSWorkspace.shared.open(url) } else { NSWorkspace.shared.activateFileViewerSelecting([url]) }
        return
    }
    if url.pathExtension.isEmpty {
        if create { try? fm.createDirectory(at: url, withIntermediateDirectories: true) }
        if fm.fileExists(atPath: url.path) { NSWorkspace.shared.open(url); return }
    }
    let parent = url.deletingLastPathComponent()  // a file not written yet: open the folder it will go in
    if fm.fileExists(atPath: parent.path) { NSWorkspace.shared.open(parent) }
}

/// A small "Show in Finder" button for one of the engine's paths.
struct RevealButton: View {
    @EnvironmentObject var model: AppModel
    let key: KeyPath<E.Paths, String>
    var label = L("Finder'da göster", "Show in Finder")
    var create = true
    var body: some View {
        Button { Task { await model.refreshPaths(); reveal(model.paths?[keyPath: key], create: create) } } label: {
            Label(label, systemImage: "folder")
        }
        .help(model.paths.map { shortPath($0[keyPath: key]) } ?? "")
    }
}

func shortPath(_ p: String) -> String {
    let home = NSHomeDirectory()
    return p.hasPrefix(home) ? "~" + p.dropFirst(home.count) : p
}

struct FolderList: View {
    @EnvironmentObject var model: AppModel
    var rows: [(String, String, KeyPath<E.Paths, String>, Bool)] {
        [(L("Belge klasörü", "Documents folder"), "doc.on.doc", \.documents, false),
         (L("Davalar (şifreli anahtarlar)", "Cases (encrypted keys)"), "lock.rectangle.stack", \.cases, true),
         (L("Modeller", "Models"), "cpu", \.models, true),
         (L("MASAK listeleri", "MASAK lists"), "checkmark.shield", \.masak, true),
         (L("Gazete sayfaları", "Gazette pages"), "newspaper", \.gazette, true),
         (L("Emsal kararlar (önbellek)", "Precedents (cache)"), "building.columns", \.precedents, true),
         (L("Katip ayarları", "Katip settings"), "gearshape", \.katip, true),
         (L("Motor kaydı", "Engine log"), "doc.text", \.log, true),
         (L("Claude Desktop ayar dosyası", "Claude Desktop settings file"), "doc.badge.gearshape", \.claudeDesktop, false)]
    }
    var body: some View {
        ForEach(rows, id: \.0) { r in
            LabeledContent {
                RevealButton(key: r.2, label: L("Göster", "Show"), create: r.3).buttonStyle(.borderless)
            } label: {
                Label {
                    VStack(alignment: .leading, spacing: 1) {
                        Text(r.0)
                        if let p = model.paths { Text(shortPath(p[keyPath: r.2])).font(.caption).foregroundStyle(.secondary)
                            .lineLimit(1).truncationMode(.middle).textSelection(.enabled) }
                    }
                } icon: { Image(systemName: r.1).foregroundStyle(.secondary) }
            }
        }
    }
}

// MARK: About

struct AboutScreen: View {
    @EnvironmentObject var model: AppModel
    var version: String { Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "?" }
    var build: String { Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "?" }

    struct Credit: Identifiable { let name: String; let what: String; let licence: String; var id: String { name } }
    static let credits: [Credit] = [
        Credit(name: "Katip Kalkan, katip-mask", what: L("Maskeleme kodu ve kuralları", "Masking code and rules"), licence: "AGPL-3.0"),
        Credit(name: "Katip Mask Nano, Mini, Base", what: L("Ad tanıma modelleri", "Name models"), licence: "CC BY-SA 4.0"),
        Credit(name: "PaddleOCR PP-OCRv5", what: L("Taranmış belge okuma modelleri", "Scanned-document reading models"), licence: "Apache-2.0"),
        Credit(name: "RapidOCR", what: "OCR", licence: "Apache-2.0"),
        Credit(name: "PyMuPDF", what: L("PDF okuma (Artifex)", "PDF reading (Artifex)"), licence: "AGPL-3.0"),
        Credit(name: "ONNX Runtime", what: L("Modelleri çalıştırır (Microsoft)", "Runs the models (Microsoft)"), licence: "MIT"),
        Credit(name: "NumPy", what: L("Sayısal hesap", "Numerics"), licence: "BSD-3-Clause"),
        Credit(name: "cryptography", what: L("Şifreleme (AES-GCM)", "Encryption (AES-GCM)"), licence: "Apache-2.0 / BSD-3-Clause"),
        Credit(name: "Playwright", what: L("DD aramaları için tarayıcı sürücüsü (Microsoft)", "Browser driver for DD lookups (Microsoft)"), licence: "Apache-2.0"),
        Credit(name: "Node.js", what: L("Playwright sürücüsüyle gelir", "Comes with the Playwright driver"), licence: "MIT"),
        Credit(name: "tqdm", what: L("İlerleme göstergesi", "Progress bars"), licence: "MPL-2.0 / MIT"),
        Credit(name: "Python", what: L("Motorun dili", "The engine's language"), licence: "PSF-2.0"),
        Credit(name: "PyInstaller", what: L("Motoru paketler", "Packages the engine"), licence: L("GPL-2.0, paketleme istisnasıyla", "GPL-2.0 with bootloader exception")),
        Credit(name: L("Açık Mevzuat dizini", "Açık Mevzuat index"), what: L("Mevzuat arama dizini (acik-mevzuat)", "Statute lookup index (acik-mevzuat)"), licence: "MIT"),
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HStack(alignment: .center, spacing: 16) {
                    Image(nsImage: NSApp.applicationIconImage).resizable().frame(width: 84, height: 84)
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Katip").font(.largeTitle.weight(.semibold))
                        Text(L("Sürüm \(version) (\(build))", "Version \(version) (\(build))")).foregroundStyle(.secondary)
                        if let s = model.status { Text(L("Motor \(s.version)", "Engine \(s.version)")).font(.caption).foregroundStyle(.secondary) }
                    }
                }
                Text(L("Katip, müvekkil adlarını ve kişisel verileri (KVKK) belge yapay zekâya gitmeden önce bu Mac'te gizler, cevaptaki adları geri getirir. Hiçbir belge bilgisayardan çıkmaz.",
                       "Katip hides client names and personal data (KVKK) on this Mac before a document reaches an AI, and puts the names back into the answer. No document leaves the computer."))
                    .fixedSize(horizontal: false, vertical: true)

                GroupBox {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(L("Katip'i Fikri Fırat yapıyor. Açık kaynaklı; hatalar, öneriler ve katkılar GitHub'da. Katip'i faydalı bulduysanız GitHub Sponsors ile destek olabilirsiniz.",
                               "Katip is made by Fikri Fırat. It is open source; bugs, ideas and contributions live on GitHub. If Katip helps you, you can support it through GitHub Sponsors."))
                            .fixedSize(horizontal: false, vertical: true)
                        HStack(spacing: 10) {
                            Link(destination: URL(string: "https://github.com/fikrifirat/katip")!) { Label("GitHub", systemImage: "chevron.left.forwardslash.chevron.right") }
                            Link(destination: URL(string: "https://github.com/fikrifirat/katip/issues/new")!) { Label(L("Hata bildir", "Report a problem"), systemImage: "exclamationmark.bubble") }
                            Link(destination: URL(string: "https://github.com/sponsors/fikrifirat")!) { Label(L("Destek ol", "Support Katip"), systemImage: "heart") }
                        }
                        .buttonStyle(.bordered)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading).padding(4)
                } label: { Label(L("Yapan", "Made by"), systemImage: "person") }

                GroupBox {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(L("Katip AGPL-3.0 lisanslıdır: kaynak kodunu görebilir, değiştirebilir ve paylaşabilirsiniz; değiştirip başkalarına sunarsanız kodu da paylaşmanız gerekir. Büroya özel (AGPL dışı) lisans için GitHub'dan yazın.",
                               "Katip is licensed AGPL-3.0: you can read, change and share its source; if you change it and offer it to others, you share your code too. For a firm licence without the AGPL terms, write on GitHub."))
                            .font(.callout).fixedSize(horizontal: false, vertical: true)
                        Text(L("Mevzuat metinleri ve mahkeme kararları telif koruması dışındadır (FSEK m.31).",
                               "Legislation and court decisions are not protected by copyright (FSEK art. 31)."))
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading).padding(4)
                } label: { Label(L("Lisans", "Licence"), systemImage: "doc.plaintext") }

                GroupBox {
                    Grid(alignment: .leading, horizontalSpacing: 14, verticalSpacing: 6) {
                        ForEach(Self.credits) { c in
                            GridRow {
                                Text(c.name).font(.callout.weight(.medium))
                                Text(c.what).font(.callout).foregroundStyle(.secondary)
                                Text(c.licence).font(.caption.monospaced()).foregroundStyle(.secondary)
                            }
                        }
                    }
                    .padding(4)
                } label: { Label(L("Katip'in kullandıkları", "Built with"), systemImage: "shippingbox") }
                Text("© 2026 Fikri Fırat").font(.caption).foregroundStyle(.secondary)
            }
            .padding(22)
            .frame(maxWidth: 720, alignment: .leading)
        }
        .task { await model.refreshStatus() }
    }
}
