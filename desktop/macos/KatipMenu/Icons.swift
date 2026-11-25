import AppKit
import SwiftUI

/// A System Settings–style icon: a white symbol on a coloured rounded square.
struct Tile: View {
    let symbol: String
    let color: Color
    var size: CGFloat = 22
    var body: some View {
        RoundedRectangle(cornerRadius: size * 0.26, style: .continuous)
            .fill(LinearGradient(colors: [color.opacity(0.92), color], startPoint: .top, endPoint: .bottom))
            .frame(width: size, height: size)
            .overlay(Image(systemName: symbol).font(.system(size: size * 0.52, weight: .semibold)).foregroundStyle(.white))
            .shadow(color: .black.opacity(0.12), radius: 0.5, y: 0.5)
    }
}

/// The real icon of an app installed on this Mac, as Finder shows it (nothing bundled); a tile when it isn't there.
struct AppIcon: View {
    let path: String
    let fallback: String
    var size: CGFloat = 30
    var body: some View {
        if FileManager.default.fileExists(atPath: path) {
            Image(nsImage: NSWorkspace.shared.icon(forFile: path)).resizable().frame(width: size, height: size)
        } else {
            Tile(symbol: fallback, color: .gray, size: size * 0.86)
        }
    }
}

enum Apps {
    static let claude = "/Applications/Claude.app"
    static let terminal = "/System/Applications/Utilities/Terminal.app"
    static let chrome = "/Applications/Google Chrome.app"
}

/// A judge's gavel, drawn (SF Symbols has none): a wooden head with brass bands, a handle and the sound block.
/// `down` swings it onto the block.
struct Gavel: View {
    var down = false
    var size: CGFloat = 64
    private let wood = LinearGradient(colors: [Color(red: 0.55, green: 0.33, blue: 0.17), Color(red: 0.36, green: 0.2, blue: 0.1)],
                                      startPoint: .top, endPoint: .bottom)
    private let brass = Color(red: 0.86, green: 0.68, blue: 0.3)

    var body: some View {
        let u = size / 64
        ZStack {
            // sound block
            RoundedRectangle(cornerRadius: 3 * u).fill(wood).frame(width: 34 * u, height: 8 * u)
                .overlay(RoundedRectangle(cornerRadius: 3 * u).fill(brass).frame(height: 2 * u).offset(y: -3 * u))
                .offset(x: -10 * u, y: 25 * u)
            ZStack {
                RoundedRectangle(cornerRadius: 2 * u).fill(wood).frame(width: 6 * u, height: 38 * u).offset(y: 12 * u)
                RoundedRectangle(cornerRadius: 5 * u).fill(wood).frame(width: 34 * u, height: 16 * u).offset(y: -12 * u)
                ForEach([-11.0, 11.0], id: \.self) { x in
                    Rectangle().fill(brass).frame(width: 3 * u, height: 16 * u).offset(x: x * u, y: -12 * u)
                }
            }
            .rotationEffect(.degrees(down ? -62 : -28), anchor: UnitPoint(x: 0.5, y: 0.98))
            .offset(x: 8 * u, y: -6 * u)
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

extension Screen {
    var tint: Color {
        switch self {
        case .mask: return .blue
        case .restore: return .green
        case .review: return Color(red: 0.55, green: 0.33, blue: 0.17)
        case .cases: return .orange
        case .features: return .purple
        case .models: return .teal
        case .connections: return .pink
        case .settings: return .gray
        case .about: return .indigo
        }
    }
}

func featureTint(_ id: String) -> Color {
    switch id {
    case "mevzuat": return .indigo
    case "emsal": return Color(red: 0.55, green: 0.33, blue: 0.17)
    case "dd_masak": return .green
    case "dd_ilan": return .orange
    default: return .blue
    }
}
