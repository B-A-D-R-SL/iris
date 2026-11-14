<!-- AI contribution: 50% or more AI-generated -->
# Stores module

**Owner pair:** Fairness & partners
**Status:** Store (US-11), partner applications (US-12), and staff review service/API/screens (US-13) implemented; email delivery uses US-57

## Responsibility

Own stores (B.A.D.R. and approved partners) and the partner applications that
lead to them, within the Iris modular monolith.

## Layers

- `api/`: HTTP validation, permissions, and routing
- `domain/`: Pure Python business rules; no Django dependencies
- `services.py`: Public write operations and transactions
- `queries.py`: Public read-only operations
- `models.py`: Module-owned Django models
- `tasks.py`: Background jobs when necessary
- `tests/`: Domain, service, and API tests

## Models

- `Store`: a place offering goods. `application` links a store to the
  `PartnerApplication` that created it; the US-13 approval sets it, and it stays
  empty for B.A.D.R. and manually created stores.
- `PartnerApplication`: a business request to become a partner. No account or
  store is created at submission. See
  [database-schema.md](../../../docs/03-design/database-schema.md#partnerapplication).

## Public functions

- `queries.partner_applications(status=None)`: applications oldest first, optionally one status.
- `queries.partner_application(application_id)`: one application or `None`.
- `services.save_store(store)`
- `services.ensure_badr_store()`
- `services.submit_application(values, *, language)`: saves a
  `submitted` application from validated form values and queues the bilingual
  `partner_application_received` email after the commit. Raises
  `ApplicationAlreadyOpen` while the contact email has a submitted application,
  and a `ValidationError` for inactive or unknown category codes.

- `services.approve_application(application, admin)`: creates a store and store-manager invitation in one transaction, records the decision and queues `partner_application_approved` through notifications. Configure `PUBLIC_APP_ORIGIN` as the public frontend origin. Free-text hours are preserved in `opening_hours.notes` until a structured schedule is provided.
- `services.reject_application(application, admin, reason)`: requires a nonblank reason of at most 500 trimmed characters, records the decision and queues `partner_application_rejected` with that stored reason. Both decision functions require an active admin and raise `ApplicationAlreadyDecided` if the application is no longer submitted. Delivery failures are recorded without message content and do not undo committed decisions.
- `services.resend_approval_invitation(application, admin)`: recovery for an approved application. Requires an active admin, expires prior unaccepted manager invitations, issues a fresh token and queues the approval template with the new link. It refuses existing accounts and never repeats the approval or its audit event. Failed issuance rolls back expiry changes.

## Recovering a lost approval email

Approval, rejection and reissue email outcomes are recorded in the shared
`EmailLog`; new sends do not use the former inline SMTP callback or its
`partner_application_decision_email_failed` event. Application logs contain no
recipient, token, message body, rejection reason or provider exception. An
operator with backend access can reissue using the application and active admin
UUIDs:

```sh
python manage.py resend_partner_invitation APPLICATION_UUID --admin-id ADMIN_UUID
```

The command reports invitation reissue without printing the recipient or token.
It directs the operator to EmailLog without promising queue insertion or delivery.
Check the log and worker outcome after the command.
Delivery failure keeps the new invitation committed, so recovery can be retried.
Every successful reissue expires previous links, including links from earlier
failed sends. Accepted invitations and existing accounts cannot be reissued.

Invitation-template jobs check that the token is still usable before starting
transport. A superseded, expired, accepted or missing invitation marks its
EmailLog `failed` with error `invitation_unavailable`, without retrying.
An unsent log remains at zero attempts; a previously attempted job retains its
count and starts no new transport attempt. This prevents sending links already
invalid at preflight; a message already in flight cannot be recalled. Reissuing
still invalidates its old link in Iris.

Approval and recovery use the shared `PUBLIC_APP_ORIGIN`, an HTTPS origin (HTTP
only for localhost/loopback development) without a path, query, fragment or
credentials. Production startup keeps its origin/sender guards. A known-template
runtime delivery-input or origin problem becomes a failed EmailLog and does not
undo approval/reissue; there is no separate inline mail-configuration precheck.
Active-admin authorization, application-state checks and essential invitation
issuance rules remain enforced before a decision can complete.

## Endpoints

- `POST /api/partner-applications/`: public, 5 requests per hour per IP. Contract
  in [api.md](../../../docs/03-design/api.md#post-apipartner-applications-us-12).
- `GET /api/staff/partner-applications/?status=`, `POST .../{id}/approve/` and
  `POST .../{id}/reject/`: admin only (`api/staff_views.py`). Contract in
  [api.md](../../../docs/03-design/api.md#staff-review-of-partner-applications-us-13).

## Dependencies

- `common.domain.contact`: shared Canadian phone/postal normalization, also used
  by households. Django/DRF/admin adapters normalize formatted input before
  canonical length checks. Direct submissions and approval-created stores retain
  E.164 phones and uppercase postal codes with one space (FIX-14).
- `categories.queries`: active category codes for `goods_categories`.
- `notifications.services`: receipt, approval, rejection and reissue email through
  the shared US-57 template/log/job pipeline. The worker selects ACS, SMTP/Mailpit
  or the reusable test fake; business requests never call transport directly.
- `accounts.services`: manager invitation issuance.
- `audit.services`: decision audit events.

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

## Audit events

Approval and rejection record a `decision` on `partner_application`, with only the outcome in metadata.

The worker renders the applicant's captured language from the shared French and
English templates. Partner rejection accepts the stored bounded decision
reason; it is escaped in HTML and is absent from EmailLog and stdout. Household
status notices separately accept their producer-validated US-32 reason; other
template families do not accept reasons or notes. SMTP has a finite
`SMTP_TIMEOUT` deadline (10 seconds by default); ACS has its separately configured
send timeout. Committed decisions retain their privacy-safe audit/log events.
