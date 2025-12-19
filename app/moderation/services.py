from typing import Dict

from app.chat.models import Message


class ModerationService:
    """
    Service responsável por moderar mensagens.
    Implementação inicial: Pass-through que aprova tudo automaticamente.
    Preparado para futura integração com OpenAI/Azure.
    """

    PROFANITY_LIST = ["bobo", "idiota", "estupido"]

    @staticmethod
    def moderate(content: str) -> Dict[str, any]:
        """
        Analisa conteúdo e retorna veredicto de moderação.

        Implementação atual: Verifica palavras proibidas localmente.
        Futuro: Integração com OpenAI Moderation API.

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

        for word in ModerationService.PROFANITY_LIST:
            if word in content_lower:
                return {
                    "verdict": Message.Status.REJECTED,
                    "provider": "local_dictionary",
                    "score": 1.0,
                    "details": {"reason": "profanity_detected", "matched_word": word},
                }

        return {
            "verdict": Message.Status.APPROVED,
            "provider": "local_dictionary",
            "score": 1.0,
            "details": {"reason": "clean_content"},
        }
