"""
AsyncPiiDetector -- asyncio/FastAPI entegrasyonu icin.

Kullanim:
    detector = AsyncPiiDetector(layers=["regex", "ner"])
    result = await detector.analyze(text)
    result = await detector.two_way(prompt, async_call_fn)
"""
from __future__ import annotations
import asyncio
from typing import Callable, Awaitable, Literal

from .detector import PiiDetector
from .base import BaseRecognizer
from .config import NerConfig, GlinerConfig
from .result import PiiResult
from .proxy import TwoWayResult


class AsyncPiiDetector:
    """
    PiiDetector'in async wrapper'i.
    Agir ML islemleri (NER, GLiNER) thread pool'da calistirilir --
    event loop'u bloklamaz.
    """

    def __init__(
        self,
        layers: list[str] | None = None,
        recognizers: list[BaseRecognizer] | None = None,
        download_policy: Literal["auto", "confirm", "never"] = "confirm",
        ner_config: NerConfig | None = None,
        gliner_config: GlinerConfig | None = None,
    ) -> None:
        self._detector = PiiDetector(
            layers=layers,
            recognizers=recognizers,
            download_policy=download_policy,
            ner_config=ner_config,
            gliner_config=gliner_config,
        )

    async def analyze(self, text: str) -> PiiResult:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._detector.analyze, text)

    async def anonymize(self, text: str, placeholder: str | None = None) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._detector.anonymize, text, placeholder
        )

    async def two_way(
        self,
        prompt: str,
        call_fn: Callable[[str], Awaitable[str]],
        on_leak: Literal["raise", "warn", "ignore"] = "warn",
        token_format: str | None = None,
    ) -> TwoWayResult:
        """
        Iki yonlu async proxy.
        call_fn async olmali: async def call_fn(masked: str) -> str
        """
        import sys
        from .leakage import LeakageAnalyzer, PiiLeakageError
        from .proxy import TwoWayResult

        # 1. Mask (sync, hizli)
        session = self._detector.create_session(prompt, token_format=token_format)
        masked = session.mask(prompt)

        # 2. Async AI cagrisi
        raw_output = await call_fn(masked)

        # 3. Leakage analizi (thread pool'da)
        loop = asyncio.get_event_loop()
        analyzer = LeakageAnalyzer(self._detector)
        report = await loop.run_in_executor(
            None, analyzer.analyze, session, raw_output
        )

        if not report.safe:
            if on_leak == "raise":
                raise PiiLeakageError(report)
            elif on_leak == "warn":
                print(f"[kvkk-pii] UYARI: {report.summary()}", file=sys.stderr)

        # 4. Restore (sync, hizli)
        output = session.restore(raw_output)

        return TwoWayResult(
            masked_prompt=masked,
            raw_ai_output=raw_output,
            output=output,
            report=report,
            session=session,
        )
