# AI contribution: 50% or more AI-generated
"""Delivery metadata; message contents and credentials never belong here."""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class EmailLog(models.Model):
    """One message and its attempts. Sent means transport acceptance, not delivery."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENDING = "sending", _("Sending")
        RETRYING = "retrying", _("Retrying")
        SENT = "sent", _("Sent")
        FAILED = "failed", _("Failed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    to_email = models.EmailField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="email_logs",
    )
    template_key = models.CharField(max_length=64)
    language = models.CharField(
        max_length=2, choices=[("fr", "Français"), ("en", "English")]
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    error = models.CharField(max_length=64, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012 - Django model metadata.
        indexes = [  # noqa: RUF012 - staff queries filter by outcome.
            models.Index(
                fields=["status", "created_at"], name="notifications_status_created"
            ),
        ]
        constraints = [  # noqa: RUF012 - enforce metadata consistency.
            models.CheckConstraint(
                condition=models.Q(language__in=["fr", "en"]),
                name="notifications_email_language",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="sent", sent_at__isnull=False)
                    | (~models.Q(status="sent") & models.Q(sent_at__isnull=True))
                ),
                name="notifications_email_sent_time",
            ),
        ]
