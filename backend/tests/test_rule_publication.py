# AI contribution: 50% or more AI-generated
from copy import deepcopy

import pytest

from modules.accounts.tests.factories import UserFactory
from modules.audit.models import AuditEvent
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish


@pytest.fixture
def publisher():
    return UserFactory()


@pytest.mark.django_db
def test_publish_records_event_and_logs_identifiers(
    publisher, caplog, django_capture_on_commit_callbacks
):
    with (
        caplog.at_level("INFO", logger="modules.rules.services"),
        django_capture_on_commit_callbacks(execute=True),
    ):
        rule = publish("priority", deepcopy(DEFAULT_RULE_VALUES["priority"]), publisher)
    event = AuditEvent.objects.get(action="rule_published")
    assert event.actor == publisher
    assert event.target_type == "rule_set_version"
    assert event.target_id == str(rule.pk)
    assert event.metadata == {"rule_type": "priority", "version": 1}
    assert caplog.messages == [
        f"rule_published rule_version_id={rule.pk} actor_id={publisher.pk}"
    ]


@pytest.mark.django_db(transaction=True)
def test_seed_audit_events_and_logs_commit_together(caplog):
    from django.core.management import call_command
    from django.db import transaction

    from modules.rules.domain.schemas import RULE_TYPES
    from modules.rules.models import RuleSetVersion

    with caplog.at_level("INFO", logger="modules.rules.services"):
        with transaction.atomic():
            call_command("seed_rules")
            assert AuditEvent.objects.filter(action="rule_published").count() == len(
                RULE_TYPES
            )
            assert not caplog.messages
        rules = list(RuleSetVersion.objects.all())
        events = AuditEvent.objects.filter(action="rule_published")
        assert events.count() == len(RULE_TYPES)
        assert {event.target_id for event in events} == {str(rule.pk) for rule in rules}
        assert len(caplog.messages) == len(RULE_TYPES)
        for rule in rules:
            assert (
                caplog.messages.count(
                    f"rule_published rule_version_id={rule.pk} actor_id={rule.created_by_id}"
                )
                == 1
            )


@pytest.mark.django_db(transaction=True)
def test_seed_failure_rolls_back_events_and_discards_logs(caplog, monkeypatch):
    from django.core.management import call_command

    from modules.rules.management.commands import seed_rules
    from modules.rules.models import RuleSetVersion

    original_publish = seed_rules.publish
    count = 0

    def fail_second(*args, **kwargs):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("publication failed")
        return original_publish(*args, **kwargs)

    monkeypatch.setattr(seed_rules, "publish", fail_second)
    with (
        caplog.at_level("INFO", logger="modules.rules.services"),
        pytest.raises(RuntimeError, match="publication failed"),
    ):
        call_command("seed_rules")
    assert count == 2
    assert not RuleSetVersion.objects.exists()
    assert not AuditEvent.objects.filter(action="rule_published").exists()
    assert not caplog.messages
