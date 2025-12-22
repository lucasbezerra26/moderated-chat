from django.db import models

from app.utils.models import BaseModel


class ModerationLog(BaseModel):
    message = models.ForeignKey(
        "chat.Message", on_delete=models.CASCADE, related_name="moderation_logs", verbose_name="Mensagem"
    )
    provider = models.CharField("Provedor", max_length=50, help_text="Ex: local_dictionary, openai, azure")
    verdict = models.CharField("Veredicto", max_length=20, help_text="Ex: APPROVED, REJECTED")
    score = models.FloatField("Score de Confiança", null=True, blank=True, help_text="0.0 a 1.0")
    raw_payload = models.JSONField("Payload Bruto", default=dict, help_text="Resposta completa")

    class Meta:
        verbose_name = "Log de Moderação"
        verbose_name_plural = "Logs de Moderação"
        indexes = [
            models.Index(fields=["message", "created_at"]),
            models.Index(fields=["provider", "verdict"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider}: {self.verdict} - {self.message.content[:30]}"
