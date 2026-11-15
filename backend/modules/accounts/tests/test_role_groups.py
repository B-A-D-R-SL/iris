# AI contribution: 50% or more AI-generated
"""Public role groups keep store and intake permissions separate."""

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser

from modules.accounts.models import User
from modules.accounts.queries import STAFF_ROLES, STORE_ROLES, UserRole, is_admin


def test_one_role_enum_and_no_case_only_alias():
    """Other modules read the field's roles from queries (FIX-31, SonarCloud S1845).

    A `User.Role` alias made `user.Role`, mistyped for `user.role`, compare the
    enum class instead of the value, so a role check was silently false.
    """
    assert User._meta.get_field("role").choices == UserRole.choices
    assert not hasattr(User, "Role")


@pytest.mark.parametrize(
    ("role", "store", "staff", "admin"),
    [
        (UserRole.BENEFICIARY, False, False, False),
        (UserRole.STORE_STAFF, True, False, False),
        (UserRole.STORE_MANAGER, True, False, False),
        (UserRole.INTAKE_WORKER, False, True, False),
        (UserRole.ADMIN, False, True, True),
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
    assert all(isinstance(role, UserRole) for role in (*STORE_ROLES, *STAFF_ROLES))


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
