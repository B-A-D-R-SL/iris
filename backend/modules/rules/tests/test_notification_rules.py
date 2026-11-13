# AI contribution: 50% or more AI-generated
"""BR-NOTIF-001/004: bounded, versioned retry and queue retention settings."""

from copy import deepcopy
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from modules.rules import queries
from modules.rules.domain.schemas import (
    DEFAULT_RULE_VALUES,
    RuleValidationError,
    validate_rule_values,
)
from modules.rules.models import RuleSetVersion


# rule: BR-NOTIF-001
@pytest.mark.parametrize(
    "delays", [[], [60], [60, 300, 900, 1800], [0, 5, 15], [True, 5, 15], [1, 5, 86401]]
)
def test_notification_retry_policy_rejects_invalid_values_br_notif_001(delays):
    values = {**DEFAULT_RULE_VALUES["notifications"], "retry_delays_seconds": delays}
    with pytest.raises(RuleValidationError):
        validate_rule_values("notifications", values)


# rule: BR-NOTIF-004
@pytest.mark.parametrize("hours", [0, -1, True, 169])
def test_job_retention_is_bounded_br_notif_004(hours):
    values = {**DEFAULT_RULE_VALUES["notifications"], "job_retention_hours": hours}
    with pytest.raises(RuleValidationError):
        validate_rule_values("notifications", values)


# rule: BR-NOTIF-001
@pytest.mark.django_db
def test_notification_policy_requires_published_rules_br_notif_001():
    with pytest.raises(ValidationError, match="unavailable"):
        queries.notification_policy()


# rule: BR-NOTIF-001
# rule: BR-NOTIF-004
def test_notification_policy_resolves_effective_versions_br_notif_001(
    notification_rules,
):
    now = timezone.now()
    RuleSetVersion.objects.create(
        rule_type="notifications",
        version=2,
        values={"retry_delays_seconds": [1, 2, 3], "job_retention_hours": 1},
        effective_from=now + timedelta(days=1),
        created_by=notification_rules.created_by,
    )
    policy = queries.notification_policy()
    assert policy == {"retry_delays_seconds": [60, 300, 900], "job_retention_hours": 24}
    policy["retry_delays_seconds"].append(999)
    assert queries.notification_policy()["retry_delays_seconds"] == [60, 300, 900]


# rule: BR-NOTIF-001
# rule: BR-NOTIF-004
@pytest.mark.parametrize(
    "invalid", [[], {"retry_delays_seconds": [1], "job_retention_hours": 24}]
)
def test_corrupt_published_notification_rule_fails_closed(notification_rules, invalid):
    RuleSetVersion.objects.create(
        rule_type="notifications",
        version=2,
        values=deepcopy(invalid),
        effective_from=timezone.now() - timedelta(seconds=1),
        created_by=notification_rules.created_by,
    )
    with pytest.raises(ValidationError, match="invalid|unavailable"):
        queries.notification_policy()
