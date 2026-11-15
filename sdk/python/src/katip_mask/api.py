"""Public API: Masker, mask(), detect()."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from importlib import resources
from typing import Iterable, Literal, Sequence

from . import safety
from ._engine import local_detect

PROFILE_SPEC = json.loads(resources.files("katip_mask.spec").joinpath("profiles.json").read_text("utf-8"))
PROFILES: dict[str, dict] = PROFILE_SPEC["profiles"]
LABELS_TR: dict[str, str] = PROFILE_SPEC["labels_tr"]
ENTITY_TYPES: tuple[str, ...] = tuple(LABELS_TR)
DEFAULT_THRESHOLD: float = PROFILE_SPEC["default_threshold"]

Profile = Literal["court", "ai", "anon"]
Style = Literal["label", "block"]


@dataclass(frozen=True)
class Span:
    """One detected value. start/end are offsets into the input string (Python code points)."""
    entity_type: str
    start: int
    end: int
    text: str
    score: float
    recognizer: str
    explanation: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MaskResult:
    text: str
    """The masked text."""
    spans: tuple[Span, ...]
    """Everything that was masked, in document order."""
    mapping: dict[str, str] = field(default_factory=dict)
    """Placeholder -> original value (style "label" only). Keep it on your side; never send it with the text."""
    profile: str = "court"
    model: str | None = None

    def restore(self, text: str) -> str:
        """Put the original values back into text that contains the placeholders, e.g. an AI model's answer."""
        return safety.restore(text, self.mapping)

    def to_dict(self) -> dict:
        return {"text": self.text, "spans": [s.to_dict() for s in self.spans], "mapping": dict(self.mapping),
                "profile": self.profile, "model": self.model}


class Masker:
    """Masks Turkish personal data on this machine. Nothing is sent anywhere; a model, when you choose one,
    is downloaded once from Hugging Face at a pinned commit and verified by SHA-256.

    profile:   "court" (court filing), "ai" (sharing with AI) or "anon" (fully anonymous); see PROFILES.
    model:     None for rules only, "mini" (recommended), "nano" (fastest), "base" (most accurate),
               or the path of a local model folder.
    threshold: minimum confidence for a rule or model hit (default 0.5, as in Katip's demo and Kalkan).
    entities:  replace the profile's entity types with your own list.
    address_detail: "street" keeps mahalle/street/district/province readable, "full" masks the whole
               address; defaults to the profile's choice.
    allow:     terms never masked (your firm's own name, a judge's name you need to keep).
    deny:      terms always masked (client names you know in advance), whole words, case-insensitive.
    style:     "label" -> "[AD SOYAD-1]" (reversible with MaskResult.mapping), "block" -> "██████".
    """

    def __init__(self, profile: Profile = "court", *, model: str | os.PathLike | None = None,
                 threshold: float = DEFAULT_THRESHOLD, entities: Sequence[str] | None = None,
                 address_detail: Literal["street", "full"] | None = None, allow: Iterable[str] = (),
                 deny: Iterable[str] = (), style: Style = "label", progress=None):
        if profile not in PROFILES:
            raise ValueError(f"unknown profile {profile!r}: use {', '.join(PROFILES)}")
        if style not in ("label", "block"):
            raise ValueError('style must be "label" or "block"')
        unknown = [e for e in (entities or ()) if e not in LABELS_TR]
        if unknown:
            raise ValueError(f"unknown entity types {unknown}: see katip_mask.ENTITY_TYPES")
        p = PROFILES[profile]
        self.profile = profile
        self.entities: list[str] = list(entities) if entities else list(p["entities"])
        self.address_detail = address_detail or p["address_detail"]
        self.threshold = float(threshold)
        self.allow, self.deny = [str(t) for t in allow], [str(t) for t in deny]
        self.style = style
        self._model = None
        self._trust = None
        if model is not None:
            from .models import MODELS
            from .ner import load
            self._model = load(model, progress=progress)
            key = str(model)
            self._trust = MODELS[key]["trust"] if key in MODELS else \
                float((self._model.config.get("katip") or {}).get("trust", 0.5))

    @property
    def model(self) -> str | None:
        return self._model.name if self._model else None

    def _spans(self, text: str, ocr_ranges, extra=None) -> list[dict]:
        if extra is None:  # tests pass model spans directly, to check the merge rules without a model
            extra = [list(x) for x in self._model.spans(text, self.threshold)] if self._model else []
        spans = local_detect.detect(text, self.threshold, self.entities, self.deny, self.allow, extra, self._trust,
                                    [list(r) for r in ocr_ranges], self.address_detail)
        if "TCKN" in self.entities or "YKN" in self.entities:
            spans = safety.id_numbers(text, spans)
        return safety.propagate(text, spans)

    def detect(self, text: str, *, ocr_ranges: Sequence[tuple[int, int]] = ()) -> list[Span]:
        """Find personal data without masking. ocr_ranges: (start, end) ranges of text that came from OCR,
        where misread ID digits and handwritten form values are still caught."""
        return [_span(s) for s in self._spans(text, ocr_ranges)]

    def mask(self, text: str, *, ocr_ranges: Sequence[tuple[int, int]] = ()) -> MaskResult:
        """Mask the text. Raises LeakError rather than return text in which a detected value is still readable."""
        return self._mask(text, ocr_ranges)

    def _mask(self, text: str, ocr_ranges=(), extra=None) -> MaskResult:
        spans = self._spans(text, ocr_ranges, extra)
        masked, spans, mapping = safety.mask_safely(text, spans, self.style, LABELS_TR)
        return MaskResult(masked, tuple(_span(s) for s in spans), mapping, self.profile, self.model)


def _span(s: dict) -> Span:
    return Span(s["entity_type"], s["start"], s["end"], s["text"], s["score"], s.get("recognizer", ""), s.get("explanation", ""))


def mask(text: str, profile: Profile = "court", **options) -> MaskResult:
    """Mask with a one-off Masker (see Masker for the options). Reuse a Masker for many documents."""
    return Masker(profile, **options).mask(text)


def detect(text: str, profile: Profile = "court", **options) -> list[Span]:
    """Detect with a one-off Masker (see Masker for the options)."""
    return Masker(profile, **options).detect(text)


def restore(text: str, mapping: dict[str, str]) -> str:
    """Put original values back in place of placeholders, using a MaskResult.mapping you stored."""
    return safety.restore(text, mapping)
