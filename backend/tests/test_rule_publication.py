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
