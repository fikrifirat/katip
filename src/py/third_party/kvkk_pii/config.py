"""
RecognizerConfig — her recognizer için ayarlanabilir hassasiyet parametreleri.

Kullanım:
    from kvkk_pii.config import TcKimlikConfig, TelefonConfig

    r = TcKimlikRecognizer(TcKimlikConfig(allow_spaced=True))
    r = TelefonRecognizer(TelefonConfig(include_landline=True, include_international=True))
"""
from dataclasses import dataclass, field


@dataclass
class TcKimlikConfig:
    allow_spaced: bool = True
    """'100 000 001 46' ve '100-000-001-46' formatlarını kabul et."""

    require_checksum: bool = True
    """False: checksum doğrulaması olmadan sadece format eşleştir (düşük precision)."""

    score_compact: float = 1.0
    """Boşluksuz format için güven skoru."""

    score_spaced: float = 0.90
    """Boşluklu/tireli format için güven skoru (biraz daha düşük)."""


@dataclass
class VknConfig:
    require_checksum: bool = True
    score: float = 0.85


@dataclass
class TelefonConfig:
    include_mobile: bool = True
    """5XX operatör kodlu cep telefonları (+90 532...)"""

    include_landline: bool = True
    """Sabit hat: 0212, 0312, 0232 vb."""

    include_international: bool = True
    """Yabancı ülke kodları: +1, +44, +49 vb. (dikkatli kullan, false positive riski)"""

    allow_parentheses: bool = True
    """0(532) formatını kabul et."""

    score_mobile: float = 0.95
    score_landline: float = 0.90
    score_international: float = 0.75


@dataclass
class IbanConfig:
    require_mod97: bool = True
    """False: format kontrolü yeterli, mod97 doğrulaması yapma."""

    score: float = 1.0


@dataclass
class EmailConfig:
    score: float = 0.99
    strict_tld: bool = False
    """True: sadece bilinen TLD'leri (.com, .net, .org, .tr...) kabul et."""


@dataclass
class AdresConfig:
    require_street_keyword: bool = True
    """
    True  (sıkı): 'Mahalle', 'Sokak', 'Cadde' gibi anahtar kelime şart.
    False (gevşek): sadece 'No:15' veya 'D:3' yeterli — çok daha fazla false positive.
    """

    require_city: bool = False
    """True: İl/ilçe adı da bulunmalı."""

    score_full: float = 0.85
    """Cadde + No + İl gibi tam adres için."""

    score_partial: float = 0.65
    """Eksik ama kısmi adres için."""


@dataclass
class SgkConfig:
    score: float = 0.80


@dataclass
class KisiAdiConfig:
    require_title: bool = True
    """
    True  (sıkı, varsayılan): 'Sayın/Bay/Dr.' gibi unvan zorunlu.
    False (gevşek): unvansız isimler de eşleştir — false positive riski yüksek.
    """

    min_word_count: int = 2
    """En az kaç kelime olmalı (1 kelimelik isimler çok gürültülü)."""

    score: float = 0.80


@dataclass
class NerConfig:
    model_id: str = "akdeniz27/xlm-roberta-base-turkish-ner"
    """HuggingFace model ID. Dile göre değiştirilebilir."""

    model_size_mb: int = 450
    """İndirme onayı mesajında gösterilecek boyut (MB)."""

    min_score: float = 0.80
    """NER model güven eşiği. Yükseltmek false positive'i azaltır."""

    min_chars: int = 3
    """Bu uzunluktan kısa entity'leri atla."""

    chunk_size: int = 400
    """Token başına karakter tahmini * max token. Uzun metinlerde chunk boyutu."""

    chunk_overlap: int = 50
    """Chunk sınırlarında entity'lerin kaçmaması için örtüşme (karakter)."""


@dataclass
class GlinerConfig:
    threshold: float = 0.5
    """GLiNER güven eşiği. Yükseltmek false positive'i azaltır."""

    labels: list[str] = field(default_factory=list)
    """Boş bırakılırsa varsayılan KVKK Madde 6 etiketleri kullanılır."""
