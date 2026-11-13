# AI contribution: 50% or more AI-generated
import json
import logging
from copy import deepcopy
from io import StringIO
from unittest.mock import patch

import pytest

from modules.accounts.tests.factories import UserFactory
from modules.audit.models import AuditEvent
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish


@pytest.fixture
def publisher():
    return UserFactory(role="admin")


@pytest.mark.django_db
def test_publish_records_event_and_logs_without_identifiers(
    publisher, django_capture_on_commit_callbacks
):
    from iris.observability import JsonLogFormatter

    logger = logging.getLogger("iris.rules")
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    try:
        assert logger.isEnabledFor(logging.INFO)
        with django_capture_on_commit_callbacks(execute=True):
            rule = publish(
                "priority", deepcopy(DEFAULT_RULE_VALUES["priority"]), publisher
            )
    finally:
        logger.removeHandler(handler)
    event = AuditEvent.objects.get(action="rule_published")
    assert event.actor == publisher
    assert event.actor_role == "admin"
    assert event.target_type == "rule_set_version"
    assert event.target_id == str(rule.pk)
    assert event.metadata == {"rule_type": "priority", "version": 1}
    payload = json.loads(stream.getvalue())
    assert payload["event"] == "rule_published"
    assert str(publisher.pk) not in stream.getvalue()
    assert set(payload) == {"timestamp", "level", "logger", "event"}


@pytest.mark.django_db(transaction=True)
def test_publication_stays_committed_when_logging_fails(publisher):
    """A failed publication log preserves success and allows later commit callbacks."""
    from django.db import transaction

    from modules.rules.models import RuleSetVersion

    completed_callbacks = []
    with patch(
        "modules.rules.services.logger.info", side_effect=RuntimeError("logging failed")
    ) as log_info:
        with transaction.atomic():
            rule = publish(
                "priority", deepcopy(DEFAULT_RULE_VALUES["priority"]), publisher
            )
            transaction.on_commit(lambda: completed_callbacks.append(rule.pk))
            assert log_info.call_count == 0
        assert log_info.call_count == 1

    rule.refresh_from_db()
    assert rule.version == 1
    assert RuleSetVersion.objects.count() == 1
    event = AuditEvent.objects.get(action="rule_published")
    assert event.actor_id == publisher.pk
    assert event.target_id == str(rule.pk)
    assert event.metadata == {"rule_type": "priority", "version": 1}
    assert completed_callbacks == [rule.pk]


@pytest.mark.django_db(transaction=True)
def test_seed_audit_events_and_logs_commit_together():
    from django.core.management import call_command
    from django.db import transaction

    from modules.rules.domain.schemas import RULE_TYPES
    from modules.rules.models import RuleSetVersion

    with patch("modules.rules.services.logger.info") as log_info:
        with transaction.atomic():
            call_command("seed_rules")
            assert AuditEvent.objects.filter(action="rule_published").count() == len(
                RULE_TYPES
            )
            assert log_info.call_count == 0
        rules = list(RuleSetVersion.objects.all())
        events = AuditEvent.objects.filter(action="rule_published")
        assert events.count() == len(RULE_TYPES)
        assert {event.target_id for event in events} == {str(rule.pk) for rule in rules}
        assert log_info.call_count == len(RULE_TYPES)
        assert all(
            call.kwargs["extra"]["event"] == "rule_published"
            for call in log_info.call_args_list
        )
        assert all(event.actor_role == "admin" for event in events)


@pytest.mark.django_db(transaction=True)
def test_seed_failure_rolls_back_events_and_discards_logs(monkeypatch):
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
        patch("modules.rules.services.logger.info") as log_info,
        pytest.raises(RuntimeError, match="publication failed"),
    ):
        call_command("seed_rules")
    assert count == 2
    assert not RuleSetVersion.objects.exists()
    assert not AuditEvent.objects.filter(action="rule_published").exists()
    assert log_info.call_count == 0


def test_audit_rule_type_allowlist_matches_rules_contract():
    from modules.audit.services import RULE_PUBLICATION_TYPES
    from modules.rules.domain.schemas import RULE_TYPES

    assert RULE_PUBLICATION_TYPES == set(RULE_TYPES)
