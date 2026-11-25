import AppKit
import SwiftUI

/// `Katip --tour <folder>`: walks the first run and every screen the way a new user would, doing the real work
/// (engine start, model download, Claude connection, masking), and saves a PNG of the window at each step.
/// Run it with KATIP_HOME, KATIP_MASK_CACHE and KATIP_CLAUDE_DESKTOP_CONFIG pointing at empty test folders.
enum Tour {
    @MainActor static func run(to dir: URL) async {
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let m = AppModel.shared
        var log: [String] = []
        func wait(_ s: Double) async { try? await Task.sleep(nanoseconds: UInt64(s * 1e9)) }
        func step(_ i: Int) async { NotificationCenter.default.post(name: .katipTourStep, object: i); await wait(0.8) }
        func until(_ limit: Double = 60, _ cond: () -> Bool) async { var t = 0.0; while !cond() && t < limit { await wait(0.25); t += 0.25 } }

        await until { m.settings != nil }
        await wait(0.8)
        snap("01-welcome", dir)
        await step(1)
        await wait(6)
        snap("02-getting-ready", dir)
        await step(2)
        snap("03-model", dir)
        let dl = Task { await m.download("mini") }
        await until(30) { (m.models?.download?.done ?? 0) > 0 }
        snap("04-model-downloading", dir)
        await dl.value
        log.append("download: \(m.models?.download?.state ?? "none"), model now \(m.settings?.model ?? "?")")
        await step(3)
        await until(20) { m.claude != nil }
        snap("05-claude", dir)
        let r = await m.connect("desktop", on: true)
        log.append("claude desktop connect: \(r?.connected == true)")
        await wait(0.5)
        snap("06-claude-connected", dir)
        await step(4)
        await wait(3)
        snap("07-ready", dir)
        await m.save(["first_run_done": true])
        await wait(1.5)
        NotificationCenter.default.post(name: .katipTourMask, object: SampleText.sentence)
        await wait(3)
        snap("08-mask", dir)
        for (i, s) in [(9, Screen.restore), (10, .cases)] {
            NotificationCenter.default.post(name: .katipShow, object: s)
            await wait(2)
            snap(String(format: "%02d-%@", i, s.rawValue), dir)
        }
        // Review: mask a sentence with names the model is unsure of, then judge the first with the gavel
        NotificationCenter.default.post(name: .katipShow, object: Screen.mask)
        NotificationCenter.default.post(name: .katipTourMask, object: "Toplantıya tanık Selin hanım ile Oğuz bey katıldı; Nurten de oradaydı.")
        await wait(3)
        NotificationCenter.default.post(name: .katipShow, object: Screen.review)
        await m.refreshReview()
        await wait(1.5)
        snap("10b-review", dir)
        if m.review?.open.isEmpty == false {
            NotificationCenter.default.post(name: .katipTourJudge, object: nil)
            await wait(0.3)
            snap("10c-review-gavel", dir)
            await wait(1.5)
            snap("10d-review-after", dir)
        }
        log.append("review: \(m.review?.open.count ?? -1) open, \(m.review?.learned.mask.count ?? -1) learned")  // counts only: never values
        // Features: every online feature starts with its setup sheet; do each the way a lawyer would
        NotificationCenter.default.post(name: .katipShow, object: Screen.features)
        await until(10) { m.features != nil }
        await wait(1.5)
        snap("11-features", dir)
        func setup(_ id: String, _ name: String, work: () async -> Void) async {
            NotificationCenter.default.post(name: .katipTourSetup, object: id)
            await wait(1.5)
            snap("\(name)-setup", dir, sheet: true)
            NotificationCenter.default.post(name: .katipTourAgree, object: nil)
            await m.setFeature(id, on: true)
            await work()
            await wait(1)
            snap("\(name)-done", dir, sheet: true)
            log.append("\(id): \(m.feature(id)?.state ?? "?") job=\(m.feature(id)?.job?.state ?? "-") \(m.feature(id)?.job?.error ?? "")")
            NotificationCenter.default.post(name: .katipTourSetup, object: nil)
            await wait(1)
        }
        await setup("emsal", "12-emsal") {}
        await setup("dd_masak", "13-masak") {}
        await setup("dd_gazette", "14-gazette") { await m.featureAction("dd_gazette", "test_browser") }
        await wait(1)
        snap("15-features-on", dir)
        for (i, s) in [(16, Screen.models), (17, .connections), (18, .settings), (19, .about)] {
            NotificationCenter.default.post(name: .katipShow, object: s)
            await wait(2)
            snap(String(format: "%02d-%@", i, s.rawValue), dir)
        }
        NotificationCenter.default.post(name: .katipShow, object: Screen.settings)
        await wait(1)
        scrollToEnd()  // the Folders list, below the fold
        await wait(1)
        snap("18b-settings-folders", dir)
        NSApp.appearance = NSAppearance(named: .darkAqua)
        NotificationCenter.default.post(name: .katipShow, object: Screen.features)
        await wait(1.5)
        snap("20-features-dark", dir)
        NotificationCenter.default.post(name: .katipShow, object: Screen.models)
        await wait(1.5)
        snap("21-models-dark", dir)
        NotificationCenter.default.post(name: .katipShow, object: Screen.review)
        await wait(1.5)
        snap("22-review-dark", dir)
        NotificationCenter.default.post(name: .katipShow, object: Screen.about)
        await wait(1.5)
        snap("23-about-dark", dir)
        try? log.joined(separator: "\n").write(to: dir.appendingPathComponent("tour.log"), atomically: true, encoding: .utf8)
        exit(0)
    }

    /// Scroll every scroll view in the main window to its end (the visible screen's form is the one that moves).
    @MainActor static func scrollToEnd() {
        func all(_ v: NSView) -> [NSScrollView] { (v as? NSScrollView).map { [$0] } ?? [] + v.subviews.flatMap(all) }
        guard let w = NSApp.windows.first(where: { $0.identifier?.rawValue == "main" }) ?? NSApp.keyWindow,
              let root = w.contentView else { return }
        for sv in all(root) {
            guard let doc = sv.documentView else { continue }
            let y = doc.isFlipped ? max(0, doc.bounds.height - sv.contentView.bounds.height) : 0
            sv.contentView.scroll(to: NSPoint(x: 0, y: y)); sv.reflectScrolledClipView(sv.contentView)
        }
    }

    @MainActor static func snap(_ name: String, _ dir: URL, sheet: Bool = false) {
        guard let w = NSApp.windows.filter({ $0.isVisible && $0.frame.width > 500 && $0.isSheet == sheet }).first,
              let v = w.contentView?.superview ?? w.contentView,
              let rep = v.bitmapImageRepForCachingDisplay(in: v.bounds) else { return }
        v.cacheDisplay(in: v.bounds, to: rep)
        try? rep.representation(using: .png, properties: [:])?.write(to: dir.appendingPathComponent(name + ".png"))
    }
}
