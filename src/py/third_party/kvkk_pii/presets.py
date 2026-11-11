"""
Hazır detector preset'leri.

Türkçe/KVKK her zaman ana odak — diğer diller ek seçenek.

Kullanım:
    from kvkk_pii.presets import turkish, german, french, multilingual

    detector = turkish()          # KVKK odaklı, varsayılan
    detector = german()           # DSGVO odaklı
    detector = multilingual()     # TR + DE + FR birlikte
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .detector import PiiDetector


def turkish(download_policy: str = "confirm") -> "PiiDetector":
    """
    KVKK uyumlu Türkçe PII detector — ana preset.

    Katmanlar: regex (TR) + NER (TR) + GLiNER (KVKK Md.6)
    Model: akdeniz27/xlm-roberta-base-turkish-ner
    """
    from .detector import PiiDetector
    from .layers.regex_layer import DEFAULT_RECOGNIZERS
    from .recognizers.kisi_adi import KisiAdiRecognizer
    from .recognizers.adres import AdresRecognizer
    from .config import NerConfig, GlinerConfig

    return PiiDetector(
        layers=["regex", "ner", "gliner"],
        recognizers=DEFAULT_RECOGNIZERS + [
            KisiAdiRecognizer(),
            AdresRecognizer(),
        ],
        download_policy=download_policy,
        ner_config=NerConfig(min_score=0.80),
        gliner_config=GlinerConfig(threshold=0.5),
    )


def german(download_policy: str = "confirm") -> "PiiDetector":
    """
    DSGVO uyumlu Almanca PII detector.

    Katmanlar: regex (genel + DE) + GLiNER
    NOT: NER için Almanca model ayrıca indirilir.
    """
    from .detector import PiiDetector
    from .layers.regex_layer import DEFAULT_RECOGNIZERS
    from .recognizers.de_recognizers import DE_RECOGNIZERS
    from .config import NerConfig, GlinerConfig

    return PiiDetector(
        layers=["regex", "ner", "gliner"],
        recognizers=DEFAULT_RECOGNIZERS + DE_RECOGNIZERS,
        download_policy=download_policy,
        ner_config=NerConfig(
            model_id="Babelscape/wikineural-multilingual-ner",
            model_size_mb=420,
            min_score=0.80,
        ),
        gliner_config=GlinerConfig(threshold=0.5),
    )


def french(download_policy: str = "confirm") -> "PiiDetector":
    """
    RGPD uyumlu Fransızca PII detector.

    Katmanlar: regex (genel + FR) + GLiNER
    """
    from .detector import PiiDetector
    from .layers.regex_layer import DEFAULT_RECOGNIZERS
    from .recognizers.fr_recognizers import FR_RECOGNIZERS
    from .config import NerConfig, GlinerConfig

    return PiiDetector(
        layers=["regex", "ner", "gliner"],
        recognizers=DEFAULT_RECOGNIZERS + FR_RECOGNIZERS,
        download_policy=download_policy,
        ner_config=NerConfig(
            model_id="Babelscape/wikineural-multilingual-ner",
            model_size_mb=420,
            min_score=0.80,
        ),
        gliner_config=GlinerConfig(threshold=0.5),
    )


def multilingual(download_policy: str = "confirm") -> "PiiDetector":
    """
    Çok dilli preset — TR + DE + FR birlikte.

    Türkçe NER için ayrı model, diğer diller için GLiNER yeterli.
    Regex katmanı tüm dil recognizer'larını içerir.
    """
    from .detector import PiiDetector
    from .layers.regex_layer import DEFAULT_RECOGNIZERS
    from .recognizers.kisi_adi import KisiAdiRecognizer
    from .recognizers.adres import AdresRecognizer
    from .recognizers.de_recognizers import DE_RECOGNIZERS
    from .recognizers.fr_recognizers import FR_RECOGNIZERS
    from .config import NerConfig, GlinerConfig

    return PiiDetector(
        layers=["regex", "ner", "gliner"],
        recognizers=(
            DEFAULT_RECOGNIZERS
            + [KisiAdiRecognizer(), AdresRecognizer()]
            + DE_RECOGNIZERS
            + FR_RECOGNIZERS
        ),
        download_policy=download_policy,
        # Türkçe NER — en iyi Türkçe model
        ner_config=NerConfig(min_score=0.80),
        # GLiNER tüm dilleri yakalar
        gliner_config=GlinerConfig(threshold=0.5),
    )
