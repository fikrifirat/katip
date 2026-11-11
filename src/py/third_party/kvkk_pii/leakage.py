"""
LeakageAnalyzer — AI çıktısındaki PII sızıntısını tespit et.

Üç kontrol yapar:
  A) AI response'unda maskelenmemiş PII var mı?
  B) Session'daki orijinal değerler response'a sızdı mı?
  C) Input'ta olmayan yeni PII hallucinate edildi mi?
"""
from __future__ import annotations
from dataclasses import dataclass, field

from .result import PiiEntity
from .session import PiiSession


@dataclass
class LeakageReport:
    """
    safe          → hiçbir sızıntı yoksa True
    leaked        → session'daki orijinal değerlerin response'da geçmesi (B)
    new_pii       → AI'ın ürettiği, input'ta olmayan PII (C)
    risk_score    → 0.0 (temiz) – 1.0 (kritik sızıntı)
    """
    leaked: list[PiiEntity] = field(default_factory=list)   # B: session değerleri sızdı
    new_pii: list[PiiEntity] = field(default_factory=list)  # C: hallucinated PII
    raw_response_entities: list[PiiEntity] = field(default_factory=list)  # A: tüm tespitler

    @property
    def safe(self) -> bool:
        return len(self.leaked) == 0 and len(self.new_pii) == 0

    @property
    def risk_score(self) -> float:
        if not self.leaked and not self.new_pii:
            return 0.0
        score = 0.0
        # Sızan session değerleri → yüksek risk (orijinal veri açığa çıktı)
        score += min(len(self.leaked) * 0.3, 0.7)
        # Hallucinated PII → orta risk
        score += min(len(self.new_pii) * 0.15, 0.3)
        return round(min(score, 1.0), 2)

    def summary(self) -> str:
        if self.safe:
            return "Temiz — PII sızıntısı tespit edilmedi."
        parts = []
        if self.leaked:
            types = ", ".join({e.entity_type for e in self.leaked})
            parts.append(f"{len(self.leaked)} session değeri sızdı ({types})")
        if self.new_pii:
            types = ", ".join({e.entity_type for e in self.new_pii})
            parts.append(f"{len(self.new_pii)} yeni PII tespit edildi ({types})")
        return " | ".join(parts) + f" — risk: {self.risk_score:.0%}"


class PiiLeakageError(Exception):
    """on_leak='raise' ile two_way() çağrıldığında fırlatılır."""
    def __init__(self, report: LeakageReport) -> None:
        self.report = report
        super().__init__(report.summary())


class LeakageAnalyzer:
    """
    Kullanım:
        analyzer = LeakageAnalyzer(detector)

        masked   = session.mask(prompt)
        response = call_openai(masked)          # ham, restore edilmemiş

        report = analyzer.analyze(session, response)
        if not report.safe:
            log_or_block(report)

        restored = session.restore(response)

    NOT: Leakage taraması için NER/GLiNER değil, yalnızca regex kullanılır.
    NER/GLiNER'ın AI çıktısında yanlış alarm üretme riski yüksektir.
    Kesin pattern'i olan yapısal PII (TC, IBAN, e-posta...) ve session
    değerlerinin exact-match kontrolü leakage tespiti için yeterlidir.
    """

    def __init__(self, detector) -> None:  # detector: PiiDetector (circular import önlemi)
        self._detector = detector
        self._scan_detector: "PiiDetector | None" = None

    def _get_scan_detector(self):
        """Leakage taraması için regex-only detector (lazy init)."""
        if self._scan_detector is None:
            # Circular import önlemi için burada import
            detector_cls = type(self._detector)
            self._scan_detector = detector_cls(
                layers=["regex"],
                recognizers=self._detector._regex_layer.recognizers,
            )
        return self._scan_detector

    @staticmethod
    def _strip_placeholders(text: str, placeholders: set[str]) -> str:
        """
        NER/GLiNER'ın placeholder içeriğini yanlış sınıflandırmaması için
        bilinen placeholder'ları metinden çıkar.
        """
        result = text
        for ph in placeholders:
            result = result.replace(ph, " ")
        return result

    def analyze(self, session: PiiSession, raw_ai_response: str) -> LeakageReport:
        """
        raw_ai_response: session.restore() ÇAĞRILMADAN önce gelen ham AI metni.
        """
        report = LeakageReport()

        # Placeholder'ları temizlenmiş metin — NER/GLiNER yanlış tetiklenmesin
        clean_for_scan = self._strip_placeholders(
            raw_ai_response, set(session.mapping.keys())
        )

        # A) Response'un içindeki yapısal PII'ı tara — regex-only (NER/GLiNER yanlış alarm üretir)
        scan = self._get_scan_detector().analyze(clean_for_scan)
        report.raw_response_entities = scan.entities

        # Orijinal değerler seti (session'dan)
        original_values = set(session.mapping.values())
        # Input'ta olan placeholder'lar (maskelenmiş hali)
        placeholders = set(session.mapping.keys())

        for entity in scan.entities:
            if entity.text in original_values:
                # B) Session'daki orijinal değer response'a sızdı
                report.leaked.append(entity)
            elif entity.text not in placeholders:
                # C) Input'ta olmayan, AI'ın ürettiği yeni PII
                report.new_pii.append(entity)

        return report
