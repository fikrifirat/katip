import Foundation

/// sdk/spec/profiles.json, copied into the engine bundle at build time. Same ladder as the web app and Kalkan:
/// each profile masks everything the one before it does, plus more.
struct ProfileSpec: Decodable {
    struct Profile: Decodable {
        let title: String
        let title_tr: String
        let address_detail: String
        let description: String
        let entities: [String]
    }
    let default_profile: String
    let profiles: [String: Profile]
    let labels_tr: [String: String]

    static let shared: ProfileSpec = {
        let url = Bundle.main.resourceURL!.appendingPathComponent("Engine/profiles.json")
        guard let data = try? Data(contentsOf: url), let spec = try? JSONDecoder().decode(ProfileSpec.self, from: data) else {
            fatalError("Engine/profiles.json missing: run ios/setup.sh")
        }
        return spec
    }()

    static let order = ["court", "ai", "anon"]

    func title(_ id: String) -> String {
        guard let p = profiles[id] else { return id }
        return L(p.title_tr, p.title)
    }

    func label(_ entity: String) -> String {
        appIsTurkish ? (labels_tr[entity] ?? entity) : (LegalInfo.entity(entity)?.titleEN ?? entity)
    }
}
