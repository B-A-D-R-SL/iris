# AI contribution: 50% or more AI-generated
"""The shared handler adapts rate refusals without changing other DRF contracts."""

import pytest
from django.utils import translation
from rest_framework.exceptions import Throttled, ValidationError

from iris.api import exception_handler
from iris.throttling import _without_port


@pytest.mark.parametrize(
    ("language", "message"),
    [("en", "Request was throttled."), ("fr", "Requête ralentie.")],
)
def test_throttled_detail_stays_private_and_retry_after_is_preserved(language, message):
    """Only the approved DRF translation is exposed, never arbitrary exception text."""
    with translation.override(language):
        response = exception_handler(Throttled(wait=17, detail="private detail"), {})
    assert response is not None
    assert response.status_code == 429
    assert response["Retry-After"] == "17"
    assert response.data == {"code": "throttled", "message": message, "fields": {}}


def test_other_drf_errors_retain_their_existing_format():
    """The shared fallback does not rewrite existing validation responses."""
    response = exception_handler(ValidationError({"name": ["Required"]}), {})
    assert response is not None
    assert response.status_code == 400
    assert response.data == {"name": ["Required"]}


def test_unhandled_errors_are_delegated_to_django():
    """Unexpected failures are not swallowed by the throttle adapter."""
    assert exception_handler(ValueError("unhandled"), {}) is None


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ("192.0.2.1", "192.0.2.1"),
        ("192.0.2.1:54321", "192.0.2.1"),
        ("2001:db8::1", "2001:db8::1"),
        ("[2001:db8::1]:54321", "2001:db8::1"),
    ],
)
def test_client_identity_ignores_only_transport_ports(address, expected):
    """IPv6 address segments remain intact when no bracketed port is present."""
    assert _without_port(address) == expected
