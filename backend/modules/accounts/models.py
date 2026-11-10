# AI contribution: 50% or more AI-generated
import uuid
from typing import Any, ClassVar

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from modules.accounts.queries import STORE_ROLES
from modules.accounts.roles import UserRole


class UserManager(BaseUserManager["User"]):
    def get_by_natural_key(self, email: str | None) -> "User":
        return self.get(email__iexact=email)

    def create_user(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> "User":
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Superusers must have is_staff and is_superuser enabled")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    Role = UserRole

    username = None  # type: ignore[assignment]
    date_joined = None  # type: ignore[assignment]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=16, blank=True)
    preferred_language = models.CharField(
        max_length=2, choices=[("fr", "Français"), ("en", "English")], default="fr"
    )
    role = models.CharField(  # NOSONAR - User.Role is the required public API.
        max_length=20, choices=Role.choices, default=Role.BENEFICIARY
    )
    store = models.ForeignKey(
        "stores.Store", null=True, blank=True, on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects: ClassVar[UserManager] = UserManager()  # type: ignore[assignment]
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        constraints = [  # noqa: RUF012 - Django model metadata.
            models.UniqueConstraint(
                Lower("email"), name="accounts_user_email_ci_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(store__isnull=False)
                | ~models.Q(role__in=list(STORE_ROLES)),
                name="accounts_user_store_required_for_store_roles",
            ),
        ]


class Invitation(models.Model):
    """A hashed, expiring link that can create exactly one new account."""

    id = models.UUIDField(_("ID"), primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("Email address"))
    first_name = models.CharField(_("First name"), max_length=150)
    last_name = models.CharField(_("Last name"), max_length=150)
    role = models.CharField(_("Role"), max_length=20, choices=User.Role.choices)
    store = models.ForeignKey(
        "stores.Store",
        verbose_name=_("Store"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="account_invitations",
    )
    token_hash = models.CharField(_("Token hash"), max_length=64, unique=True)
    expires_at = models.DateTimeField(_("Expires at"))
    accepted_at = models.DateTimeField(_("Accepted at"), null=True, blank=True)
    invited_by = models.ForeignKey(
        "accounts.User",
        verbose_name=_("Invited by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="issued_invitations",
    )

    class Meta:
        verbose_name = _("Invitation")
        verbose_name_plural = _("Invitations")
        constraints = [  # noqa: RUF012 - Django model metadata.
            models.CheckConstraint(
                condition=models.Q(store__isnull=False)
                | ~models.Q(role__in=list(STORE_ROLES)),
                name="accounts_invitation_store_required_for_store_roles",
            ),
        ]
