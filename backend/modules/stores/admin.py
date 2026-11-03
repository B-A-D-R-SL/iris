# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code

"""Administrator access to B.A.D.R. and partner Store records."""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from modules.stores.models import PartnerApplication, Store
from modules.stores.services import save_store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    """Let administrators view and edit Store details."""

    list_display = ("name", "city", "postal_code", "is_badr", "is_active")
    list_filter = ("is_badr", "is_active")
    search_fields = ("name", "city", "postal_code", "email")
    # The application link is set only by the US-13 approval, never by hand.
    readonly_fields = ("id", "is_badr", "application", "created_at", "updated_at")

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


def _is_administrator(request: HttpRequest) -> bool:
    user = request.user
    return bool(
        user.is_authenticated and user.is_active and user.is_staff and user.is_superuser
    )


@admin.register(PartnerApplication)
class PartnerApplicationAdmin(admin.ModelAdmin):
    """Read-only list of partner applications; decisions arrive with US-13."""

    list_display = ("business_name", "contact_email", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("business_name", "contact_email")
    ordering = ("created_at",)

    def has_module_permission(self, request: HttpRequest) -> bool:
        """Keep partner applications visible only to active administrators."""
        return _is_administrator(request)

    def has_view_permission(
        self, request: HttpRequest, obj: PartnerApplication | None = None
    ) -> bool:
        """Administrators may read applications; nobody else may."""
        return _is_administrator(request) and super().has_view_permission(request, obj)

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Applications come only from the public form."""
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: PartnerApplication | None = None
    ) -> bool:
        """Approve and reject are US-13 decisions, not admin edits."""
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: PartnerApplication | None = None
    ) -> bool:
        """Applications are kept as a record; nobody deletes them through the admin."""
        return False
