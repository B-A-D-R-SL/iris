from io import StringIO
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from modules.rules.domain.schemas import RULE_TYPES
from modules.rules.management.commands.seed_rules import SEED_USERNAME
from modules.rules.models import RuleSetVersion


def write_lico_csv(path: Path) -> None:
    rows = ["family_size,threshold_cents"]
    rows.extend(f"{size},{size * 1_000_000}" for size in range(1, 8))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


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
    lico_file.write_text("family_size,threshold_cents\n1,1000000\n", encoding="utf-8")

    with pytest.raises(CommandError, match="family sizes 1 through 7"):
        call_command("seed_rules", lico_file=lico_file)

    assert not RuleSetVersion.objects.exists()
