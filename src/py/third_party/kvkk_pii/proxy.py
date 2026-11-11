"""
TwoWayResult — iki yönlü PII proxy sonucu.

Kullanım:
    result = detector.two_way(
        prompt="Ali Veli TC: 10000000146 hakkında email yaz",
        call_fn=lambda masked: openai_call(masked),
    )
    result.output    # PII restore edilmiş final çıktı
    result.report    # LeakageReport
    result.safe      # bool
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

from .session import PiiSession
from .leakage import LeakageReport


@dataclass
class TwoWayResult:
    masked_prompt: str          # AI'a giden maskeli prompt
    raw_ai_output: str          # AI'dan gelen ham çıktı (restore edilmemiş)
    output: str                 # restore edilmiş final çıktı
    report: LeakageReport       # leakage analizi
    session: PiiSession         # mapping, debug için

    @property
    def safe(self) -> bool:
        return self.report.safe

    def __repr__(self) -> str:
        status = "TEMIZ" if self.safe else f"UYARI risk={self.report.risk_score:.0%}"
        return f"TwoWayResult({status}, entities={len(self.session.masked_entities)})"
