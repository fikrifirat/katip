import Foundation

/// Turkish first; English when the device's first language is not Turkish.
let appIsTurkish: Bool = (Locale.preferredLanguages.first ?? "tr").hasPrefix("tr")

func L(_ tr: String, _ en: String) -> String { appIsTurkish ? tr : en }
