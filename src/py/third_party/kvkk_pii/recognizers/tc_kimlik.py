import re
from ..base import BaseRecognizer
from ..config import TcKimlikConfig
from ..result import PiiEntity

# Kompakt: 11 rakam, ilk hane 0 olamaz
_PATTERN_COMPACT = re.compile(r"(?<!\d)([1-9][0-9]{10})(?!\d)")

# Boşluklu/tireli: "100 000 001 46" veya "100-000-001-46"
# Gruplar: 3-3-3-2 veya 4-4-3 gibi çeşitli kombinasyonlar
_PATTERN_SPACED = re.compile(
    r"(?<!\d)"
    r"([1-9][0-9]{2})"          # ilk 3 hane
    r"[\s\-]"
    r"([0-9]{3})"               # 2. grup 3 hane
    r"[\s\-]"
    r"([0-9]{3})"               # 3. grup 3 hane
    r"[\s\-]"
    r"([0-9]{2})"               # son 2 hane
    r"(?!\d)"
)


def _checksum_valid(digits: str) -> bool:
    d = [int(c) for c in digits]
    d10 = (7 * (d[0] + d[2] + d[4] + d[6] + d[8]) - (d[1] + d[3] + d[5] + d[7])) % 10
    d11 = sum(d[:10]) % 10
    return d[9] == d10 and d[10] == d11


class TcKimlikRecognizer(BaseRecognizer):
    entity_type = "TC_KIMLIK"

    def __init__(self, config: TcKimlikConfig | None = None) -> None:
        self.config = config or TcKimlikConfig()

    def find(self, text: str) -> list[PiiEntity]:
        results: list[PiiEntity] = []
        seen_spans: set[tuple[int, int]] = set()

        # Kompakt format
        for m in _PATTERN_COMPACT.finditer(text):
            digits = m.group(1)
            if self.config.require_checksum and not _checksum_valid(digits):
                continue
            span = (m.start(), m.end())
            seen_spans.add(span)
            results.append(self._entity(digits, m.start(), m.end(), self.config.score_compact))

        # Boşluklu/tireli format
        if self.config.allow_spaced:
            for m in _PATTERN_SPACED.finditer(text):
                digits = m.group(1) + m.group(2) + m.group(3) + m.group(4)
                if len(digits) != 11:
                    continue
                if self.config.require_checksum and not _checksum_valid(digits):
                    continue
                span = (m.start(), m.end())
                if span not in seen_spans:
                    results.append(
                        self._entity(m.group(0), m.start(), m.end(), self.config.score_spaced)
                    )

        return results
