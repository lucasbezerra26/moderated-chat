import uuid

from django.db import models


class BaseModel(models.Model):
    """
    Classe base abstrata que adiciona um ID UUID e timestamps
    para todos os modelos do projeto.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
