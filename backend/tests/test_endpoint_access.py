# AI contribution: 50% or more AI-generated
"""SEC-05: every API endpoint denies access by default (FIX-07).

The test walks the URL resolver, so a new endpoint is checked as soon as it is
routed. Each DRF endpoint must appear in ``ACCESS`` (roles allowed through the
permission check) and, if it is open without signing in, in ``PUBLIC`` with a
reason. A route with no entry fails ``test_every_endpoint_has_an_access_entry``.

How to add an endpoint: add ``"<url name>": {roles}`` to ``ACCESS``. Add it to
``PUBLIC`` only if anonymous visitors must reach it, and say why.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import pytest
from django.urls import URLPattern, URLResolver, get_resolver, path
from rest_framework.test import APIClient
from rest_framework.views import APIView

from modules.accounts.models import User
from modules.stores.tests.factories import StoreFactory

BENEFICIARY = User.Role.BENEFICIARY.value
STORE_STAFF = User.Role.STORE_STAFF.value
STORE_MANAGER = User.Role.STORE_MANAGER.value
INTAKE_WORKER = User.Role.INTAKE_WORKER.value
ADMIN = User.Role.ADMIN.value
EVERY_ROLE = frozenset(User.Role.values)
STORE_ROLES = frozenset({STORE_STAFF, STORE_MANAGER})

# Roles that get past the permission check, per URL name (business-rules.md matrix).
ACCESS: dict[str, frozenset[str]] = {
    "current-user": EVERY_ROLE,
    "invitation-accept": EVERY_ROLE,
    "staff-households-create": frozenset({INTAKE_WORKER, ADMIN}),
    "staff-households-detail": frozenset({INTAKE_WORKER, ADMIN}),
    "staff-households-submit": frozenset({INTAKE_WORKER, ADMIN}),
    "categories-list": EVERY_ROLE,
    "audit-search": frozenset({ADMIN}),
    "staff-categories": frozenset({ADMIN}),
    "staff-category-detail": frozenset({ADMIN}),
    "store-listing-create": STORE_ROLES,
    "store-listing-categories": STORE_ROLES,
    "listings-browse": frozenset({BENEFICIARY}),
    "partner-application-create": EVERY_ROLE,
    "schema": EVERY_ROLE,
    "swagger-ui": EVERY_ROLE,
}

# DRF endpoints open to anonymous visitors, each with the reason.
PUBLIC: dict[str, str] = {
    "invitation-accept": "The invited person has no account until they accept (US-04).",
    "categories-list": "Public reference data shown before sign-in (SET-12).",
    "partner-application-create": "Businesses apply before they have an account "
    "(US-12); rate-limited by SEC-04.",
    "schema": "OpenAPI schema for the generated TypeScript client (SET-15).",
    "swagger-ui": "Documentation page for the same OpenAPI schema (SET-15).",
}

# Plain Django views under /api/, matched by path prefix, each with the reason.
NON_DRF: dict[str, str] = {
    "api/health/": "Availability probe for Docker and App Service; returns no data.",
    "api/auth/": "django-allauth headless sign-in, session and password routes; "
    "allauth enforces its own authentication.",
}

# Sample values for path converters, so every route can be called.
SAMPLE_PATH_VALUES = {"uuid": lambda: str(uuid4()), "int": lambda: "1"}
SAMPLE_TEXT = "sample"
SKIPPED_METHODS = frozenset({"options", "head", "trace"})
BODY_METHODS = frozenset({"post", "put", "patch"})


@dataclass(frozen=True)
class Endpoint:
    """One routed API view with the methods it implements."""

    name: str
    route: str
    view: type[APIView] | None
    methods: tuple[str, ...]

    def url(self) -> str:
        """Fill each path converter with a sample value."""
        parts = []
        rest = self.route
        while "<" in rest:
            before, _, after = rest.partition("<")
            spec, _, rest = after.partition(">")
            converter = spec.split(":")[0] if ":" in spec else "str"
            make = SAMPLE_PATH_VALUES.get(converter, lambda: SAMPLE_TEXT)
            parts.extend([before, make()])
        parts.append(rest)
        return "/" + "".join(parts)


def _walk(patterns: list[Any], prefix: str = "") -> Iterator[tuple[str, URLPattern]]:
    """Yield (route, pattern) for every leaf URL pattern."""
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from _walk(pattern.url_patterns, prefix + str(pattern.pattern))
        else:
            yield prefix + str(pattern.pattern), pattern


def _view_class(pattern: URLPattern) -> type | None:
    """Return the class behind a view callback, or None for a plain function."""
    callback = pattern.callback
    return getattr(callback, "cls", None) or getattr(callback, "view_class", None)


def _methods(view: type[APIView]) -> tuple[str, ...]:
    """The HTTP methods the view both allows and implements."""
    return tuple(
        method
        for method in view.http_method_names
        if method not in SKIPPED_METHODS and hasattr(view, method)
    )


def _api_endpoints(patterns: list[Any] | None = None) -> list[Endpoint]:
    """Every routed view under /api/, DRF or not (project URLs by default)."""
    if patterns is None:
        patterns = get_resolver().url_patterns
    endpoints = []
    for route, pattern in _walk(patterns):
        if not route.startswith("api/"):
            continue
        view = _view_class(pattern)
        drf_view = view if view and issubclass(view, APIView) else None
        methods = _methods(drf_view) if drf_view else ()
        endpoints.append(Endpoint(pattern.name or "", route, drf_view, methods))
    return endpoints


ENDPOINTS = _api_endpoints()
DRF_ENDPOINTS = [endpoint for endpoint in ENDPOINTS if endpoint.view is not None]
PROTECTED_CALLS = [
    pytest.param(endpoint, method, id=f"{method.upper()} {endpoint.name}")
    for endpoint in DRF_ENDPOINTS
    if endpoint.name not in PUBLIC
    for method in endpoint.methods
]
ROLE_CALLS = [
    pytest.param(endpoint, method, role, id=f"{method.upper()} {endpoint.name} {role}")
    for endpoint in DRF_ENDPOINTS
    for method in endpoint.methods
    for role in sorted(EVERY_ROLE)
]


def _call(client: APIClient, endpoint: Endpoint, method: str) -> Any:
    """Send one request; write methods get an empty JSON body."""
    request = getattr(client, method)
    if method in BODY_METHODS:
        return request(endpoint.url(), {}, format="json")
    return request(endpoint.url())


@pytest.fixture
def permission_denials(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record each time DRF's permission check turns a request away."""
    denials: list[str] = []
    original = APIView.permission_denied

    def spy(self: APIView, request: Any, message: Any = None, code: Any = None):
        denials.append(type(self).__name__)
        return original(self, request, message=message, code=code)

    monkeypatch.setattr(APIView, "permission_denied", spy)
    return denials


