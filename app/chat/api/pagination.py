from rest_framework.pagination import CursorPagination


class MessageCursorPagination(CursorPagination):
    """Paginação por cursor para mensagens (scroll infinito)."""

    page_size = 20
    ordering = "-created_at"
    cursor_query_param = "cursor"
