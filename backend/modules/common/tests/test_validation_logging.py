# AI contribution: 50% or more AI-generated
"""Contact diagnostics expose only a known field while validation continues."""

import json
import logging

import pytest
from django.core.exceptions import ValidationError

from iris.observability import JsonLogFormatter
from modules.common.domain.contact import normalize_postal_code
from modules.common.validators import normalize_model_contacts
from modules.stores.tests.factories import StoreFactory

EVENT = "contact_normalization_rejected"
PRIVATE_PHONE = "+447911123456"
PRIVATE_EXCEPTION = "private@example.test secret diagnostic"


@pytest.fixture
def contact_logs(caplog, monkeypatch):
    logger = logging.getLogger("iris.validation")
    monkeypatch.setattr(logger, "propagate", False)
    logger.addHandler(caplog.handler)
    caplog.set_level(logging.INFO, logger=logger.name)
    try:
        yield caplog
    finally:
        logger.removeHandler(caplog.handler)


def _store(**values):
    return StoreFactory.build(opening_hours={"mon": [["09:00", "17:00"]]}, **values)


def test_valid_contact_normalization_does_not_log_a_rejection(contact_logs):
    store = _store(phone=" +1 (514) 555-0123 ", postal_code=" h2x  1y4 ")
    store.clean_fields()
    assert store.phone == "+15145550123"
    assert store.postal_code == "H2X 1Y4"
    assert not contact_logs.records


def test_rejection_preserves_input_and_logs_no_value_or_exception(contact_logs):
    def reject(value):
        raise ValueError(f"{PRIVATE_EXCEPTION}: {value}")

    store = _store(phone=PRIVATE_PHONE, postal_code="h2x1y4")
    normalize_model_contacts(
        store, {"phone": reject, "postal_code": normalize_postal_code}
    )
    assert store.phone == PRIVATE_PHONE
    assert store.postal_code == "H2X 1Y4"
    [record] = contact_logs.records
    assert record.levelno == logging.INFO
    assert record.getMessage() == EVENT
    assert record.args == ()
    assert record.exc_info is None and record.exc_text is None
    assert record.stack_info is None
    assert PRIVATE_PHONE not in repr(record.__dict__)
    assert PRIVATE_EXCEPTION not in repr(record.__dict__)
    payload = json.loads(JsonLogFormatter().format(record))
    assert payload == {
        "timestamp": payload["timestamp"],
        "level": "INFO",
        "logger": "iris.validation",
        "event": EVENT,
        "field": "phone",
    }


def test_invalid_fields_still_collect_all_validation_errors(contact_logs):
    store = _store(phone=PRIVATE_PHONE, postal_code="D2X 1Y4")
    with pytest.raises(ValidationError) as raised:
        store.clean_fields()
    assert {"phone", "postal_code"} <= raised.value.message_dict.keys()
    assert [record.field for record in contact_logs.records] == ["phone", "postal_code"]


def test_excluded_contacts_are_unchanged_and_do_not_log(contact_logs):
    store = _store(phone=PRIVATE_PHONE, postal_code="D2X 1Y4")
    store.clean_fields(exclude={"phone", "postal_code"})
    assert store.phone == PRIVATE_PHONE
    assert store.postal_code == "D2X 1Y4"
    assert not contact_logs.records


@pytest.mark.parametrize(
    ("logger", "event", "field", "allowed"),
    [
        ("iris.validation", EVENT, "phone", True),
        ("iris.validation", EVENT, "contact_phone", True),
        ("iris.validation", EVENT, "postal_code", True),
        ("iris.stores", EVENT, "phone", False),
        ("iris.validation", "other_event", "phone", False),
        ("iris.validation", EVENT, PRIVATE_EXCEPTION, False),
        ("iris.validation", EVENT, ["phone"], False),
        ("iris.validation", EVENT, None, False),
    ],
)
def test_json_contact_field_allowlist_is_event_and_logger_specific(
    logger, event, field, allowed
):
    record = logging.makeLogRecord(
        {
            "name": logger,
            "levelname": "INFO",
            "msg": PRIVATE_EXCEPTION,
            "event": event,
            "field": field,
            "value": PRIVATE_PHONE,
            "exception": ValueError(PRIVATE_EXCEPTION),
        }
    )
    encoded = JsonLogFormatter().format(record)
    payload = json.loads(encoded)
    assert ("field" in payload) is allowed
    if allowed:
        assert payload["field"] == field
    assert PRIVATE_PHONE not in encoded
    assert PRIVATE_EXCEPTION not in encoded
