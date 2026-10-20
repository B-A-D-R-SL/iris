# AI contribution: 50% or more AI-generated
"""Tests for version-one rule seeding and the reviewed LICO CSV format."""

from io import StringIO
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from modules.rules.domain.schemas import RULE_TYPES
from modules.rules.management.commands.seed_rules import SEED_USERNAME
from modules.rules.models import RuleSetVersion


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
    """Preserve all seven official 2024 amounts and their source metadata."""
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
    """Rerunning the seed leaves version-one rules and their publisher intact."""
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


@pytest.mark.django_db
def test_seed_rules_fails_before_partial_seed_when_lico_is_missing(
    tmp_path: Path,
) -> None:
    """A missing LICO file aborts the entire seed transaction."""
    missing_file = tmp_path / "lico_2024.csv"

    with pytest.raises(CommandError, match="does not exist"):
        call_command("seed_rules", lico_file=missing_file)

    assert not RuleSetVersion.objects.exists()


@pytest.mark.django_db
def test_seed_rules_rejects_incomplete_lico_data(tmp_path: Path) -> None:
    """Reject a CSV that omits any required family size before publishing."""
    lico_file = tmp_path / "lico_2024.csv"
    write_lico_csv(lico_file, ["1,1000000"])

    with pytest.raises(CommandError, match="family sizes 1 through 7"):
        call_command("seed_rules", lico_file=lico_file)

    assert not RuleSetVersion.objects.exists()


@pytest.mark.django_db
def test_seed_rules_rejects_duplicate_lico_family_size(tmp_path: Path) -> None:
    """Reject repeated family-size rows before creating rule versions."""
    lico_file = tmp_path / "lico_2024.csv"
    rows = [f"{size},{size * 1_000_000}" for size in range(1, 8)]
    write_lico_csv(lico_file, [*rows, "7,7000000"])

    with pytest.raises(CommandError, match="family size 7 more than once"):
        call_command("seed_rules", lico_file=lico_file)

    assert not RuleSetVersion.objects.exists()


@pytest.mark.django_db
def test_seed_rules_rejects_missing_lico_retrieval_date(tmp_path: Path) -> None:
    """Require a retrieval date so each published threshold has provenance."""
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
