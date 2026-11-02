# AI contribution: 50% or more AI-generated
from types import SimpleNamespace

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction

from conftest import _audit_safe_teardown

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("fail", [False, True])
def test_audit_cleanup_restores_trigger(fail):
    test_case = SimpleNamespace(_databases_names=lambda **kwargs: ["default"])

    def cleanup(_test_case):
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE audit_auditevent")
            if fail:
                cursor.execute("SELECT 1 / 0")

    if fail:
        with pytest.raises(DatabaseError):
            _audit_safe_teardown(test_case, cleanup)
    else:
        _audit_safe_teardown(test_case, cleanup)

    with (
        pytest.raises(IntegrityError, match="append-only"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute("TRUNCATE audit_auditevent")
