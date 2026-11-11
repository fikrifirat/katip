"""Fransızca (Fransa) PII tanıyıcılar — RGPD uyumlu."""
import re
from ..base import BaseRecognizer
from ..result import PiiEntity


class FrNir(BaseRecognizer):
    """
    NIR — Numéro d'Inscription au Répertoire (INSEE/Sécurité Sociale).
    Format: 1 + AA + MM + DEP(2) + COM(3) + ORD(3) + CLE(2) = 15 hane
    Cinsiyet: 1=erkek, 2=kadın
    """
    entity_type = "TC_KIMLIK"  # Ulusal kimlik numarası kategorisi

    _PATTERN = re.compile(
        r"(?<!\d)"
        r"([12][0-9]{2})"           # cinsiyet + yıl
        r"[\s]?"
        r"([0-9]{2})"               # ay
        r"[\s]?"
        r"([0-9]{2}[0-9AB])"        # departman (2A/2B Korsika dahil)
        r"[\s]?"
        r"([0-9]{3})"               # komün
        r"[\s]?"
        r"([0-9]{3})"               # sıra no
        r"[\s]?"
        r"([0-9]{2})"               # kontrol anahtarı
        r"(?!\d)"
    )

    def _checksum_valid(self, nir_digits: str) -> bool:
        """Kontrol anahtarı = 97 - (sayı mod 97)"""
        # 2A → 19, 2B → 18
        n = nir_digits[:-2].replace("2A", "19").replace("2B", "18")
        try:
            check = 97 - (int(n) % 97)
            return check == int(nir_digits[-2:])
        except ValueError:
            return False

    def find(self, text: str) -> list[PiiEntity]:
        results: list[PiiEntity] = []
        for m in self._PATTERN.finditer(text):
            raw = m.group(0).replace(" ", "")
            if len(raw) == 15 and self._checksum_valid(raw):
                results.append(self._entity(m.group(0), m.start(), m.end(), 0.95))
        return results


class FrPasseport(BaseRecognizer):
    """
    Fransız pasaport numarası.
    Format: 2 rakam + 2 harf + 5 rakam (örn: 12AB34567)
    """
    entity_type = "PASAPORT_TR"

    _PATTERN = re.compile(r"\b([0-9]{2}[A-Z]{2}[0-9]{5})\b")

    def find(self, text: str) -> list[PiiEntity]:
        return [
            self._entity(m.group(1), m.start(), m.end(), 0.80)
            for m in self._PATTERN.finditer(text)
        ]


class FrSiren(BaseRecognizer):
    """
    SIREN — Fransız şirket kimlik numarası (9 hane, Luhn algoritması).
    SIRET = SIREN + 5 hane (14 toplam).
    """
    entity_type = "VKN"

    _PATTERN_SIREN = re.compile(r"(?<!\d)([0-9]{9})(?!\d)")
    _PATTERN_SIRET = re.compile(r"(?<!\d)([0-9]{14})(?!\d)")

    def _luhn_valid(self, n: str) -> bool:
        total = 0
        for i, d in enumerate(reversed(n)):
            x = int(d)
            if i % 2 == 1:
                x *= 2
                if x > 9:
                    x -= 9
            total += x
        return total % 10 == 0

    def find(self, text: str) -> list[PiiEntity]:
        results: list[PiiEntity] = []
        seen: set[tuple[int, int]] = set()

        # SIRET önce (daha spesifik)
        for m in _PATTERN_SIRET.finditer(text):
            if self._luhn_valid(m.group(1)[:9]):  # SIREN kısmı kontrol
                span = (m.start(), m.end())
                seen.add(span)
                results.append(self._entity(m.group(1), m.start(), m.end(), 0.85))

        for m in self._PATTERN_SIREN.finditer(text):
            span = (m.start(), m.end())
            if span not in seen and self._luhn_valid(m.group(1)):
                results.append(self._entity(m.group(1), m.start(), m.end(), 0.80))

        return results

# SIRET için module-level compile
_PATTERN_SIRET = re.compile(r"(?<!\d)([0-9]{14})(?!\d)")


FR_RECOGNIZERS: list[BaseRecognizer] = [
    FrNir(),
    FrPasseport(),
    FrSiren(),
]
