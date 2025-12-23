from abc import ABC, abstractmethod
from typing import TypedDict


class ModerationResult(TypedDict):
    verdict: str
    provider: str
    score: float | None
    details: dict


class ModerationStrategy(ABC):
    """
    Interface abstrata para estratégias de moderação de conteúdo.

    Define o contrato que todas as implementações de moderação devem seguir,
    permitindo trocar provedores (Gemini, OpenAI, Local) sem afetar o domínio.

    Princípios aplicados:
    - Dependency Inversion Principle (DIP)
    - Strategy Pattern
    - Interface Segregation
    """

    @abstractmethod
    def moderate(self, content: str) -> ModerationResult:
        """
        Analisa conteúdo e retorna veredicto de moderação.

        Args:
            content: Texto a ser moderado

        Returns:
            ModerationResult com verdict, provider, score e details
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Retorna identificador único do provedor."""
        pass
