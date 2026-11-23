# AI contribution: 50% or more AI-generated
"""US-93: linking a household's account and re-inviting it are audited."""

from typing import Any

import pytest
from django.core.exceptions import ValidationError

from modules.audit import services
from modules.audit.models import AuditEvent

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("method", ["invitation", "counter"])
def test_link_account_records_how_the_account_was_linked(
    event_inputs: dict[str, Any], method: str
) -> None:
    event_inputs.update(action="link_account", metadata={"method": method})
    event = services.record(**event_inputs)
    assert (event.action, event.metadata) == ("link_account", {"method": method})


@pytest.mark.parametrize(
    "metadata",
    [{}, {"method": "email"}, {"method": "counter", "email": "x@example.test"}],
)
def test_link_account_refuses_other_metadata(
    event_inputs: dict[str, Any], metadata: dict[str, Any]
) -> None:
    event_inputs.update(action="link_account", metadata=metadata)
    with pytest.raises(ValidationError, match="metadata"):
        services.record(**event_inputs)
    assert not AuditEvent.objects.exists()


def test_link_account_is_only_for_households(event_inputs: dict[str, Any]) -> None:
    event_inputs.update(
        action="link_account",
        target_type="store",
        target_id="1",
        metadata={"method": "counter"},
    )
    with pytest.raises(ValidationError, match="metadata"):
        services.record(**event_inputs)


def test_invite_records_no_metadata(event_inputs: dict[str, Any]) -> None:
    event_inputs.update(action="invite")
    assert services.record(**event_inputs).action == "invite"
    event_inputs.update(metadata={"email": "x@example.test"})
    with pytest.raises(ValidationError, match="metadata"):
        services.record(**event_inputs)