def _user_with_role(role: str) -> User:
    """An active user with the role; store roles get the store they need."""
    store = StoreFactory() if role in STORE_ROLES else None
    return User.objects.create_user(
        email=f"{role}-{uuid4().hex}@example.test",
        password="local-test-password",
        role=role,
        store=store,
    )


def _missing_entries(endpoints: list[Endpoint]) -> list[str]:
    """URL names of DRF endpoints that ACCESS does not cover."""
    return sorted(
        {endpoint.name for endpoint in endpoints if endpoint.view} - set(ACCESS)
    )


def test_every_endpoint_has_an_access_entry() -> None:
    """A routed DRF endpoint without an ACCESS entry fails, and so does a stale one."""
    names = [endpoint.name for endpoint in DRF_ENDPOINTS]
    assert all(names), "Every DRF route needs a URL name so it can be listed."
    assert len(names) == len(set(names)), "DRF URL names must be unique."

    missing = _missing_entries(DRF_ENDPOINTS)
    stale = sorted(set(ACCESS) - set(names))
    assert not missing, (
        f"New endpoint(s) {missing} have no entry in ACCESS in "
        "backend/tests/test_endpoint_access.py. Add the roles allowed to call "
        "each one (and a PUBLIC reason if anonymous visitors may call it)."
    )
    assert not stale, f"ACCESS lists routes that no longer exist: {stale}"
    assert set(PUBLIC) <= set(ACCESS), "Every PUBLIC entry also needs an ACCESS entry."
    assert all(ACCESS.values()), "An ACCESS entry must allow at least one role."


def test_a_new_unlisted_endpoint_is_reported() -> None:
    """The check catches a route added without an ACCESS entry."""

    class NewView(APIView):
        def get(self, request: Any) -> None:
            """Stand-in handler; never called."""

    patterns = [path("api/new-things/", NewView.as_view(), name="new-things")]

    assert _missing_entries(_api_endpoints(patterns)) == ["new-things"]


def test_every_plain_api_view_is_listed() -> None:
    """A non-DRF view under /api/ must match a NON_DRF prefix with a reason."""
    unknown = sorted(
        endpoint.route
        for endpoint in ENDPOINTS
        if endpoint.view is None
        and not any(endpoint.route.startswith(prefix) for prefix in NON_DRF)
    )
    assert not unknown, (
        f"Plain Django views {unknown} skip DRF's default permissions. Use a DRF "
        "view, or add the path prefix to NON_DRF with a reason."
    )


def test_every_reason_is_written() -> None:
    """Each exception to deny-by-default explains itself."""
    assert all(reason.strip() for reason in [*PUBLIC.values(), *NON_DRF.values()])


@pytest.mark.django_db
@pytest.mark.parametrize(("endpoint", "method"), PROTECTED_CALLS)
def test_anonymous_requests_are_denied(endpoint: Endpoint, method: str) -> None:
    """Without a session, every non-public endpoint answers 401 or 403."""
    response = _call(APIClient(), endpoint, method)

    assert response.status_code in (401, 403), (
        f"{method.upper()} /{endpoint.route} answered {response.status_code} "
        "to an anonymous request."
    )


@pytest.mark.django_db
@pytest.mark.parametrize(("endpoint", "method", "role"), ROLE_CALLS)
def test_roles_match_the_access_table(
    endpoint: Endpoint, method: str, role: str, permission_denials: list[str]
) -> None:
    """Allowed roles pass the permission check; every other role gets 403."""
    client = APIClient()
    client.force_login(_user_with_role(role))

    response = _call(client, endpoint, method)

    label = f"{method.upper()} /{endpoint.route} as {role}"
    if role in ACCESS[endpoint.name]:
        assert not permission_denials, f"{label} was refused by the permission check."
        assert response.status_code != 401, f"{label} answered 401."
    else:
        assert response.status_code == 403, (
            f"{label} answered {response.status_code}; ACCESS does not allow {role}."
        )
