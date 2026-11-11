<!-- AI contribution: 50% or more AI-generated -->
# Production settings (FIX-04)

[FIX-04 #630](https://github.com/B-A-D-R-SL/iris/issues/630) hardens Django's
production configuration. It does not deploy Azure resources. SET-17 owns
staging deployment; FIX-17 adds the dedicated CI security gates.

## Selecting the settings

Both `iris.wsgi` and `iris.asgi` default to `iris.settings.production` when
`DJANGO_SETTINGS_MODULE` is absent. An explicit setting takes precedence.
`manage.py` defaults to local settings and Compose explicitly selects local
settings, so the existing local development command is unchanged.

The ASGI entry point still disables persistent database connections. WSGI still
checks routes during startup before accepting requests.

## Required configuration

Supply deployment values through environment configuration/Key Vault. Never put
real credentials in the repository or command examples.

| Variable | Production requirement |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | `iris.settings.production` for production management commands and workers |
| `DJANGO_SECRET_KEY` | Generated secret, at least 50 characters; `django-insecure` and `iris-insecure` prefixes are refused |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames for this deployment; `*` is refused |
| `DATABASE_URL` | PostgreSQL connection string for this environment |
| `EMAIL_BACKEND` | Real delivery backend; console, dummy, file-based and in-memory backends are refused |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | Delivery-provider configuration when using Django's SMTP backend |
| `DRF_ANON_THROTTLE_RATE` | Anonymous client limit; default `60/min` |
| `DRF_USER_THROTTLE_RATE` | Authenticated account limit; default `300/min` |
| `DRF_NUM_PROXIES` | Verified number of trusted reverse proxies; default `0` ignores forwarded client IPs |
| `ALLAUTH_TRUSTED_PROXY_COUNT` | Separate verified proxy count for allauth sign-in limits; default `0` ignores forwarded client IPs |

Throttle rates must use a positive request count and a second/minute/hour/day
period, for example `60/min`. Accepted period names are `s`, `sec`, `secs`,
`second`, `seconds`; `m`, `min`, `mins`, `minute`, `minutes`; `h`, `hr`, `hrs`,
`hour`, `hours`; and `d`, `day`, `days`. Zero, negative or malformed rates,
unsupported periods such as `month`, and negative proxy counts are refused
during production startup. Both proxy counts must be nonnegative integers.

Django 6.1 uses `MAILERS`; Iris builds its default mailer from the `EMAIL_*`
environment variables. Production validates that effective configuration.
The variable name `EMAIL_BACKEND` does not imply that Iris uses Django's
deprecated `EMAIL_BACKEND` setting internally.

## HTTPS and trusted proxies

Production sets secure session/CSRF cookies, redirects HTTP to HTTPS, and uses
`SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`.
Azure's trusted front end must strip/replace incoming `X-Forwarded-Proto` values
and provide the original connection's scheme. The application must be reached
through that trusted front end. Verify this when SET-17 supplies App Service;
the setting alone does not prove the proxy behaves correctly.

Set `DRF_NUM_PROXIES` to the actual trusted proxy count before relying on
forwarded addresses for rate limits. With `0`, client-supplied
`X-Forwarded-For` is ignored. Anonymous client identification removes a connection
port from forwarded IPv4 or bracketed IPv6 addresses so a new port does not
create a fresh allowance.

Allauth resolves sign-in client IPs independently of DRF. Production also reads
`ALLAUTH_TRUSTED_PROXY_COUNT`; configure both counts for the verified proxy chain.
With `0`, allauth uses `REMOTE_ADDR`, so users behind one proxy share its IP quota.
With a positive count, allauth selects that trusted position from the right of
`X-Forwarded-For` and normalizes connection ports. Only trusted front ends may
reach the backend, and their forwarding-header behavior must be verified in
SET-17 before enabling this trust. Synthetic tests cover zero, one and two proxy
hops; they do not establish Azure's actual topology.

## HSTS preload decision

HSTS lasts one year and includes subdomains. `SECURE_HSTS_PRELOAD` remains
`False` until the domain owner approves preload and confirms HTTPS for all
affected subdomains. Django's `security.W021` warns about this deliberate
choice, so production explicitly acknowledges only that check with a comment.
All other security/deployment warnings remain errors in the strict check below.
Revisit the acknowledgement when the domain policy is confirmed.

## API documentation and request limits

`/api/schema/` and `/api/docs/` require an authenticated, active Iris `admin`
role in production. Django's `is_staff` flag alone does not grant access.
Local/test settings keep them accessible for development; offline schema
generation through `manage.py spectacular` is unchanged.

General production DRF limits use the configured anonymous/account rates and the
shared PostgreSQL-backed cache. They are best effort under concurrency. The
partner application endpoint keeps its separate `5/hour/IP` policy shared by
anonymous and signed-in callers. Allauth's sign-in limits remain independent,
and the plain Django health probe is not DRF-throttled.

DRF checks permissions before throttling. Repeated anonymous requests to protected
routes return 401 without consuming the DRF quota; these limits do not cover all
rejected traffic. Broader ingress protection belongs at the trusted front end.

DRF HTTP 429 responses use
`{ "code": "throttled", "message": "…", "fields": {} }` and preserve
`Retry-After`. The message follows the request language. Allauth's separate
authentication responses are documented in
[authentication routing](auth-routing.md#rate-limit-responses).

## Verification before deployment

From `backend/`, with the intended environment values loaded, run:

```bash
python manage.py check --settings=iris.settings.production --deploy --fail-level WARNING
```

This checks configuration without sending mail or proving Azure connectivity.
The same check is exercised by isolated automated tests with synthetic values.
Request tests cover HTTP redirects, forwarded HTTPS, HSTS, admin documentation
access and throttling. SET-17 must also verify those behaviors on the deployed
hostname after providing the proxy and delivery configuration.
