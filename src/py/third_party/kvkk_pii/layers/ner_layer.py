"""Layer 2: XLM-RoBERTa NER — akdeniz27/xlm-roberta-base-turkish-ner."""
from __future__ import annotations
import os
from typing import Literal

from ..config import NerConfig
from ..result import PiiEntity
from ..logging import logger

_DEFAULT_MODEL_ID = "akdeniz27/xlm-roberta-base-turkish-ner"
_CACHE_DIR = os.path.expanduser("~/.cache/huggingface/hub")

_LABEL_MAP = {
    "PER": "KISI_ADI", "LOC": "KONUM", "ORG": "KURUM",
    "B-PER": "KISI_ADI", "I-PER": "KISI_ADI",
    "B-LOC": "KONUM",    "I-LOC": "KONUM",
    "B-ORG": "KURUM",    "I-ORG": "KURUM",
}

# NER'in yanlış sınıflandırdığı bilinen false positive'ler
_NER_STOPLIST: set[str] = {
    "TC", "AB", "EU", "UN", "NATO", "ABD", "BM", "İl", "İlçe",
    "Cd", "Sk", "No", "Apt", "Kat", "TL", "USD", "EUR",
}

DownloadPolicy = Literal["auto", "confirm", "never"]


def _model_cached(model_id: str) -> bool:
    try:
        from huggingface_hub import try_to_load_from_cache
        result = try_to_load_from_cache(model_id, "config.json")
        return result is not None and result != "not_in_cache"  # type: ignore[comparison-overlap]
    except Exception:
        return False


def _ask_user_confirmation(model_id: str, model_size_mb: int) -> bool:
    logger.info(
        f"NER katmanı için model gerekiyor: "
        f"Model={model_id}, Boyut=~{model_size_mb} MB, Konum={_CACHE_DIR}"
    )
    try:
        answer = input("İndirilsin mi? [E/h] ").strip().lower()
        return answer in ("", "e", "evet", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        logger.warning("Non-interactive ortam, model indirilmiyor.")
        return False


def _split_into_chunks(text: str, chunk_size: int, overlap: int) -> list[tuple[str, int]]:
    """
    Uzun metni chunk'lara böl. Her chunk (metin, başlangıç_offset) döndürür.
    Kelime sınırlarında böler — token ortasında kesilmez.
    """
    if len(text) <= chunk_size:
        return [(text, 0)]

    chunks: list[tuple[str, int]] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Kelime sınırına geri çekil
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        chunk = text[start:end]
        chunks.append((chunk, start))

        next_start = end - overlap
        if next_start <= start:
            next_start = end  # sonsuz döngü önlemi
        start = next_start

    return chunks


class NerLayer:
    def __init__(
        self,
        download_policy: DownloadPolicy = "confirm",
        config: NerConfig | None = None,
    ) -> None:
        self._policy = download_policy
        self._config = config or NerConfig()
        self._pipeline = None

    def _load(self) -> None:
        if self._pipeline is not None:
            return
        try:
            from transformers import pipeline as hf_pipeline
        except ImportError:
            raise ImportError("NER için: pip install kvkk-pii[ner]")

        model_id = self._config.model_id
        cached = _model_cached(model_id)
        if not cached:
            if self._policy == "never":
                raise RuntimeError(f"Model cache'de yok, download_policy='never'.")
            if self._policy == "confirm" and not _ask_user_confirmation(model_id, self._config.model_size_mb):
                raise RuntimeError("Model indirme reddedildi.")
            logger.info(f"Model indiriliyor: {model_id} ...")

        self._pipeline = hf_pipeline(
            "ner",
            model=model_id,
            aggregation_strategy="simple",
            device=-1,
        )
        if not cached:
            logger.info("Model hazır.")

    def _run_pipeline(self, text: str) -> list[dict]:
        """Uzun metin için chunk'layarak çalıştır, offset'leri düzelt."""
        cfg = self._config
        chunks = _split_into_chunks(text, cfg.chunk_size, cfg.chunk_overlap)

        if len(chunks) == 1:
            return self._pipeline(text)  # type: ignore[return-value]

        all_items: list[dict] = []
        seen_spans: set[tuple[int, int]] = set()

        for chunk_text, offset in chunks:
            items = self._pipeline(chunk_text)
            for item in items:
                abs_start = item["start"] + offset
                abs_end = item["end"] + offset
                span = (abs_start, abs_end)
                if span not in seen_spans:  # overlap bölgesinde duplicate önle
                    seen_spans.add(span)
                    all_items.append({**item, "start": abs_start, "end": abs_end})

        return all_items

    def analyze(self, text: str, already_found: list[PiiEntity]) -> list[PiiEntity]:
        self._load()
        cfg = self._config
        occupied = [(e.start, e.end) for e in already_found]
        entities: list[PiiEntity] = []

        for item in self._run_pipeline(text):
            entity_type = _LABEL_MAP.get(item.get("entity_group", ""))
            if entity_type is None:
                continue

            word = item["word"].strip()
            score = float(item["score"])
            start, end = item["start"], item["end"]

            if score < cfg.min_score:
                continue
            if len(word) < cfg.min_chars:
                continue
            if word.upper() in _NER_STOPLIST:
                continue
            if any(s <= start < e or s < end <= e for s, e in occupied):
                continue

            entities.append(PiiEntity(
                entity_type=entity_type,
                text=word,
                start=start,
                end=end,
                score=score,
                layer="ner",
            ))

        return entities
