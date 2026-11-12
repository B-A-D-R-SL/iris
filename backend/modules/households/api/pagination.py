# AI contribution: 50% or more AI-generated
"""Return a search page and its exact total from one PostgreSQL snapshot."""

from sys import maxsize

from django.core.paginator import InvalidPage, Page, Paginator
from django.db.models import Count, Window
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination


class _CountedPaginator(Paginator):
    def __init__(self, objects, page_size: int, total: int):
        super().__init__(objects, page_size)
        self._total = total

    @property
    def count(self) -> int:
        """Reuse the window count instead of executing the search a second time."""
        return self._total


class HouseholdSearchPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        """Preserve page-number responses while avoiding the separate COUNT query."""
        self.request = request
        page_size = self.get_page_size(request) or self.page_size
        raw_number = request.query_params.get(self.page_query_param) or 1
        # Preserve DRF's optional "last" page shortcut, which needs a count first.
        if raw_number in self.last_page_strings:
            return super().paginate_queryset(queryset, request, view)
        try:
            number = int(raw_number)
            offset = (number - 1) * page_size
            if number < 1 or offset > maxsize:
                raise ValueError("Page is outside the database offset range.")
        except (TypeError, ValueError) as exc:
            raise NotFound(self.invalid_page_message) from exc
        rows = list(
            queryset.annotate(_search_total=Window(Count("pk")))[
                offset : offset + page_size
            ]
        )
        total = int(rows[0]._search_total) if rows else 0
        paginator = _CountedPaginator(queryset, page_size, total)
        try:
            number = paginator.validate_number(number)
        except InvalidPage as exc:
            raise NotFound(self.invalid_page_message) from exc
        self.page = Page(rows, number, paginator)
        self.display_page_controls = (
            paginator.num_pages > 1 and self.template is not None
        )
        return rows
