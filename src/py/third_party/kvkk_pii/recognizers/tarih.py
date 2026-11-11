"""Tarih tanıyıcı — GG.AA.YYYY, GG/AA/YYYY, DD Month YYYY formatları."""
import re
from ..base import BaseRecognizer
from ..result import PiiEntity

_TR_MONTHS = (
    r"(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|"
    r"Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)"
)

_PATTERNS = [
    # GG.AA.YYYY veya GG/AA/YYYY veya GG-AA-YYYY
    re.compile(r"\b(0?[1-9]|[12][0-9]|3[01])[.\-/](0?[1-9]|1[0-2])[.\-/](19|20)\d{2}\b"),
    # YYYY-MM-DD (ISO)
    re.compile(r"\b(19|20)\d{2}-(0?[1-9]|1[0-2])-(0?[1-9]|[12][0-9]|3[01])\b"),
    # GG Month YYYY (Türkçe ay adı)
    re.compile(
        rf"\b(0?[1-9]|[12][0-9]|3[01])\s+{_TR_MONTHS}\s+(19|20)\d{{2}}\b",
        re.IGNORECASE,
    ),
]


class TarihRecognizer(BaseRecognizer):
    """
    Tarih tespiti. Doğum tarihi gibi bağlamsal PII için kullanışlı.
    Yüksek false-positive riski var — context'e bağlı kullan.
    """
    entity_type = "TC_KIMLIK"  # override edilebilir, varsayılan genel

    def __init__(self, entity_type: str = "TARIH") -> None:  # type: ignore[override]
        # TARIH EntityType'a eklenmeli — şimdilik string olarak kullanılıyor
        self._entity_type_str = entity_type

    def find(self, text: str) -> list[PiiEntity]:
        results: list[PiiEntity] = []
        seen: set[tuple[int, int]] = set()
        for pattern in _PATTERNS:
            for m in pattern.finditer(text):
                span = (m.start(), m.end())
                if span not in seen:
                    seen.add(span)
                    results.append(PiiEntity(
                        entity_type=self._entity_type_str,  # type: ignore[arg-type]
                        text=m.group(),
                        start=m.start(),
                        end=m.end(),
                        score=0.75,
                        layer="regex",
                    ))
        return results
