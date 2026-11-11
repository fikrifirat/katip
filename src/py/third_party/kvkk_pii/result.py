from dataclasses import dataclass, field
from typing import Literal

EntityType = Literal[
    # Layer 1 — Regex: kimlik
    "TC_KIMLIK",
    "VKN",
    "IBAN_TR",
    "PASAPORT_TR",
    # Layer 1 — Regex: iletişim
    "TELEFON_TR",
    "EMAIL",
    "IP_ADRESI",
    # Layer 1 — Regex: diğer
    "PLAKA_TR",
    "KREDI_KARTI",
    "TARIH",
    "ADRES",
    "SGK_NO",
    # Layer 1/2 — kişi adı (regex unvan bazlı veya NER)
    "KISI_ADI",
    # Layer 2 — NER
    "KONUM",
    "KURUM",
    # Layer 3 — GLiNER (KVKK Madde 6)
    "SAGLIK_VERISI",
    "DINI_INANC",
    "SIYASI_GORUS",
    "SENDIKA_UYELIGII",
    "BIYOMETRIK_VERI",
]

LayerName = Literal["regex", "ner", "gliner"]


@dataclass
class PiiEntity:
    entity_type: EntityType
    text: str
    start: int
    end: int
    score: float          # 0.0 – 1.0
    layer: LayerName

    def __repr__(self) -> str:
        return (
            f"PiiEntity(type={self.entity_type!r}, text={self.text!r}, "
            f"start={self.start}, end={self.end}, score={self.score:.2f}, layer={self.layer!r})"
        )


@dataclass
class PiiResult:
    text: str
    entities: list[PiiEntity] = field(default_factory=list)

    def has(self, entity_type: EntityType) -> bool:
        return any(e.entity_type == entity_type for e in self.entities)

    def by_type(self, entity_type: EntityType) -> list[PiiEntity]:
        return [e for e in self.entities if e.entity_type == entity_type]

    def anonymize(self, placeholder: str | None = None) -> str:
        """Tespit edilen entity'leri placeholder ile değiştirir."""
        result = self.text
        # Sondan başa doğru değiştir — index kayması olmasın
        for entity in sorted(self.entities, key=lambda e: e.start, reverse=True):
            tag = placeholder or f"[{entity.entity_type}]"
            result = result[: entity.start] + tag + result[entity.end :]
        return result
