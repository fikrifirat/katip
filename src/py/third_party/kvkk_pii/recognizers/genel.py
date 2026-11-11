import re
from ..base import BaseRecognizer
from ..result import PiiEntity


class EmailRecognizer(BaseRecognizer):
    entity_type = "EMAIL"
    _pattern = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

    def find(self, text: str) -> list[PiiEntity]:
        return [
            self._entity(m.group(), m.start(), m.end(), 0.99)
            for m in self._pattern.finditer(text)
        ]


class IpAdresRecognizer(BaseRecognizer):
    entity_type = "IP_ADRESI"
    _pattern = re.compile(
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    )

    def find(self, text: str) -> list[PiiEntity]:
        return [
            self._entity(m.group(), m.start(), m.end(), 0.99)
            for m in self._pattern.finditer(text)
        ]


class PasaportRecognizer(BaseRecognizer):
    entity_type = "PASAPORT_TR"
    _pattern = re.compile(r"\b[U][0-9]{8}\b", re.IGNORECASE)

    def find(self, text: str) -> list[PiiEntity]:
        return [
            self._entity(m.group(), m.start(), m.end(), 0.90)
            for m in self._pattern.finditer(text)
        ]
