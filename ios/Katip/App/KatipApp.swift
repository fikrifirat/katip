import SwiftUI

@main
struct KatipApp: App {
    @StateObject private var engine = MaskEngine()
    @StateObject private var store = SessionStore()
    @State private var incoming: URL?

    var body: some Scene {
        WindowGroup {
            HomeView(incoming: $incoming)
                .environmentObject(engine)
                .environmentObject(store)
                .background(EngineHost(engine: engine).frame(width: 1, height: 1).opacity(0).accessibilityHidden(true))
                .tint(Theme.accent)
                // Files shared to Katip from Files, Mail, WhatsApp... ("Open in Katip" / "Copy to Katip").
                .onOpenURL { incoming = $0 }
        }
    }
}

enum Theme {
    static let lime = Color(red: 0xD4 / 255, green: 0xFF / 255, blue: 0x3A / 255)
    static let ink = Color(red: 0x0B / 255, green: 0x0D / 255, blue: 0x10 / 255)
    /// Lime is unreadable on white, so light mode uses a dark olive accent.
    static let accent = Color(uiColor: UIColor { $0.userInterfaceStyle == .dark
        ? UIColor(red: 0xD4 / 255, green: 0xFF / 255, blue: 0x3A / 255, alpha: 1)
        : UIColor(red: 0x4A / 255, green: 0x5C / 255, blue: 0x00 / 255, alpha: 1) })
    static let placeholder = Color(uiColor: UIColor { $0.userInterfaceStyle == .dark
        ? UIColor(red: 0xD4 / 255, green: 0xFF / 255, blue: 0x3A / 255, alpha: 0.22)
        : UIColor(red: 0xD4 / 255, green: 0xFF / 255, blue: 0x3A / 255, alpha: 0.55) })
}
