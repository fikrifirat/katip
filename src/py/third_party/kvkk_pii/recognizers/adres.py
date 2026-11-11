"""Türk adres tanıyıcı — Mahalle/Sokak/Cadde + No formatı."""
import re
from ..base import BaseRecognizer
from ..config import AdresConfig
from ..result import PiiEntity

# Cadde/sokak türleri
_STREET_KEYWORDS = (
    r"(?:Mahallesi?|Mah\.|Sokak|Sk\.|Sokağı|Cadde|Cad\.|Caddesi|"
    r"Bulvar|Blv\.|Bulvarı|Yolu|Yol|Köyü|Sitesi)"
)

# Numara/daire
_NO_PATTERN = r"(?:No|Numara|No:|Kapı No|Apt\.?)\s*:?\s*[0-9]+"
_DAIRE_PATTERN = r"(?:D(?:aire)?\.?|Kat)\s*:?\s*[0-9]+"

# Türk illeri (kısmi liste — NER geri kalanını yakalar)
_CITIES = (
    r"(?:Adana|Ankara|Antalya|Bursa|Diyarbakır|Erzurum|Eskişehir|"
    r"Gaziantep|İstanbul|İzmir|Kayseri|Kocaeli|Konya|Malatya|"
    r"Mersin|Samsun|Trabzon|Şanlıurfa|Van|Denizli|Muğla|Tekirdağ)"
)

# Posta kodu: 5 hane
_POSTAL_CODE = r"\b[0-9]{5}\b"

# Tam adres: sokak/cadde keyword + numara
_PATTERN_FULL = re.compile(
    rf"[A-ZÇĞİÖŞÜa-zçğışöşü\s]{{2,30}}"   # sokak/cadde adı
    rf"\s*{_STREET_KEYWORDS}"
    rf"(?:\s*,?\s*{_NO_PATTERN})?"
    rf"(?:\s*,?\s*{_DAIRE_PATTERN})?"
    rf"(?:\s*,?\s*{_CITIES})?",
)

# Kısmi adres: sadece "No:15 D:3" veya "No:15 Kadıköy" gibi
_PATTERN_PARTIAL = re.compile(
    rf"(?:{_NO_PATTERN})"
    rf"(?:\s*,?\s*{_DAIRE_PATTERN})?"
    rf"(?:\s*[/,]\s*{_CITIES})?",
)


class AdresRecognizer(BaseRecognizer):
    """
    Türk adres tanıyıcı.

    Config önerileri:
        AdresConfig(require_street_keyword=True)   → az false positive
        AdresConfig(require_street_keyword=False)  → daha kapsamlı, daha gürültülü
    """
    entity_type = "ADRES"

    def __init__(self, config: AdresConfig | None = None) -> None:
        self.config = config or AdresConfig()

    def find(self, text: str) -> list[PiiEntity]:
        results: list[PiiEntity] = []
        seen: set[tuple[int, int]] = set()

        # Tam adres: cadde/sokak keyword zorunlu
        for m in _PATTERN_FULL.finditer(text):
            span_text = m.group(0).strip()
            if len(span_text) < 10:
                continue
            span = (m.start(), m.start() + len(span_text))
            if span not in seen:
                seen.add(span)
                results.append(PiiEntity(
                    entity_type="ADRES",  # type: ignore[arg-type]
                    text=span_text,
                    start=span[0],
                    end=span[1],
                    score=self.config.score_full,
                    layer="regex",
                ))

        # Kısmi adres: sadece "require_street_keyword=False" ise
        if not self.config.require_street_keyword:
            for m in _PATTERN_PARTIAL.finditer(text):
                span_text = m.group(0).strip()
                span = (m.start(), m.start() + len(span_text))
                if span not in seen:
                    seen.add(span)
                    results.append(PiiEntity(
                        entity_type="ADRES",  # type: ignore[arg-type]
                        text=span_text,
                        start=span[0],
                        end=span[1],
                        score=self.config.score_partial,
                        layer="regex",
                    ))

        return results
