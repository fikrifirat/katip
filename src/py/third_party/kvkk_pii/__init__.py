"""kvkk-pii — KVKK uyumlu Türkçe PII detection kütüphanesi."""
from .detector import PiiDetector
from .result import PiiEntity, PiiResult
from .base import BaseRecognizer
from .layers.regex_layer import DEFAULT_RECOGNIZERS
from .session import PiiSession
from .leakage import LeakageAnalyzer, LeakageReport, PiiLeakageError
from .proxy import TwoWayResult
from .async_detector import AsyncPiiDetector
from .compliance import ComplianceReport
from . import presets

__version__ = "0.2.0"
__all__ = [
    "PiiDetector", "PiiEntity", "PiiResult",
    "BaseRecognizer", "DEFAULT_RECOGNIZERS",
    "PiiSession", "LeakageAnalyzer", "LeakageReport", "PiiLeakageError",
    "TwoWayResult",
    "AsyncPiiDetector",
    "ComplianceReport",
    "presets",
]
