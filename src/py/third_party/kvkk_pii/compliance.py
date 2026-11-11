"""
KVKK Uyum Raporu -- tespit edilen PII'i KVKK maddeleriyle iliskilendir.

Kullanim:
    report = ComplianceReport.from_result(result)
    print(report.summary())
    report.to_dict()  # JSON export icin
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

from .result import PiiResult, PiiEntity

RiskLevel = Literal["low", "medium", "high", "critical"]

# Entity type -> KVKK maddesi + aciklama
_KVKK_MAP: dict[str, dict] = {
    "TC_KIMLIK": {
        "madde": "KVKK Madde 6 degil — Kimlik verisi (Madde 4/c)",
        "kategori": "Kimlik Verisi",
        "risk": "critical",
        "oneri": "Isleme icin acik riza veya kanuni dayanak gerekli.",
    },
    "VKN": {
        "madde": "Kimlik Verisi (Madde 4/c)",
        "kategori": "Kimlik Verisi",
        "risk": "medium",
        "oneri": "Vergi kaydi amacli isleme mesru menfaatle yapilabilir.",
    },
    "IBAN_TR": {
        "madde": "Finansal Veri (Madde 4/c)",
        "kategori": "Finansal Veri",
        "risk": "high",
        "oneri": "Odeme islemleri disinda saklanmamali.",
    },
    "KREDI_KARTI": {
        "madde": "Finansal Veri (Madde 4/c)",
        "kategori": "Finansal Veri",
        "risk": "critical",
        "oneri": "PCI-DSS uyumu zorunlu. Kart numarasi asla loglanmamali.",
    },
    "TELEFON_TR": {
        "madde": "Iletisim Verisi (Madde 4/c)",
        "kategori": "Iletisim Verisi",
        "risk": "medium",
        "oneri": "Pazarlama amacli isleme icin acik riza gerekli (IYS).",
    },
    "EMAIL": {
        "madde": "Iletisim Verisi (Madde 4/c)",
        "kategori": "Iletisim Verisi",
        "risk": "medium",
        "oneri": "Ticari elektronik ileti icin IYS kaydi gerekli.",
    },
    "KISI_ADI": {
        "madde": "Kisisel Veri (Madde 3/d)",
        "kategori": "Kimlik Verisi",
        "risk": "low",
        "oneri": "Diger verilerle birlestigi durumda risk artar.",
    },
    "KONUM": {
        "madde": "Konum Verisi (Madde 4/c)",
        "kategori": "Konum Verisi",
        "risk": "medium",
        "oneri": "Surekli konum takibi icin acik riza gerekli.",
    },
    "ADRES": {
        "madde": "Konum Verisi (Madde 4/c)",
        "kategori": "Konum Verisi",
        "risk": "medium",
        "oneri": "Adres verisi kimlikle bilesince yuksek risk.",
    },
    "SAGLIK_VERISI": {
        "madde": "KVKK Madde 6 — Ozel Nitelikli Kisisel Veri",
        "kategori": "Ozel Nitelikli Veri",
        "risk": "critical",
        "oneri": "Acik riza zorunlu. Yetkili kurum olmadan islenemez.",
    },
    "DINI_INANC": {
        "madde": "KVKK Madde 6 — Ozel Nitelikli Kisisel Veri",
        "kategori": "Ozel Nitelikli Veri",
        "risk": "critical",
        "oneri": "Acik riza zorunlu. Kural olarak islenemez.",
    },
    "SIYASI_GORUS": {
        "madde": "KVKK Madde 6 — Ozel Nitelikli Kisisel Veri",
        "kategori": "Ozel Nitelikli Veri",
        "risk": "critical",
        "oneri": "Acik riza zorunlu. Kural olarak islenemez.",
    },
    "SENDIKA_UYELIGII": {
        "madde": "KVKK Madde 6 — Ozel Nitelikli Kisisel Veri",
        "kategori": "Ozel Nitelikli Veri",
        "risk": "critical",
        "oneri": "Acik riza zorunlu. Kural olarak islenemez.",
    },
    "BIYOMETRIK_VERI": {
        "madde": "KVKK Madde 6 — Ozel Nitelikli Kisisel Veri",
        "kategori": "Ozel Nitelikli Veri",
        "risk": "critical",
        "oneri": "Acik riza zorunlu. Guvenli ortamda saklanmali.",
    },
    "SGK_NO": {
        "madde": "Kimlik Verisi (Madde 4/c)",
        "kategori": "Kimlik Verisi",
        "risk": "high",
        "oneri": "SGK islemleri disinda islenemez.",
    },
    "IP_ADRESI": {
        "madde": "Kisisel Veri (Madde 3/d) — baglamsal",
        "kategori": "Teknik Veri",
        "risk": "low",
        "oneri": "Dinamik IP tek basina kisisel veri sayilmayabilir.",
    },
    "PLAKA_TR": {
        "madde": "Kimlik Verisi (Madde 4/c) — dolayli",
        "kategori": "Kimlik Verisi",
        "risk": "low",
        "oneri": "Arac sahibiyle iliskilendirildiginde kisisel veri.",
    },
}

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass
class Violation:
    entity_type: str
    count: int
    madde: str
    kategori: str
    risk: RiskLevel
    oneri: str
    samples: list[str] = field(default_factory=list)


@dataclass
class ComplianceReport:
    violations: list[Violation]
    overall_risk: RiskLevel
    entity_count: int
    has_madde6: bool

    @classmethod
    def from_result(cls, result: PiiResult, max_samples: int = 3) -> "ComplianceReport":
        # Entity type basina grupla
        by_type: dict[str, list[PiiEntity]] = {}
        for e in result.entities:
            by_type.setdefault(e.entity_type, []).append(e)

        violations: list[Violation] = []
        for entity_type, entities in by_type.items():
            mapping = _KVKK_MAP.get(entity_type)
            if not mapping:
                continue
            violations.append(Violation(
                entity_type=entity_type,
                count=len(entities),
                madde=mapping["madde"],
                kategori=mapping["kategori"],
                risk=mapping["risk"],
                oneri=mapping["oneri"],
                samples=[e.text for e in entities[:max_samples]],
            ))

        # En yuksek risk seviyesi
        if violations:
            overall_risk = max(violations, key=lambda v: _RISK_ORDER[v.risk]).risk
        else:
            overall_risk = "low"

        has_madde6 = any(v.kategori == "Ozel Nitelikli Veri" for v in violations)

        # Risk seviyesine gore sirala
        violations.sort(key=lambda v: _RISK_ORDER[v.risk], reverse=True)

        return cls(
            violations=violations,
            overall_risk=overall_risk,
            entity_count=len(result.entities),
            has_madde6=has_madde6,
        )

    def summary(self) -> str:
        if not self.violations:
            return "No PII detected."

        lines = [
            f"KVKK Compliance Report — {self.entity_count} entities, overall risk: {self.overall_risk.upper()}",
        ]
        if self.has_madde6:
            lines.append("KVKK Article 6 (Special Category Data) detected!")
        lines.append("")
        for v in self.violations:
            lines.append(f"  [{v.risk.upper()}] {v.entity_type} x {v.count}")
            lines.append(f"    Article: {v.madde}")
            lines.append(f"    Advice : {v.oneri}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "overall_risk": self.overall_risk,
            "entity_count": self.entity_count,
            "has_madde6": self.has_madde6,
            "violations": [
                {
                    "entity_type": v.entity_type,
                    "count": v.count,
                    "madde": v.madde,
                    "kategori": v.kategori,
                    "risk": v.risk,
                    "oneri": v.oneri,
                    "samples": v.samples,
                }
                for v in self.violations
            ],
        }
