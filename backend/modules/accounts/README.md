<!-- AI contribution: 50% or more AI-generated -->
# Accounts module

**Owner pair:** Platform & setup
**Status:** US-01 browser sign-in, sign-out, and current-user endpoint implemented; US-04 invitation acceptance backend and public page implemented; issuing workflows pending

## Responsibility

Own the accounts feature boundary within the Iris modular monolith.

## Layers

- `api/`: HTTP validation, permissions, and routing
- `domain/`: Pure Python business rules; no Django dependencies
- `services.py`: Public write operations and transactions
- `queries.py`: Public read-only operations
- `models.py`: Module-owned Django models
- `tasks.py`: Background jobs when necessary
- `tests/`: Domain, service, and API tests

## Public functions

The module owns `User` and `Invitation`, serves the authenticated `GET /api/me/`
endpoint, and enforces browser sign-in limits through its allauth adapter.
Public signup remains closed until US-02 adds email verification.
Only the browser headless client is enabled; `/api/auth/app/v1/` routes return 404.
The `AuthCache` stores failed-attempt counters in PostgreSQL so workers share
the five-attempt, 15-minute lockout. The Django admin uses
`RateLimitedAdminAuthenticationForm` and shares that limit with browser sign-in.

`queries.STORE_ROLES` and `queries.STAFF_ROLES` expose immutable groups from
`User.Role`. `queries.is_admin(user)` checks an active, authenticated admin.
The role enum lives in `roles.py` so model constraints can use these groups
without a circular import; `User.Role` remains the same public interface.

Invitation services:

- `create_invitation(email, first_name, last_name, role, store=None, invited_by=None)`
  saves the invited identity, role and optional store. It generates a token from
  32 random bytes, stores only its unique SHA-256 hash, and returns the raw token
  for the caller's email. The saved expiry uses the active
  `invitations.expires_after_days` RuleSet value (default seven days); new rule
  versions affect only future invitations. This service does not send email.
  Missing or invalid lifetime configuration raises `invitation_unavailable`.
- `accept_invitation(token, password)` validates the saved expiry, one-use token
  and configured sign-up password rules. It atomically creates a new active user
  from the invitation and records `accepted_at`. Existing active or inactive
  accounts with the same email are refused case-insensitively, without changes
  to them. Acceptance does not sign in or switch the browser session.
- `reissue_store_manager_invitation(...)` expires prior unaccepted manager
  invitations under lock and creates a new token. The active-admin caller in
  stores locks the approved application; failed issuance rolls back old-link
  expiry. The caller queues the new link through notifications.

`queries.invitation_is_usable(token, email)` exposes a public boolean for the
notification worker's invitation preflight. Accounts checks the recipient,
token, expiry, acceptance and absence of an existing account. A token valid at
preflight can still change state before an in-flight email reaches its recipient;
expired/reissued links remain invalid in Iris.

`POST /api/invitations/accept/` is public to anonymous callers and all signed-in
roles with a valid token. It accepts only `token` and `password`, returning
HTTP 200 with `{"accepted": true}`. Errors use `{code, message, fields}`:
HTTP 400 for `invitation_invalid`, `invitation_expired`, `invitation_used`,
`email_already_registered` or `validation_error`. Acceptance uses the saved
expiry rather than re-reading lifetime configuration. Signed-in requests still
require CSRF
protection (403 when refused); unsupported methods return 405. A failed request
does not create a user or consume the invitation.

Recognized invitation and password-validation codes map to approved French and
English messages. Unknown validation details receive generic feedback rather
than exception text. Password validation still uses the configured sign-up rules.

## Local setup after pulling

Apply the invitation migration and seed the invitation rules before issuing
invitations. These commands preserve existing development data:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_rules
```

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

## Accepting an invitation in the browser

The public page `/invitation/:token` (#431) asks for a password and matching
confirmation in French or English. It sends the token and password to the
acceptance API; confirmation stays in the browser. Password inputs are not
trimmed. The backend applies the complete password policy and token checks.

Successful anonymous acceptance opens `/sign-in`. A visitor who already has a
session sees confirmation and guidance to use the existing sign-out control
before signing into the new account. Acceptance never signs in or signs out
automatically. Recoverable errors preserve the entered values for retry;
expired links explain that the inviter must provide a new link.
Unexpected page failures emit only the fixed
`invitation_accept_failed_unexpectedly` event; handled API errors are not logged
again by the page.

## Later workflows

US-57 supplies shared bilingual email templates and queued delivery. The account
adapter maps allauth confirmation and password-reset messages to that service,
using the saved user language and a reviewed action URL. It rejects unsupported
allauth mail types rather than sending outside the queue. Signup remains closed.
US-02/US-03 must configure the frontend action URLs and any additional allauth
mail types before enabling their workflows.

US-13 partner approval and operator reissue now build and queue manager
invitations through the shared service. Staff/store-team issuing screens and
endpoints and household linking remain in US-05, US-06 and US-18. Their callers
build `/invitation/<token>` links from the token returned by
`create_invitation` and `PUBLIC_APP_ORIGIN`, then use
[the notification service](../notifications/README.md). Acceptance does not issue
or send a fresh invitation.

## Audit events

Authentication logs `sign_in_succeeded` and `signed_out` with only the user UUID
as account data, for both browser and admin sessions. Anonymous sign-out emits
no account event. `sign_in_failed` and `sign_in_rate_limited` have no account
identifiers. Invitation services emit `invitation_created` and
`invitation_accepted` only after transaction commit, without recipient details,
account identifiers, tokens or passwords. Document later business audit events
when their workflows are added.
