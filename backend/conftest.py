# AI contribution: 50% or more AI-generated
from contextlib import ExitStack
from datetime import UTC, datetime

import pytest
from django.db import connections, transaction
from django.test import TransactionTestCase


def _audit_safe_teardown(test_case, teardown):
    """Allow Django's test flush while restoring the audit trigger on failure."""
    with ExitStack() as stack:
        disabled = []
        for alias in test_case._databases_names(include_mirrors=False):
            connection = connections[alias]
            if connection.vendor != "postgresql":
                continue
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_trigger WHERE "
                    "tgrelid = to_regclass('audit_auditevent') "
                    "AND tgname = 'audit_append_only' AND tgenabled = 'O'"
                )
                if not cursor.fetchone():
                    continue
            stack.enter_context(transaction.atomic(using=alias))
            with connection.cursor() as cursor:
                cursor.execute(
                    "ALTER TABLE audit_auditevent DISABLE TRIGGER audit_append_only"
                )
            disabled.append(connection)
        # On failure, exiting the atomic blocks rolls back the trigger changes.
        teardown(test_case)
        for connection in reversed(disabled):
            with connection.cursor() as cursor:
                cursor.execute(
                    "ALTER TABLE audit_auditevent ENABLE TRIGGER audit_append_only"
                )


@pytest.fixture(scope="session", autouse=True)
def _allow_audit_test_flush():
    original = TransactionTestCase._fixture_teardown
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            TransactionTestCase,
            "_fixture_teardown",
            lambda self: _audit_safe_teardown(self, original),
        )
        yield


@pytest.fixture(autouse=True)
def _reset_test_mailer():
    """Every test receives a clean in-memory transport, including worker tests."""
    from adapters.mailer.fake import reset_fake_mailer

    reset_fake_mailer()
    yield
    reset_fake_mailer()


@pytest.fixture
def notification_rules(db):
    """Publish the required policy explicitly for workflows that queue email."""
    from django.apps import apps
    from django.contrib.auth import get_user_model

    from modules.rules.domain.schemas import DEFAULT_RULE_VALUES

    publisher = get_user_model().objects.create_user(
        email="notification-rules@example.test", password=None, role="admin"
    )
    return apps.get_model("rules", "RuleSetVersion").objects.create(
        rule_type="notifications",
        version=1,
        values=DEFAULT_RULE_VALUES["notifications"],
        effective_from=datetime(2000, 1, 1, tzinfo=UTC),
        created_by=publisher,
    )
