# AI contribution: 50% or more AI-generated
from contextlib import ExitStack

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
