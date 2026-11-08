# AI contribution: 50% or more AI-generated
"""Household draft, members, and transactionally persisted draft-change audit."""

import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.households.domain.address import normalize_address, normalize_postal_code
from modules.households.domain.expiry import (
    STATUS_APPROVED,
    STATUS_RENEWAL_NEEDED,
    STATUS_SUSPENDED,
)
from modules.households.domain.person import (
    normalize_person,
    valid_name,
    validate_birth_date,
)
from modules.households.messages import domain_error_message
from modules.households.search_expressions import (
    SearchKey,
    address_search_key,
    member_name_key,
)

PHONE_VALIDATOR = RegexValidator(
    r"^\+1\d{10}$", _("Enter a Canadian telephone number.")
)


class Household(models.Model):
    class Channel(models.TextChoices):
        ONLINE = "online", _("Online")
        WALK_IN = "walk_in", _("Walk-in")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        SUBMITTED = "submitted", _("Submitted")
        REVIEW_REQUIRED = "review_required", _("Review required")
        AWAITING_VISIT = "awaiting_visit", _("Awaiting visit")
        APPROVED = STATUS_APPROVED, _("Approved")
        RENEWAL_NEEDED = STATUS_RENEWAL_NEEDED, _("Renewal needed")
        SUSPENDED = STATUS_SUSPENDED, _("Suspended")
        REJECTED = "rejected", _("Rejected")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    holder = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="household",
    )
    member_number = models.CharField(max_length=10, unique=True, null=True, blank=True)
    channel = models.CharField(
        max_length=12, choices=Channel.choices, default=Channel.WALK_IN
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    # Walk-ins may lack accounts. Keep their optional contact details on the file.
    email = models.EmailField(max_length=254, null=True, blank=True)
    preferred_language = models.CharField(
        max_length=2, choices=[("fr", "Français"), ("en", "English")], default="fr"
    )
    phone = models.CharField(max_length=16, validators=[PHONE_VALIDATOR])
    street_number = models.CharField(max_length=10, blank=True)
    street_name = models.CharField(max_length=120, blank=True)
    unit = models.CharField(max_length=10, blank=True)
    city = models.CharField(max_length=80, blank=True)
    postal_code = models.CharField(max_length=7, blank=True)
    address_key = models.CharField(max_length=200, blank=True, db_index=True)
    # PostgreSQL maintains these stored keys, including bulk writes and old rows.
    search_email_key = models.GeneratedField(
        expression=SearchKey("email"),
        output_field=models.TextField(),
        db_persist=True,
        null=True,
    )
    search_number_key = models.GeneratedField(
        expression=SearchKey("member_number"),
        output_field=models.TextField(),
        db_persist=True,
        null=True,
    )
    search_address_key = models.GeneratedField(
        expression=SearchKey("address_key"),
        output_field=models.TextField(),
        db_persist=True,
    )
    search_address_text = models.GeneratedField(
        expression=address_search_key(),
        output_field=models.TextField(),
        db_persist=True,
    )
    alternate_name = models.CharField(max_length=100, blank=True)
    alternate_phone = models.CharField(max_length=16, blank=True)
    alternate_email = models.EmailField(max_length=254, null=True, blank=True)
    identity_checked_in_person = models.BooleanField(default=False)
    # Data-processing consent (walk-in: notice read aloud, agreed verbally).
    # US-20 may move consents to privacy.ConsentRecord later.
    consent_data_processing_at = models.DateTimeField(null=True, blank=True)
    consent_text_version = models.CharField(max_length=20, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    status_reason = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="households_created",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="households_verified",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    anonymized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [  # noqa: RUF012
            models.Index(
                fields=["status", "expires_at"], name="households__status_4f9d18_idx"
            ),
            GinIndex(
                fields=["search_email_key"],
                opclasses=["gin_trgm_ops"],
                name="household_email_search_gin",
            ),
            GinIndex(
                fields=["search_number_key"],
                opclasses=["gin_trgm_ops"],
                name="household_number_search_gin",
            ),
            GinIndex(
                fields=["phone"],
                opclasses=["gin_trgm_ops"],
                name="household_phone_search_gin",
            ),
            GinIndex(
                fields=["search_address_key"],
                opclasses=["gin_trgm_ops"],
                name="household_key_search_gin",
            ),
            GinIndex(
                fields=["search_address_text"],
                opclasses=["gin_trgm_ops"],
                name="household_address_search_gin",
            ),
        ]

    def clean(self) -> None:
        """Normalize contact/address keys and keep identity verification fields consistent."""
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()
        if self.channel == self.Channel.WALK_IN and self.holder_id is not None:
            raise ValidationError(
                {"holder": _("Walk-in files cannot link an online account yet.")}
            )
        fields = (self.street_number, self.street_name, self.city, self.postal_code)
        if any(fields) and not all(fields):
            # Partial draft addresses can be saved while the user completes step 2.
            self.address_key = ""
        elif all(fields):
            try:
                self.postal_code = normalize_postal_code(self.postal_code)
                self.address_key = normalize_address(
                    self.street_number, self.street_name, self.unit, self.postal_code
                )
            except ValueError as exc:
                raise ValidationError(
                    {"postal_code": domain_error_message(exc)}
                ) from exc
        else:
            self.address_key = ""
        if self.identity_checked_in_person and (
            not self.verified_by_id or not self.verified_at
        ):
            raise ValidationError(
                {"identity_checked_in_person": _("Staff verification is required.")}
            )
        if not self.identity_checked_in_person and (
            self.verified_by_id or self.verified_at
        ):
            raise ValidationError(
                {"identity_checked_in_person": _("Verification fields must be empty.")}
            )


class Member(models.Model):
    class Relation(models.TextChoices):
        HOLDER = "holder", _("Holder")
        SPOUSE_PARTNER = "spouse_partner", _("Spouse or partner")
        CHILD = "child", _("Child")
        PARENT = "parent", _("Parent")
        SIBLING = "sibling", _("Sibling")
        GRANDPARENT = "grandparent", _("Grandparent")
        GRANDCHILD = "grandchild", _("Grandchild")
        OTHER_RELATIVE = "other_relative", _("Other relative")
        OTHER = "other", _("Other")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="members"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    relation = models.CharField(max_length=20, choices=Relation.choices)
    person_key = models.CharField(
        max_length=220, db_index=True, blank=True, editable=False
    )
    search_name_key = models.GeneratedField(
        expression=member_name_key(),
        output_field=models.TextField(),
        db_persist=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [  # noqa: RUF012
            GinIndex(
                fields=["search_name_key"],
                opclasses=["gin_trgm_ops"],
                name="member_name_search_gin",
            )
        ]
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["household"],
                condition=Q(relation="holder"),
                name="households_one_holder_member",
            )
        ]

    def clean(self) -> None:
        """Validate member identity fields and maintain the duplicate-detection key."""
        super().clean()
        self.first_name, self.last_name = (
            self.first_name.strip(),
            self.last_name.strip(),
        )
        for field in ("first_name", "last_name"):
            if not valid_name(getattr(self, field)):
                raise ValidationError(
                    {field: _("Use letters, spaces, apostrophes or hyphens.")}
                )
        try:
            validate_birth_date(
                self.date_of_birth,
                timezone.localdate(),
                holder=self.relation == self.Relation.HOLDER,
            )
            self.person_key = normalize_person(
                self.first_name, self.last_name, self.date_of_birth
            )
        except ValueError as exc:
            raise ValidationError({"date_of_birth": domain_error_message(exc)}) from exc


class HouseholdDraftEvent(models.Model):
    """Write-once household-specific audit until US-62 is integrated.

    Keep event payload free of names, DOB, phone, address and email.
    """

    class Action(models.TextChoices):
        CREATED = "created", _("Created")
        UPDATED = "updated", _("Updated")

    id = models.BigAutoField(primary_key=True)
    household = models.ForeignKey(
        Household, on_delete=models.PROTECT, related_name="draft_events"
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=12, choices=Action.choices)
    actor_role = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)


# Names kept for the SET-18 seed (#617), which imports them from this module.
HouseholdStatus = Household.Status
HouseholdChannel = Household.Channel
