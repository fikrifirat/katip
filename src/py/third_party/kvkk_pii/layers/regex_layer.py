"""
Layer 1: Regex tabanlı PII tespiti.

Varsayılan recognizer seti DEFAULT_RECOGNIZERS'dır.
PiiDetector(recognizers=[...]) ile özelleştirilebilir.
"""
from ..base import BaseRecognizer
from ..result import PiiEntity
from ..recognizers.tc_kimlik import TcKimlikRecognizer
from ..recognizers.vkn import VknRecognizer
from ..recognizers.iban import IbanRecognizer
from ..recognizers.telefon import TelefonRecognizer
from ..recognizers.plaka import PlakaRecognizer
from ..recognizers.genel import EmailRecognizer, IpAdresRecognizer, PasaportRecognizer
from ..recognizers.kredi_karti import KrediKartiRecognizer
from ..recognizers.sgk import SgkRecognizer

# Varsayılan aktif recognizer seti (kullanıcı override edebilir)
DEFAULT_RECOGNIZERS: list[BaseRecognizer] = [
    TcKimlikRecognizer(),
    IbanRecognizer(),
    TelefonRecognizer(),
    EmailRecognizer(),
    IpAdresRecognizer(),
    PasaportRecognizer(),
    KrediKartiRecognizer(),
    SgkRecognizer(),
    VknRecognizer(),    # TC Kimlik'ten sonra — çakışma önlemi
    PlakaRecognizer(),  # En sona — false positive riski yüksek
]


def _remove_overlaps(entities: list[PiiEntity]) -> list[PiiEntity]:
    """Örtüşen entity'lerde score'u yüksek olanı tut."""
    entities = sorted(entities, key=lambda e: (e.start, -e.score))
    result: list[PiiEntity] = []
    last_end = -1
    for entity in entities:
        if entity.start >= last_end:
            result.append(entity)
            last_end = entity.end
    return result


class RegexLayer:
    def __init__(
        self,
        recognizers: list[BaseRecognizer] | None = None,
        disable: list[str] | None = None,
        before: list[BaseRecognizer] | None = None,
        after: list[BaseRecognizer] | None = None,
    ) -> None:
        base = recognizers if recognizers is not None else list(DEFAULT_RECOGNIZERS)
        if disable:
            disabled = set(disable)
            base = [r for r in base if r.entity_type not in disabled]
        final = list(before or []) + base + list(after or [])
        self.recognizers = final

    def analyze(self, text: str) -> list[PiiEntity]:
        entities: list[PiiEntity] = []
        for recognizer in self.recognizers:
            if recognizer.enabled:
                entities.extend(recognizer.find(text))
        return _remove_overlaps(entities)
