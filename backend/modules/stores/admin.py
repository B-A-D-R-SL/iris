# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code

"""Administrator access to B.A.D.R. and partner Store records."""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from modules.stores.models import Store
from modules.stores.services import save_store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    """Let administrators view and edit Store details."""

    list_display = ("name", "city", "postal_code", "is_badr", "is_active")
    list_filter = ("is_badr", "is_active")
    search_fields = ("name", "city", "postal_code", "email")
    readonly_fields = ("id", "created_at", "updated_at")

    def has_module_permission(self, request: HttpRequest) -> bool:
        """Keep Store records visible only to active administrators."""
        user = request.user
        return bool(
            user.is_authenticated
            and user.is_active
            and user.is_staff
            and user.is_superuser
        )

    def has_view_permission(
        self, request: HttpRequest, obj: Store | None = None
    ) -> bool:
        """Deny Store reads to all non-administrators."""
        return self.has_module_permission(request) and super().has_view_permission(
            request, obj
        )

    def has_change_permission(
        self, request: HttpRequest, obj: Store | None = None
    ) -> bool:
        """Deny Store edits to all non-administrators."""
        return self.has_module_permission(request) and super().has_change_permission(
            request, obj
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Only administrators may create a Store through Django admin."""
        return self.has_module_permission(request) and super().has_add_permission(
            request
        )

    def has_delete_permission(
        self, request: HttpRequest, obj: Store | None = None
    ) -> bool:
        """Store deactivation is handled by a later story; never delete it here."""
        return False

    def save_model(
        self, request: HttpRequest, obj: Store, form: Any, change: bool
    ) -> None:
        """Route admin writes through the stores service."""
        save_store(obj)
