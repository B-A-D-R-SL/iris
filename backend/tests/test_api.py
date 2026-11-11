# AI contribution: 50% or more AI-generated
"""SEC-01/04/05: production documentation access and real throttled API calls."""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from modules.accounts.models import User
from modules.accounts.tests.factories import UserFactory
from modules.categories.tests.factories import CategoryFactory
from modules.stores.tests.factories import StoreFactory
from tests.security_helpers import production_api

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def clean_quotas():
    """A real shared cache is used, with isolated counters for each scenario."""
    cache.clear()
    yield
    cache.clear()


def generated_user(role=User.Role.BENEFICIARY, **overrides):
    """Generate database-valid store users as well as the other application roles."""
    store = (
        StoreFactory()
        if role in (User.Role.STORE_MANAGER, User.Role.STORE_STAFF)
        else None
    )
    return UserFactory(role=role, store=store, **overrides)


@pytest.mark.parametrize("role", User.Role.values)
def test_production_docs_allow_only_the_active_application_admin(role):
    """Both real documentation routes enforce the Iris role, without is_staff."""
    user = generated_user(role, is_staff=False)
    result = production_api(
        """
from modules.accounts.models import User
client.force_login(User.objects.get(pk=sys.argv[1]))
responses = [client.get(url, secure=True) for url in ['/api/schema/', '/api/docs/']]
print(json.dumps([response.status_code for response in responses]))
""",
        str(user.pk),
    )
    assert result == ([200, 200] if role == User.Role.ADMIN else [403, 403])


def test_django_staff_flag_does_not_grant_production_documentation_access():
    """SEC-05: Django admin-site access cannot replace the Iris admin role."""
    user = generated_user(User.Role.INTAKE_WORKER, is_staff=True)
    result = production_api(
        """
from modules.accounts.models import User
client.force_login(User.objects.get(pk=sys.argv[1]))
print(json.dumps([client.get(url, secure=True).status_code
                  for url in ['/api/schema/', '/api/docs/']]))
""",
        str(user.pk),
    )
    assert result == [403, 403]


@pytest.mark.parametrize("inactive_admin", [False, True])
def test_production_docs_refuse_anonymous_and_inactive_admin(inactive_admin):
    """Possessing an inactive account cannot provide access to either document."""
    identifier = (
        str(generated_user(User.Role.ADMIN, is_active=False).pk)
        if inactive_admin
        else ""
    )
    result = production_api(
        """
if sys.argv[1]:
    from modules.accounts.models import User
    client.force_login(User.objects.get(pk=sys.argv[1]))
print(json.dumps([client.get(url, secure=True).status_code
                  for url in ['/api/schema/', '/api/docs/']]))
""",
        identifier,
    )
    assert result == [401, 401]


def test_test_settings_keep_documentation_accessible():
    """Development-schema generation remains usable without signing in."""
    client = APIClient()
    assert client.get("/api/schema/").status_code == 200
    assert client.get("/api/docs/").status_code == 200


def test_anonymous_quota_boundary_queries_the_database_and_keeps_retry_header():
    """SEC-04: allow exactly the quota, then refuse before another database read."""
    category = CategoryFactory()
    result = production_api(
        """
responses = [client.get('/api/categories/', secure=True) for _ in range(3)]
print(json.dumps({'statuses': [response.status_code for response in responses],
                  'categories': responses[0].json(), 'error': responses[2].json(),
                  'retry': responses[2].headers['Retry-After']}))
"""
    )
    assert result["statuses"] == [200, 200, 429]
    assert result["categories"] == [
        {
            "code": category.code,
            "name_fr": category.name_fr,
            "name_en": category.name_en,
            "is_food": category.is_food,
            "default_value_cents": category.default_value_cents,
        }
    ]
    assert result["error"] == {
        "code": "throttled",
        "message": "Requête ralentie.",
        "fields": {},
    }
    assert result["retry"] == "60"


@pytest.mark.parametrize(
    ("language", "message"),
    [("en", "Request was throttled."), ("fr", "Requête ralentie.")],
)
def test_throttled_responses_are_translated(language, message):
    """SEC-04: the standard 429 envelope uses the request's supported language."""
    result = production_api(
        """
for _ in range(2):
    client.get('/api/categories/', secure=True, HTTP_ACCEPT_LANGUAGE=sys.argv[1])
response = client.get('/api/categories/', secure=True, HTTP_ACCEPT_LANGUAGE=sys.argv[1])
print(json.dumps({'status': response.status_code, 'error': response.json()}))
""",
        language,
    )
    assert result == {
        "status": 429,
        "error": {"code": "throttled", "message": message, "fields": {}},
    }


