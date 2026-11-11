"""SGK (Sosyal Güvenlik Kurumu) numarası tanıyıcı."""
import re
from ..base import BaseRecognizer
from ..config import SgkConfig
from ..result import PiiEntity

# SGK sicil numarası: genellikle 10-11 hane, belirli prefix'lerle
# İşyeri SGK: xx-xxx-xxx-x-xx formatı
_PATTERN_ISYERI = re.compile(
    r"\b([0-9]{2})[\-\s]([0-9]{3})[\-\s]([0-9]{3})[\-\s]([0-9]{1})[\-\s]([0-9]{2})\b"
)

# Sigortalı sicil no: TC kimliğe bağlı olmayan eski sistemde 9-11 hane
# Bağlamsal anahtar kelime gerektir — aksi halde çok fazla false positive
_PATTERN_SICIL = re.compile(
    r"(?:SGK|Sicil|Sigorta|SSK)\s*(?:No|Numarası|:)?\s*:?\s*([0-9]{9,11})\b",
    re.IGNORECASE,
)


class SgkRecognizer(BaseRecognizer):
    """
    SGK numarası tanıyıcı.
    İşyeri SGK numaraları format bazlı, sicil numaraları bağlamsal (keyword zorunlu).
    """
    entity_type = "SGK_NO"

    def __init__(self, config: SgkConfig | None = None) -> None:
        self.config = config or SgkConfig()

    def find(self, text: str) -> list[PiiEntity]:
        results: list[PiiEntity] = []

        # İşyeri SGK — format yeterince spesifik
        for m in _PATTERN_ISYERI.finditer(text):
            results.append(self._entity(m.group(0), m.start(), m.end(), self.config.score))

        # Sigortalı sicil — keyword bağlamı zorunlu
        for m in _PATTERN_SICIL.finditer(text):
            results.append(self._entity(m.group(1), m.start(1), m.end(1), self.config.score))

        return results
