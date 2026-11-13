# AI contribution: 50% or more AI-generated
"""Public role groups keep store and intake permissions separate."""

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser

from modules.accounts.models import User
from modules.accounts.queries import STAFF_ROLES, STORE_ROLES, is_admin


@pytest.mark.parametrize(
    ("role", "store", "staff", "admin"),
    [
        (User.Role.BENEFICIARY, False, False, False),
        (User.Role.STORE_STAFF, True, False, False),
        (User.Role.STORE_MANAGER, True, False, False),
        (User.Role.INTAKE_WORKER, False, True, False),
        (User.Role.ADMIN, False, True, True),
        ("unknown", False, False, False),
        (None, False, False, False),
    ],
)
def test_role_permissions(role, store, staff, admin):
    """Each role belongs only to its intended permission groups."""
    user = SimpleNamespace(role=role, is_authenticated=True, is_active=True)
    assert (role in STORE_ROLES) is store
    assert (role in STAFF_ROLES) is staff
    assert is_admin(user) is admin
    assert all(isinstance(role, User.Role) for role in (*STORE_ROLES, *STAFF_ROLES))


@pytest.mark.parametrize(
    "user",
    [
        None,
        AnonymousUser(),
        SimpleNamespace(role="admin", is_authenticated=False, is_active=True),
        SimpleNamespace(role="admin", is_authenticated=True, is_active=False),
        SimpleNamespace(is_authenticated=True, is_active=True),
    ],
)
def test_admin_check_denies_inactive_anonymous_or_missing_role(user):
    """Admin checks deny incomplete or inactive identities."""
    assert not is_admin(user)