def test_authenticated_accounts_have_separate_quotas_shared_across_ips():
    """SEC-04: changing networks does not reset an account, or block another user."""
    first, second = generated_user(), generated_user()
    result = production_api(
        """
from modules.accounts.models import User
client.force_login(User.objects.get(pk=sys.argv[1]))
responses = [client.get('/api/categories/', secure=True, REMOTE_ADDR=f'192.0.2.{index}')
             for index in range(1, 5)]
client.force_login(User.objects.get(pk=sys.argv[2]))
responses.append(client.get('/api/categories/', secure=True, REMOTE_ADDR='192.0.2.4'))
print(json.dumps([response.status_code for response in responses]))
""",
        str(first.pk),
        str(second.pk),
    )
    assert result == [200, 200, 200, 429, 200]


def test_anonymous_clients_have_independent_ip_quotas():
    """SEC-04: one visitor exhausting a quota does not block another address."""
    result = production_api(
        """
responses = [client.get('/api/categories/', secure=True, REMOTE_ADDR='192.0.2.1')
             for _ in range(3)]
responses.append(client.get('/api/categories/', secure=True, REMOTE_ADDR='192.0.2.2'))
print(json.dumps([response.status_code for response in responses]))
"""
    )
    assert result == [200, 200, 429, 200]


def test_spoofing_forwarded_addresses_does_not_reset_an_untrusted_client():
    """SEC-04: with no trusted proxy, forwarded headers cannot choose the quota."""
    result = production_api(
        """
responses = [client.get('/api/categories/', secure=True, REMOTE_ADDR='192.0.2.1',
                        HTTP_X_FORWARDED_FOR=f'198.51.100.{index}')
             for index in range(3)]
print(json.dumps([response.status_code for response in responses]))
"""
    )
    assert result == [200, 200, 429]


@pytest.mark.parametrize("address", ["198.51.100.8", "[2001:db8::8]"])
def test_trusted_proxy_ports_cannot_reset_the_quota(address):
    """SEC-04: Azure's forwarded IPv4/IPv6 connection ports do not change identity."""
    result = production_api(
        """
responses = [client.get('/api/categories/', secure=True, REMOTE_ADDR='192.0.2.9',
                        HTTP_X_FORWARDED_FOR=f'{sys.argv[1]}:{1000 + index}')
             for index in range(3)]
print(json.dumps([response.status_code for response in responses]))
""",
        address,
        proxies=1,
    )
    assert result == [200, 200, 429]


@pytest.mark.parametrize("signed_in", [False, True])
def test_quota_reopens_at_the_exact_window_boundary(signed_in):
    """SEC-04: advance only DRF's clock; the real cache and admission logic run."""
    user_id = str(generated_user().pk) if signed_in else ""
    result = production_api(
        """
if sys.argv[1]:
    from modules.accounts.models import User
    client.force_login(User.objects.get(pk=sys.argv[1]))
count = 3 if sys.argv[1] else 2
responses = [client.get('/api/categories/', secure=True) for _ in range(count + 1)]
clock['now'] += 60
responses.append(client.get('/api/categories/', secure=True))
print(json.dumps([response.status_code for response in responses]))
""",
        user_id,
    )
    assert result == ([200, 200, 200, 429, 200] if signed_in else [200, 200, 429, 200])


def test_invitation_validation_failures_are_rate_limited_with_the_module_envelope():
    """SEC-04: the public password form inherits production throttles."""
    result = production_api(
        """
responses = [client.post('/api/invitations/accept/', {}, format='json', secure=True)
             for _ in range(3)]
print(json.dumps({'statuses': [response.status_code for response in responses],
                  'error': responses[-1].json(), 'retry': responses[-1]['Retry-After']}))
"""
    )
    assert result["statuses"] == [400, 400, 429]
    assert result["error"]["code"] == "throttled"
    assert set(result["error"]) == {"code", "message", "fields"}
    assert result["error"]["fields"] == {}
    assert result["retry"] == "60"


def test_partner_applications_keep_their_stricter_shared_hourly_limit():
    """BR-PARTNER-02: its explicit IP throttle survives global default classes."""
    result = production_api(
        """
responses = [client.post('/api/partner-applications/', {}, format='json', secure=True)
             for _ in range(6)]
print(json.dumps({'statuses': [response.status_code for response in responses],
                  'error': responses[-1].json()}))
"""
    )
    assert result["statuses"] == [400, 400, 400, 400, 400, 429]
    assert result["error"]["code"] == "throttled"
