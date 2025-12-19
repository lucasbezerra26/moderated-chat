from django.contrib import admin

from app.moderation.models import ModerationLog


@admin.register(ModerationLog)
class ModerationLogAdmin(admin.ModelAdmin):
    list_display = ["id", "message", "provider", "verdict", "score", "created_at"]
    list_filter = ["provider", "verdict", "created_at"]
    search_fields = ["message__content"]
    readonly_fields = ["id", "created_at", "updated_at", "raw_payload"]

    def has_add_permission(self, request):
        return False
