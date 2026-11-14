# AI contribution: 50% or more AI-generated
"""Notice entry limits come from the notice_upload rule (review rule 2, T-03.18.2)."""

import re
from collections.abc import Callable
from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import translation

from adapters.file_store.memory import InMemoryFileStore
from modules.documents.services import NoticeSettingsMissing, record_staff_notice
from modules.documents.tests.factories import make_member
from modules.rules import queries as rule_queries

pytestmark = pytest.mark.django_db


@pytest.fixture
def member() -> Any:
    return make_member()


def _filed(**changes: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "did_not_file": False,
        "tax_year": 2025,
        "total_income_cents": 4_321_000,
        "name_on_notice": "Example Holder",
        "postal_code_on_notice": "H2X 1Y4",
        "notice_date": date(2026, 4, 30),
        "seen_in_person": True,
    }
    return values | changes


def _pdf() -> SimpleUploadedFile:
    return SimpleUploadedFile("scan.pdf", b"%PDF-1.7", content_type="application/pdf")


# rule: BR-DOC-002
def test_the_earliest_tax_year_comes_from_the_notice_rule(
    member: Any, worker: Any, publish_notice_rule: Callable[..., None]
) -> None:
    publish_notice_rule(earliest_tax_year=2010)
    entry = _filed(tax_year=2009, notice_date=date(2010, 4, 30))

    with translation.override("en"), pytest.raises(ValidationError) as refused:
        record_staff_notice(
            member.pk, entry, _pdf(), worker, file_store=InMemoryFileStore()
        )

    assert refused.value.message_dict == {
        "tax_year": ["Enter a tax year from 2010 on."]
    }


# rule: BR-DOC-003
def test_the_reason_length_comes_from_the_notice_rule(
    member: Any, worker: Any, publish_notice_rule: Callable[..., None]
) -> None:
    publish_notice_rule(reason_max_length=20)
    entry = {"did_not_file": True, "did_not_file_reason": "x" * 21}

    with translation.override("en"), pytest.raises(ValidationError) as refused:
        record_staff_notice(member.pk, entry, None, worker)

    assert refused.value.message_dict == {
        "did_not_file_reason": ["Use at most 20 characters."]
    }


def test_a_rule_without_the_entry_limits_is_treated_as_missing(
    member: Any, worker: Any, monkeypatch: Any
) -> None:
    """A notice_upload version published before these limits existed fails closed."""
    older = SimpleNamespace(values={"max_bytes": 1024, "link_minutes": 5})
    monkeypatch.setattr(rule_queries, "active", lambda rule_type, at=None: older)
    entry = {"did_not_file": True, "did_not_file_reason": "No income in 2025"}

    with pytest.raises(NoticeSettingsMissing):
        record_staff_notice(member.pk, entry, None, worker)


# rule: BR-DOC-001
def test_an_income_above_the_rule_maximum_is_refused_in_both_languages(
    member: Any, worker: Any, notice_rule: None
) -> None:
    """forms-and-fields.md: total income is 0 to 500,000 $ (max_income_cents)."""
    entry = _filed(total_income_cents=50_000_001)
    messages = {}
    for language in ("en", "fr"):
        with translation.override(language), pytest.raises(ValidationError) as refused:
            record_staff_notice(
                member.pk, entry, _pdf(), worker, file_store=InMemoryFileStore()
            )
        messages[language] = refused.value.message_dict

    assert messages["en"] == {
        "total_income_cents": ["Enter an amount of at most $500,000."]
    }
    [french] = messages["fr"]["total_income_cents"]
    assert re.fullmatch(r"Entrez un montant d'au plus 500\s000 \$\.", french)


# rule: BR-DOC-001
def test_an_income_at_the_rule_maximum_is_recorded(
    member: Any, worker: Any, notice_rule: None
) -> None:
    entry = _filed(total_income_cents=50_000_000)

    notice = record_staff_notice(
        member.pk, entry, _pdf(), worker, file_store=InMemoryFileStore()
    )

    assert notice.total_income_cents == 50_000_000


# rule: BR-DOC-001
def test_the_income_maximum_comes_from_the_notice_rule(
    member: Any, worker: Any, publish_notice_rule: Callable[..., None]
) -> None:
    publish_notice_rule(max_income_cents=100_000)

    with translation.override("en"), pytest.raises(ValidationError) as refused:
        record_staff_notice(
            member.pk,
            _filed(total_income_cents=100_001),
            _pdf(),
            worker,
            file_store=InMemoryFileStore(),
        )

    assert refused.value.message_dict == {
        "total_income_cents": ["Enter an amount of at most $1,000."]
    }
