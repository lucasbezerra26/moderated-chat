import json
from typing import Dict, Tuple

import structlog
from django.conf import settings
from google import genai
from google.genai import types

from app.chat.models import Message

logger = structlog.get_logger(__name__)


def _analyze_text_with_gemini(text_content: str) -> Tuple[bool, str]:
    """
    Analisa conteúdo usando Google Gemini para moderação.

    Args:
        text_content: Texto a ser analisado

    Returns:
        Tupla (aprovado, motivo)
    """
    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)

        system_instruction = """
        Você é um sistema de moderação de chat de alta precisão.
        Analise a mensagem e verifique violações de segurança.

        Regras de bloqueio:
        - HATE: Discurso de ódio, racismo, homofobia.
        - SEXUAL: Conteúdo sexualmente explícito.
        - VIOLENCE: Ameaças reais, incentivo à violência ou autolesão.
        - HARASSMENT: Assédio ou bullying severo.

        Retorne APENAS um objeto JSON com o formato:
        {
            "approved": boolean,
            "reason": "string ou null",
            "category": "string ou null",
            "score": float
        }
        """

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=text_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )

        result = json.loads(response.text)

        logger.info(
            "gemini_moderation_result",
            approved=result["approved"],
            category=result.get("category"),
            score=result.get("score"),
        )

        return result["approved"], result.get("reason", "")

    except Exception as e:
        logger.exception("gemini_moderation_error", error=str(e))
        return True, "Erro na verificação, aprovado por fallback"


class GeminiModerationService:
    """
    Service de moderação usando Google Gemini.
    """

    def moderate(self, content: str) -> Dict[str, any]:
        """
        Analisa conteúdo usando Google Gemini.

        Args:
            content: Conteúdo da mensagem a ser moderada

        Returns:
            Dict contendo:
                - verdict: "APPROVED" ou "REJECTED"
                - provider: Nome do provedor de moderação
                - score: Score de confiança (0.0 a 1.0)
                - details: Detalhes adicionais incluindo motivo de rejeição
        """
        is_approved, reason = _analyze_text_with_gemini(content)

        if is_approved:
            return {
                "verdict": Message.Status.APPROVED,
                "provider": "google_gemini",
                "score": 1.0,
                "details": {"reason": "clean_content"},
            }

        return {
            "verdict": Message.Status.REJECTED,
            "provider": "google_gemini",
            "score": 1.0,
            "details": {"reason": reason},
        }
