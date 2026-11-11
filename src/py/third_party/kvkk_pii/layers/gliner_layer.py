"""Layer 3: GLiNER zero-shot NER — KVKK Madde 6 özel kategoriler."""
from __future__ import annotations
from ..result import PiiEntity
from ..logging import logger

_MODEL_ID = "urchade/gliner_multi-v2.1"
_MODEL_SIZE_MB = 180

# KVKK Madde 6 — özel nitelikli kişisel veriler
_DEFAULT_LABELS = [
    "health information",       # sağlık verisi
    "religious belief",         # din, mezhep
    "political opinion",        # siyasi görüş
    "trade union membership",   # sendika üyeliği
    "biometric data",           # biyometrik veri
    "genetic data",             # genetik veri
    "sexual orientation",       # cinsel yönelim
]

_LABEL_MAP = {
    "health information": "SAGLIK_VERISI",
    "religious belief": "DINI_INANC",
    "political opinion": "SIYASI_GORUS",
    "trade union membership": "SENDIKA_UYELIGII",
    "biometric data": "BIYOMETRIK_VERI",
    "genetic data": "BIYOMETRIK_VERI",
    "sexual orientation": "SAGLIK_VERISI",
}


class GlinerLayer:
    def __init__(
        self,
        labels: list[str] | None = None,
        download_policy: str = "confirm",
        config=None,  # GlinerConfig
    ) -> None:
        from ..config import GlinerConfig
        cfg = config or GlinerConfig()
        self._labels = labels or cfg.labels or _DEFAULT_LABELS
        self._threshold = cfg.threshold
        self._model = None
        self._policy = download_policy

    def _model_cached(self) -> bool:
        try:
            from huggingface_hub import try_to_load_from_cache
            result = try_to_load_from_cache(_MODEL_ID, "config.json")
            return result is not None and result != "not_in_cache"  # type: ignore[comparison-overlap]
        except Exception:
            return False

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from gliner import GLiNER
        except ImportError:
            raise ImportError(
                "GLiNER katmanı için gliner gerekli: pip install kvkk-pii[full]"
            )

        cached = self._model_cached()
        if not cached:
            if self._policy == "never":
                raise RuntimeError(f"GLiNER modeli cache'de yok ve download_policy='never'.")
            if self._policy == "confirm":
                import os
                cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
                logger.info(
                    f"GLiNER katmanı için model gerekiyor: "
                    f"Model={_MODEL_ID}, Boyut=~{_MODEL_SIZE_MB} MB, Konum={cache_dir}"
                )
                try:
                    answer = input("İndirilsin mi? [E/h] ").strip().lower()
                    if answer not in ("", "e", "evet", "y", "yes"):
                        raise RuntimeError("GLiNER model indirme reddedildi.")
                except (EOFError, KeyboardInterrupt):
                    raise RuntimeError("Non-interactive ortam, GLiNER indirme iptal edildi.")
            logger.info(f"GLiNER modeli indiriliyor: {_MODEL_ID} ...")

        self._model = GLiNER.from_pretrained(_MODEL_ID)

        if not cached:
            logger.info("GLiNER modeli hazır.")

    def analyze(
        self,
        text: str,
        already_found: list[PiiEntity],
        threshold: float | None = None,
    ) -> list[PiiEntity]:
        self._load()
        raw = self._model.predict_entities(text, self._labels, threshold=threshold or self._threshold)
        entities: list[PiiEntity] = []

        occupied = {(e.start, e.end) for e in already_found}

        for item in raw:
            entity_type = _LABEL_MAP.get(item["label"])
            if entity_type is None:
                continue

            start = item["start"]
            end = item["end"]

            if any(s <= start < e or s < end <= e for s, e in occupied):
                continue

            entities.append(
                PiiEntity(
                    entity_type=entity_type,
                    text=item["text"],
                    start=start,
                    end=end,
                    score=float(item["score"]),
                    layer="gliner",
                )
            )

        return entities
