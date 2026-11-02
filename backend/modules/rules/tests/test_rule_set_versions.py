# AI contribution: Below 50% AI-generated
from copy import deepcopy
from datetime import datetime

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from modules.accounts.tests.factories import UserFactory
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.models import RuleSetVersion
from modules.rules.queries import active
from modules.rules.services import publish


def at(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.get_current_timezone())


@pytest.fixture
def publisher():
    return UserFactory()


@pytest.mark.django_db
def test_publish_creates_successive_immutable_versions(publisher) -> None:
    first_values = deepcopy(DEFAULT_RULE_VALUES["priority"])
    second_values = {**first_values, "income_gap_max_points": 61}
    first = publish(
        "priority",
        first_values,
        publisher,
        effective_from=at(2026, 1, 1),
    )
    second = publish(
        "priority",
        second_values,
        publisher,
        effective_from=at(2026, 2, 1),
    )

    assert (first.rule_type, first.version, first.values) == (
        "priority",
        1,
        first_values,
    )
    assert (second.rule_type, second.version, second.values) == (
        "priority",
        2,
        second_values,
    )
    assert RuleSetVersion.objects.filter(rule_type="priority").count() == 2

    first.values = {**first_values, "income_gap_max_points": 999}
    with pytest.raises(ValidationError, match="cannot be updated"):
        first.save()
    with pytest.raises(ValidationError, match="cannot be updated"):
        RuleSetVersion.objects.filter(pk=first.pk).update(
            values={**first_values, "income_gap_max_points": 999}
        )
    with pytest.raises(ValidationError, match="cannot be deleted"):
        RuleSetVersion.objects.filter(pk=first.pk).delete()

    assert RuleSetVersion.objects.get(pk=first.pk).values == first_values


@pytest.mark.django_db
def test_active_resolves_using_effective_date_not_highest_version(publisher) -> None:
    defaults = deepcopy(DEFAULT_RULE_VALUES["tiers"])
    january = publish(
        "tiers",
        {**defaults, "tier_2_delay_hours": 1},
        publisher,
        effective_from=at(2026, 1, 1),
    )
    february = publish(
        "tiers",
        {**defaults, "tier_2_delay_hours": 2},
        publisher,
        effective_from=at(2026, 2, 1),
    )
    backdated_correction = publish(
        "tiers",
        {**defaults, "tier_2_delay_hours": 1.5},
        publisher,
        effective_from=at(2026, 1, 15),
    )

    assert active("tiers", at=at(2025, 12, 31)) is None
    assert active("tiers", at=at(2026, 1, 10)) == january
    assert active("tiers", at=at(2026, 1, 20)) == backdated_correction
    assert active("tiers", at=at(2026, 3, 1)) == february


@pytest.mark.django_db
def test_active_prefers_later_version_for_equal_effective_dates(publisher) -> None:
    defaults = deepcopy(DEFAULT_RULE_VALUES["retention"])
    first = publish(
        "retention",
        {**defaults, "notice_files_days": 30},
        publisher,
        effective_from=at(2026, 1, 1),
    )
    second = publish(
        "retention",
        {**defaults, "notice_files_days": 60},
        publisher,
        effective_from=at(2026, 1, 1),
    )

    assert active("retention", at=at(2026, 1, 1)) == second
    assert first.version == 1


@pytest.mark.django_db
def test_publish_rejects_naive_effective_date(publisher) -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        publish(
            "priority",
            deepcopy(DEFAULT_RULE_VALUES["priority"]),
            publisher,
            effective_from=datetime(2026, 1, 1),  # noqa: DTZ001 - validation case
        )
