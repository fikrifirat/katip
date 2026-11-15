"""Katip Mask: find and mask Turkish personal data (KVKK) on your own machine.

    >>> from katip_mask import Masker
    >>> m = Masker("ai")                       # rules only; Masker("ai", model="mini") adds the name model
    >>> r = m.mask("Davacı Ahmet YILMAZ, T.C. 10000000146")
    >>> r.text
    'Davacı [AD SOYAD-1], T.C. [T.C. KİMLİK NO-1]'
    >>> r.restore("[AD SOYAD-1] haklıdır.")
    'Ahmet YILMAZ haklıdır.'

The guarantee is narrow and stated plainly: every value the detector finds is masked everywhere it occurs
in the text, or masking fails with LeakError. Values the detector does not find are not covered; review
the output before you rely on it.
"""
from .api import (DEFAULT_THRESHOLD, ENTITY_TYPES, LABELS_TR, PROFILES, Masker, MaskResult, Span, detect, mask,
                  restore)
from .models import MODELS, ModelError, cache_dir, download_model, model_path
from .safety import LeakError

__version__ = "0.1.0"

__all__ = ["Masker", "MaskResult", "Span", "LeakError", "ModelError", "mask", "detect", "restore", "PROFILES",
           "ENTITY_TYPES", "LABELS_TR", "DEFAULT_THRESHOLD", "MODELS", "download_model", "model_path", "cache_dir",
           "__version__"]
