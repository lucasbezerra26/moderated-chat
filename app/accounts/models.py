from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.db import models
from app.utils.models import BaseModel

class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    name = models.CharField("Nome", max_length=500)
    email = models.EmailField("Email", unique=True)
    is_active = models.BooleanField("Ativo", default=True)
    is_staff = models.BooleanField("Equipe", default=False)
    is_superuser = models.BooleanField("Super-Usuário", default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

        permissions = [
            ("can_access_report", "Pode acessar os relatórios do Power BI"),
        ]

    def __str__(self):
        return self.name
