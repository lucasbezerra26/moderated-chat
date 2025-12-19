from django.contrib import admin

from app.chat.models import Message, Room, RoomParticipant


class RoomParticipantInline(admin.TabularInline):
    model = RoomParticipant
    extra = 1


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["name", "is_private", "created_at"]
    list_filter = ["is_private", "created_at"]
    search_fields = ["name"]
    inlines = [RoomParticipantInline]


@admin.register(RoomParticipant)
class RoomParticipantAdmin(admin.ModelAdmin):
    list_display = ["user", "room", "role", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["user__email", "room__name"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "room", "author", "content_preview", "status", "created_at"]
    list_filter = ["status", "created_at", "room"]
    search_fields = ["content", "author__email"]
    readonly_fields = ["id", "created_at", "updated_at"]

    def content_preview(self, obj):
        return obj.content[:50]

    content_preview.short_description = "Prévia"
