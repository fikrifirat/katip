import re
from ..base import BaseRecognizer
from ..result import PiiEntity

_PATTERN = re.compile(
    r"(?<!\w)"
    r"(0[1-9]|[1-7][0-9]|8[01])"
    r"[\s]?"
    r"([A-ZÇĞİÖŞÜ]{1,3})"
    r"[\s]?"
    r"([0-9]{2,4})"
    r"(?!\w)",
    re.IGNORECASE,
)


class PlakaRecognizer(BaseRecognizer):
    entity_type = "PLAKA_TR"

    def find(self, text: str) -> list[PiiEntity]:
        return [
            self._entity(m.group(0), m.start(), m.end(), 0.80)
            for m in _PATTERN.finditer(text)
        ]
