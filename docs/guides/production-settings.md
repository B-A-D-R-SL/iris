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
| `MAILER_ADAPTER` | `azure` for ACS staging; `smtp` for SMTP delivery. The test-only `fake` is refused |
| `DEFAULT_FROM_EMAIL` | Valid public sender address; for ACS use the connected domain's exact verified MailFrom address |
| `PUBLIC_APP_ORIGIN` | Public HTTPS application origin, with no credentials, path, query or fragment; local/private addresses are refused in production |
| `AZURE_COMMUNICATION_CONNECTION_STRING` | Required secret when `MAILER_ADAPTER=azure` |
| `AZURE_EMAIL_SEND_TIMEOUT_SECONDS` | Positive finite send/polling timeout; default `30` seconds |
| `EMAIL_BACKEND` | When selecting SMTP, use a real delivery backend; console, dummy, file-based and in-memory backends are refused |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | SMTP-provider configuration; independent of the ACS adapter |
| `SMTP_TIMEOUT` | Positive finite SMTP transport timeout; default `10` seconds |
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
deprecated `EMAIL_BACKEND` setting internally. `MAILER_ADAPTER` chooses the
application transport independently: the Azure adapter calls the ACS email SDK,
whereas SMTP uses Django's configured mailer.

## Email delivery (US-57)

The web process records delivery metadata and queues only after the business
transaction commits. The Procrastinate worker selects the adapter, renders the
captured recipient language and sends the message. Run migrations and seed the
`notifications` RuleSet before enabling producers. The deployed worker must use
the same production settings, database, adapter, sender and public origin as the
web process; a running web process alone does not send queued email.

Partner receipt, approval, rejection and operator reissue all use this shared
pipeline. Invitation links use `PUBLIC_APP_ORIGIN`, as do the other email
templates; no separate `FRONTEND_URL` is required. A successful reissue queues a
new link and invalidates older unaccepted invitations. Worker preflight refuses
already invalid invitation jobs before transport, while an in-flight message
cannot be recalled. Inspect EmailLog for outcomes rather than the former inline
partner-decision email-failure event.

The supplied staging resources are `iris-stg-email-ar1` and its
`AzureManagedDomain`, plus `iris-stg-acs-ar1`. User-provided screenshots show
`canada` as the data location on the Communication Service Overview and Email
Communication Service Properties, and the domain as Active. Ammar reports
successful Azure portal Try Email delivery to a university inbox. These are
screenshot-observed configuration and reported provider-side delivery evidence;
we have not performed a live Iris-to-ACS worker send. SET-17 must supply the exact
domain MailFrom address and runtime connection-string configuration when the
application and worker are deployed. The current Azure adapter uses that
connection string; direct Entra authentication to ACS is not implemented.

For the SET-17 handoff, configure these values on both the web application and
worker. Preserve the deployment's database, Django secret and allowed hosts from
the configuration table above.

| Runtime setting | SET-17 value |
| --- | --- |
| `MAILER_ADAPTER` | `azure` |
| `DEFAULT_FROM_EMAIL` | Exact MailFrom address from `iris-stg-email-ar1/AzureManagedDomain` |
| `PUBLIC_APP_ORIGIN` | The deployed Iris frontend's public HTTPS origin |
| `AZURE_COMMUNICATION_CONNECTION_STRING` | Resolved value of Key Vault secret `acs-connection-string` |
| `AZURE_EMAIL_SEND_TIMEOUT_SECONDS` | `30` by default |

For the current vault, the App Service setting can use
`@Microsoft.KeyVault(SecretUri=https://iris-stg-kv-ar1.vault.azure.net/secrets/acs-connection-string)`.
Confirm successful reference resolution. The URI/reference itself is not the
connection-string value, and local Docker Compose does not resolve App Service
Key Vault references. The root `.env` controls local Compose interpolation;
`backend/.env` is for standalone Django. Compose explicitly selects SMTP/Mailpit,
so local email verification does not require an ACS secret.

US-57 implementation can be reviewed with local worker/Mailpit verification and
mocked ACS adapter tests while SET-17 hosting is pending. Once staging is deployed,
verify the resolved configuration and run the application-to-ACS send together
with SET-17. The PR must state this verification boundary explicitly.

Inject the ACS secret through deployment configuration. With App Service,
[Key Vault references](https://learn.microsoft.com/en-us/azure/app-service/app-service-key-vault-references)
can resolve it using the workload's managed identity. The original supplied
inventory lists `iris-stg-kv-ar1` in West US 2; moving/replacing it in Canada East
is planned. This implementation does not move the vault or provision hosting.
Azure's `Global` resource location is separate from the communication resources'
configured data geography. The supplied screenshots show matching `canada` data
locations; preserve compatible geographies in the SET-17 deployment. Canadian
data location does not establish that every network transit hop stays in Canada.
See [domain connection
requirements](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/email/connect-email-communication-resource).

Defaults are three retries after 60, 300 and 900 seconds, captured from the active
notification rule for each send. Terminal email job payloads become eligible for
cleanup after 24 hours by default, with an hourly maintenance task. Normal removal
therefore occurs after approximately 24–25 hours while the worker is healthy;
pending/retrying jobs remain. Monitor worker/cleanup failures, and review the
[notification module runbook](../../backend/modules/notifications/README.md)
for the legacy-job rollout and privacy boundary around temporary one-use links.

Production configuration checks do not contact Azure. A separate staging smoke
send using synthetic content and a controlled recipient must verify domain
linkage, permissions, sender and worker operation. `EmailLog.status=sent` means
provider acceptance, not inbox delivery or bounce detection. Failed-email staff
screens and provider delivery events remain US-61.

Microsoft has announced ACS Email retirement on September 30, 2028. Track the
replacement separately; the adapter boundary keeps that change outside business
callers and templates. See [Microsoft's retirement guide](https://learn.microsoft.com/en-us/azure/communication-services/acs-retirement-and-breaking-changes-guide).

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
