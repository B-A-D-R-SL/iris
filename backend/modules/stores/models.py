# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code

"""Store records shared by B.A.D.R. and approved partner businesses."""

import re
import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from modules.stores.fields import CitextEmailField

POSTAL_CODE_PATTERN = r"^[A-Za-z]\d[A-Za-z] ?\d[A-Za-z]\d$"
E164_PHONE_NUMBER_PATTERN = r"^\+[1-9]\d{1,14}$"


class Store(models.Model):
    """A place that can offer goods for pickup in Iris."""

    id = models.UUIDField(
        pgettext_lazy("store field", "ID"),
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        pgettext_lazy("store field", "Store name"),
        max_length=150,
        validators=[MinLengthValidator(2)],
    )
    street_number = models.CharField(
        pgettext_lazy("store field", "Street number"), max_length=10
    )
    street_name = models.CharField(
        pgettext_lazy("store field", "Street"), max_length=120
    )
    unit = models.CharField(
        pgettext_lazy("store field", "Apt."),
        max_length=10,
        null=True,
        blank=True,
        default=None,
    )
    city = models.CharField(pgettext_lazy("store field", "City"), max_length=80)
    postal_code = models.CharField(
        pgettext_lazy("store field", "Postal code"),
        max_length=7,
        validators=[
            RegexValidator(POSTAL_CODE_PATTERN, _("Enter a Canadian postal code."))
        ],
    )
    phone = models.CharField(
        pgettext_lazy("store field", "Phone number"),
        max_length=16,
        validators=[
            RegexValidator(
                E164_PHONE_NUMBER_PATTERN,
                "Enter a phone number in E.164 format.",
            )
        ],
    )
    email = CitextEmailField(
        pgettext_lazy("store field", "Email address"), max_length=254
    )
    opening_hours = models.JSONField(
        pgettext_lazy("store field", "Opening hours"), default=dict
    )
    pickup_instructions = models.CharField(
        pgettext_lazy("store field", "Pickup instructions"),
        max_length=300,
        null=True,
        blank=True,
        default=None,
    )
    is_badr = models.BooleanField(
        pgettext_lazy("store field", "B.A.D.R. store"), default=False
    )
    is_active = models.BooleanField(
        pgettext_lazy("store field", "Active"), default=True
    )
    # Set by the US-13 approval; B.A.D.R. and manually created stores have none.
    application = models.OneToOneField(
        "stores.PartnerApplication",
        verbose_name=pgettext_lazy("store field", "Partner application"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="store",
    )
    created_at = models.DateTimeField(
        pgettext_lazy("store field", "Created at"), auto_now_add=True
    )
    updated_at = models.DateTimeField(
        pgettext_lazy("store field", "Updated at"), auto_now=True
    )

    class Meta:
        verbose_name = _("Store")
        verbose_name_plural = _("Stores")
        constraints = [  # noqa: RUF012 - Django reads declarative model metadata.
            models.UniqueConstraint(
                fields=["is_badr"],
                condition=Q(is_badr=True),
                name="stores_single_badr_store",
            )
        ]

    def clean(self) -> None:
        """Store valid Canadian postal codes in uppercase with one space."""
        super().clean()
        compact_code = self.postal_code.replace(" ", "").upper()
        if re.fullmatch(r"[A-Z]\d[A-Z]\d[A-Z]\d", compact_code):
            self.postal_code = f"{compact_code[:3]} {compact_code[3:]}"

    def __str__(self) -> str:
        return self.name


CANADIAN_PHONE_PATTERN = r"^\+1[2-9]\d{9}$"
NEQ_PATTERN = r"^\d{10}$"
STREET_NUMBER_PATTERN = r"^\d{1,8}(?:[A-Za-z]| ?\d/\d)?$"
NAME_PATTERN = r"^[^\W\d_]+(?:[ '’-][^\W\d_]+)*$"


class BusinessType(models.TextChoices):
    """Business types offered on the partner application form."""

    GROCERY = "grocery", pgettext_lazy("business type", "Grocery")
    SUPERMARKET = "supermarket", pgettext_lazy("business type", "Supermarket")
    BAKERY = "bakery", pgettext_lazy("business type", "Bakery")
    RESTAURANT = "restaurant", pgettext_lazy("business type", "Restaurant")
    CAFE = "cafe", pgettext_lazy("business type", "Café")
    CONVENIENCE_STORE = (
        "convenience_store",
        pgettext_lazy("business type", "Convenience store"),
    )
    PHARMACY = "pharmacy", pgettext_lazy("business type", "Pharmacy")
    FARM_PRODUCER = "farm_producer", pgettext_lazy("business type", "Farm or producer")
    COMMUNITY_ORGANIZATION = (
        "community_organization",
        pgettext_lazy("business type", "Community organization"),
    )
    OTHER = "other", pgettext_lazy("business type", "Other")


class DonationFrequency(models.TextChoices):
    """How often a business expects to donate."""

    DAILY = "daily", pgettext_lazy("donation frequency", "Daily")
    WEEKLY = "weekly", pgettext_lazy("donation frequency", "Weekly")
    MONTHLY = "monthly", pgettext_lazy("donation frequency", "Monthly")
    OCCASIONAL = "occasional", pgettext_lazy("donation frequency", "Occasionally")


class ApplicationStatus(models.TextChoices):
    """Lifecycle of a partner application; US-13 records the decision."""

    SUBMITTED = "submitted", pgettext_lazy("application status", "Submitted")
    APPROVED = "approved", pgettext_lazy("application status", "Approved")
    REJECTED = "rejected", pgettext_lazy("application status", "Rejected")


class ApplicationLanguage(models.TextChoices):
    """Language used for the emails sent to the contact, who has no account."""

    FRENCH = "fr", "Français"
    ENGLISH = "en", "English"


class PartnerApplication(models.Model):
    """A business request to become a partner; no account or store is created."""

    id = models.UUIDField(
        pgettext_lazy("partner application field", "ID"),
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    business_name = models.CharField(
        pgettext_lazy("partner application field", "Business name"),
        max_length=150,
        validators=[MinLengthValidator(2)],
    )
    business_type = models.CharField(
        pgettext_lazy("partner application field", "Business type"),
        max_length=30,
        choices=BusinessType.choices,
    )
    neq = models.CharField(
        pgettext_lazy("partner application field", "Quebec enterprise number (NEQ)"),
        max_length=10,
        null=True,
        blank=True,
        default=None,
        validators=[RegexValidator(NEQ_PATTERN)],
    )
    street_number = models.CharField(
        pgettext_lazy("partner application field", "Street number"),
        max_length=10,
        validators=[RegexValidator(STREET_NUMBER_PATTERN)],
    )
    street_name = models.CharField(
        pgettext_lazy("partner application field", "Street"),
        max_length=120,
        validators=[MinLengthValidator(2)],
    )
    unit = models.CharField(
        pgettext_lazy("partner application field", "Apt."),
        max_length=10,
        null=True,
        blank=True,
        default=None,
    )
    city = models.CharField(
        pgettext_lazy("partner application field", "City"), max_length=80
    )
    postal_code = models.CharField(
        pgettext_lazy("partner application field", "Postal code"),
        max_length=7,
        validators=[RegexValidator(POSTAL_CODE_PATTERN)],
    )
    contact_first_name = models.CharField(
        pgettext_lazy("partner application field", "First name"),
        max_length=100,
        validators=[RegexValidator(NAME_PATTERN)],
    )
    contact_last_name = models.CharField(
        pgettext_lazy("partner application field", "Last name"),
        max_length=100,
        validators=[RegexValidator(NAME_PATTERN)],
    )
    contact_role = models.CharField(
        pgettext_lazy("partner application field", "Role"),
        max_length=100,
        null=True,
        blank=True,
        default=None,
    )
    # Case-insensitive, so the open-application rule ignores letter case.
    contact_email = CitextEmailField(
        pgettext_lazy("partner application field", "Email address"), max_length=254
    )
    contact_phone = models.CharField(
        pgettext_lazy("partner application field", "Phone number"),
        max_length=16,
        validators=[RegexValidator(CANADIAN_PHONE_PATTERN)],
    )
    website = models.URLField(
        pgettext_lazy("partner application field", "Website"),
        max_length=200,
        null=True,
        blank=True,
        default=None,
    )
    # Stable category codes (business-rules.md); codes never change once in use.
    goods_categories = ArrayField(
        models.CharField(max_length=64),
        verbose_name=pgettext_lazy(
            "partner application field", "Types of goods offered"
        ),
    )
    expected_frequency = models.CharField(
        pgettext_lazy("partner application field", "Expected donation frequency"),
        max_length=10,
        choices=DonationFrequency.choices,
    )
    opening_hours = models.CharField(
        pgettext_lazy("partner application field", "Opening hours"), max_length=300
    )
    message = models.CharField(
        pgettext_lazy("partner application field", "Message"),
        max_length=1000,
        null=True,
        blank=True,
        default=None,
    )
    consent_contact = models.BooleanField(
        pgettext_lazy("partner application field", "Consent to be contacted")
    )
    language = models.CharField(
        pgettext_lazy("partner application field", "Language"),
        max_length=2,
        choices=ApplicationLanguage.choices,
        default=ApplicationLanguage.FRENCH,
    )
    status = models.CharField(
        pgettext_lazy("partner application field", "Status"),
        max_length=10,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.SUBMITTED,
    )
    decision_reason = models.CharField(
        pgettext_lazy("partner application field", "Decision reason"),
        max_length=500,
        null=True,
        blank=True,
        default=None,
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=pgettext_lazy("partner application field", "Decided by"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="decided_partner_applications",
    )
    decided_at = models.DateTimeField(
        pgettext_lazy("partner application field", "Decided at"), null=True, blank=True
    )
    created_at = models.DateTimeField(
        pgettext_lazy("partner application field", "Created at"), auto_now_add=True
    )

    class Meta:
        verbose_name = _("Partner application")
        verbose_name_plural = _("Partner applications")
        ordering = ("created_at",)
        constraints = [  # noqa: RUF012 - Django reads declarative model metadata.
            models.UniqueConstraint(
                fields=["contact_email"],
                condition=Q(status=ApplicationStatus.SUBMITTED),
                name="stores_application_one_open_per_email",
            ),
            models.CheckConstraint(
                condition=Q(consent_contact=True),
                name="stores_application_consent_given",
            ),
            models.CheckConstraint(
                condition=Q(goods_categories__len__gt=0),
                name="stores_application_has_category",
            ),
            models.CheckConstraint(
                condition=~Q(status=ApplicationStatus.REJECTED)
                | (Q(decision_reason__isnull=False) & ~Q(decision_reason="")),
                name="stores_application_rejection_has_reason",
            ),
            models.CheckConstraint(
                condition=Q(status__in=ApplicationStatus.values),
                name="stores_application_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(business_type__in=BusinessType.values),
                name="stores_application_business_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(expected_frequency__in=DonationFrequency.values),
                name="stores_application_frequency_valid",
            ),
            models.CheckConstraint(
                condition=Q(language__in=ApplicationLanguage.values),
                name="stores_application_language_valid",
            ),
        ]
        indexes = [  # noqa: RUF012 - Django reads declarative model metadata.
            models.Index(
                fields=["status", "created_at"], name="stores_application_status_idx"
            )
        ]

    def __str__(self) -> str:
        return self.business_name
