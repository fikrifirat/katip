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
        for (i, s) in [(9, Screen.restore), (10, .cases), (11, .connections), (12, .settings)] {
            NotificationCenter.default.post(name: .katipShow, object: s)
            await wait(2)
            snap(String(format: "%02d-%@", i, s.rawValue), dir)
        }
        NSApp.appearance = NSAppearance(named: .darkAqua)
        NotificationCenter.default.post(name: .katipShow, object: Screen.mask)
        await wait(1.5)
        snap("13-mask-dark", dir)
        try? log.joined(separator: "\n").write(to: dir.appendingPathComponent("tour.log"), atomically: true, encoding: .utf8)
        exit(0)
    }

    @MainActor static func snap(_ name: String, _ dir: URL) {
        guard let w = NSApp.windows.filter({ $0.isVisible && $0.frame.width > 500 }).first,
              let v = w.contentView?.superview ?? w.contentView,
              let rep = v.bitmapImageRepForCachingDisplay(in: v.bounds) else { return }
        v.cacheDisplay(in: v.bounds, to: rep)
        try? rep.representation(using: .png, properties: [:])?.write(to: dir.appendingPathComponent(name + ".png"))
    }
}
