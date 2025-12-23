import json

import structlog
from django.conf import settings
from google import genai
from google.genai import types

from app.moderation.domain.strategies import ModerationResult, ModerationStrategy

logger = structlog.get_logger(__name__)


class GeminiModerator(ModerationStrategy):
    """
    Implementação de moderação usando Google Gemini AI.

    Camada de Infraestrutura: responsável por detalhes técnicos
    de integração com API externa do Google Gemini.
    """

    SYSTEM_INSTRUCTION = """
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

    def __init__(self):
        api_key = settings.GOOGLE_API_KEY
        if not api_key:
            raise ValueError("GOOGLE_API_KEY não configurada")

        self.client = genai.Client(api_key=api_key)
        self.model = settings.GEMINI_MODEL

    def moderate(self, content: str) -> ModerationResult:
        log = logger.bind(provider="gemini", content_length=len(content))

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=content,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )

            result = json.loads(response.text)

            log.info(
                "gemini_moderation_result",
                approved=result["approved"],
                category=result.get("category"),
                score=result.get("score"),
            )

            if result["approved"]:
                return ModerationResult(
                    verdict="APPROVED",
                    provider=self.get_provider_name(),
                    score=result.get("score", 1.0),
                    details={"reason": "clean_content"},
                )

            return ModerationResult(
                verdict="REJECTED",
                provider=self.get_provider_name(),
                score=result.get("score", 1.0),
                details={"reason": result.get("reason", "Conteúdo inapropriado"), "category": result.get("category")},
            )

        except Exception as exc:
            log.exception("gemini_api_error", error=str(exc))
            return self._fallback_reject(str(exc))

    def _fallback_reject(self, error_msg: str) -> ModerationResult:
        return ModerationResult(
            verdict="REJECTED",
            provider=self.get_provider_name(),
            score=0.0,
            details={"reason": "Falha na moderação por IA", "error": error_msg},
        )

    def get_provider_name(self) -> str:
        return "google_gemini"
