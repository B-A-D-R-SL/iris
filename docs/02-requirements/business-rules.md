<!-- AI contribution: Below 50% AI-generated -->
# Business rules

Every rule Iris applies, with its default value. Values marked *(setting)* are stored in the rule settings module (`rules`) and can be changed by an admin without a developer; changing one creates a new version, so past decisions stay reproducible. Code never hard-codes these values: business-rule functions in `domain/` receive them as arguments.

Decisions taken where B.A.D.R. had not specified anything are marked **Default**. They can be changed later through the settings or an ADR.

Each owner publishes their section of this document in their own pull request. This version contains the listing categories and the prohibited items (SET-12), and partner applications (US-12); the other sections (roles, eligibility, reservations, priority, strikes, notifications, retention) are added by their owners.

## Invitations (US-04)

| Rule ID | Business rule |
| --- | --- |
| BR-INV-001 | Set expiry from `invitations.expires_after_days` (seed default **7 days**). The saved expiry is exclusive; later rule versions affect only new invitations. Missing or invalid configuration prevents issuing a link. |
| BR-INV-002 | Accept an invitation once, creating the user and consuming the token atomically. Failed validation leaves the token unused. |
| BR-INV-003 | Create new accounts only. Refuse email addresses already registered to active or inactive users, case-insensitively, when issuing and accepting. Identity, role and store come from the invitation. |

These are the US-04 rules already implemented on `main` (#430). Only a token's
SHA-256 hash is stored. Acceptance does not change the browser session.

## Partner applications (US-12)

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

## Notices of assessment (US-18)

The following rule IDs are introduced with T-03.18.2 (#468), the walk-in
notices of US-18 (#466). The registration owner and reviewers must confirm
them before merge.

| Rule ID | Business rule |
| --- | --- |
| BR-DOC-001 | A filed notice needs the file, the tax year, the line-199 total income in integer cents (0 or more), the name on the notice, the postal code on the notice, the notice date and the "seen in person" answer. |
| BR-DOC-002 | The notice date is after December 31 of the tax year and not after today (Montreal); the tax year is 2000 or later and has ended. Which tax years count for eligibility is decided at approval (`auto_approval.accepted_tax_years`, #469). |
| BR-DOC-003 | "Did not file" needs a reason of 1 to 500 characters after trimming and refuses a file or any notice value. |
| BR-DOC-004 | The file is a JPEG, PNG or PDF recognized from its first bytes (never its name or declared type), not empty, and at most `max_bytes` in rule type `notice_upload` (default 10 MB *(setting)*). |
| BR-DOC-005 | Each adult has at most one current notice. A new entry supersedes the current one; the old row and its file are kept as history (database constraint). |
| BR-DOC-006 | Notice files are never public. Staff get a link valid `link_minutes` in rule type `notice_upload` (default 5 minutes *(setting)*, fixed when the link is issued), signed for one staff user and usable only with that user's session; issuing it is recorded in the audit log. |
| BR-DOC-007 | Notices are recorded only for members aged 18 or older (Montreal date) of a draft walk-in household. |

The limits come from the versioned `notice_upload` RuleSet, not from
hardcoded values. BR-DOC-001 to BR-DOC-004 are checked in
`backend/modules/documents/domain/notice.py`; BR-DOC-005 and BR-DOC-006 in
`backend/modules/documents/services.py` and the `IncomeNotice` constraints;
BR-DOC-007 in `backend/modules/households/services.py`.

### Walk-in approval (#469)

Every adult needs a current notice or a non-filing reason. Approval rechecks the
notice against the member's current name, ignoring case and accents and allowing
extra middle names. A mismatch, including a holder name corrected after upload,
sets `review_required` with `NAME_MISMATCH`.

Non-filing, an unseen notice, an unaccepted tax year, a postal-code mismatch or
unverified identity also requires review; existing review flags are not cleared.
Non-filers are never counted as zero income. Missing mandatory information
prevents a decision. Accepted tax years come from `auto_approval.accepted_tax_years`.
Otherwise the eligibility service applies LICO: ineligible files are rejected
with `INCOME_ABOVE_LICO`, and eligible files are approved for
`file_validity.approved_months` (seed default **12 calendar months**, Montreal).
Approved files with email receive a beneficiary set-password invitation after
commit. The new-account-only invitation rule still applies.

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
