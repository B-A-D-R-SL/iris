# AI contribution: 50% or more AI-generated
"""One rule for who may manage walk-in files and notices (T-03.18.2 review)."""

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser

from modules.accounts.queries import is_intake_staff


@pytest.mark.parametrize(
    ("role", "active", "expected"),
    [
        ("intake_worker", True, True),
        ("admin", True, True),
        ("intake_worker", False, False),
        ("admin", False, False),
        ("beneficiary", True, False),
        ("store_staff", True, False),
        ("store_manager", True, False),
    ],
)
def test_only_active_intake_workers_and_admins_are_intake_staff(
    role: str, active: bool, expected: bool
) -> None:
    user = SimpleNamespace(is_authenticated=True, is_active=active, role=role)

    assert is_intake_staff(user) is expected


def test_signed_out_visitor_is_not_intake_staff() -> None:
    assert is_intake_staff(AnonymousUser()) is False
