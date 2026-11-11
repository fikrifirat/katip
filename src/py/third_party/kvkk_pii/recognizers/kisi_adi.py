"""Kişi adı tanıyıcı — unvan/lakap prefix bazlı regex."""
import re
from ..base import BaseRecognizer
from ..config import KisiAdiConfig
from ..result import PiiEntity

_UNVAN = (
    r"(?:"
    r"Sayın|Sn\.|Bay|Bayan|"
    r"Dr\.|Prof\.|Doç\.|Yrd\.?\s*Doç\.|Arş\.?\s*Gör\.|Öğr\.?\s*Gör\.|"
    r"Av\.|Müh\.|Uzm\.|Op\.|Opr\."
    r")"
)

_TR_WORD = r"[A-ZÇĞİÖŞÜ][a-zçğışöşüA-ZÇĞİÖŞÜ]{1,25}"

# Unvan zorunlu: "Sayın Ali Veli"
_PATTERN_WITH_TITLE = re.compile(
    rf"{_UNVAN}\s+(?:{_TR_WORD}\s?){{1,3}}"
)

# Unvansız: büyük harfle başlayan 2-3 kelime — false positive riski yüksek
# Sadece KisiAdiConfig(require_title=False) ile aktif
_PATTERN_NO_TITLE = re.compile(
    rf"(?<!\w)(?:{_TR_WORD}\s){{1,2}}{_TR_WORD}(?!\w)"
)

# Yaygın Türkçe kelimeler — isim gibi görünen false positive'ler
_STOPWORDS: set[str] = {
    "Türkiye", "Cumhuriyeti", "İstanbul", "Ankara", "İzmir", "Antalya",
    "Bursa", "Adana", "Konya", "Gaziantep", "Mersin", "Kayseri",
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
    "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar",
    "Türk", "Telekom", "Bankası", "Anonim", "Şirketi", "Limited",
}


class KisiAdiRecognizer(BaseRecognizer):
    """
    Unvan prefix bazlı isim tespiti.
    NER katmanı (Layer 2) zaten kişi adı tespit eder — bu yalnızca
    regex-only modda veya ek güvence olarak kullanılır.
    """
    entity_type = "KISI_ADI"

    def __init__(self, config: KisiAdiConfig | None = None) -> None:
        self.config = config or KisiAdiConfig()

    def find(self, text: str) -> list[PiiEntity]:
        results: list[PiiEntity] = []
        seen: set[tuple[int, int]] = set()

        # Unvan zorunlu mod (varsayılan)
        for m in _PATTERN_WITH_TITLE.finditer(text):
            span_text = m.group(0).strip()
            words = span_text.split()
            if len(words) < self.config.min_word_count:
                continue
            span = (m.start(), m.start() + len(span_text))
            seen.add(span)
            results.append(PiiEntity(
                entity_type="KISI_ADI",
                text=span_text,
                start=span[0],
                end=span[1],
                score=self.config.score,
                layer="regex",
            ))

        # Unvansız mod (gevşek) — dikkatli kullan
        if not self.config.require_title:
            for m in _PATTERN_NO_TITLE.finditer(text):
                span_text = m.group(0).strip()
                words = span_text.split()

                # Stopword kontrolü
                if any(w in _STOPWORDS for w in words):
                    continue
                if len(words) < self.config.min_word_count:
                    continue

                span = (m.start(), m.start() + len(span_text))
                if span not in seen:
                    seen.add(span)
                    results.append(PiiEntity(
                        entity_type="KISI_ADI",
                        text=span_text,
                        start=span[0],
                        end=span[1],
                        score=self.config.score * 0.7,  # unvansız daha düşük güven
                        layer="regex",
                    ))

        return results
