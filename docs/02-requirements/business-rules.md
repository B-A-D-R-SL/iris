<!-- AI contribution: 50% or more AI-generated -->
# Business rules

Every rule Iris applies, with its default value. Values marked *(setting)* are stored in the rule settings module (`rules`) and can be changed by an admin without a developer; changing one creates a new version, so past decisions stay reproducible. Code never hard-codes these values: business-rule functions in `domain/` receive them as arguments.

Decisions taken where B.A.D.R. had not specified anything are marked **Default**. They can be changed later through the settings or an ADR.

Each module owner publishes and updates their rules in this document through reviewed pull requests.

## Shared household access (US-63)

Mark confirmed this scope for US-63: intake workers and administrators share
household files across staff; the registering staff member does not own the file.

| Rule ID | Business rule |
| --- | --- |
| BR-HH-ACCESS-001 | Active intake workers and administrators can search all non-anonymized households, including files created by another staff member and unassigned files. Other roles, inactive users and anonymous callers are refused. `created_by` records provenance and never restricts staff search scope. |
| BR-HH-ACCESS-002 | Anonymized households are excluded before counting and pagination and cannot be read, edited or offered for resuming through the walk-in endpoints. |
| BR-HH-AUDIT-001 | Search results disclose household details. Persist a view event for each returned household before disclosing the response; an audit failure prevents disclosure. Events contain household IDs and empty metadata, never search text or personal details. |
| SEC-08 | Walk-in creation, detail reads, edits and submission append central audit events with actor, household ID and action. Each eligibility decision appends an event containing decision ID, eligible/ineligible outcome and LICO rule version. Mutations and audit events share one transaction: either failure rolls back both. Automatic decisions have a null actor and system role. Detail audit failure prevents disclosure. |
| SEC-09 | Walk-in audit metadata is empty. Eligibility audit metadata accepts only a canonical decision UUID, a closed eligible/ineligible outcome and a positive integer rule version. Never include names, contact/address details, birth dates, income amounts, thresholds or document contents. |

These access and privacy rules have no configurable numeric threshold. The API
enforces them; the frontend uses the search API's authorization response to decide
whether to open the search screen. Audit retention and any change to disclosure
logging belong to an agreed audit/privacy policy.

## Invitations (US-04)

| Rule ID | Business rule |
| --- | --- |
| BR-INV-001 | Set an invitation's expiry from the active `invitations.expires_after_days` RuleSet, initially **7 days** *(setting)*. The saved expiry is exclusive and later rule versions affect only newly created invitations. Missing or unusable configuration prevents invitation creation. |
| BR-INV-002 | A valid invitation can be accepted once. Create the user and record acceptance atomically; failed validation does not consume the token. Concurrent acceptance cannot create or overwrite multiple accounts. |
| BR-INV-003 | Invitations create new active accounts only. Refuse an email already registered to any active or inactive account, case-insensitively, both when issuing and when accepting. The invitation supplies the new account's identity, role and optional store. |

