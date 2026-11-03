# AI contribution: 50% or more AI-generated
"""US-12 POST /api/partner-applications/: public form, errors, limits, schema."""

import json
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils import translation
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.categories.tests.factories import CategoryFactory
from modules.stores.api.views import _without_port
from modules.stores.models import ApplicationStatus, PartnerApplication
from modules.stores.tests.factories import PartnerApplicationFactory, StoreFactory

URL = "/api/partner-applications/"
ROLES = ("beneficiary", "store_staff", "store_manager", "intake_worker", "admin")
NAME_ERROR = (
    "Enter a name of 1 to 100 letters; spaces, apostrophes and hyphens are allowed."
)


def payload(**overrides: Any) -> dict[str, Any]:
    """What the Become a partner page sends; generated data only."""
    data: dict[str, Any] = {
        "business_name": "Boulangerie Exemple",
        "business_type": "bakery",
        "neq": "",
        "website": "exemple.test",
        "street_number": "1234A",
        "street_name": "rue Exemple",
        "unit": "",
        "city": "Montréal",
        "postal_code": "h2x1y4",
        "contact_first_name": "Marie-Ève",
        "contact_last_name": "D’Exemple",
        "contact_role": "",
        "contact_email": "Owner@Example.test",
        "contact_phone": "+15145550123",
        "goods_categories": ["bakery", "dairy_eggs", "bakery"],
        "expected_frequency": "weekly",
        "opening_hours": "lun-ven 9 h-18 h",
        "message": "",
        "consent_contact": True,
    }
    return {**data, **overrides}


@pytest.fixture(autouse=True)
def setup(db: Any) -> None:
    cache.clear()  # rate-limit counts must not leak between tests
    CategoryFactory(code="bakery")
    CategoryFactory(code="dairy_eggs")


def post(
    client: APIClient, data: dict[str, Any], language: str = "en", **extra: Any
) -> Any:
    return client.post(URL, data, format="json", HTTP_ACCEPT_LANGUAGE=language, **extra)


def test_submission_is_saved_and_confirmed_by_email(
    django_capture_on_commit_callbacks: Any,
) -> None:
    # rule: AC1 + AC2 main path through the API, the database and the email
    with django_capture_on_commit_callbacks(execute=True):
        response = post(APIClient(), payload())
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "status", "created_at"}
    assert body["status"] == "submitted"
    assert body["created_at"].endswith("Z")

    application = PartnerApplication.objects.get(pk=body["id"])
    assert application.contact_email == "owner@example.test"
    assert application.postal_code == "H2X 1Y4"
    assert application.website == "https://exemple.test"
    assert application.goods_categories == ["bakery", "dairy_eggs"]
    assert application.neq is None and application.unit is None
    assert application.language == "en"
    assert [message.subject for message in mail.outbox] == [
        "We received your partner application"
    ]
    assert mail.outbox[0].to == ["owner@example.test"]


@pytest.mark.parametrize("role", ROLES)
def test_every_role_may_apply(role: str) -> None:
    # Public endpoint: allowed for anonymous visitors and every signed-in role.
    store = StoreFactory() if role.startswith("store_") else None
    client = APIClient()
    client.force_authenticate(UserFactory(role=role, store=store))
    assert post(client, payload()).status_code == 201


def test_anonymous_visitor_may_apply_without_an_account() -> None:
    users_before = get_user_model()._default_manager.count()
    client = APIClient(enforce_csrf_checks=True)
    assert post(client, payload()).status_code == 201
    assert get_user_model()._default_manager.count() == users_before


def test_signed_in_session_without_csrf_token_is_refused() -> None:
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(UserFactory())
    response = post(client, payload())
    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert not PartnerApplication.objects.exists()


