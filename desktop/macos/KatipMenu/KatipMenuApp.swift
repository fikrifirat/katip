import AppKit
import SwiftUI

@main
struct KatipMenuApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var delegate
    @StateObject private var model = AppModel.shared

    var body: some Scene {
        Window("Katip", id: "main") {
            RootView()
                .environmentObject(model)
                .onAppear { AppDelegate.mainWindowShown() }
                .onDisappear { AppDelegate.mainWindowClosed() }
        }
        .defaultSize(width: 900, height: 640)
        .windowResizability(.contentMinSize)
        .commands {
            CommandGroup(replacing: .appInfo) {
                Button(L("Katip Hakkında", "About Katip")) {
                    NotificationCenter.default.post(name: .katipOpenMain, object: nil)
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                        NotificationCenter.default.post(name: .katipShow, object: Screen.about)
                    }
                }
            }
        }

        MenuBarExtra {
            MenuContent().environmentObject(model)
        } label: {
            Image(systemName: model.running ? "checkmark.shield.fill" : "checkmark.shield")
        }
        .menuBarExtraStyle(.window)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    static var launchedAtLogin = false

    func applicationWillFinishLaunching(_ notification: Notification) {
        if let e = NSAppleEventManager.shared().currentAppleEvent, e.eventID == kAEOpenApplication,
           e.paramDescriptor(forKeyword: keyAEPropData)?.enumCodeValue == keyAELaunchedAsLogInItem {
            Self.launchedAtLogin = true
        }
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        let args = CommandLine.arguments
        if args.contains("--selftest") { Task { await SelfTest.run() } }
        if let i = args.firstIndex(of: "--tour"), i + 1 < args.count { Task { await Tour.run(to: URL(fileURLWithPath: args[i + 1])) } }
        if Self.launchedAtLogin {  // at login: menu bar only, no window
            DispatchQueue.main.async { NSApp.windows.first { $0.identifier?.rawValue == "main" }?.close() }
        }
    }

    /// Closing the window keeps Katip in the menu bar.
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag { NotificationCenter.default.post(name: .katipOpenMain, object: nil) }
        return true
    }

    /// While the window is open Katip has a Dock icon and ⌘-Tab entry; closed, it lives in the menu bar only.
    static func mainWindowShown() {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
    }

    static func mainWindowClosed() { NSApp.setActivationPolicy(.accessory) }
}

extension Notification.Name { static let katipOpenMain = Notification.Name("katip.openMain") }

struct MenuContent: View {
    @EnvironmentObject var model: AppModel
    @Environment(\.openWindow) private var openWindow

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Circle().fill(model.running ? Color.green : Color.secondary.opacity(0.5)).frame(width: 9, height: 9)
                Text("Katip").font(.headline)
                Text(model.running ? L("çalışıyor", "running") : L("beklemede", "idle")).foregroundStyle(.secondary)
                Spacer()
                if model.busy { ProgressView().controlSize(.small) }
            }
            if let s = model.status {
                Text(L("\(s.served) belge · \(Int(s.rssPeakMb)) MB · \(modelLabel(s.model))", "\(s.served) masked · \(Int(s.rssPeakMb)) MB · \(modelLabel(s.model))"))
                    .font(.caption).foregroundStyle(.secondary)
            } else {
                Text(L("Bellekte hiçbir şey yok. İlk işte başlar, 15 dakika boşta kalınca durur.",
                       "Nothing in memory. Starts on the next task, stops after 15 idle minutes."))
                    .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }
            Divider()
            MenuButton(L("Panodakini maskele", "Mask the clipboard"), icon: "eye.slash") { Task { await model.clipboard(restore: false) } }
            MenuButton(L("Panodakini geri çevir", "Restore the clipboard"), icon: "arrow.uturn.backward") { Task { await model.clipboard(restore: true) } }
            if let note = model.note {
                Text(note).font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }
            Divider()
            MenuButton(L("Katip'i aç…", "Open Katip…"), icon: "macwindow") { open() }
            MenuButton(model.running ? L("Motoru durdur", "Stop engine") : L("Motoru başlat", "Start engine"),
                       icon: model.running ? "stop.circle" : "play.circle") { Task { await model.toggleEngine() } }
            Divider()
            MenuButton(L("Katip'ten çık", "Quit Katip"), icon: "power") { NSApplication.shared.terminate(nil) }
        }
        .padding(14)
        .frame(width: 290)
        .task {
            while !Task.isCancelled {
                await model.refreshStatus()
                try? await Task.sleep(nanoseconds: 4_000_000_000)
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .katipOpenMain)) { _ in open() }
    }

    func open() {
        openWindow(id: "main")
        NSApp.activate(ignoringOtherApps: true)
    }

    func modelLabel(_ s: String) -> String {
        for n in ["base", "mini", "nano"] where s.contains("-\(n)") { return modelTitle(n) }
        return L("yalnızca kurallar", "rules only")
    }
}

struct MenuButton: View {
    let title: String
    let icon: String
    let action: () -> Void
    init(_ title: String, icon: String, action: @escaping () -> Void) { self.title = title; self.icon = icon; self.action = action }
    @State private var hover = false
    var body: some View {
        Button(action: action) {
            Label(title, systemImage: icon).frame(maxWidth: .infinity, alignment: .leading).contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .padding(.vertical, 3).padding(.horizontal, 6)
        .background(RoundedRectangle(cornerRadius: 5).fill(hover ? Color.accentColor.opacity(0.15) : .clear))
        .onHover { hover = $0 }
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
            out["masked"] = m.maskedText
            out["names_hidden"] = !m.maskedText.contains("DEMİRCİ") && !m.maskedText.contains("10000000146")
            let r = try await c.restore(m.maskedText, matter: "selftest")
            out["restored_matches"] = r.text == sample
            struct Done: Decodable { let deleted: Bool }
            let _: Done? = try? await c.call("/v1/forget", body: ["matter": "selftest"])
        } catch {
            out["error"] = error.localizedDescription
        }
        let data = try! JSONSerialization.data(withJSONObject: out, options: [.sortedKeys])
        print(String(data: data, encoding: .utf8)!)
        exit(out["error"] == nil ? 0 : 1)
    }
}
