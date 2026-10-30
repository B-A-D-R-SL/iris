# AI contribution: 50% or more AI-generated
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class AuditEvent(models.Model):
    class Action(models.TextChoices):
        VIEW = "view"
        DECISION = "decision"

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    actor_role = models.CharField(max_length=20)
    action = models.CharField(max_length=20, choices=Action.choices)
    target_type = models.CharField(
        max_length=64,
        validators=[RegexValidator(r"\A[a-z][a-z0-9_]*\Z")],
    )
    target_id = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
