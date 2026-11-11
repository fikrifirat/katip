"""Kredi kartı numarası tanıyıcı — Luhn algoritması ile doğrulama."""
import re
from ..base import BaseRecognizer
from ..result import PiiEntity

# 13-19 hane, isteğe bağlı boşluk veya tire ile ayrılmış gruplar
_PATTERN = re.compile(
    r"\b(?:\d[ \-]?){13,18}\d\b"
)


def _luhn_valid(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _known_prefix(number: str) -> bool:
    """Bilinen kart ağı prefix'i ile başlıyor mu?"""
    n = number.replace(" ", "").replace("-", "")
    return (
        n[0] == "4"                          # Visa
        or n[:2] in ("51", "52", "53", "54", "55")  # Mastercard
        or n[:4] in ("6011",)                # Discover
        or n[:2] in ("34", "37")             # Amex
        or n[:4] in ("3528", "3589")         # JCB
    )


class KrediKartiRecognizer(BaseRecognizer):
    entity_type = "KREDI_KARTI"

    def find(self, text: str) -> list[PiiEntity]:
        results: list[PiiEntity] = []
        for m in _PATTERN.finditer(text):
            raw = m.group()
            digits_only = raw.replace(" ", "").replace("-", "")
            if len(digits_only) < 13 or len(digits_only) > 19:
                continue
            if _luhn_valid(digits_only) and _known_prefix(digits_only):
                results.append(self._entity(raw, m.start(), m.end(), 0.95))
        return results
