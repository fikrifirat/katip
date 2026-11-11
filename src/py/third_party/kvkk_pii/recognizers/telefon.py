import re
from ..base import BaseRecognizer
from ..config import TelefonConfig
from ..result import PiiEntity

# Cep telefonu: +90 veya 0 ile başlayan 5XX
_PATTERN_MOBILE = re.compile(
    r"(?<!\d)"
    r"(?:\+90[\s\-]?|0)"
    r"\(?(5[0-9]{2})\)?"
    r"[\s\-]?([0-9]{3})[\s\-]?([0-9]{2})[\s\-]?([0-9]{2})"
    r"(?!\d)"
)

# Sabit hat: alan kodu 2XX, 3XX, 4XX (İstanbul=212/216, Ankara=312, İzmir=232...)
_PATTERN_LANDLINE = re.compile(
    r"(?<!\d)"
    r"(?:\+90[\s\-]?|0)"
    r"\(?([2-4][0-9]{2})\)?"
    r"[\s\-]?([0-9]{3})[\s\-]?([0-9]{2})[\s\-]?([0-9]{2})"
    r"(?!\d)"
)

# Uluslararası: +XX veya +XXX ile başlayan (Türkiye hariç)
_PATTERN_INTERNATIONAL = re.compile(
    r"(?<!\d)"
    r"\+(?!90\b)"                                  # +90 değil
    r"([1-9][0-9]{0,2})"                           # ülke kodu 1-3 hane
    r"[\s\-]?"
    r"([0-9]{1,4}(?:[\s\-][0-9]{2,8}){1,4})"      # boşluk/tire ile ayrılmış gruplar
    r"(?!\d)"
)


class TelefonRecognizer(BaseRecognizer):
    entity_type = "TELEFON_TR"

    def __init__(self, config: TelefonConfig | None = None) -> None:
        self.config = config or TelefonConfig()

    def find(self, text: str) -> list[PiiEntity]:
        results: list[PiiEntity] = []

        if self.config.include_mobile:
            for m in _PATTERN_MOBILE.finditer(text):
                results.append(self._entity(m.group(0), m.start(), m.end(), self.config.score_mobile))

        if self.config.include_landline:
            for m in _PATTERN_LANDLINE.finditer(text):
                # Mobil ile örtüşme önlemi
                if not any(r.start == m.start() for r in results):
                    results.append(
                        self._entity(m.group(0), m.start(), m.end(), self.config.score_landline)
                    )

        if self.config.include_international:
            for m in _PATTERN_INTERNATIONAL.finditer(text):
                total_digits = len(m.group(1) + m.group(2).replace(" ", "").replace("-", ""))
                if total_digits < 7 or total_digits > 15:
                    continue
                if not any(r.start == m.start() for r in results):
                    results.append(
                        self._entity(m.group(0), m.start(), m.end(), self.config.score_international)
                    )

        return results