@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_only_post_is_allowed(method: str) -> None:
    client = APIClient()
    client.force_authenticate(UserFactory(role="admin"))
    response = getattr(client, method)(URL)
    assert response.status_code == 405
    assert response.json()["code"] == "method_not_allowed"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("business_name", "B", "Enter the business name (2 to 150 characters)."),
        ("business_name", "B" * 151, "Enter the business name (2 to 150 characters)."),
        ("business_type", "casino", "Choose a business type."),
        (
            "neq",
            "123456789",
            "The NEQ has exactly 10 digits. You can also leave this field empty.",
        ),
        (
            "neq",
            "12345678901",
            "The NEQ has exactly 10 digits. You can also leave this field empty.",
        ),
        ("website", "not a site", "Enter a web address like example.ca."),
        ("street_number", "rue", "Enter a street number like 1234 or 1234A."),
        ("street_name", "R", "Enter the street (2 to 120 characters)."),
        ("unit", "A" * 11, "Enter at most 10 characters."),
        ("postal_code", "12345", "Enter a postal code like H2X 1Y4."),
        ("contact_first_name", "Al3x", NAME_ERROR),
        ("contact_last_name", "", NAME_ERROR),
        ("contact_role", "R" * 101, "Enter at most 100 characters."),
        ("contact_email", "owner-at-example", "Enter an email like name@example.ca."),
        (
            "contact_phone",
            "5145550123",
            "Enter a 10-digit number, for example (514) 555-0123.",
        ),
        (
            "contact_phone",
            "+11235550123",
            "Enter a 10-digit number, for example (514) 555-0123.",
        ),
        ("goods_categories", [], "Choose at least one type of goods."),
        ("goods_categories", ["unknown_code"], "Choose types of goods from the list."),
        ("expected_frequency", "yearly", "Choose how often you expect to donate."),
        (
            "opening_hours",
            "h" * 301,
            "Enter the opening hours (at most 300 characters).",
        ),
        ("message", "m" * 1001, "Enter at most 1,000 characters."),
        ("consent_contact", False, "Tick this box to send the application."),
    ],
)
def test_each_field_is_validated_with_a_clear_message(
    field: str, value: Any, message: str
) -> None:
    # rule: AC1, each field validated with a clear message
    response = post(APIClient(), payload(**{field: value}))
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["fields"] == {field: [message]}
    assert not PartnerApplication.objects.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("business_name", "Bo"),
        ("business_name", "B" * 150),
        ("neq", "1234567890"),
        ("street_number", "12 1/2"),
        ("contact_last_name", "D" * 100),
        ("opening_hours", "h" * 300),
        ("message", "m" * 1000),
    ],
)
def test_boundary_values_are_accepted(field: str, value: str) -> None:
    assert post(APIClient(), payload(**{field: value})).status_code == 201


def test_missing_required_fields_are_all_reported() -> None:
    response = post(APIClient(), {})
    assert response.status_code == 400
    fields = response.json()["fields"]
    optional = {"neq", "website", "unit", "contact_role", "message"}
    assert set(fields) == set(payload()) - optional


def test_errors_use_the_requested_language() -> None:
    response = post(APIClient(), payload(consent_contact=False), language="fr")
    body = response.json()
    assert body["message"] == "Vérifiez les champs indiqués."
    assert body["fields"] == {
        "consent_contact": ["Cochez cette case pour envoyer la demande."]
    }


@pytest.mark.parametrize("field", ["status", "decided_by", "decision_reason", "id"])
def test_server_owned_fields_cannot_be_submitted(field: str) -> None:
    response = post(APIClient(), payload(**{field: "approved"}))
    assert response.status_code == 400
    assert response.json()["fields"] == {field: ["This field cannot be submitted."]}


def test_open_application_with_same_email_returns_409() -> None:
    # rule: BR-PARTNER-01 (AC3), an open application cannot be submitted twice
    PartnerApplicationFactory(contact_email="owner@example.test")
    response = post(APIClient(), payload(contact_email="OWNER@example.test"))
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "application_already_open"
    assert body["message"].startswith("An application is already in progress.")
    assert "owner@example.test" in body["message"]
    assert body["fields"] == {}
    assert PartnerApplication.objects.count() == 1


def test_already_open_message_is_translated() -> None:
    # rule: BR-PARTNER-01, explain the duplicate refusal in the request's language
    PartnerApplicationFactory(contact_email="owner@example.test")
    response = post(APIClient(), payload(), language="fr")
    assert response.json()["message"].startswith("Une demande est déjà en cours.")


def test_decided_application_lets_the_contact_apply_again() -> None:
    # rule: BR-PARTNER-01, a decided application does not block another submission
    PartnerApplicationFactory(
        contact_email="owner@example.test",
        status=ApplicationStatus.REJECTED,
        decision_reason="Generated reason",
    )
    assert post(APIClient(), payload()).status_code == 201


