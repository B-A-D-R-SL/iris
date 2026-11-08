# AI contribution: 50% or more AI-generated
"""Income evidence for an adult member: a notice of assessment or a non-filing reason.

Rules BR-DOC-001 to BR-DOC-005 are in docs/02-requirements/business-rules.md.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

# BR-DOC-001: a filed notice has its file and every value, and no reason.
_CONFIRMED_SHAPE = (
    Q(status="confirmed")
    & ~Q(file_ref="")
    & Q(tax_year__isnull=False)
    & Q(total_income_cents__isnull=False)
    & ~Q(name_on_notice="")
    & ~Q(postal_code_on_notice="")
    & Q(notice_date__isnull=False)
    & Q(did_not_file_reason="")
)
# BR-DOC-003: a non-filer has a reason and nothing from a notice.
_DID_NOT_FILE_SHAPE = (
    Q(status="did_not_file")
    & ~Q(did_not_file_reason="")
    & Q(file_ref="")
    & Q(tax_year__isnull=True)
    & Q(total_income_cents__isnull=True)
    & Q(name_on_notice="")
    & Q(postal_code_on_notice="")
    & Q(notice_date__isnull=True)
    & Q(seen_in_person=False)
)


class IncomeNotice(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", _("Confirmed")
        DID_NOT_FILE = "did_not_file", _("Did not file")

    class Source(models.TextChoices):
        STAFF = "staff", _("Staff")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # PROTECT: households turns ProtectedError into a field error on member edits.
    member = models.ForeignKey(
        "households.Member", on_delete=models.PROTECT, related_name="income_notices"
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    source = models.CharField(max_length=20, choices=Source.choices)
    # Opaque private storage reference, never a URL or the uploaded file name.
    file_ref = models.CharField(max_length=300, blank=True)
    tax_year = models.PositiveSmallIntegerField(null=True, blank=True)
    # Line 199 total income, integer cents (review rule 6).
    total_income_cents = models.PositiveBigIntegerField(null=True, blank=True)
    name_on_notice = models.CharField(max_length=100, blank=True)
    postal_code_on_notice = models.CharField(max_length=7, blank=True)
    notice_date = models.DateField(null=True, blank=True)
    seen_in_person = models.BooleanField(default=False)
    did_not_file_reason = models.CharField(max_length=500, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="income_notices_recorded",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # BR-DOC-005: set when a newer entry replaces this one; null means current.
    superseded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["member"],
                condition=Q(superseded_at__isnull=True),
                name="documents_one_current_notice_per_member",
            ),
            models.CheckConstraint(
                condition=_CONFIRMED_SHAPE | _DID_NOT_FILE_SHAPE,
                name="documents_notice_shape",
            ),
        ]

    @property
    def has_file(self) -> bool:
        return bool(self.file_ref)
