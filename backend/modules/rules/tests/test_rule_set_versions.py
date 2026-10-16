from datetime import datetime

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from modules.rules.models import RuleSetVersion
from modules.rules.queries import active
from modules.rules.services import publish


def at(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.get_current_timezone())


@pytest.fixture
def publisher(django_user_model):
    return django_user_model.objects.create_user(
        username="rule-publisher",
        password="not-used-by-this-test",
    )


@pytest.mark.django_db
def test_publish_creates_successive_immutable_versions(publisher) -> None:
    first = publish(
        "priority",
        {"score": 10},
        publisher,
        effective_from=at(2026, 1, 1),
    )
    second = publish(
        "priority",
        {"score": 20},
        publisher,
        effective_from=at(2026, 2, 1),
    )

    assert (first.rule_type, first.version, first.values) == (
        "priority",
        1,
        {"score": 10},
    )
    assert (second.rule_type, second.version, second.values) == (
        "priority",
        2,
        {"score": 20},
    )
    assert RuleSetVersion.objects.filter(rule_type="priority").count() == 2

    first.values = {"score": 999}
    with pytest.raises(ValidationError, match="cannot be updated"):
        first.save()
    with pytest.raises(ValidationError, match="cannot be updated"):
        RuleSetVersion.objects.filter(pk=first.pk).update(values={"score": 999})
    with pytest.raises(ValidationError, match="cannot be deleted"):
        RuleSetVersion.objects.filter(pk=first.pk).delete()

    assert RuleSetVersion.objects.get(pk=first.pk).values == {"score": 10}


@pytest.mark.django_db
def test_active_resolves_using_effective_date_not_highest_version(publisher) -> None:
    january = publish(
        "tiers",
        {"tier": "january"},
        publisher,
        effective_from=at(2026, 1, 1),
    )
    february = publish(
        "tiers",
        {"tier": "february"},
        publisher,
        effective_from=at(2026, 2, 1),
    )
    backdated_correction = publish(
        "tiers",
        {"tier": "corrected-january"},
        publisher,
        effective_from=at(2026, 1, 15),
    )

    assert active("tiers", at=at(2025, 12, 31)) is None
    assert active("tiers", at=at(2026, 1, 10)) == january
    assert active("tiers", at=at(2026, 1, 20)) == backdated_correction
    assert active("tiers", at=at(2026, 3, 1)) == february


@pytest.mark.django_db
def test_active_prefers_later_version_for_equal_effective_dates(publisher) -> None:
    first = publish(
        "retention",
        {"days": 30},
        publisher,
        effective_from=at(2026, 1, 1),
    )
    second = publish(
        "retention",
        {"days": 60},
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
            {"score": 10},
            publisher,
            effective_from=datetime(2026, 1, 1),  # noqa: DTZ001 - validation case
        )