def test_sixth_request_in_an_hour_from_one_ip_is_throttled() -> None:
    # rule: BR-PARTNER-02 (SEC-04), 5 requests per hour per client IP
    client = APIClient()
    for index in range(5):
        email = f"owner-{index}@example.test"
        response = post(client, payload(contact_email=email), REMOTE_ADDR="10.0.0.1")
        assert response.status_code == 201
    response = post(client, payload(), REMOTE_ADDR="10.0.0.1")
    assert response.status_code == 429
    assert response.json()["code"] == "throttled"
    other_ip = post(client, payload(), REMOTE_ADDR="10.0.0.2")
    assert other_ip.status_code == 201


def test_rate_limit_counts_rejected_requests_too() -> None:
    # rule: BR-PARTNER-02, validation refusals consume the allowance
    client = APIClient()
    for _ in range(5):
        post(client, {}, REMOTE_ADDR="10.0.0.1")
    assert post(client, payload(), REMOTE_ADDR="10.0.0.1").status_code == 429


def test_forged_forwarded_header_does_not_reset_the_limit() -> None:
    # rule: BR-PARTNER-02, untrusted forwarded headers cannot change the client IP
    client = APIClient()
    for index in range(5):
        post(client, {}, REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR=f"9.9.9.{index}")
    response = post(
        client, payload(), REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="9.9.9.99"
    )
    assert response.status_code == 429


def test_signing_in_does_not_reset_the_ip_limit() -> None:
    # rule: BR-PARTNER-02, authentication does not create another allowance
    client = APIClient()
    for _ in range(5):
        post(client, {}, REMOTE_ADDR="10.0.0.1")
    client.force_authenticate(UserFactory())
    assert post(client, payload(), REMOTE_ADDR="10.0.0.1").status_code == 429


def test_signed_in_users_on_one_ip_share_the_limit() -> None:
    # rule: BR-PARTNER-02, accounts on one IP share the allowance
    first, second, third = APIClient(), APIClient(), APIClient()
    for client in (first, second, third):
        client.force_authenticate(UserFactory())
    for index, client in enumerate((first, first, first, second, second)):
        email = f"owner-{index}@example.test"
        response = post(client, payload(contact_email=email), REMOTE_ADDR="10.0.0.1")
        assert response.status_code == 201
    assert post(third, payload(), REMOTE_ADDR="10.0.0.1").status_code == 429


def test_port_in_forwarded_address_does_not_reset_the_limit(settings: Any) -> None:
    # rule: BR-PARTNER-02, changing the connection port does not reset the allowance
    # Behind one proxy, the client address may arrive as "ip:port", and the
    # port changes with every connection.
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}
    client = APIClient()
    for index in range(5):
        post(
            client,
            {},
            REMOTE_ADDR="10.0.0.9",
            HTTP_X_FORWARDED_FOR=f"9.9.9.9:{1000 + index}",
        )
    blocked = post(
        client, payload(), REMOTE_ADDR="10.0.0.9", HTTP_X_FORWARDED_FOR="9.9.9.9:2222"
    )
    assert blocked.status_code == 429
    other_client = post(
        client, payload(), REMOTE_ADDR="10.0.0.9", HTTP_X_FORWARDED_FOR="9.9.9.8:1111"
    )
    assert other_client.status_code == 201


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ("203.0.113.5", "203.0.113.5"),
        ("203.0.113.5:54321", "203.0.113.5"),
        ("2001:db8::1", "2001:db8::1"),
        ("[2001:db8::1]:54321", "2001:db8::1"),
    ],
)
def test_throttle_ignores_the_port_of_a_client_address(
    address: str, expected: str
) -> None:
    # rule: BR-PARTNER-02, normalize IPv4 and IPv6 addresses without their ports
    assert _without_port(address) == expected


def test_schema_documents_the_public_endpoint(client: Client) -> None:
    with translation.override("en"):
        response = client.get(
            reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json"
        )
    schema = json.loads(response.content)
    operation = schema["paths"][URL]["post"]
    assert operation["operationId"] == "partner_applications_create"
    assert set(operation["responses"]) == {"201", "400", "409", "429"}
    assert set(schema["paths"][URL]) == {"post"}
    submitted = schema["components"]["schemas"]["SubmittedPartnerApplication"]
    assert set(submitted["properties"]) == {"id", "status", "created_at"}
