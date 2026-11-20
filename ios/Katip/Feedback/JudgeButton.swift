import SwiftUI
import UIKit

// The shared Katip feedback control, built from /feedback-block/SPEC.md (reference: connector/katip_kalkan/ui/emsal.html).
// States: idle -> open -> striking -> saved | error. Verdicts are 0/1/2 in a fixed order; labels come from the caller.

struct Verdict: Identifiable, Hashable {
    let puan: Int
    let label: String
    var id: Int { puan }

    var color: Color {
        switch puan {
        case 0: return Color(light: 0xB42318, dark: 0xF97066)
        case 1: return Color(light: 0xB54708, dark: 0xFDB022)
        default: return Color(light: 0x2F6F1F, dark: 0xA6E36B)
        }
    }
}

extension Color {
    init(light: UInt32, dark: UInt32) {
        func ui(_ h: UInt32) -> UIColor {
            UIColor(red: CGFloat((h >> 16) & 0xFF) / 255, green: CGFloat((h >> 8) & 0xFF) / 255, blue: CGFloat(h & 0xFF) / 255, alpha: 1)
        }
        self.init(uiColor: UIColor { $0.userInterfaceStyle == .dark ? ui(dark) : ui(light) })
    }
}

struct JudgeButton: View {
    let verdicts: [Verdict]
    /// The current verdict, if the lawyer judged this block before.
    let current: Int?
    /// Saves the verdict; throw to show the error state.
    let save: @MainActor (Int) async throws -> Void

    enum Phase: Equatable { case idle, open, striking, saved, error(String) }
    @State private var phase: Phase = .idle
    @State private var swing = false
    @State private var ring = false
    @State private var shake: CGFloat = 0
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @AccessibilityFocusState private var focusedChip: Int?

    private static let tile = Color(red: 0x1F / 255, green: 0x24 / 255, blue: 0x2B / 255)

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Button(action: tapGavel) {
                    HStack(spacing: 8) {
                        GavelIcon(angle: hammerAngle, ring: ring && !reduceMotion)
                            .frame(width: 26, height: 26)
                        Text(pillLabel).font(.footnote.weight(.semibold))
                    }
                    .padding(.leading, 8).padding(.trailing, 14).frame(height: 36)
                    .foregroundStyle(isSaved ? Self.tile : .white)
                    .background(isSaved ? Theme.lime : Self.tile, in: Capsule())
                    .offset(x: shake)
                }
                .buttonStyle(.plain)
                .disabled(phase == .striking)
                .accessibilityLabel(pillLabel)

                if phase == .open {
                    ForEach(verdicts) { v in
                        Button { Task { await strike(v) } } label: {
                            Text(v.label).font(.caption.weight(.semibold))
                                .padding(.horizontal, 12).frame(height: 32)
                                .overlay(Capsule().stroke(v.puan == current ? v.color : Color.secondary.opacity(0.35), lineWidth: 1.5))
                                .foregroundStyle(v.puan == current ? v.color : .primary)
                        }
                        .buttonStyle(.plain)
                        .accessibilityFocused($focusedChip, equals: v.puan)
                        .transition(.opacity.combined(with: .offset(x: -6)))
                    }
                }
            }
            if let status { Text(status).font(.caption).foregroundStyle(isError ? Verdict(puan: 0, label: "").color : .secondary) }
        }
        .onAppear { if current != nil { phase = .saved } }
    }

    private var isSaved: Bool { phase == .saved }
    private var isError: Bool { if case .error = phase { return true }; return false }

    private var hammerAngle: Double {
        switch phase {
        case .saved: return 0
        case .striking: return reduceMotion ? 20 : (swing ? -1 : 28)
        default: return 20
        }
    }

    private var pillLabel: String {
        switch phase {
        case .striking: return L("Kaydediliyor", "Saving")
        case .saved: return verdicts.first { $0.puan == current }?.label ?? L("Hüküm ver", "Judge")
        case .error: return L("Tekrar dene", "Try again")
        default: return L("Hüküm ver", "Judge")
        }
    }

    private var status: String? {
        switch phase {
        case .saved: return L("Kaydedildi · değiştirmek için tokmağa basın", "Saved · tap the gavel to change")
        case let .error(m): return m
        default: return nil
        }
    }

    private func tapGavel() {
        withAnimation(.easeOut(duration: 0.18)) {
            switch phase {
            case .open: phase = current == nil ? .idle : .saved
            default: phase = .open
            }
        }
        if phase == .open { focusedChip = verdicts.first?.puan }
    }

    private func strike(_ v: Verdict) async {
        withAnimation(.easeOut(duration: 0.18)) { phase = .striking }
        UIImpactFeedbackGenerator(style: .light).impactOccurred()
        if !reduceMotion {
            withAnimation(.timingCurve(0.5, 0, 0.9, 0.4, duration: 0.5).repeatForever(autoreverses: true)) { swing = true }
        }
        let started = Date()
        var failure: String?
        do { try await save(v.puan) } catch { failure = error.localizedDescription }
        let wait = 0.45 - Date().timeIntervalSince(started)       // the strike is seen at least once
        if wait > 0 { try? await Task.sleep(nanoseconds: UInt64(wait * 1e9)) }
        withAnimation(.easeOut(duration: 0.15)) { swing = false }
        if let failure {
            phase = .error(failure)
            UIAccessibility.post(notification: .announcement, argument: failure)
            UINotificationFeedbackGenerator().notificationOccurred(.error)
            if !reduceMotion {
                for x in [-4.0, 4.0, -4.0, 0.0] {
                    withAnimation(.linear(duration: 0.08)) { shake = x }
                    try? await Task.sleep(nanoseconds: 85_000_000)
                }
            }
        } else {
            phase = .saved
            UIAccessibility.post(notification: .announcement, argument: status)
            UINotificationFeedbackGenerator().notificationOccurred(.success)
            if !reduceMotion {
                ring = false
                withAnimation(.easeOut(duration: 0.5)) { ring = true }
            }
        }
    }
}

/// The gavel from the reference SVG (viewBox 28x28): a base, a hammer rotating around (26, 16), an impact ring at (8, 22).
private struct GavelIcon: View {
    let angle: Double
    let ring: Bool

    var body: some View {
        GeometryReader { geo in
            let s = geo.size.width / 28
            ZStack(alignment: .topLeading) {
                Circle().stroke(lineWidth: 1.5 * s)
                    .frame(width: 14 * s, height: 14 * s)
                    .scaleEffect(ring ? 1.8 : 0.4)
                    .opacity(ring ? 0 : (angle == 0 ? 0.9 : 0))
                    .position(x: 8 * s, y: 22 * s)
                RoundedRectangle(cornerRadius: 1.5 * s).opacity(0.55)
                    .frame(width: 14 * s, height: 3.5 * s).position(x: 8 * s, y: 23.75 * s)
                ZStack(alignment: .topLeading) {
                    rect(11, 14.5, 15.5, 3, 1.5, s)
                    rect(4.5, 8, 7, 14, 2, s)
                    rect(3.5, 9.5, 9, 2, 1, s)
                    rect(3.5, 18.5, 9, 2, 1, s)
                }
                .frame(width: 28 * s, height: 28 * s, alignment: .topLeading)
                .rotationEffect(.degrees(angle), anchor: UnitPoint(x: 26 / 28, y: 16 / 28))
            }
        }
        .accessibilityHidden(true)
    }

    private func rect(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat, _ r: CGFloat, _ s: CGFloat) -> some View {
        RoundedRectangle(cornerRadius: r * s).frame(width: w * s, height: h * s).offset(x: x * s, y: y * s)
    }
}