Sources: [US-04 #428](https://github.com/B-A-D-R-SL/iris/issues/428),
[task #430](https://github.com/B-A-D-R-SL/iris/issues/430), and Leon's
new-account-only scope decision recorded in `AI_USAGE.md`.
Tokens contain 32 random bytes; store only their SHA-256 hash. The public
acceptance endpoint sets the password and leaves the browser session unchanged.
Issuing screens and invitation emails belong to the calling workflows.

## Pickups (US-44)

The following rule IDs are introduced for review with US-44 (#520).

| Rule ID | Business rule |
| --- | --- |
| BR-RES-001 | Only an active `store_staff` or `store_manager` account assigned to a store can look up or confirm a pickup, and only for reservations on that store's listings. A code that belongs to another store's live reservation is answered "picked up somewhere else", naming no store and no household; any other code is unknown. |
| BR-RES-002 | A pickup is confirmed only while the reservation is `reserved` and the time is within the listing's pickup window, both ends included. The store, status and window are checked again under a row lock when confirming, so the pickup is recorded once, with the confirming staff member and the time. Late confirmation of a no-show is US-45. |
| BR-RES-003 | Before confirming, staff see the household holder's and the alternate's first name and last initial, the listing title, the unit and the quantity. No contact detail or full name is sent. An anonymized household is treated as an unknown code. |
| BR-RES-004 | Pickup codes are unique per listing, not per store. If two `reserved` reservations at the same store share the typed code, the lookup is refused and staff find the person in today's pickups instead. A finished reservation with the same code never hides a live one. |
| BR-RES-005 | **Default:** Confirming a pickup does not change listing stock: the units stay counted as taken so they are not offered again. |

Codes are compared after removing spaces and changing to uppercase; the length
comes from the reservation's `pickup_code` column (6). BR-RES-001 to BR-RES-005
are checked in `backend/modules/reservations/queries.py` and `services.py`,
the names in `backend/modules/households/domain/names.py`, and the window in
`backend/modules/reservations/domain/pickup.py`.

## Partner applications (US-12)

### BR-PARTNER-05: Recovery of unaccepted manager invitations

Only an active admin may reissue the invitation for an approved application, via
`resend_partner_invitation APPLICATION_UUID --admin-id ADMIN_UUID`. Expire prior
unaccepted manager links and create a fresh invitation atomically; retain the
application decision and its audit event. Refuse accepted invitations and existing
accounts. Failed issuance rolls back expiry changes; send the new email only
after commit, and permit another recovery if delivery fails. The shared worker
checks invitation usability before transport: obsolete/expired/accepted/missing
invitations mark EmailLog failed with `invitation_unavailable`, without a new
transport attempt or retry. This does not recall a message already in flight;
the superseded link remains invalid when used.

### BR-PARTNER-03: Atomic administrator decisions

Only active administrators may decide submitted applications. Approval creates the
store and manager invitation, decision fields and audit event atomically. Already
decided applications cannot be decided again. Receipt, approval, rejection and
reissue emails use the shared notifications service, which queues after commit
and records transport outcomes in EmailLog.

### BR-PARTNER-04: Required rejection reason and storage limit

A rejection needs a nonblank reason, trimmed before saving, with at most **500
characters**. This is the existing `PartnerApplication.decision_reason` storage
and API contract, not an administrator-configurable threshold. Raising it requires
a coordinated model/schema/API change; invitation expiry remains RuleSet data.
The dedicated `partner_application_rejected` email preserves this stored reason
without changing its content, escaping it for HTML. Household status notices
separately accept the validated US-32 reason; other templates do not accept
reasons. These values are absent from EmailLog and application logs.

### BR-PARTNER-01: One open application per contact email

A contact email may have at most one application with status `submitted`, regardless
of letter case. Approved or rejected applications do not prevent another application.
The database enforces this rule, including when submissions arrive concurrently;
the API returns `409 application_already_open` for a duplicate open application.
This implements US-12 AC3.

### BR-PARTNER-02: Shared application limit per client IP

The public application endpoint applies a limit of **5 requests per hour per client
IP**, shared by anonymous and signed-in callers. A port in the client address does
not create another allowance. Requests that reach the throttle count, including
submissions refused with 400 or 409. Authentication refusals, such as a signed-in
session missing its CSRF token (403), happen before throttling and do not count.
Requests over the allowance receive `429 throttled`.

This implements SEC-04 and task #445. The rate is configured in DRF's
`DEFAULT_THROTTLE_RATES`, and trusted proxies through `DRF_NUM_PROXIES`. This is a
best-effort spam limit; concurrent requests can exceed the allowance because DRF's
cache admission checks are not atomic.

## Eligibility (US-16)

The following rule IDs are introduced for review with US-16 (#457).
The eligibility owner and reviewers must confirm them before merge.

| Rule ID | Business rule |
| --- | --- |
| BR-ELIG-001 | Sum the accepted line-199 income of every household member aged 18 or older, using integer cents. |
| BR-ELIG-002 | Household income at or below the applicable LICO threshold is eligible; income above it is not. |
| BR-ELIG-003 | Use the household's full member count to select the threshold; sizes seven or above use the size-seven threshold. |

Threshold values come from the versioned `lico_thresholds` RuleSet,
not from hardcoded values.

## Household size

| Rule ID | Business rule |
| --- | --- |
| BR-HH-001 | Drafts and submissions use the active `household_size.max_people` RuleSet limit, including the holder. Approved seed default: 15 people (14 additional members). Missing configuration prevents size validation; there is no runtime fallback. |

## Duplicate households (US-25)

Approved rules for #479 and #478.

| Rule ID | Business rule |
| --- | --- |
| BR-DUP-001 | The same address and unit, or a member with the same names and birth date, in another open file is a possible duplicate. Suspended files count. Ignore draft, rejected and anonymized files, and files whose `expires_at` is in the past. |
| BR-DUP-002 | Save possible duplicates as review_required with reason POSSIBLE_DUPLICATE. Keep both files. A clean file becomes submitted. Approval is a separate step. |
| BR-DUP-003 | Submissions sharing an address or person wait on PostgreSQL advisory locks. Take locks in a fixed order before the search and hold them until the outer transaction ends. |

Open statuses: `submitted`, `review_required`, `awaiting_visit`,
`approved`, `renewal_needed`, and `suspended`. A missing or future expiry does not
exclude a file.

## Household suspension (US-32)

| Rule ID | Business rule |
| --- | --- |
| BR-HH-SUSPEND-001 | Only an active administrator can suspend an approved file or reactivate a suspended file. Both actions require a reason and an audit event. |
| BR-HH-SUSPEND-002 | Suspension preserves the approval expiry, cancels every reserved reservation without a strike, and returns its units to the listing. Reactivation is refused after expiry. |
| BR-HH-SUSPEND-003 | A localized status email, including the workflow's normalized and privacy-validated reason, is queued after commit when the household has an email. A counter-only file without email can still change status. Delivery failure does not undo the change. |
| BR-HH-SUSPEND-004 | A status reason is limited by the active `household_suspension.reason_max_length` RuleSet value (default 500, schema ceiling 2,000). Suspension also retains the existing 500-character `Household.status_reason` model bound; reactivation clears that stored field and may use a longer validated reason under its active rule. Reasons containing personal, identity, document or financial information are refused before an audit event or email job is created. |

## Notifications (US-57)

| Rule ID | Business rule |
| --- | --- |
| BR-NOTIF-001 | Retry transient delivery failures using exactly three positive delays from the active `notifications.retry_delays_seconds` RuleSet: defaults **60, 300 and 900 seconds** *(setting)* after successive failures. The initial attempt plus these retries gives at most four attempts. Capture the delay list for each queued send; later rule versions affect new sends. Confirmed permanent failures stop immediately. |
| BR-NOTIF-002 | Queue delivery after the originating transaction commits. A rollback creates no surviving delivery log or job. Known-template address/context/runtime-email-configuration failures record failed EmailLog metadata with zero attempts and no job, without undoing a valid business action. Unknown template keys remain programmer errors. Delivery and post-commit enqueue failures do not undo committed actions. Business authorization and essential issuance rules remain enforced. There is no atomic-outbox or exactly-once guarantee across the commit/enqueue/provider boundaries. |
| BR-NOTIF-003 | Use a User's persisted preferred language; for a raw recipient use the caller's saved `fr`/`en` preference, defaulting to French. Render only reviewed context fields, with links on the configured application origin. Income and identity/document fields and arbitrary case notes are excluded. Partner rejection accepts US-13's stored reason of at most 500 trimmed characters (BR-PARTNER-04). Household suspension/reactivation accepts the normalized, privacy-validated reason under the producer's active RuleSet (BR-HH-SUSPEND-004); capture supports its 2,000-character schema ceiling so later rule versions do not invalidate pending text. These three templates escape reasons once in HTML; other templates accept none. Record delivery metadata without subject/body/context/reason/token content; application logs also exclude recipient addresses. |
| BR-NOTIF-004 | Delete terminal email-queue job payloads once older than `notifications.job_retention_hours`, default **24 hours** *(setting)*. Cleanup runs hourly, so normal removal is approximately 24–25 hours after the terminal event while the worker is healthy. Pending/running/retrying jobs remain. EmailLog metadata is retained; this cleanup does not implement general EmailLog retention. Legacy jobs on their original default queue require targeted rollout cleanup. |

The new `notifications` RuleSet validates exactly three integer delays from
1 to 86,400 seconds and retention from 1 to 168 hours. Missing or invalid active
configuration records a failed notification instead of silently inventing runtime
defaults. Native queue executions govern the retry budget; database failures can
consume an execution without a transport call. EmailLog counts transport attempts
separately. `sent` means successful transport/provider acceptance, not inbox
delivery. Producer workflows and reminder/digest/matching scheduling remain with
their owning stories; US-57 supplies their bilingual templates and calling
contracts. See [US-57 #538](https://github.com/B-A-D-R-SL/iris/issues/538) and the
[notification runbook](../../backend/modules/notifications/README.md).

## Listings

### Categories

Every listing belongs to exactly one active category. The category decides two things:

- **Food or not:** a listing in a food category needs a best-before date on or after the pickup end date (margin `best_before_margin_days` in rule type `listing_safety`, default 0 days *(setting)*).
- **Default value:** when a store leaves the estimated value empty, the listing is valued at the category's default value × quantity (used in reports).

The `code` is the stable identifier used by the API, the database and the partner application form (`goods_categories`); it never changes once a category is in use. Admins can rename or deactivate a category, but a category in use cannot be deleted, only deactivated (US-35). Screens show the name in the user's language.

**Categories (Default, seed file `backend/modules/categories/data/categories.yaml`):**

| Code | Français | English | Food | Default value |
| --- | --- | --- | --- | --- |
| `fruits_vegetables` | Fruits et légumes | Fruits and vegetables | Yes | $5 |
| `bakery` | Boulangerie | Bakery | Yes | $4 |
| `dairy_eggs` | Produits laitiers et œufs | Dairy and eggs | Yes | $6 |
| `meat_fish` | Viandes et poissons | Meat and fish | Yes | $10 |
| `prepared_meals` | Plats préparés | Prepared meals | Yes | $8 |
| `dry_goods` | Épicerie sèche | Dry goods | Yes | $4 |
| `canned_goods` | Conserves | Canned goods | Yes | $3 |
| `frozen` | Surgelés | Frozen food | Yes | $7 |
| `beverages` | Boissons | Beverages | Yes | $3 |
| `baby_food` | Alimentation pour bébé | Baby food | Yes | $5 |
| `hygiene` | Hygiène personnelle | Personal hygiene | No | $5 |
| `household_cleaning` | Produits ménagers | Household cleaning | No | $5 |
| `baby_care` | Soins pour bébé | Baby care | No | $8 |
| `clothing` | Vêtements | Clothing | No | $10 |
| `school_supplies` | Fournitures scolaires | School supplies | No | $5 |
| `other` | Autre | Other | No | $5 |

Default values are stored in cents (`default_value_cents`, $5 = `500`).

### Category management rules (US-35)

The following rule IDs are introduced for review with US-35 (#501).
The categories owner and reviewers must confirm them before merge.

| Rule ID | Business rule |
| --- | --- |
| BR-CAT-001 | A category's default value is from 0 to the listing value limit (`estimated_value_max_cents` in rule type `listing_posting`, default $1,000 *(setting)*). On an edit it is checked only when it changes, so a later, lower limit does not block renaming or deactivating an older category. |
| BR-CAT-002 | A category's code is unique and cannot change after creation. |
| BR-CAT-003 | A category is never deleted, only deactivated; a deactivated category is not offered for new listings, and listings that already use it keep it. Only admins manage categories. |

The value limit comes from the versioned `listing_posting` RuleSet, not from a
hardcoded value. BR-CAT-001 is checked in
`backend/modules/categories/domain/rules.py`; BR-CAT-002 and BR-CAT-003 in
`backend/modules/categories/services.py`.

### Prohibited items

Stores never post these items (Default):

- Alcohol
- Tobacco and vaping products
- Cannabis
- Prescription or over-the-counter medication
- Opened or home-made food
- Recalled products
- Infant formula past its date
- Weapons

Prohibited items have **no category**, so they cannot be posted through any category. Staff tick **"Safe and allowed"** on every post to confirm the goods are safe and contain no prohibited item; the confirmation is stored with who and when, and a listing cannot be published without it. The rule type `listing_safety` keeps a list of prohibited category codes *(setting)*, empty by default because no category above is prohibited; an admin can add a code to stop new posts in that category.

### Safety rules (US-34)

The following rule IDs are introduced for review with US-34 (#497).
The listings owner and reviewers must confirm them before merge.

| Rule ID | Business rule |
| --- | --- |
| BR-LIST-001 | Every listing needs the "Safe and allowed" confirmation, stored with who and when. |
| BR-LIST-002 | A listing in a category on the `listing_safety` prohibited list cannot be posted, and the posting form does not offer that category. |
| BR-LIST-003 | A food listing needs a best-before date on or after the pickup end date (Montreal time) plus `best_before_margin_days`; a non-food listing ignores it. |

The margin and the prohibited list come from the versioned `listing_safety`
RuleSet, not from hardcoded values. The rules are checked in
`backend/modules/listings/domain/safety.py`.

### Browsing rules (US-36)

The following rule IDs are introduced for review with US-36 (#504).
The listings owner and reviewers must confirm them before merge.

| Rule ID | Business rule |
| --- | --- |
| BR-LIST-004 | An approved household (status `approved` and not expired) sees a listing when it is published, has units left and its pickup has not ended. Until tiers exist (US-51), every approved household sees every such listing. |
| BR-LIST-005 | The "pickup today" filter keeps visible listings whose pickup starts before the next midnight, Montreal time, including a window that started the day before. |

Visibility is decided only in `listings.queries.visible_listings`; the end of
the day comes from `backend/modules/listings/domain/browsing.py`.
