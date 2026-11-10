# AI contribution: 50% or more AI-generated
"""Tests for version-one rule seeding and the reviewed LICO CSV format."""

from io import StringIO
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from modules.rules.domain.schemas import DEFAULT_RULE_VALUES, RULE_TYPES
from modules.rules.management.commands.seed_rules import SEED_USERNAME
from modules.rules.models import RuleSetVersion
from modules.rules.services import publish


def write_lico_csv(path: Path, data_rows: list[str] | None = None) -> None:
    """Write LICO metadata and either seven default rows or supplied test rows."""
    rows = [
        "# AI contribution: 50% or more AI-generated",
        "# source_url: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1110024101",
        "# retrieved_on: 2026-10-18",
        "family_size,threshold_cents",
    ]
    rows.extend(
        data_rows
        if data_rows is not None
        else [f"{size},{size * 1_000_000}" for size in range(1, 8)]
    )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


@pytest.mark.django_db
def test_seed_rules_loads_reviewed_2024_lico_values_in_cents() -> None:
    call_command("seed_rules", stdout=StringIO())

    lico = RuleSetVersion.objects.get(rule_type="lico_thresholds")
    assert lico.version == 1
    assert lico.values == {
        "year": 2024,
        "source_url": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1110024101",
        "retrieved_on": "2026-10-18",
        "thresholds": {
            "1": 3_126_400,
            "2": 3_892_200,
            "3": 4_785_100,
            "4": 5_809_600,
            "5": 6_589_200,
            "6": 7_431_500,
            "7": 8_273_900,
        },
    }


@pytest.mark.django_db
def test_seed_rules_creates_every_version_once(tmp_path: Path) -> None:
    lico_file = tmp_path / "lico_2024.csv"
    write_lico_csv(lico_file)
    output = StringIO()

    call_command("seed_rules", lico_file=lico_file, stdout=output)
    call_command("seed_rules", lico_file=lico_file, stdout=output)

    assert RuleSetVersion.objects.count() == len(RULE_TYPES)
    assert set(RuleSetVersion.objects.values_list("rule_type", flat=True)) == set(
        RULE_TYPES
    )
    assert set(RuleSetVersion.objects.values_list("version", flat=True)) == {1}
    lico = RuleSetVersion.objects.get(rule_type="lico_thresholds")
    assert lico.values["year"] == 2024
    assert lico.values["thresholds"] == {
        str(size): size * 1_000_000 for size in range(1, 8)
    }
    assert "Rule defaults are already seeded." in output.getvalue()

    publisher = get_user_model()._default_manager.get(
        **{get_user_model().USERNAME_FIELD: SEED_USERNAME}
    )
    assert not publisher.has_usable_password()
    assert publisher.role == "admin"


# rule: BR-HH-001
@pytest.mark.django_db
def test_seed_adds_household_size_without_replacing_existing_rules() -> None:
    publisher = get_user_model().objects.create_user(email="rules-test@example.test")
    existing = publish("priority", DEFAULT_RULE_VALUES["priority"], publisher)

    call_command("seed_rules", stdout=StringIO())

    existing.refresh_from_db()
    assert existing.values == DEFAULT_RULE_VALUES["priority"]
    assert RuleSetVersion.objects.filter(rule_type="priority").count() == 1
    configured = publish("household_size", {"max_people": 3}, publisher)
    call_command("seed_rules", stdout=StringIO())
    versions = RuleSetVersion.objects.filter(rule_type="household_size").order_by(
        "version"
    )
    assert [rule.values for rule in versions] == [{"max_people": 15}, {"max_people": 3}]
    assert versions.last() == configured


@pytest.mark.django_db
def test_seed_rules_fails_before_partial_seed_when_lico_is_missing(
    tmp_path: Path,
) -> None:
    missing_file = tmp_path / "lico_2024.csv"

    with pytest.raises(CommandError, match="does not exist"):
        call_command("seed_rules", lico_file=missing_file)

    assert not RuleSetVersion.objects.exists()


@pytest.mark.django_db
def test_seed_rules_rejects_incomplete_lico_data(tmp_path: Path) -> None:
    lico_file = tmp_path / "lico_2024.csv"
    write_lico_csv(lico_file, ["1,1000000"])

    with pytest.raises(CommandError, match="family sizes 1 through 7"):
        call_command("seed_rules", lico_file=lico_file)

    assert not RuleSetVersion.objects.exists()


@pytest.mark.django_db
def test_seed_rules_rejects_duplicate_lico_family_size(tmp_path: Path) -> None:
    lico_file = tmp_path / "lico_2024.csv"
    rows = [f"{size},{size * 1_000_000}" for size in range(1, 8)]
    write_lico_csv(lico_file, [*rows, "7,7000000"])

    with pytest.raises(CommandError, match="family size 7 more than once"):
        call_command("seed_rules", lico_file=lico_file)

    assert not RuleSetVersion.objects.exists()


@pytest.mark.django_db
def test_seed_rules_rejects_missing_lico_retrieval_date(tmp_path: Path) -> None:
    """Each published threshold needs a source retrieval date."""
    lico_file = tmp_path / "lico_2024.csv"
    write_lico_csv(lico_file)
    lines = lico_file.read_text(encoding="utf-8").splitlines()
    lico_file.write_text(
        "\n".join(line for line in lines if not line.startswith("# retrieved_on:"))
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(CommandError, match="retrieved_on must use an ISO date"):
        call_command("seed_rules", lico_file=lico_file)

    assert not RuleSetVersion.objects.exists()


@pytest.mark.django_db
def test_seed_upgrades_non_login_legacy_beneficiary():
    user = get_user_model().objects.create_user(email=SEED_USERNAME, role="beneficiary")
    user.set_unusable_password()
    user.save(update_fields=["password"])
    call_command("seed_rules", stdout=StringIO())
    user.refresh_from_db()
    assert user.role == "admin"
    assert not user.has_usable_password()


@pytest.mark.django_db
def test_seed_refuses_to_promote_usable_account():
    user = get_user_model().objects.create_user(
        email=SEED_USERNAME, password="example-password", role="beneficiary"
    )
    with pytest.raises(CommandError, match="non-login system account"):
        call_command("seed_rules", stdout=StringIO())
    user.refresh_from_db()
    assert user.role == "beneficiary"
    assert not RuleSetVersion.objects.exists()


@pytest.mark.django_db
def test_seed_corrects_existing_account_even_when_rules_are_already_seeded():
    call_command("seed_rules", stdout=StringIO())
    user = get_user_model().objects.get(email=SEED_USERNAME)
    user.role = "beneficiary"
    user.save(update_fields=["role"])
    call_command("seed_rules", stdout=StringIO())
    user.refresh_from_db()
    assert user.role == "admin"
