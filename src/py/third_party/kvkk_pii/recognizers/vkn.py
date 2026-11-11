import re
from ..base import BaseRecognizer
from ..result import PiiEntity

_PATTERN = re.compile(r"\b([1-9][0-9]{9})\b")


def _checksum_valid(vkn: str) -> bool:
    d = [int(c) for c in vkn]
    total = 0
    for i in range(9):
        tmp = (d[i] + (9 - i)) % 10
        if tmp == 0:
            val = 9
        else:
            val = (tmp * (2 ** (9 - i))) % 9
            if val == 0:
                val = 9
        total += val
    check = total % 10
    return d[9] == check


class VknRecognizer(BaseRecognizer):
    entity_type = "VKN"

    def find(self, text: str) -> list[PiiEntity]:
        return [
            self._entity(m.group(1), m.start(), m.end(), 0.85)
            for m in _PATTERN.finditer(text)
            if _checksum_valid(m.group(1))
        ]
