"""BaseRecognizer — tüm recognizer'ların implement etmesi gereken arayüz."""
from abc import ABC, abstractmethod
from .result import PiiEntity, EntityType


class BaseRecognizer(ABC):
    """
    Özel recognizer yazmak için bu sınıfı extend et:

        class KurumEmailRecognizer(BaseRecognizer):
            entity_type = "EMAIL"
            enabled = True

            def find(self, text: str) -> list[PiiEntity]:
                ...
    """

    entity_type: EntityType       # tespit edilen entity tipi
    enabled: bool = True          # False ise regex_layer tarafından atlanır

    @abstractmethod
    def find(self, text: str) -> list[PiiEntity]:
        """Metindeki PII entity'lerini bul ve döndür."""
        ...

    def _entity(
        self,
        text: str,
        start: int,
        end: int,
        score: float,
    ) -> PiiEntity:
        """Kolaylık metodu — tekrar tekrar PiiEntity(...) yazmamak için."""
        return PiiEntity(
            entity_type=self.entity_type,
            text=text,
            start=start,
            end=end,
            score=score,
            layer="regex",
        )
