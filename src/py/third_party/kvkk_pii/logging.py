"""kvkk-pii logging -- kullanici log seviyesini kontrol edebilir."""
import logging

logger = logging.getLogger("kvkk_pii")

# Varsayilan: WARNING (sessiz)
# Kullanici: logging.getLogger("kvkk_pii").setLevel(logging.DEBUG)


def set_verbosity(level: str) -> None:
    """'debug', 'info', 'warning', 'error' kabul eder."""
    numeric = getattr(logging, level.upper(), logging.WARNING)
    logger.setLevel(numeric)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[kvkk-pii] %(levelname)s: %(message)s"))
        logger.addHandler(handler)
