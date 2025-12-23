from typing import Any, Dict

from django.conf import settings

from app.chat.models import Message


class LocalModerationService:
    """
    Service de moderação local usando dicionário de palavras proibidas.
    """

    def moderate(self, content: str) -> Dict[str, Any]:
        """
        Analisa conteúdo verificando palavras proibidas localmente.

        Args:
            content: Conteúdo da mensagem a ser moderada

        Returns:
            Dict contendo:
                - verdict: "APPROVED" ou "REJECTED"
                - provider: Nome do provedor de moderação
                - score: Score de confiança (0.0 a 1.0)
                - details: Detalhes adicionais do processamento
        """
        content_lower = content.lower()

        for word in settings.PROFANITY_LIST:
            if word in content_lower:
                return {
                    "verdict": Message.Status.REJECTED,
                    "provider": "local_dictionary",
                    "score": 1.0,
                    "details": {"reason": f"Palavra proibida detectada: {word}"},
                }

        return {
            "verdict": Message.Status.APPROVED,
            "provider": "local_dictionary",
            "score": 1.0,
            "details": {"reason": "clean_content"},
        }
