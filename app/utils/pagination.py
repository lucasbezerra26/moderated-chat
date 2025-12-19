from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    """
    Custom pagination class that allows dynamic page_size via query parameter
    """

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
