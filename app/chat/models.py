from django.db import models
from django.conf import settings
from app.utils.models import BaseModel


class Room(BaseModel):
    name = models.CharField("Nome da Sala", max_length=255)
    is_private = models.BooleanField("Sala Privada", default=False)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="rooms",
        verbose_name="Participantes"
    )

    class Meta:
        verbose_name = "Sala"
        verbose_name_plural = "Salas"
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_private', 'created_at']),
        ]

    def __str__(self):
        return self.name


class Message(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        APPROVED = "APPROVED", "Aprovada"
        REJECTED = "REJECTED", "Rejeitada"

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Sala"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Autor"
    )
    content = models.TextField("Conteúdo")
    status = models.CharField(
        "Status",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    class Meta:
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"
        indexes = [
            models.Index(fields=['room', 'status', 'created_at']),
            models.Index(fields=['author', 'created_at']),
        ]
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.email}: {self.content[:50]}"
