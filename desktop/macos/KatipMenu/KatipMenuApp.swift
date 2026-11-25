import AppKit
import SwiftUI

@main
struct KatipMenuApp: App {
    @StateObject private var model = EngineModel()

    init() {
        if CommandLine.arguments.contains("--selftest") {
            Task { await SelfTest.run() }
        }
    }

    var body: some Scene {
        MenuBarExtra {
            MenuView().environmentObject(model)
        } label: {
            Image(systemName: model.status == nil ? "shield" : "checkmark.shield.fill")
        }
        .menuBarExtraStyle(.window)
    }
}

@MainActor
final class EngineModel: ObservableObject {
    @Published var status: EngineClient.Status?
    @Published var busy = false
    @Published var note: String?
    let client = EngineClient()

    func refresh() async { status = await client.status() }

    func toggle() async {
        busy = true
        defer { busy = false }
        if status == nil {
            do { try await client.start(); note = nil } catch { note = error.localizedDescription }
        } else {
            await client.stop()
            try? await Task.sleep(nanoseconds: 400_000_000)
        }
        await refresh()
    }

    /// Mask (or restore) whatever text is on the clipboard and put the result back on it.
    func clipboard(restore: Bool) async {
        let pb = NSPasteboard.general
        guard let text = pb.string(forType: .string), !text.isEmpty else {
            note = "The clipboard has no text."
            return
        }
        busy = true
        defer { busy = false }
        do {
            if status == nil { try await client.start() }
            let out: String
            if restore {
                let r = try await client.restore(text)
                out = r.text
                note = "Put back \(r.placeholders_restored) values. The clipboard holds the real names now."
            } else {
                let m = try await client.mask(text)
                out = m.masked_text
                note = "Masked \(m.placeholders.count) values in \(Int(m.ms)) ms. The clipboard holds the masked text."
            }
            pb.clearContents()
            pb.setString(out, forType: .string)
        } catch {
            note = error.localizedDescription
        }
        await refresh()
    }
}

struct MenuView: View {
    @EnvironmentObject var model: EngineModel

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Circle().fill(model.status == nil ? Color.secondary : Color.green).frame(width: 9, height: 9)
                Text(model.status == nil ? "Katip engine is stopped" : "Katip engine is running").font(.headline)
                Spacer()
                if model.busy { ProgressView().controlSize(.small) }
            }
            if let s = model.status {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Version \(s.version) · \(s.served) masked · \(Int(s.rss_peak_mb)) MB")
                    Text(s.model).lineLimit(2)
                    Text("Case keys: \(s.vault)")
                }
                .font(.caption).foregroundStyle(.secondary)
            } else {
                Text("Nothing runs and nothing is in memory. It starts when you need it and stops after 15 idle minutes.")
                    .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }
            Divider()
            Button("Mask the clipboard") { Task { await model.clipboard(restore: false) } }
            Button("Put names back in the clipboard") { Task { await model.clipboard(restore: true) } }
            Divider()
            Button(model.status == nil ? "Start engine" : "Stop engine") { Task { await model.toggle() } }
            Button("Show engine log") { NSWorkspace.shared.activateFileViewerSelecting([EngineClient.logURL]) }
            if let note = model.note {
                Text(note).font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }
            Divider()
            Button("Quit Katip") { NSApplication.shared.terminate(nil) }
        }
        .buttonStyle(.borderless)
        .padding(14)
        .frame(width: 300)
        .task {
            while !Task.isCancelled {
                await model.refresh()
                try? await Task.sleep(nanoseconds: 5_000_000_000)
            }
        }
    }
}

/// `Katip.app/Contents/MacOS/Katip --selftest`: start the engine, mask and restore one synthetic sentence,
/// print what happened as JSON and quit. Lets CI and humans check the app without clicking.
enum SelfTest {
    @MainActor static func run() async {
        let c = EngineClient()
        var out: [String: Any] = [:]
        let sample = "Davacı Ayşe DEMİRCİ (T.C. Kimlik No: 10000000146) vekili Av. Mehmet KARA."
        do {
            try await c.start()
            let st = await c.status()
            out["running"] = st != nil
            out["version"] = st?.version
            let m = try await c.mask(sample, matter: "selftest")
            out["masked"] = m.masked_text
            out["names_hidden"] = !m.masked_text.contains("DEMİRCİ") && !m.masked_text.contains("10000000146")
            let r = try await c.restore(m.masked_text, matter: "selftest")
            out["restored_matches"] = r.text == sample
        } catch {
            out["error"] = error.localizedDescription
        }
        let data = try! JSONSerialization.data(withJSONObject: out, options: [.sortedKeys])
        print(String(data: data, encoding: .utf8)!)
        exit(out["error"] == nil ? 0 : 1)
    }
}
