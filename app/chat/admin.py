from django.contrib import admin
from app.chat.models import Room, Message


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_private', 'created_at']
    list_filter = ['is_private', 'created_at']
    search_fields = ['name']
    filter_horizontal = ['participants']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'room', 'author', 'content_preview', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'room']
    search_fields = ['content', 'author__email']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def content_preview(self, obj):
        return obj.content[:50]
    content_preview.short_description = 'Prévia'
