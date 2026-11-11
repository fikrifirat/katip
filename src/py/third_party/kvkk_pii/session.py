"""
PiiSession — LLM proxy kullanımı için reversible maskeleme.

Her request için yeni bir session oluştur.
Session ephemeral'dır — serialize edilmez, saklanmaz.
"""
from __future__ import annotations
import random
import string
from dataclasses import dataclass

from .result import PiiEntity, PiiResult

DEFAULT_TOKEN_FORMAT = "[{type}_{id}]"


def _short_id() -> str:
    """3 karakterli rastgele alfanumerik ID üret."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=3))


@dataclass
class MaskedEntity:
    entity: PiiEntity
    placeholder: str   # örn. "[TC_KIMLIK_a3f]"
    original: str      # orijinal metin


class PiiSession:
    """
    Kullanım:
        session = detector.create_session(text)
        masked  = session.mask()
        # → "[KISI_ADI_x7k] TC: [TC_KIMLIK_a3f]"

        restored = session.restore("[KISI_ADI_x7k] bulunamadı")
        # → "Ali Veli bulunamadı"

    Token formatı özelleştirme:
        # JSON/SQL için güvenli
        session = detector.create_session(text, token_format="__{type}_{id}__")

        # XML için
        session = detector.create_session(text, token_format="PII_{type}_{id}")

        # Sadece tip, ID olmadan (restore çalışmaz, sadece anonymize için)
        detector.anonymize(text, placeholder="***")
    """

    def __init__(self, result: PiiResult, token_format: str = DEFAULT_TOKEN_FORMAT) -> None:
        self._result = result
        self._token_format = token_format
        # orijinal değer → placeholder (aynı değer tekrar geçerse aynı placeholder)
        self._value_to_placeholder: dict[str, str] = {}
        # placeholder → orijinal değer (restore için)
        self._placeholder_to_value: dict[str, str] = {}
        self.masked_entities: list[MaskedEntity] = []

    def _make_placeholder(self, entity_type: str, uid: str) -> str:
        return self._token_format.format(type=entity_type, id=uid)

    def _get_or_create_placeholder(self, entity: PiiEntity) -> str:
        key = entity.text
        if key in self._value_to_placeholder:
            return self._value_to_placeholder[key]

        uid = _short_id()
        # Çakışma ihtimaline karşı yeniden üret
        while self._make_placeholder(entity.entity_type, uid) in self._placeholder_to_value:
            uid = _short_id()

        placeholder = self._make_placeholder(entity.entity_type, uid)
        self._value_to_placeholder[key] = placeholder
        self._placeholder_to_value[placeholder] = key
        return placeholder

    def mask(self, text: str | None = None) -> str:
        """
        Session'ın analiz ettiği metni maskele.
        text=None ise orijinal analiz metnini kullanır.
        """
        source = text if text is not None else self._result.text
        if text is not None and text != self._result.text:
            raise ValueError(
                "mask() orijinal metinle çağrılmalı. "
                "Farklı metin için yeni session oluştur."
            )

        result = source
        # Sondan başa doğru değiştir — index kayması olmasın
        for entity in sorted(self._result.entities, key=lambda e: e.start, reverse=True):
            placeholder = self._get_or_create_placeholder(entity)
            self.masked_entities.append(
                MaskedEntity(entity=entity, placeholder=placeholder, original=entity.text)
            )
            result = result[: entity.start] + placeholder + result[entity.end :]

        return result

    def restore(self, masked_text: str) -> str:
        """AI response'undaki placeholder'ları orijinal değerlerle değiştir."""
        result = masked_text
        # Uzun placeholder'ları önce işle — kısa olanların içinde geçmesi olasılığına karşı
        for placeholder, original in sorted(
            self._placeholder_to_value.items(), key=lambda x: -len(x[0])
        ):
            result = result.replace(placeholder, original)
        return result

    @property
    def mapping(self) -> dict[str, str]:
        """placeholder → orijinal değer haritası (audit/debug için)."""
        return dict(self._placeholder_to_value)

    def __repr__(self) -> str:
        return f"PiiSession(entities={len(self.masked_entities)}, placeholders={len(self._placeholder_to_value)})"
