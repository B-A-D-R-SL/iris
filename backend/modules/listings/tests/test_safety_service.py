# AI contribution: 50% or more AI-generated
"""US-34 through the posting service and PostgreSQL, with the real safety rule."""

from dataclasses import replace
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from zoneinfo import ZoneInfo

import pytest
from django.core.exceptions import ValidationError
from django.utils import translation

from modules.categories.models import Category
from modules.categories.tests.factories import CategoryFactory
from modules.listings import services
from modules.listings.domain.posting import Refusal
from modules.listings.models import Listing
from modules.rules.models import RuleSetVersion
from modules.rules.services import publish

MONTREAL = ZoneInfo("America/Montreal")


def ban_and_margin(
    case: SimpleNamespace, *, codes: list[str] | None = None, margin: int = 0
) -> None:
    """Publish a newer listing_safety version, as an admin would."""
    publish(
        "listing_safety",
        {"best_before_margin_days": margin, "prohibited_category_codes": codes or []},
        case.user,
        effective_from=case.now,
    )


def refusal_messages(case: SimpleNamespace, **changes: Any) -> dict[str, list[str]]:
    with pytest.raises(ValidationError) as caught:
        services.post_listing(case.store.pk, case.user, replace(case.data, **changes))
    assert not Listing.objects.exists()
    return caught.value.message_dict


# rule: BR-LIST-001 safe-and-allowed confirmation, stored with who and when (AC1)
def test_us34_publishes_safe_food_listing_with_who_and_when(
    posting_case: SimpleNamespace,
) -> None:
    case = posting_case
    listing = services.post_listing(case.store.pk, case.user, case.data)
    listing.refresh_from_db()
    assert listing.safe_confirmed_by_id == case.user.pk
    assert listing.safe_confirmed_at == case.now
    assert listing.best_before == case.data.best_before


# rule: BR-LIST-003 food best-before on or after the pickup end date (AC2)
def test_us34_refuses_food_best_before_before_pickup_end(
    posting_case: SimpleNamespace,
) -> None:
    case = posting_case
    messages = refusal_messages(
        case, best_before=case.data.best_before - timedelta(days=1)
    )
    assert messages == {
        "best_before": ["Choose Oct. 27, 2026 or later (end of pickup)."]
    }


def test_us34_refuses_food_without_best_before(posting_case: SimpleNamespace) -> None:
    messages = refusal_messages(posting_case, best_before=None)
    assert messages == {
        "best_before": ["Enter a best-before date. It is required for food."]
    }


def test_us34_best_before_message_is_french(posting_case: SimpleNamespace) -> None:
    case = posting_case
    with translation.override("fr"):
        messages = refusal_messages(
            case, best_before=case.data.best_before - timedelta(days=1)
        )
    assert messages == {
        "best_before": ["Choisissez le 27 oct. 2026 ou après (fin de la cueillette)."]
    }


def test_us34_pickup_end_day_is_the_montreal_day_not_utc(
    posting_case: SimpleNamespace,
) -> None:
    """21:30 in Montreal on Oct 27 is already Oct 28 in UTC."""
    case = posting_case
    start = datetime(2026, 10, 27, 20, 30, tzinfo=MONTREAL)
    end = datetime(2026, 10, 27, 21, 30, tzinfo=MONTREAL)
    assert end.astimezone(ZoneInfo("UTC")).date() == date(2026, 10, 28)
    on_the_day = replace(
        case.data, pickup_start=start, pickup_end=end, best_before=date(2026, 10, 27)
    )
    services.post_listing(case.store.pk, case.user, on_the_day)
    assert Listing.objects.count() == 1

    day_before = replace(on_the_day, best_before=date(2026, 10, 26))
    with pytest.raises(ValidationError) as caught:
        services.post_listing(case.store.pk, case.user, day_before)
    assert "best_before" in caught.value.message_dict
    assert Listing.objects.count() == 1


def test_us34_applies_margin_from_newest_rule_version(
    posting_case: SimpleNamespace,
) -> None:
    case = posting_case
    ban_and_margin(case, margin=2)
    messages = refusal_messages(case, best_before=case.data.best_before + timedelta(1))
    assert messages == {
        "best_before": ["Choose Oct. 29, 2026 or later (end of pickup)."]
    }

    services.post_listing(
        case.store.pk,
        case.user,
        replace(case.data, best_before=case.data.best_before + timedelta(days=2)),
    )
    assert Listing.objects.count() == 1


def test_us34_non_food_ignores_best_before(posting_case: SimpleNamespace) -> None:
    case = posting_case
    clothing = cast(Category, CategoryFactory(is_food=False))
    services.post_listing(
        case.store.pk,
        case.user,
        replace(case.data, category=clothing.code, best_before=date(2026, 1, 1)),
    )
    assert Listing.objects.get().category_id == clothing.pk


# rule: BR-LIST-002 categories on the prohibited list cannot be posted (AC3)
def test_us34_refuses_prohibited_category(posting_case: SimpleNamespace) -> None:
    case = posting_case
    ban_and_margin(case, codes=[case.category.code])
    messages = refusal_messages(case)
    assert messages == {
        "category": ["This category can't be posted. Choose another one."]
    }


def test_us34_malformed_safety_rules_make_posting_unavailable(
    posting_case: SimpleNamespace,
) -> None:
    case = posting_case
    # Bypasses publish() validation to simulate a corrupted stored version.
    RuleSetVersion.objects.create(
        rule_type="listing_safety",
        version=2,
        values={"best_before_margin_days": -1, "prohibited_category_codes": []},
        effective_from=case.now,
        created_by=case.user,
    )
    with pytest.raises(services.PostingUnavailable, match="safety rules"):
        services.post_listing(case.store.pk, case.user, case.data)
    assert not Listing.objects.exists()


def test_us34_refusal_params_are_formatted_and_old_refusals_still_work(
    posting_case: SimpleNamespace,
) -> None:
    case = posting_case

    def checker(listing_data: Any, category: Any, rules: Any) -> list[Refusal]:
        return [
            Refusal("title", "unsafe_listing"),
            Refusal(
                "best_before", "best_before_too_early", {"date": date(2026, 12, 1)}
            ),
        ]

    with pytest.raises(ValidationError) as caught:
        services.post_listing(case.store.pk, case.user, case.data, safety_check=checker)
    assert caught.value.message_dict == {
        "title": ["This listing was refused by the safety checks."],
        "best_before": ["Choose Dec. 1, 2026 or later (end of pickup)."],
    }


def test_us34_service_passes_montreal_pickup_end_date_to_checker(
    posting_case: SimpleNamespace,
) -> None:
    case = posting_case
    seen: dict[str, Any] = {}

    def checker(listing_data: Any, category: Any, rules: Any) -> list[Refusal]:
        seen.update(listing_data)
        return []

    services.post_listing(case.store.pk, case.user, case.data, safety_check=checker)
    assert seen["pickup_end_date"] == case.data.pickup_end.astimezone(MONTREAL).date()
