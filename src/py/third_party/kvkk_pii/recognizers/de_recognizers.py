"""Almanca (Almanya) PII tanıyıcılar — DSGVO uyumlu."""
import re
from ..base import BaseRecognizer
from ..result import PiiEntity


class DeSteuerId(BaseRecognizer):
    """
    Steueridentifikationsnummer — 11 haneli Alman vergi kimlik numarası.
    Format: İlk hane 1-9, ikinci hane 0 olamaz, checksum (ISO 7064 Mod 11,10).
    """
    entity_type = "VKN"  # Vergi kimlik numarası kategorisi

    _PATTERN = re.compile(r"(?<!\d)([1-9][0-9]{10})(?!\d)")

    def _checksum_valid(self, n: str) -> bool:
        """ISO 7064 Mod 11,10 algoritması."""
        product = 10
        for i in range(10):
            total = (int(n[i]) + product) % 10
            if total == 0:
                total = 10
            product = (total * 2) % 11
        check = 11 - product
        if check == 10:
            check = 0
        return check == int(n[10])

    def find(self, text: str) -> list[PiiEntity]:
        return [
            self._entity(m.group(1), m.start(), m.end(), 0.85)
            for m in self._PATTERN.finditer(text)
            if self._checksum_valid(m.group(1))
        ]


class DePersonalausweis(BaseRecognizer):
    """
    Personalausweis (Alman Kimlik Kartı) numarası.
    Format: L[LLLLLLLLL] — 9 karakter, harf+rakam karışımı, özel alfabe.
    """
    entity_type = "PASAPORT_TR"  # Kimlik belgesi kategorisi

    # Geçerli karakterler: 0-9, C, F, G, H, J, K, L, M, N, P, R, T, V, W, X, Y, Z
    _VALID_CHARS = set("0123456789CFGHJKLMNPRTVWXYZ")
    _PATTERN = re.compile(r"\b([A-Z][A-Z0-9]{8})\b")

    def _valid(self, s: str) -> bool:
        return all(c in self._VALID_CHARS for c in s)

    def find(self, text: str) -> list[PiiEntity]:
        return [
            self._entity(m.group(1), m.start(), m.end(), 0.75)
            for m in self._PATTERN.finditer(text)
            if self._valid(m.group(1))
        ]


class DeKrankenversicherung(BaseRecognizer):
    """
    Krankenversicherungsnummer — Alman sağlık sigortası numarası.
    Format: 1 harf + 9 rakam (örn: A123456789)
    Bağlamsal keyword zorunlu — false positive riski var.
    """
    entity_type = "SGK_NO"

    _PATTERN = re.compile(
        r"(?:Krankenversicherung|KV-Nummer|Versicherungsnummer|KVNR)"
        r"\s*:?\s*([A-Z][0-9]{9})\b",
        re.IGNORECASE,
    )

    def find(self, text: str) -> list[PiiEntity]:
        return [
            self._entity(m.group(1), m.start(1), m.end(1), 0.90)
            for m in self._PATTERN.finditer(text)
        ]


DE_RECOGNIZERS: list[BaseRecognizer] = [
    DeSteuerId(),
    DePersonalausweis(),
    DeKrankenversicherung(),
]
