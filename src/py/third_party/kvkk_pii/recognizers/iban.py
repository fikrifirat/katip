import re
from ..base import BaseRecognizer
from ..config import IbanConfig
from ..result import PiiEntity

# Tüm IBAN formatları: 2 harf ülke kodu + 2 check digit + 11-30 alfanumerik
_PATTERN = re.compile(r"\b([A-Z]{2}[0-9]{2}[A-Z0-9]{11,30})\b", re.IGNORECASE)

# Ülke kodu → beklenen uzunluk (ISO 13616)
_IBAN_LENGTHS: dict[str, int] = {
    "TR": 26, "DE": 22, "FR": 27, "GB": 22, "NL": 18,
    "ES": 24, "IT": 27, "AT": 20, "BE": 16, "CH": 21,
    "PL": 28, "PT": 25, "SE": 24, "NO": 15, "DK": 18,
    "FI": 18, "HU": 28, "CZ": 24, "RO": 24, "BG": 22,
}


def _mod97_valid(iban: str) -> bool:
    iban = iban.upper().replace(" ", "")
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    return int(numeric) % 97 == 1


class IbanRecognizer(BaseRecognizer):
    entity_type = "IBAN_TR"

    def __init__(self, config: IbanConfig | None = None) -> None:
        self.config = config or IbanConfig()

    def find(self, text: str) -> list[PiiEntity]:
        results: list[PiiEntity] = []
        for m in _PATTERN.finditer(text):
            iban = m.group(1).upper()
            country = iban[:2]

            # Ülke kodu biliniyorsa uzunluk kontrolü
            expected_len = _IBAN_LENGTHS.get(country)
            if expected_len and len(iban) != expected_len:
                continue

            if self.config.require_mod97 and not _mod97_valid(iban):
                continue

            results.append(self._entity(m.group(1), m.start(), m.end(), self.config.score))
        return results
