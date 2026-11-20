import CryptoKit
import Foundation
import Security

/// Saved documents, encrypted with AES-256-GCM. The key lives in the Keychain, readable only while this device is
/// unlocked and never synced or backed up. The file also has complete data protection and is excluded from
/// iCloud/iTunes backups. Documents older than 30 days are deleted at launch, like Kalkan's vault.
@MainActor
final class SessionStore: ObservableObject {
    @Published private(set) var sessions: [MaskSession] = []
    @Published var loadError: String?

    static let keepDays = 30
    private let fileURL: URL

    init() {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("Katip", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true,
                                                 attributes: [.protectionKey: FileProtectionType.complete])
        var d = dir
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        try? d.setResourceValues(values)
        fileURL = dir.appendingPathComponent("sessions.bin")
        load()
    }

    func upsert(_ s: MaskSession) {
        if let i = sessions.firstIndex(where: { $0.id == s.id }) { sessions[i] = s } else { sessions.insert(s, at: 0) }
        save()
    }

    func delete(_ id: UUID) {
        sessions.removeAll { $0.id == id }
        save()
    }

    func deleteAll() {
        sessions = []
        try? FileManager.default.removeItem(at: fileURL)
        Keychain.deleteKey()
    }

    private func load() {
        guard let blob = try? Data(contentsOf: fileURL) else { return }
        do {
            let box = try AES.GCM.SealedBox(combined: blob)
            let plain = try AES.GCM.open(box, using: Keychain.key())
            let all = try JSONDecoder().decode([MaskSession].self, from: plain)
            let cutoff = Date().addingTimeInterval(-Double(Self.keepDays) * 86400)
            sessions = all.filter { $0.created > cutoff }
            if sessions.count != all.count { save() }
        } catch {
            loadError = L("Kayıtlı belgeler açılamadı.", "Saved documents could not be opened.")
        }
    }

    private func save() {
        do {
            let plain = try JSONEncoder().encode(sessions)
            let sealed = try AES.GCM.seal(plain, using: Keychain.key()).combined!
            try sealed.write(to: fileURL, options: [.atomic, .completeFileProtection])
        } catch {
            loadError = L("Belge kaydedilemedi.", "The document could not be saved.")
        }
    }
}

enum Keychain {
    private static let account = "katip.vault.key"

    static func key() throws -> SymmetricKey {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrAccount as String: account,
                                    kSecReturnData as String: true]
        var out: CFTypeRef?
        if SecItemCopyMatching(query as CFDictionary, &out) == errSecSuccess, let data = out as? Data {
            return SymmetricKey(data: data)
        }
        let key = SymmetricKey(size: .bits256)
        let data = key.withUnsafeBytes { Data($0) }
        let add: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrAccount as String: account,
                                  kSecValueData as String: data,
                                  kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly]
        let status = SecItemAdd(add as CFDictionary, nil)
        guard status == errSecSuccess else { throw NSError(domain: NSOSStatusErrorDomain, code: Int(status)) }
        return key
    }

    static func deleteKey() {
        SecItemDelete([kSecClass as String: kSecClassGenericPassword, kSecAttrAccount as String: account] as CFDictionary)
    }
}
