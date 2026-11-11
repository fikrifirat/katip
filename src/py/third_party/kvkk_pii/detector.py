"""Ana PiiDetector sınıfı — 3 katmanlı PII tespiti."""
from __future__ import annotations
from typing import Literal, TYPE_CHECKING

from .base import BaseRecognizer
from .result import PiiEntity, PiiResult
from .layers.regex_layer import RegexLayer, DEFAULT_RECOGNIZERS
from .layers.ner_layer import NerLayer
from .layers.gliner_layer import GlinerLayer
from .config import NerConfig, GlinerConfig

LayerSpec = Literal["regex", "ner", "gliner"]


class PiiDetector:
    """
    Kullanım örnekleri:

        # Sadece regex (varsayılan)
        detector = PiiDetector()

        # Regex + NER
        detector = PiiDetector(layers=["regex", "ner"])

        # Tam sistem
        detector = PiiDetector(layers=["regex", "ner", "gliner"])

        # Özel recognizer seti
        from kvkk_pii.recognizers.kisi_adi import KisiAdiRecognizer
        detector = PiiDetector(recognizers=DEFAULT_RECOGNIZERS + [KisiAdiRecognizer()])

        # Sadece belirli recognizer'lar
        detector = PiiDetector(recognizers=[TcKimlikRecognizer(), EmailRecognizer()])

    Modeller ilk kullanımda HuggingFace'den indirilir ve cache'lenir.
    """

    def __init__(
        self,
        layers: list[LayerSpec] | None = None,
        recognizers: list[BaseRecognizer] | None = None,
        disable: list[str] | None = None,
        before: list[BaseRecognizer] | None = None,
        after: list[BaseRecognizer] | None = None,
        download_policy: Literal["auto", "confirm", "never"] = "confirm",
        ner_config: NerConfig | None = None,
        gliner_config: GlinerConfig | None = None,
    ) -> None:
        self._layers: list[LayerSpec] = layers or ["regex"]
        self._regex_layer = RegexLayer(
            recognizers=recognizers, disable=disable, before=before, after=after,
        )
        self._ner: NerLayer | None = None
        self._gliner: GlinerLayer | None = None

        if "ner" in self._layers:
            self._ner = NerLayer(download_policy=download_policy, config=ner_config)
        if "gliner" in self._layers:
            self._gliner = GlinerLayer(download_policy=download_policy, config=gliner_config)

    def analyze(self, text: str) -> PiiResult:
        result = PiiResult(text=text)
        entities: list[PiiEntity] = self._regex_layer.analyze(text)

        if self._ner is not None:
            entities.extend(self._ner.analyze(text, already_found=entities))

        if self._gliner is not None:
            entities.extend(
                self._gliner.analyze(text, already_found=entities)
            )

        result.entities = sorted(entities, key=lambda e: e.start)
        return result

    def anonymize(self, text: str, placeholder: str | None = None) -> str:
        return self.analyze(text).anonymize(placeholder)

    def compliance_report(self, text: str) -> "ComplianceReport":
        from .compliance import ComplianceReport
        return ComplianceReport.from_result(self.analyze(text))

    def create_session(self, text: str, token_format: str | None = None) -> "PiiSession":
        """
        LLM proxy kullanımı için session oluştur.

        token_format örnekleri:
            "[{type}_{id}]"      → varsayılan: [TC_KIMLIK_a3f]
            "__{type}_{id}__"    → JSON/SQL güvenli: __TC_KIMLIK_a3f__
            "PII_{type}_{id}"    → XML güvenli: PII_TC_KIMLIK_a3f
            "<<{type}_{id}>>"    → özel format
        """
        from .session import PiiSession, DEFAULT_TOKEN_FORMAT
        result = self.analyze(text)
        return PiiSession(result, token_format=token_format or DEFAULT_TOKEN_FORMAT)

    def leakage_analyzer(self) -> "LeakageAnalyzer":
        """LeakageAnalyzer döndür."""
        from .leakage import LeakageAnalyzer
        return LeakageAnalyzer(self)

    def two_way(
        self,
        prompt: str,
        call_fn: "Callable[[str], str]",
        on_leak: "Literal['raise', 'warn', 'ignore']" = "warn",
        token_format: str | None = None,
    ) -> "TwoWayResult":
        """
        İki yönlü PII proxy — mask → AI → leakage check → restore.

        Args:
            prompt:   Kullanıcının orijinal metni (PII içerebilir).
            call_fn:  Maskeli metni alıp AI çıktısı döndüren fonksiyon.
                      Örn: lambda masked: openai.chat.completions.create(...)
            on_leak:  Sızıntı durumunda ne yapılsın:
                      'raise'  → PiiLeakageError fırlat
                      'warn'   → stderr'e yaz, devam et (varsayılan)
                      'ignore' → sessiz devam et

        Returns:
            TwoWayResult — output, report, session, safe
        """
        import sys
        from .leakage import LeakageAnalyzer, PiiLeakageError
        from .proxy import TwoWayResult

        # 1. Mask
        session = self.create_session(prompt, token_format=token_format)
        masked = session.mask(prompt)

        # 2. AI çağrısı
        raw_output = call_fn(masked)

        # 3. Leakage analizi (restore ÖNCE)
        analyzer = LeakageAnalyzer(self)
        report = analyzer.analyze(session, raw_output)

        if not report.safe:
            if on_leak == "raise":
                raise PiiLeakageError(report)
            elif on_leak == "warn":
                print(f"[kvkk-pii] UYARI: {report.summary()}", file=sys.stderr)

        # 4. Restore
        output = session.restore(raw_output)

        return TwoWayResult(
            masked_prompt=masked,
            raw_ai_output=raw_output,
            output=output,
            report=report,
            session=session,
        )
