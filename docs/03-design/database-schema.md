<!-- AI contribution: 50% or more AI-generated -->
<!-- File-length exception: the model field/nullability/constraint tables, complete
Mermaid ERD and module migration order form one cross-module schema contract.
Keep them together so changes such as EmailLog's User foreign key or the required
store assignment for store roles can be checked against all three representations
in the same review. -->
# Iris database schema — Release 1 implementation

Reviewed 15 November 2026 for [SET-21 (#412)](https://github.com/B-A-D-R-SL/iris/issues/412)
against local `main` at `a022580640be604eaf08f56aedd2f6d548583c65` (through PR #710).
The existing field tables and ERD below are updated from the models and migrations;
this is an implementation snapshot, not a live database inspection. The
[architecture review](../04-architecture/architecture.md#release-1-review)
records the differences, reasons and PR/issue evidence.

There are 15 application models across 11 model-owning modules and 27 concrete
application foreign keys. Priority, Review, Reporting and Privacy have no model
tables in this snapshot; Privacy does have a shared reason-validation service.
Fields use Django model names; FK database columns append `_id`. SQL nullability
is distinct from a blank form value. Framework tables are described separately.

## Changes over sprints

Iris follows an Agile methodology. Small design changes can be made in later sprints as requirements develop. The responsible module owners review those changes and update this document, the ERD, and the migration plan together. Changes to a database whose migrations have already been applied are introduced through new migrations.

## Database terms

| Term | Meaning |
| --- | --- |
| Nullability | Whether a database field can contain NULL, meaning no value. An optional form input does not by itself specify SQL nullability. |
| Constraint | A database rule that protects data, such as uniqueness or a CHECK. Business rules enforced by services are identified separately below. |
| Index | A structure that helps database lookups. PostgreSQL unique constraints have supporting indexes. |
| Module owner | The Django module responsible for the model, migrations, and public services and queries. |
| Foreign key (FK) | A field linking a record to another model. |
| Unique key (UK) | A field or combination of fields that cannot be duplicated. |

## Sign-in, sign-up, and invitations

Users sign in with email and password through Django/allauth. The User password field stores an encoded password hash and its hashing metadata. Django handles password hashing and verification. Password hashes are excluded from API responses.

Public household sign-up remains closed; email verification belongs to US-02.
An invited person accepts a one-use invitation to create a new active User carrying
the invited role and optional store assignment. Existing active or inactive accounts
with the invited email are refused case-insensitively and are not overwritten
(the #430 clarification). Acceptance neither signs in nor switches an existing
session. A store can have multiple managers and staff. Settings prefer Argon2
password hashes and retain PBKDF2 for verification of existing hashes.

Sources: [Issue #422](https://github.com/B-A-D-R-SL/iris/issues/422), [Issue #426](https://github.com/B-A-D-R-SL/iris/issues/426), [Issue #428](https://github.com/B-A-D-R-SL/iris/issues/428), [Issue #433](https://github.com/B-A-D-R-SL/iris/issues/433), [Django password storage](https://docs.djangoproject.com/en/stable/topics/auth/passwords/).

## Models

### User

**Owner module:** `accounts`.

A person who can sign in to Iris.

| Field | Logical type | Key | Details |
| --- | --- | --- | --- |
| id | UUID | Primary key | Stable public user identifier. |
| email | string | Unique key | Case-insensitive unique sign-in email. |
| password | string | — | Django-managed encoded password hash, including hashing metadata; never the plain-text password. Django standard field: NULL is not allowed. |
| first_name | string | — | User first name. |
| last_name | string | — | User last name. |
| phone | string | — | Contact phone number. |
| preferred_language | string | — | `fr` or `en`; default `fr`. |
| role | string | — | `beneficiary`, `store_staff`, `store_manager`, `intake_worker`, or `admin`. |
| store | reference | Foreign key | Required for store staff and managers; nullable for other roles. Deletion is protected while users reference the store. |
| is_active | boolean | — | Whether the account is active. |
| last_login | datetime | — | Most recent sign-in time; Django authentication metadata. Nullable. |
| is_superuser | boolean | — | Django permission bypass flag; distinct from the Iris admin role. |
| is_staff | boolean | — | Django admin-site access flag; distinct from the Iris role. |
| created_at | datetime | — | Creation time. |
| updated_at | datetime | — | Last-save time. |

**Documented constraints and business rules**

| Rule | Enforcement |
| --- | --- |
| Email must be unique regardless of case. | Database unique constraint on lowercased email. |
| Passwords are stored as Django-managed hashes; inactive accounts cannot sign in. | Django/allauth authentication. |
| Store staff and managers must have a store. | Database check constraint. |
| A store referenced by a user cannot be deleted. | Protected foreign key. |

**Documented indexes**

| Fields | Purpose |
| --- | --- |
| email | The unique email constraint provides an index for sign-in lookup. |

Sources: [Issue #424](https://github.com/B-A-D-R-SL/iris/issues/424), [Issue #433](https://github.com/B-A-D-R-SL/iris/issues/433).

### Invitation

**Owner module:** `accounts`.

An invitation to create a new active account with an assigned role. Acceptance does not sign the user in or switch an existing session.

| Field | Logical type | Key | Details |
| --- | --- | --- | --- |
| email | string | — | Recipient email. |
| first_name | string | — | Recipient first name. |
| last_name | string | — | Recipient last name. |
| role | string | — | Role assigned on acceptance. |
| store | reference | Foreign key | Optional store assignment. Nullable. |
| token_hash | string | Unique key | SHA-256 hash of the invitation token; not the raw token. |
| expires_at | datetime | — | Expiration saved when issued, using the active `invitations.expires_after_days` rule. |
| accepted_at | datetime | — | Acceptance time; unset before acceptance. Nullable. |
| invited_by | reference | Foreign key | Person who issued the invitation, when applicable. Nullable. |
| id | uuid | Primary key | Stable UUID identifier. |

**Documented constraints and business rules**

| Rule | Enforcement |
| --- | --- |
| Invitations are refused at or after the saved expiry and can be accepted once. The default lifetime is seven days. | Issuance reads the active `invitations.expires_after_days` RuleSet value; later rule versions affect only new invitations. Acceptance checks the saved expiry and marks acceptance atomically with user creation. |
| Generate a token from 32 random bytes and store only its unique SHA-256 hash. | Invitation generation service and database uniqueness. The raw token is returned to the caller for its invitation email. |
| Acceptance creates a new user; an existing active or inactive user with the invited email is refused case-insensitively. | Invitation acceptance service and the User email constraint. |

Sources: [Issue #428](https://github.com/B-A-D-R-SL/iris/issues/428), [Issue #430](https://github.com/B-A-D-R-SL/iris/issues/430).

### Store

**Owner module:** `stores`.

An approved partner store, including the B.A.D.R. store.

| Field | Logical type | Key | Details |
| --- | --- | --- | --- |
| name | string | — | Store name. |
| street_number | string | — | Civic number. |
| street_name | string | — | Street name. |
| unit | string | — | Unit or suite. Nullable. |
| city | string | — | City name. |
| postal_code | string | — | Postal code. |
| phone | string | — | Contact phone number. |
| email | string | — | Contact email. |
| opening_hours | json | — | Three stored forms. A completed weekly schedule has keys `mon` to `sun`, each `{"open": "HH:MM", "close": "HH:MM"}` or null when closed, plus an optional read-only `notes` (BR-STORE-006). A store just approved from a partner application holds only `{"notes": "..."}`, and the B.A.D.R. placeholder holds `{}`. Consumers must not assume the day keys exist until an admin saves the schedule. |
| pickup_instructions | string | — | Instructions for collecting goods. Nullable. |
| is_badr | boolean | — | Identifies the B.A.D.R. store. |
| is_active | boolean | — | Whether the store is active. |
| application | reference | FK, UK | Nullable one-to-one to the PartnerApplication that created the store (column `application_id`). Set by the US-13 approval; null for B.A.D.R. and manually created stores. PROTECT. |
| created_at | datetime | — | Store creation time. |
| id | uuid | Primary key | Stable UUID identifier. |
| updated_at | datetime | — | Last-save time. |

**Documented constraints and business rules**

| Rule | Enforcement |
| --- | --- |
| At most one Store has is_badr set to true. | Partial unique index. |
| Inactive stores cannot post; deactivation cancels open listings and their reservations, never the B.A.D.R. store (BR-STORE-002 to BR-STORE-004). | Store, listing and reservation services (US-14). |

**Documented indexes**

| Fields | Purpose |
| --- | --- |
| is_badr | Partial unique index enforcing at most one B.A.D.R. store. |

Sources: [Issue #439](https://github.com/B-A-D-R-SL/iris/issues/439), [Issue #452](https://github.com/B-A-D-R-SL/iris/issues/452), [Iteration 2 plan](https://github.com/B-A-D-R-SL/iris/blob/main/docs/06-planning/iteration-2.md).

### PartnerApplication

**Owner module:** `stores`.

A business request to become a partner; no account or store is created at submission. Implemented by US-12 (#445) as table `stores_partnerapplication`. Field names and rules follow the [partner application form](../02-requirements/forms-and-fields.md#partner-application-form).

| Field | Type | Null | Details |
| --- | --- | --- | --- |
| id | uuid | No | Primary key. |
| business_name | varchar(150) | No | 2 to 150 characters. |
| business_type | text choice | No | `grocery`, `supermarket`, `bakery`, `restaurant`, `cafe`, `convenience_store`, `pharmacy`, `farm_producer`, `community_organization`, `other`. |
| neq | varchar(10) | Yes | Quebec enterprise number, exactly 10 digits. |
| street_number, street_name, unit, city, postal_code | as Store | `unit` only | Business address; postal code stored as `A1A 1A1`. |
| contact_first_name, contact_last_name | varchar(100) | No | Letters, spaces, apostrophes, hyphens. |
| contact_role | varchar(100) | Yes | Optional role. |
| contact_email | citext | No | Lowercase; becomes the store manager's sign-in after approval. |
| contact_phone | varchar(16) | No | Canadian number in E.164, for example `+15145550123`. |
| website | varchar(200) | Yes | `https://` added if missing. |
| goods_categories | text[] | No | Stable category codes; at least one, each active at submission. |
| expected_frequency | text choice | No | `daily`, `weekly`, `monthly`, `occasional`. |
| opening_hours | varchar(300) | No | Free text, for example "lun-ven 9 h-18 h". |
| message | varchar(1000) | Yes | Optional additional information. |
| consent_contact | boolean | No | Consent to be contacted; must be true (Law 25 record, with `created_at`). |
| language | text choice | No | `fr` (default) or `en`; language of the emails to the contact, who has no account. |
| status | text choice | No | `submitted` (default), `approved`, `rejected`. |
| decision_reason | varchar(500) | Yes | Required when rejected. |
| decided_by | uuid FK accounts_user | Yes | Administrator who decided (US-13). PROTECT. |
| decided_at | timestamptz | Yes | Decision time (US-13). |
| created_at | timestamptz | No | Submission time. |

**Constraints and indexes**

| Rule | Enforcement |
| --- | --- |
| At most one `submitted` application per contact email, ignoring case. | Partial unique index `stores_application_one_open_per_email` on citext `contact_email` where `status = 'submitted'`; the service checks first for a friendly message. |
| Consent given. | CHECK `stores_application_consent_given`. |
| At least one goods category. | CHECK `stores_application_has_category`; active codes checked by the service. |
| Rejection requires a reason. | CHECK `stores_application_rejection_has_reason`. |
| Choice values valid. | CHECKs on `status`, `business_type`, `expected_frequency`, `language`. |
| Review list by status, oldest first (US-13). | Index `stores_application_status_idx` on (`status`, `created_at`). |
| Approval creates a Store and Invitation, updates application status, and records audit atomically. Email follows commit. | Approval transaction and background notification (US-13). |

Sources: [Issue #443](https://github.com/B-A-D-R-SL/iris/issues/443), [Issue #445](https://github.com/B-A-D-R-SL/iris/issues/445), [Issue #447](https://github.com/B-A-D-R-SL/iris/issues/447).

### Household

**Owner module:** `households`.

A household registration and approval file.

Migration history: the SET-18 seed (#617) created the first table (`0001_initial`); US-17 (#461) migrates it forward (`0002_walk_in_registration`: walk-in fields, `Member`, `HouseholdDraftEvent`, seeded rows converted; `0003_household_consent`: consent fields), as decided on #461.

| Field | Logical type | Key | Details |
| --- | --- | --- | --- |
| holder | reference | FK, UK | Optional holder User, distinct from the holder Member. Walk-in linking is refused by model validation; accepting its invitation does not populate this field. US-93 (#704, Release 2) owns that path. Nullable. |
| member_number | string | Unique key | Optional short file number. Nullable. |
| channel | string | — | Registration channel: walk-in or online. |
| status | string | — | Household file status. |
| status_reason | string | — | Optional reason for the current status. |
| email | string | — | Optional holder email; without it a walk-in is served only at the counter. Nullable. |
| preferred_language | string | — | `fr` or `en`; used for emails. |
| street_number | string | — | Civic number. |
| street_name | string | — | Street name. |
| unit | string | — | Optional apartment or unit. |
| city | string | — | City name. |
| postal_code | string | — | Validated, normalized Canadian postal code. |
| address_key | string | — | Normalized address, including unit, used to find possible duplicates. |
| phone | string | — | Household contact phone. |
| alternate_name, alternate_phone, alternate_email | string | — | Optional alternate for pickups. |
| identity_checked_in_person | boolean | — | Staff checked photo ID in person; nothing about the ID is stored. |
| consent_data_processing_at | datetime | — | When the person agreed to data processing (walk-in: notice read aloud); empty until given. Nullable. |
| consent_text_version | string | — | Version of the consent text that was read, for example `2026-11-v1`. US-20 may move consents to a separate record later. |
| created_by | reference | Foreign key | Person who created the household file. Nullable. |
| created_at | datetime | — | Household file creation time. |
| updated_at | datetime | — | Last change to the file. |
| verified_by | reference | Foreign key | Staff member who checked the identity. Nullable. |
| verified_at | datetime | — | Identity check time. Nullable. |
| submitted_at | datetime | — | Submission time. Nullable. |
| approved_at | datetime | — | Approval time. Nullable. |
| expires_at | datetime | — | Approval expiration time. Nullable. |
| anonymized_at | datetime | — | Time personal data was removed. Nullable. |
| id | uuid | Primary key | Stable UUID identifier. |
| search_email_key | string | — | Stored generated normalized email key; internal search field. Nullable. |
| search_number_key | string | — | Stored generated normalized member-number key; internal search field. Nullable. |
| search_address_key | string | — | Stored generated duplicate-address search key. |
| search_address_text | string | — | Stored generated full-address search text. |

**Confirmed information requirements**

These documented workflow inputs are retained as requirements. They are separate from the field definitions shown in the ERD.

| Information | Requirement |
| --- | --- |
| Main contact | Registration collects first name, last name, date of birth, optional email, phone, and preferred language for the household holder. |
| Identity check | Staff record that identity was checked in person, without storing identity-document details. |

**Documented constraints and business rules**

| Rule | Enforcement |
| --- | --- |
| Possible duplicate addresses or people trigger review. | Duplicate detection service. |
| Approval lasts twelve months; suspended or expired households cannot reserve. | Approval and reservation services. |

Sources: [Issue #461](https://github.com/B-A-D-R-SL/iris/issues/461), [Issue #463](https://github.com/B-A-D-R-SL/iris/issues/463), [PR #617](https://github.com/B-A-D-R-SL/iris/pull/617), [Issue #469](https://github.com/B-A-D-R-SL/iris/issues/469), [Issue #477](https://github.com/B-A-D-R-SL/iris/issues/477).

### Member

**Owner module:** `households`.

A person belonging to a household.

| Field | Logical type | Key | Details |
| --- | --- | --- | --- |
| household | reference | Foreign key | Household containing this member. |
| first_name | string | — | Member first name. |
| last_name | string | — | Member last name. |
| date_of_birth | date | — | Used to determine age. |
| relation | string | — | Relationship within the household. |
| person_key | string | — | Normalized person identity used to find possible duplicates. |
| created_at | datetime | — | When the member was added. |
| updated_at | datetime | — | Last change to the member. |
| id | uuid | Primary key | Stable UUID identifier. |
| search_name_key | string | — | Stored generated normalized name key; excludes birth date. |

**Documented constraints and business rules**

| Rule | Enforcement |
| --- | --- |
| Record household membership, name, date of birth, and relationship. | Household registration. |
| A matching person in another active file triggers review. | Duplicate detection service. |

Source: [Issue #463](https://github.com/B-A-D-R-SL/iris/issues/463).

### HouseholdDraftEvent

**Owner module:** `households`.

A local record of who created, edited or submitted a walk-in draft. It remains
alongside central AuditEvent after FIX-08 (PR #701); it has no database append-only
trigger and does not replace the central audit guarantee.

| Field | Logical type | Key | Details |
| --- | --- | --- | --- |
| household | reference | Foreign key | Draft that was created or edited. |
| actor | reference | Foreign key | Staff member who acted. |
| actor_role | string | — | Their role at that moment. |
| action | string | — | `created`, `updated` or `submitted`. |
| created_at | datetime | — | When it happened. |
| id | bigint | Primary key | Bigint primary key. |

**Documented constraints and business rules**

| Rule | Enforcement |
| --- | --- |
| No names, dates of birth, phone numbers, addresses or emails in the event. | `households` services. |

Sources: [Issue #463](https://github.com/B-A-D-R-SL/iris/issues/463), [Issue #464](https://github.com/B-A-D-R-SL/iris/issues/464), [Issue #547](https://github.com/B-A-D-R-SL/iris/issues/547).

### IncomeNotice

**Owner module:** `documents`.

An adult member income-evidence record or a non-filing explanation.

| Field | Logical type | Key | Details |
| --- | --- | --- | --- |
| member | reference | Foreign key | Member whose income evidence is recorded. |
| id | UUID | Primary key | Notice identifier used by the staff file link. |
| status | string | — | `confirmed` (values from a notice) or `did_not_file`. |
| source | string | — | Source of recorded values; staff entry uses `staff`. |
| file_ref | string | — | Opaque private storage reference (`income-notices/<random>`); never a URL or the uploaded file name. |
| tax_year | integer | — | Tax year represented. Nullable. |
| total_income_cents | integer | — | Line 199 assessed income: Montant etabli; integer cents. Nullable. |
| name_on_notice | string | — | Name recorded on the notice. |
| postal_code_on_notice | string | — | Postal code recorded on the notice. |
| notice_date | date | — | Notice issuance date. Nullable. |
| seen_in_person | boolean | — | Whether staff saw the notice in person. |
| did_not_file_reason | string | — | Required explanation for a non-filing adult. |
| recorded_by | reference | Foreign key | Staff user who recorded the entry. |
| created_at | datetime | — | When the entry was recorded. |
| superseded_at | datetime | — | When a newer entry replaced this one; empty for the current notice. Nullable. |

**Documented constraints and business rules**

- A member may retain notice records from different tax years.
- Eligibility uses the appropriate verified notice for the relevant
  tax year, rather than adding income across different years.
- A corrected or replacement entry supersedes the member's current
  notice; the old row and file are kept (BR-DOC-005, T-03.18.2).
- `documents_one_current_notice_per_member`: unique `member` where
  `superseded_at` is empty.
- `documents_notice_shape`: a `confirmed` row has a file and every
  notice value and no reason; a `did_not_file` row has a reason, no
  file, no notice value and `seen_in_person` false.

| Rule | Enforcement |
| --- | --- |
| Each adult needs accepted evidence or a required non-filing explanation for approval. | Document and approval services. |
| Record line 199 assessed income in integer cents. Do not extract SIN or document numbers. | Document entry and reading. |


Sources: [Issue #468](https://github.com/B-A-D-R-SL/iris/issues/468), [Issue #474](https://github.com/B-A-D-R-SL/iris/issues/474).

### EligibilityDecision

**Owner module:** `eligibility`.

An immutable record of calculation inputs and eligibility result.

| Field | Logical type | Key | Details |
| --- | --- | --- | --- |
| household | reference | Foreign key | Household being assessed. |
| household_size | integer | — | Household size used for the calculation. |
| adult_incomes_cents | list | — | Snapshot of the adult income inputs, in cents. |
| household_income_cents | integer | — | Sum of accepted adult incomes in cents. |
| threshold_cents | integer | — | Applied income threshold in cents. |
| threshold_year | integer | — | Threshold reference year. |
| ruleset_version | reference | Foreign key | Applied rule version. |
| eligible | boolean | — | Eligibility result. |
| decided_by_type | string | — | Whether the decision was made by a person or automatically. |
| decided_by | reference | Foreign key | Decision maker, when applicable. Nullable. |
| created_at | datetime | — | Decision recording time. |
| id | uuid | Primary key | Stable UUID identifier. |

**Documented constraints and business rules**

| Rule | Enforcement |
| --- | --- |
| Preserve the input snapshot, applied threshold, rule version, result, and time. Existing decisions are never updated. | Eligibility service/model and PostgreSQL UPDATE/DELETE rejection trigger. |
| Sum accepted income for members aged eighteen or older. Income at or below the household-size threshold is eligible. | Eligibility calculation. |
| Use the seven-or-more threshold group for households of seven or more. | Eligibility calculation. |

Sources: [Issue #457](https://github.com/B-A-D-R-SL/iris/issues/457), [Issue #460](https://github.com/B-A-D-R-SL/iris/issues/460).

### RuleSetVersion

**Owner module:** `rules`.

A preserved version of configurable business rules.

| Field | Logical type | Key | Details |
| --- | --- | --- | --- |
| rule_type | string | — | Type of settings. |
| version | integer | — | Version number. |
| values | json | — | Versioned settings; JSONB documented. |
| effective_from | datetime | — | When the version takes effect. |
| created_by | reference | Foreign key | Person who published the rule version. |
| created_at | datetime | — | Creation time. |
| id | bigint | Primary key | Bigint primary key. |

**Documented constraints and business rules**

| Rule | Enforcement |
| --- | --- |
| The combination of rule_type and version is unique. Publishing creates a new version and preserves previous versions. | Composite unique constraint, publishing service and ORM mutation refusal; no database append-only trigger. |
| Validate values against the schema for the rule type. | Rule validation service. |

**Documented indexes**

| Fields | Purpose |
| --- | --- |
| rule_type, version | Composite unique constraint provides its supporting index. |

Source: [Iteration 2 plan](https://github.com/B-A-D-R-SL/iris/blob/main/docs/06-planning/iteration-2.md).

### Category

**Owner module:** `categories`.

An approved category of goods.

| Field | Logical type | Key | Details |
| --- | --- | --- | --- |
| code | string | Unique key | Category code. |
| name_fr | string | — | French category name. |
| name_en | string | — | English category name. |
| is_food | boolean | — | Whether food-safety rules apply. |
| default_value_cents | integer | — | Default estimated monetary value in cents. |
| is_active | boolean | — | Whether the category is available for selection. |
| id | uuid | Primary key | Stable UUID identifier. |

**Documented constraints and business rules**

| Rule | Enforcement |
| --- | --- |
| A category in use can be deactivated, but cannot be deleted. | Category service; the admin API has no delete (US-35). |
| The code cannot change after creation. | `save_category()` and the admin API. |
| The default value is between 0 and the listing value limit (`listing_posting.estimated_value_max_cents`). | Category service, from the rule settings. |
| Inactive categories are hidden from the posting and partner forms; existing listings keep them. | Public `queries.list_active_categories()`. |

Source: [Issue #501](https://github.com/B-A-D-R-SL/iris/issues/501).

### Listing

**Owner module:** `listings`.

Goods offered by an active store.

| Field | Logical type | Key | Details |
| --- | --- | --- | --- |
| store | reference | Foreign key | Offering store. |
| category | reference | Foreign key | Goods category. |
| title | string | — | Listing title. |
| description | string | — | Optional description. Nullable. |
| quantity_total | integer | — | Total offered units. |
| quantity_reserved | integer | — | Reserved units. |
| unit | string | — | item or bundle. |
| max_per_household | integer | — | Quantity limit per household. |
| pickup_start | datetime | — | Pickup window start. |
| pickup_end | datetime | — | Pickup window end. |
| best_before | date | — | Required for food: pickup end date plus `listing_safety.best_before_margin_days`; non-food bypasses this safety check. Nullable. |
| photo_ref | string | — | Optional stored photo reference. Nullable. |
| estimated_value_cents | integer | — | Optional estimated value in cents. Nullable. |
| status | string | — | `published`, `closed` or `cancelled`; sold out is derived from stock counters. |
| safe_confirmed_by | reference | Foreign key | Person who confirmed listing safety. |
| safe_confirmed_at | datetime | — | Safety confirmation time. |
| published_at | datetime | — | Publication time. |
| id | uuid | Primary key | Stable UUID identifier. |
| cancelled_at | datetime | — | Time store deactivation cancelled the listing. Nullable. |
| created_by | uuid | Foreign key | User who posted the listing. PROTECT. |
| created_at | datetime | — | Creation time. |
| updated_at | datetime | — | Last-save time. |

**Documented constraints and business rules**

| Rule | Enforcement |
| --- | --- |
| quantity_total >= 1; 0 <= quantity_reserved <= quantity_total; pickup_end > pickup_start. | Database CHECK constraints. |
| Food needs a best-before date meeting the configured safety margin. Prohibited categories cannot be selected. | Listing safety rules. |
| Post for the assigned active store and record safety confirmation. | Posting permissions and service. |

Sources: [Issue #491](https://github.com/B-A-D-R-SL/iris/issues/491), [Issue #493](https://github.com/B-A-D-R-SL/iris/issues/493), [Issue #497](https://github.com/B-A-D-R-SL/iris/issues/497).

### Reservation

**Owner module:** `reservations`.

A household claim on goods from a listing.

| Field | Logical type | Key | Details |
| --- | --- | --- | --- |
| listing | reference | Foreign key | Reserved listing. |
| household | reference | Foreign key | Receiving household. |
| quantity | integer | — | Reserved units. |
| pickup_code | string | — | Six-character collection code. |
| status | string | — | Reservation status. |
| late_cancel | boolean | — | Cancellation during the pickup window. |
| made_by_type | string | — | Whether the reservation was made by the household or staff. |
| made_by | reference | Foreign key | Person who created the reservation. |
| picked_up_at | datetime | — | Collection confirmation time. Nullable. |
| confirmed_by | reference | Foreign key | Person who confirmed collection. Nullable. |
| id | uuid | Primary key | Stable UUID identifier. |
| created_at | datetime | — | Reservation creation time. |
| updated_at | datetime | — | Reservation last-save time; bulk/status-only writes do not automatically refresh it. |

**Documented constraints and business rules**

| Rule | Enforcement |
| --- | --- |
| The combination of listing and pickup_code is unique. | Composite unique constraint. |
| Stock allocation and reservation creation are atomic. Enforce household limits and approved, non-expired, non-suspended eligibility. | Reservation transaction and validation. |

**Documented indexes**

| Fields | Purpose |
| --- | --- |
| listing, pickup_code | Composite unique constraint provides a per-listing code lookup index. |

Sources: [Issue #513](https://github.com/B-A-D-R-SL/iris/issues/513), [Issue #515](https://github.com/B-A-D-R-SL/iris/issues/515), [Issue #520](https://github.com/B-A-D-R-SL/iris/issues/520).

### AuditEvent

**Owner module:** `audit`.

An accountable record of access or action.

| Field | Logical type | Key | Details |
| --- | --- | --- | --- |
| actor | reference | Foreign key | Nullable for a saved automatic household eligibility decision only; then actor_role is `system`. Human actors are saved Users. PROTECT. |
| actor_role | string | — | Role at the time of the action. |
| action | string | — | Recorded action. |
| target_type | string | — | Affected record type. |
| target_id | identifier | — | Identifier of the affected record. |
| metadata | json | — | Event details without personal data. |
| created_at | datetime | — | Event recording time. |
| id | bigint | Primary key | Bigint primary key. |

**Documented constraints and business rules**

| Rule | Enforcement |
| --- | --- |
| Events are append-only. UPDATE, DELETE and TRUNCATE are refused; metadata excludes personal data. Null actor requires system role, decision action and household target. | Database trigger/CHECK and public audit service; the service also verifies the saved automatic decision. |

Sources: [Issue #547](https://github.com/B-A-D-R-SL/iris/issues/547), [Issue #549](https://github.com/B-A-D-R-SL/iris/issues/549), [Issue #567](https://github.com/B-A-D-R-SL/iris/issues/567).

### EmailLog

**Owner module:** `notifications`.

Email-delivery status without retained email content.

| Field | Logical type | Key | Details |
| --- | --- | --- | --- |
| id | UUID | Primary key | One delivery's stable identifier across retries. |
| to_email | string | — | Recipient address. A failed validation record may retain a database-safe malformed address; empty when the input cannot be represented safely in this field. |
| user | reference | Foreign key | Optional account; `SET_NULL` preserves delivery metadata when the user is deleted. Nullable. |
| template_key | string | — | Template used. |
| language | string | — | Captured recipient preference, `fr` or `en`. |
| status | string | — | `pending`, `sending`, `retrying`, `sent` or `failed`. |
| attempts | integer | — | Transport attempts started by the worker, initially zero; distinct from the queue's execution count. |
| error | string | — | Bounded internal error code; no provider exception text. |
| sent_at | datetime | — | Set after transport/provider acceptance; unset for other statuses. This is not inbox-delivery confirmation. Nullable. |
| created_at | datetime | — | Delivery record creation time. |
| updated_at | datetime | — | Last delivery-state update. |

**Documented constraints and business rules**

| Rule | Enforcement |
| --- | --- |
| Record delivery information without subject, body, rendering context or token fields. | Notification service. |
| Send after the originating transaction commits; use the documented retry schedule. | Background notification jobs. |
| Only `fr` or `en`; sent records have `sent_at`, other statuses do not. | Database CHECK constraints. |
| Filter delivery outcomes by status and creation time. | Index `notifications_status_created` on (`status`, `created_at`). |

The protected EmailLog table may retain a recipient address; application stdout
logs may not. Restricted queue payloads temporarily hold only the rendering
context needed for delivery and the captured retry list. Hourly terminal-job
cleanup preserves EmailLog metadata; general log retention and the staff failed
email interface remain separate work. See [notification rules](../02-requirements/business-rules.md#notifications-us-57).

Sources: [Issue #538](https://github.com/B-A-D-R-SL/iris/issues/538), [Issue #541](https://github.com/B-A-D-R-SL/iris/issues/541).

## Cross-model constraints and deletion rules

| Area | Database and service boundary |
| --- | --- |
| IDs | UUIDs except bigint IDs for RuleSetVersion, AuditEvent and HouseholdDraftEvent |
| User / Invitation | Store-role assignment CHECK on both; User email is unique and has an additional `Lower(email)` unique constraint; Invitation token hash is unique |
| Store / application | At most one `is_badr=true` Store; optional application one-to-one; partial unique submitted contact email; application consent/category/status/rejection checks |
| Household / Member | Optional unique holder User and member number; partial unique holder Member per household; walk-in account-link refusal is model validation, not a SQL CHECK |
| IncomeNotice | Partial unique current notice per member; CHECK enforces confirmed versus non-filer shape; superseded rows/files remain |
| EligibilityDecision | Positive household size/threshold, nonnegative total, valid decider type and actor-null consistency CHECKs; snapshot consistency validated by model/service; ORM and PostgreSQL append-only protection |
| RuleSetVersion | Unique `(rule_type, version)`; active lookup index `(rule_type, effective_from, version)`; ORM rejects updates/deletes; unlike AuditEvent and EligibilityDecision it has no append-only database trigger |
| Listing | Bounded quantities/value, `0 <= quantity_reserved <= quantity_total`, end after start, valid unit/status CHECKs; publication and food rules in services/domain |
| Reservation | Unique `(listing, pickup_code)`; positive quantity and valid status/made-by type CHECKs; household and per-listing limits in service transaction |
| AuditEvent | Database append-only trigger; null actor only for `system` / `decision` / `household`; public service validates saved automatic decision and metadata |
| EmailLog | Valid language CHECK; `sent_at` required exactly when status is sent; outcome/time index; `sent` is transport acceptance |

All concrete FKs use Django `PROTECT`, with three exceptions:
`Member.household` uses `CASCADE`, while `Invitation.invited_by` and
`EmailLog.user` use `SET_NULL`. Protected notice/history references can still
prevent deletion of a household/member. `on_delete` describes Django's deletion
behavior; it is not a claim that PostgreSQL uses identical SQL cascade clauses.

Household search adds four stored generated search columns on Household, one
on Member, and six trigram GIN indexes including phone. Migrations install
`pg_trgm` and `unaccent`; generated keys are internal and excluded from APIs.

## Relationships in plain language

Each row corresponds to one concrete FK. A parent may have zero children;
a nullable FK permits no parent. `on_delete` is Django deletion behavior,
not a claim of identical PostgreSQL cascade clauses.

| Parent | Child.field | Cardinality | Nullable FK | Django on_delete |
| --- | --- | --- | --- | --- |
| Store | User.store | One-to-many | Yes | PROTECT |
| Store | Invitation.store | One-to-many | Yes | PROTECT |
| User | Invitation.invited_by | One-to-many | Yes | SET_NULL |
| PartnerApplication | Store.application | One-to-one | Yes | PROTECT |
| User | PartnerApplication.decided_by | One-to-many | Yes | PROTECT |
| User | Household.holder | One-to-one | Yes | PROTECT |
| User | Household.created_by | One-to-many | Yes | PROTECT |
| User | Household.verified_by | One-to-many | Yes | PROTECT |
| Household | Member.household | One-to-many | No | CASCADE |
| Household | HouseholdDraftEvent.household | One-to-many | No | PROTECT |
| User | HouseholdDraftEvent.actor | One-to-many | No | PROTECT |
| Member | IncomeNotice.member | One-to-many | No | PROTECT |
| User | IncomeNotice.recorded_by | One-to-many | No | PROTECT |
| Household | EligibilityDecision.household | One-to-many | No | PROTECT |
| RuleSetVersion | EligibilityDecision.ruleset_version | One-to-many | No | PROTECT |
| User | EligibilityDecision.decided_by | One-to-many | Yes | PROTECT |
| User | RuleSetVersion.created_by | One-to-many | No | PROTECT |
| Store | Listing.store | One-to-many | No | PROTECT |
| Category | Listing.category | One-to-many | No | PROTECT |
| User | Listing.safe_confirmed_by | One-to-many | No | PROTECT |
| User | Listing.created_by | One-to-many | No | PROTECT |
| Listing | Reservation.listing | One-to-many | No | PROTECT |
| Household | Reservation.household | One-to-many | No | PROTECT |
| User | Reservation.made_by | One-to-many | No | PROTECT |
| User | Reservation.confirmed_by | One-to-many | Yes | PROTECT |
| User | AuditEvent.actor | One-to-many | Yes | PROTECT |
| User | EmailLog.user | One-to-many | Yes | SET_NULL |

## ERD

The existing diagram now includes all 15 models, their concrete fields and all
27 application foreign keys. Fields match the tables above; UUID/bigint
identify the stored key types. `FK, UK` denotes a one-to-one relationship.
An optional parent endpoint reflects SQL nullability. Partial uniqueness
(one holder Member or current notice) remains in the constraint notes.

[Open the ERD diagram](https://mermaid.live/view#pako:eJzFPAtv3DbSf4XwoWiCb9fxOo9r7cMBzuOu-c5t8vnRAh8CCFyJu8taEhVKsr1N8t9vZvgQtaJ2N3UOFxT1io8hOe8ZjvTpIFWZODg5-O67T7KUzQn79OGgWYlCfDg4YR8O5ryGXxNmG3_lWvJ5Lmrs_YTd6c1Sq7bMzPC_HM1nx8dHZkalZcH1-pXKlbbdsxdPnz5_1uu-EvdNOGRB_3pDXiqdCR0OevHsr89-mJtBuSxF2MePuEjtFpotwLW6e5e5fc-eHf_wVPiON7ei3Oj58uXLd999KIV-LflS8-JDyeDfZaO0YOrzdKo-setaaHbCamyLdL8tb2XDG6nK_iCaFhsj8UFkyXxtBr7nuoENnFVVLlMziKZ9tuucMN51DWFHpp-wTKQyC9boJnxmP6m2FiuVZzAO_wg9BBqOSbXgTRRWf9yt0HIhg4Fd52cz-mdRzAmXK9czMtA3vNZ80SDZmuEs2sfWCTwFBJrBdunPjh6pKsQvqpEp4regziHUjWFapMiyWw74JpdLOZe5bNavgQK1IcbGvi_aXFyK5lehqX_rVA1ja9Ekt2bwkADxaVHy24U2lh_S13CdHX0u60aWyz5rv4LxS6XXw0Gp7RkuGwDiC5GkqlxIXYzsMQC4sTnX4w4D2NG3jutz0zlCnP7YLczUH1jwTER5vz9s5EB27FmbyRhb9khZcJmfKzw1bA0GBEM-md_4r240IqDidX0H7AjK7PXvvFyqacFLvhQZEyUq_6wbseL1agJqJ81hFzAVn_FvIRqe8YafslIAgzGwBazKuSynqGD9_ENmFoCVeZlxAAhSnmcn7Jfr83Mma1aqhvE8V3ciO_xw0O0UYItGFoLlvG6SXC1lCbv9WdUNihLiopbLcgqtOOrULcNb2EjZOGXmdnnIfmnzHM1Ub5G5UrngJewjqdtKaESdxwmDhkLWxOjzNR6ILXK-PGUZcUrasIVWBR38rYaT8KyA3Wi1sYZFOdAXzlFyONGHAyILtTBsiY2nY4fDsWE4OjxBwxeLbve0nWkN1gJ4JhW7dj_YdwAZeE7e4kZ-WwmYYIgNQMHIN0hD09-b3bYyY_Df-3_BtMsGMc-qdg5WhvgTupBKwAs6dniB3Myuce4r8DaAyrUo4Si4i7aUH1vhqU9DYzCqlSpxz69U2cAG7XPZoraOjtdiIbQGGcwBfy1IA0xegIBpEApAm1jwNkesxSYj9tA1EqVYyFSCgzIxOs9QxT0YKdMoTw2_EQlIyA0-whpEriEKaR77B2LiQnxsJeyPLWC4aTckB8FiFnIN4mgZnYYpIhfurgZJFLkgqQCSVVo1IgXlyO5WEgYjUYAJEAWgAgRRmNaIC6XTrLxBDOMDwsWu-Pi2yrrx58DJ05oDLXsTvjilFTg8n7Zz1PX129d7sRJiL5WVRL0xyjE9Ee3G7y-n3Zy4sPaZ5QL_gFYBRgYywGFRTCtQk2lElAI-eFchanhu2wyEAlYdUXJ21UbdiDJB9W0E6_Kns-nx8xek0JlaEMVlh3kafkrqGXs0vzNNcfqK-wpYszb0fYMPBgpSGVlMINPVrcgmwGm0G9IgJNDdovWhh7NohE4yvq7Ji4kvavDluOrMY89ahBaURsPmYkFY6nAbx5JhL-9dG1S_B6GAU9ytlN3-BpYm5mjWxUaQQ-CerY1r9HCOtsxmwI3xGPwR4PoZdYcyKm9B9Y5rPzfewcanUeCgghHj1_gHdVELSNvOfCm4mLQL-DMGtQLbzvME_Q9EPT0xfPoW2t2pATd-qAR-R0qrSpQwPAEHD9QhGDwhbvI1q9OVyIAP2f9evvtlgvTW6hZ2B9Ih6qkqYYjpQWNRVHBIcIVSYQKk6PZletNWCdi1Rrcp8T6s9jZ8RPWdqjwHLY0zlkpl9W43Zs4zJPdbx0E1cezLw7PD14cXhxGVvsvMGyWzxcgH8SUIzcQoF7dNUGti2qgpEqdRBDAScjYrkGBrUoJFH8Hx26IMV0hk9viQXaJcr2nk9eV09tQTxFg_Qp0_srWOLTiZa78ILQDofH_x7urNq6s9jJwRt_Qbm7oIMsYUxHuT-GA3Yh3jqDnqVfDynAgfI75nz49YuuIaaAeabOu0Zl3htKVWqSDvBf1hWPBGNBM2B2cFGwFnDW81L6EthUhsgpELBCYSfYaEkDoBUeQwMYXhC_iRAGWyNkUvB-LhAlXHOlF6yUv5h9Wh5KRENZ34CFv6v1bMRQpOGJyhAlfVifkErA4cDKg6OwKvdimb6Ak3NeFLe2LwuDI4D3hMVadqDGMAU9fsbHbGZmez3cryGwC0CvUbQLKK9htA6qvjb7E1o3qTnpt1LhpkTeC3ChRmjboV4GpVrfBhtYa_ZZSsDlrofz0YmPXMvIc1Fsy58c6qnEP4qlOIVE7B38C0Tx2oMeuaf1_7mIW8G6-0ti3gzRzAyCSoacvGAOTN4ezFswnpOpCDooKd_8_s-ezZ8-fPj2bHT2NQ78Sc4sEPB6umqeqTJ0-QnEA4uWAU6ZbL3jRMiRjDk9jcDBoU76u4fA3xAHAEaDwwJTAF9gzCydOVc_Ggp27nNpiOmuf7iqKRZKEhygFtgkycAXJBi9yRDZ6wAnCywh8qBVQTgWKgNk34P0BWGeYk-rj6Pm_LKagu9iNbTWc_sNX3MWBAydpEgp4nAGPS_pQlQCxIi0VtKlAR4tYmsdQ07ge2oG6eC0dlkZ2yoq3RV2Vg_8HwnYO3ffzc5gwBA7JZBdbocTwOCYPWRzZcfezCV99tPX3i3NrZZLuRCXm6EBCAY-Pi-7j-402LuCWiNmhQ_YLOO0JXX4vfiaoxGJlNOCZwLPS8gviWfOroXDKIXX7SOOlnGDkDp0LIAYfFE9gR7BF5B493mHkHjwy2z4NSlwOwh3vg2XvE0ncZxQdEADTeeJWdr-U503ZgtmgSSfPYbpPMPmS_8fwGlVEuyxskiKTwHzaZoW9VgEjnDLSTzIi_T20ERSObOowUMyVMGq9SVZsDSmA1AEZ5vkN00H58yh795a9HoKwuBCqIw8O4qOG-nJ3un6xeKY2BeO5d_O3RxoqXpTBR_9JwBm7UNp-wO3t0TJCUeFe0lck7ytEGTPu2GGOTINR-SlKs2gbQx7jfAiAKE8GUAABPhjdWHlv0drafckfCiihJGo9EfVsQ1Z0wDcOp_1Zc2anaCtxjzGzgmbDz24SWvxquRg1Vov7O5R-AKm9iq-2Rp3WAEvDDMdDpANiOMFmOe54YSoCmXUgIRQB6LVHOs9b4_CLutQqu05VxMOxSl8bJWgoIGCiICTZvWA_GnWJqUWgSGgLh5HAbJ9nFDBX3WM2I6tQywQNX7eNzsKxH09QOdCuMxEEbUOkyIgJ2ARvbhIhjoxTP6WyNcGzcMajrIUEzQX2UnB0IJ3MPgTFQNLth-DCfDAuEYOlKpDegO2SZVCbLRRZosWC2B3UAMC0ao5KZIZQOpNsfPkdNRpcHr0mHEX5H7KT1gvAeBqNBvItAB43s5m9o6-nuyGyCL0FDkLTgcNYNZ4-syjzBTeCdKphfELpctdnjU5t1Aa0JiFmCy1nusBB2T0hydz-KmsH-sk5S6rw1ZCJKUtzxmtbt-5LHR8cvprPZ9HZG9u74CHx-NKG3HgR5WhwYDTQaksl4dgytpY5jzbtWcf8ifrouNWp9MJsadfmqfab2Url-puhyuluA9Exn59l18ZRpQdwRflswX3iTNzSp5Ol097eDdGyYLVr1DPS2_G5QZWAgGo43-szAtcxPeV4rK7sw5qESyt7aWQbUftQqVbkuULUaEFfYaAQCkEaCYBgPWWpMq8b90g3n5c_kr8hvWvr8HeF44N7aEomH-7Zuu0SeDcdElubqABSOIdnOWxy7rf2vcOyE-P0NIob-l6hFMpcaojK6nDX6SjR4XwzKHTyx6LWPyA3u0S01P-uVrMgvlGWfk6NODDHE0O-wmtNx60PcDTzxHvafcEVmX9yjqwP-v8EG4mYPpvRK3wker00i4s9x5AYvDEOuoK4nYNC5XEq8v7Ys-tI8ViNp1hh7EtzOMDidhJYhk9HYlao3RlQPHwuVeWrZxi4wcRgxly_WTozMVNplta5WQpq7YBNmwP8KRfeGe1IMnPMVGBbgiGyI7F6505gasN2dBmAu3jTpMsQI6SkMSofYs8gi9P3sEVfjjRwuzsQtQk6FiWVNvdXW0M7X3bBHYORa4GOKlrl1MSh7ksksgcekp_dCYKrVKQU35gf4Dm5tZoCe2pPBoTWJZ20a4torF2A4F2Q1ORY6AEPeot5BFwtjvO6O_pE59tRstn7yN83LTBV_f-xqcji7vjhn1tiC_CuOmzJh9KZuQwd-iXc-_D5ZgzZAhuH3jH5qAbEmujGjxsfKUqMwzDLbSlLye0BiUSfOfvwRb6rBl8N0Iw04YT-jUscbebQO8tTvgWZudzFIU4E2tL4gsBbqJI94ZfSL6d0REfbABNeO-0Aji2DaE_rd8Xhdt3QZTTpx-71dLUTZc8TdBZzhmxrv3v36nTseTasF3BpJrYEbl0OcS_oEvTDk9HIKg01k2-bNUOqCysVQc1EZD-otjybKKyKPf40JMEJh3JuIxAb-MB5aZD0AsH1xhxkWAgJsireumfEQIMxyYcGmv2kJueWuPlYZ-R_zbeaCsG-lIyqVfm5SgwXuzaYGn-yhY_I8bfNhWprS-URkK6K1l9HLklc1xHsu8qFRTq3KsmobymtYyYxIfrfBDem_bAsE6mo1epDrrSCbFSgdAulg0TWp1x_dgDgYr9E8HKfX_LxOl2JXbBMbNbQ242z3gZ3M9kQFWxAbkfUNOAqvUTclLciKG1FzF7LhXbzLmZO4YGkpWk7uHEAU57ZReB-R4mX37sy5Z-2CUxna7mKWcYH2sIwYk6MeTYRvlBD_aYfMedUAzuHqCv8AswHBMFEdZ4dhtB_JXlIxiHUJ_ECsG7CQT6ne4yXLVNoWxjDGg-nFQtAVWEKORaD33DawDrC2474qAqZqynpl9e4oK35NyZ6nka_Rfni1EllSW8kZXBeO2vSFNnd2ZbrqLhjHIjeaIZCWb8olYmPLlKDQZaFUFogWPk6xsBxFE-WdZGAdUwf2lish1vB66bWtDRU1oJMc8wK4pUGupYEjam5H5Y0_Chbf3HLZVXXWgqqCAkp7yrkS94caq7DeEHjTus2bxUOGR90-afQ_8brYt8WIBkEqaUS3VXqOK8M61bKywY9PIgXNIxrKifpH8MAo2Ul-KSoI-qvwQEAkzM7HdYSfqIW9nUEfyv4cTutfX0DkV6AynrdlNrKxApxs0NpJ5xJgmYtZE8w0BHSo1EfSAV6ibREZOIka131Pj-wOwn51x6h16zxRZoNZ0Db0b-fA14mto9woQ0bRObEAcbKZUOUQXdn3KRIjWIcBkAT0OUgTlXeeGgcUBdLU2FPpBGaUjTxSEm3HPRjmqX3MFNbGuhy2N_Pboxcvvhvi7YF28r0h1ntkQwGO19gTluaqNvF7ikFCnmMNQI2MQDeENTA5hH2IZDQbcJj0xl0KRvKkg5dihulSH-haslj8jvjafXgmAW3pYVp3JRH9Uc3k91T5v2uSR0WQBTV6KBOkIe01rhtGWtKeZ1vWd9OIXrvIBYPATTD7VwR-67L38JWgh6pvR2X74oDVXO6Qu0KTC5EKeUtv-0Q10Kaa3Es7Wq1j72Av5f3UVyb6Olek7ohz4KUoRFPk4sBZVbxaSQyrkO9BPGMLFlrtStCrUPtFqxLMC1wxb1wHGwkd8v6VhNKRZI_JZhnQW682gjXGdTkwGCDW8GSIyE1J3SYi-ymPjk5fFRuEJPvaG4hwbt6ToFOwsPnNE8MDpgj7ToPxBeWpzGtlYTSERgDDPhZUEXjRC96we1iCOMjv-hJok2cxb0L4LQUcIoLI0Ed4eJxTZIEyTOKiXVyDzioO2U9twW0fuIf4LhAtgLptpK45lhO-8Nlgg1Mf_6cDlttMRl-4tM_4WHBBlhA7W9k5oxhHuIQSw-Yts2TGgjp27XfWhzKM2twrfxgUEEUzaMBaN1d_07tY24N7DZRdYa1_AXNMdb8r0Y7lYNX1-nvKACNzBKlwnmpVYxqswTLLKGZUMnydyRYxHLIztoA-45zYqi2HaryO1ogGTJnhsfEdfgp5oCvHIsaufsUlze5cpErpH7S6KFNzEWaDyVMA2aLrK1_zNZAKShX2312y1YWn7PLNVULvglbW1649ljpS-r2YdwdpiBjPRjt0wUHIDJgbrSv7SMmy-D2gL6N6xaum1YbLLJ4r70VOmKuy2u7ugT8MDRMI1-wPJO3aNVFRk6FY1LjyBvdPDuiV5mVdYQmcbyT3vrs6cS8S4vcaJKm7P4RWsZc9P7aiFcB_4l6krTUUI2WeQmtFFfP4MQdKu9kaH9OBlhrddyzSwIsXrIegEkFU7pulNJ1viWUXxqMUja2Ebtz5nnhQ3fta7kWu7nVGg2F8feMKmc6-RCzLubqfet4Jzd9XJrIsBCs7f-rK3G1jint1AzqlcTA5KPDtCpkdnBwEX9fwH9eIfFtj89Ma4Zc1Bh_WCL-rEf2sRvjhi5GPaoTf1Oh_UiP8okb_gxp9sP5zGuHXNMKPafS-pQFIWWrEyILntZgcVLz8f6WKgxOsiZ7ArHa58p0Go_a7G2bIl38Deggfwg)

[Edit the ERD source](https://mermaid.live/edit#pako:eJzFPAtv3DbSf4XwoWiCb9fxOo9r7cMBzuOu-c5t8vnRAh8CCFyJu8taEhVKsr1N8t9vZvgQtaJ2N3UOFxT1io8hOe8ZjvTpIFWZODg5-O67T7KUzQn79OGgWYlCfDg4YR8O5ryGXxNmG3_lWvJ5Lmrs_YTd6c1Sq7bMzPC_HM1nx8dHZkalZcH1-pXKlbbdsxdPnz5_1uu-EvdNOGRB_3pDXiqdCR0OevHsr89-mJtBuSxF2MePuEjtFpotwLW6e5e5fc-eHf_wVPiON7ei3Oj58uXLd999KIV-LflS8-JDyeDfZaO0YOrzdKo-setaaHbCamyLdL8tb2XDG6nK_iCaFhsj8UFkyXxtBr7nuoENnFVVLlMziKZ9tuucMN51DWFHpp-wTKQyC9boJnxmP6m2FiuVZzAO_wg9BBqOSbXgTRRWf9yt0HIhg4Fd52cz-mdRzAmXK9czMtA3vNZ80SDZmuEs2sfWCTwFBJrBdunPjh6pKsQvqpEp4regziHUjWFapMiyWw74JpdLOZe5bNavgQK1IcbGvi_aXFyK5lehqX_rVA1ja9Ekt2bwkADxaVHy24U2lh_S13CdHX0u60aWyz5rv4LxS6XXw0Gp7RkuGwDiC5GkqlxIXYzsMQC4sTnX4w4D2NG3jutz0zlCnP7YLczUH1jwTER5vz9s5EB27FmbyRhb9khZcJmfKzw1bA0GBEM-md_4r240IqDidX0H7AjK7PXvvFyqacFLvhQZEyUq_6wbseL1agJqJ81hFzAVn_FvIRqe8YafslIAgzGwBazKuSynqGD9_ENmFoCVeZlxAAhSnmcn7Jfr83Mma1aqhvE8V3ciO_xw0O0UYItGFoLlvG6SXC1lCbv9WdUNihLiopbLcgqtOOrULcNb2EjZOGXmdnnIfmnzHM1Ub5G5UrngJewjqdtKaESdxwmDhkLWxOjzNR6ILXK-PGUZcUrasIVWBR38rYaT8KyA3Wi1sYZFOdAXzlFyONGHAyILtTBsiY2nY4fDsWE4OjxBwxeLbve0nWkN1gJ4JhW7dj_YdwAZeE7e4kZ-WwmYYIgNQMHIN0hD09-b3bYyY_Df-3_BtMsGMc-qdg5WhvgTupBKwAs6dniB3Myuce4r8DaAyrUo4Si4i7aUH1vhqU9DYzCqlSpxz69U2cAG7XPZoraOjtdiIbQGGcwBfy1IA0xegIBpEApAm1jwNkesxSYj9tA1EqVYyFSCgzIxOs9QxT0YKdMoTw2_EQlIyA0-whpEriEKaR77B2LiQnxsJeyPLWC4aTckB8FiFnIN4mgZnYYpIhfurgZJFLkgqQCSVVo1IgXlyO5WEgYjUYAJEAWgAgRRmNaIC6XTrLxBDOMDwsWu-Pi2yrrx58DJ05oDLXsTvjilFTg8n7Zz1PX129d7sRJiL5WVRL0xyjE9Ee3G7y-n3Zy4sPaZ5QL_gFYBRgYywGFRTCtQk2lElAI-eFchanhu2wyEAlYdUXJ21UbdiDJB9W0E6_Kns-nx8xek0JlaEMVlh3kafkrqGXs0vzNNcfqK-wpYszb0fYMPBgpSGVlMINPVrcgmwGm0G9IgJNDdovWhh7NohE4yvq7Ji4kvavDluOrMY89ahBaURsPmYkFY6nAbx5JhL-9dG1S_B6GAU9ytlN3-BpYm5mjWxUaQQ-CerY1r9HCOtsxmwI3xGPwR4PoZdYcyKm9B9Y5rPzfewcanUeCgghHj1_gHdVELSNvOfCm4mLQL-DMGtQLbzvME_Q9EPT0xfPoW2t2pATd-qAR-R0qrSpQwPAEHD9QhGDwhbvI1q9OVyIAP2f9evvtlgvTW6hZ2B9Ih6qkqYYjpQWNRVHBIcIVSYQKk6PZletNWCdi1Rrcp8T6s9jZ8RPWdqjwHLY0zlkpl9W43Zs4zJPdbx0E1cezLw7PD14cXhxGVvsvMGyWzxcgH8SUIzcQoF7dNUGti2qgpEqdRBDAScjYrkGBrUoJFH8Hx26IMV0hk9viQXaJcr2nk9eV09tQTxFg_Qp0_srWOLTiZa78ILQDofH_x7urNq6s9jJwRt_Qbm7oIMsYUxHuT-GA3Yh3jqDnqVfDynAgfI75nz49YuuIaaAeabOu0Zl3htKVWqSDvBf1hWPBGNBM2B2cFGwFnDW81L6EthUhsgpELBCYSfYaEkDoBUeQwMYXhC_iRAGWyNkUvB-LhAlXHOlF6yUv5h9Wh5KRENZ34CFv6v1bMRQpOGJyhAlfVifkErA4cDKg6OwKvdimb6Ak3NeFLe2LwuDI4D3hMVadqDGMAU9fsbHbGZmez3cryGwC0CvUbQLKK9htA6qvjb7E1o3qTnpt1LhpkTeC3ChRmjboV4GpVrfBhtYa_ZZSsDlrofz0YmPXMvIc1Fsy58c6qnEP4qlOIVE7B38C0Tx2oMeuaf1_7mIW8G6-0ti3gzRzAyCSoacvGAOTN4ezFswnpOpCDooKd_8_s-ezZ8-fPj2bHT2NQ78Sc4sEPB6umqeqTJ0-QnEA4uWAU6ZbL3jRMiRjDk9jcDBoU76u4fA3xAHAEaDwwJTAF9gzCydOVc_Ggp27nNpiOmuf7iqKRZKEhygFtgkycAXJBi9yRDZ6wAnCywh8qBVQTgWKgNk34P0BWGeYk-rj6Pm_LKagu9iNbTWc_sNX3MWBAydpEgp4nAGPS_pQlQCxIi0VtKlAR4tYmsdQ07ge2oG6eC0dlkZ2yoq3RV2Vg_8HwnYO3ffzc5gwBA7JZBdbocTwOCYPWRzZcfezCV99tPX3i3NrZZLuRCXm6EBCAY-Pi-7j-402LuCWiNmhQ_YLOO0JXX4vfiaoxGJlNOCZwLPS8gviWfOroXDKIXX7SOOlnGDkDp0LIAYfFE9gR7BF5B493mHkHjwy2z4NSlwOwh3vg2XvE0ncZxQdEADTeeJWdr-U503ZgtmgSSfPYbpPMPmS_8fwGlVEuyxskiKTwHzaZoW9VgEjnDLSTzIi_T20ERSObOowUMyVMGq9SVZsDSmA1AEZ5vkN00H58yh795a9HoKwuBCqIw8O4qOG-nJ3un6xeKY2BeO5d_O3RxoqXpTBR_9JwBm7UNp-wO3t0TJCUeFe0lck7ytEGTPu2GGOTINR-SlKs2gbQx7jfAiAKE8GUAABPhjdWHlv0drafckfCiihJGo9EfVsQ1Z0wDcOp_1Zc2anaCtxjzGzgmbDz24SWvxquRg1Vov7O5R-AKm9iq-2Rp3WAEvDDMdDpANiOMFmOe54YSoCmXUgIRQB6LVHOs9b4_CLutQqu05VxMOxSl8bJWgoIGCiICTZvWA_GnWJqUWgSGgLh5HAbJ9nFDBX3WM2I6tQywQNX7eNzsKxH09QOdCuMxEEbUOkyIgJ2ARvbhIhjoxTP6WyNcGzcMajrIUEzQX2UnB0IJ3MPgTFQNLth-DCfDAuEYOlKpDegO2SZVCbLRRZosWC2B3UAMC0ao5KZIZQOpNsfPkdNRpcHr0mHEX5H7KT1gvAeBqNBvItAB43s5m9o6-nuyGyCL0FDkLTgcNYNZ4-syjzBTeCdKphfELpctdnjU5t1Aa0JiFmCy1nusBB2T0hydz-KmsH-sk5S6rw1ZCJKUtzxmtbt-5LHR8cvprPZ9HZG9u74CHx-NKG3HgR5WhwYDTQaksl4dgytpY5jzbtWcf8ifrouNWp9MJsadfmqfab2Url-puhyuluA9Exn59l18ZRpQdwRflswX3iTNzSp5Ol097eDdGyYLVr1DPS2_G5QZWAgGo43-szAtcxPeV4rK7sw5qESyt7aWQbUftQqVbkuULUaEFfYaAQCkEaCYBgPWWpMq8b90g3n5c_kr8hvWvr8HeF44N7aEomH-7Zuu0SeDcdElubqABSOIdnOWxy7rf2vcOyE-P0NIob-l6hFMpcaojK6nDX6SjR4XwzKHTyx6LWPyA3u0S01P-uVrMgvlGWfk6NODDHE0O-wmtNx60PcDTzxHvafcEVmX9yjqwP-v8EG4mYPpvRK3wker00i4s9x5AYvDEOuoK4nYNC5XEq8v7Ys-tI8ViNp1hh7EtzOMDidhJYhk9HYlao3RlQPHwuVeWrZxi4wcRgxly_WTozMVNplta5WQpq7YBNmwP8KRfeGe1IMnPMVGBbgiGyI7F6505gasN2dBmAu3jTpMsQI6SkMSofYs8gi9P3sEVfjjRwuzsQtQk6FiWVNvdXW0M7X3bBHYORa4GOKlrl1MSh7ksksgcekp_dCYKrVKQU35gf4Dm5tZoCe2pPBoTWJZ20a4torF2A4F2Q1ORY6AEPeot5BFwtjvO6O_pE59tRstn7yN83LTBV_f-xqcji7vjhn1tiC_CuOmzJh9KZuQwd-iXc-_D5ZgzZAhuH3jH5qAbEmujGjxsfKUqMwzDLbSlLye0BiUSfOfvwRb6rBl8N0Iw04YT-jUscbebQO8tTvgWZudzFIU4E2tL4gsBbqJI94ZfSL6d0REfbABNeO-0Aji2DaE_rd8Xhdt3QZTTpx-71dLUTZc8TdBZzhmxrv3v36nTseTasF3BpJrYEbl0OcS_oEvTDk9HIKg01k2-bNUOqCysVQc1EZD-otjybKKyKPf40JMEJh3JuIxAb-MB5aZD0AsH1xhxkWAgJsireumfEQIMxyYcGmv2kJueWuPlYZ-R_zbeaCsG-lIyqVfm5SgwXuzaYGn-yhY_I8bfNhWprS-URkK6K1l9HLklc1xHsu8qFRTq3KsmobymtYyYxIfrfBDem_bAsE6mo1epDrrSCbFSgdAulg0TWp1x_dgDgYr9E8HKfX_LxOl2JXbBMbNbQ242z3gZ3M9kQFWxAbkfUNOAqvUTclLciKG1FzF7LhXbzLmZO4YGkpWk7uHEAU57ZReB-R4mX37sy5Z-2CUxna7mKWcYH2sIwYk6MeTYRvlBD_aYfMedUAzuHqCv8AswHBMFEdZ4dhtB_JXlIxiHUJ_ECsG7CQT6ne4yXLVNoWxjDGg-nFQtAVWEKORaD33DawDrC2474qAqZqynpl9e4oK35NyZ6nka_Rfni1EllSW8kZXBeO2vSFNnd2ZbrqLhjHIjeaIZCWb8olYmPLlKDQZaFUFogWPk6xsBxFE-WdZGAdUwf2lish1vB66bWtDRU1oJMc8wK4pUGupYEjam5H5Y0_Chbf3HLZVXXWgqqCAkp7yrkS94caq7DeEHjTus2bxUOGR90-afQ_8brYt8WIBkEqaUS3VXqOK8M61bKywY9PIgXNIxrKifpH8MAo2Ul-KSoI-qvwQEAkzM7HdYSfqIW9nUEfyv4cTutfX0DkV6AynrdlNrKxApxs0NpJ5xJgmYtZE8w0BHSo1EfSAV6ibREZOIka131Pj-wOwn51x6h16zxRZoNZ0Db0b-fA14mto9woQ0bRObEAcbKZUOUQXdn3KRIjWIcBkAT0OUgTlXeeGgcUBdLU2FPpBGaUjTxSEm3HPRjmqX3MFNbGuhy2N_Pboxcvvhvi7YF28r0h1ntkQwGO19gTluaqNvF7ikFCnmMNQI2MQDeENTA5hH2IZDQbcJj0xl0KRvKkg5dihulSH-haslj8jvjafXgmAW3pYVp3JRH9Uc3k91T5v2uSR0WQBTV6KBOkIe01rhtGWtKeZ1vWd9OIXrvIBYPATTD7VwR-67L38JWgh6pvR2X74oDVXO6Qu0KTC5EKeUtv-0Q10Kaa3Es7Wq1j72Av5f3UVyb6Olek7ohz4KUoRFPk4sBZVbxaSQyrkO9BPGMLFlrtStCrUPtFqxLMC1wxb1wHGwkd8v6VhNKRZI_JZhnQW682gjXGdTkwGCDW8GSIyE1J3SYi-ymPjk5fFRuEJPvaG4hwbt6ToFOwsPnNE8MDpgj7ToPxBeWpzGtlYTSERgDDPhZUEXjRC96we1iCOMjv-hJok2cxb0L4LQUcIoLI0Ed4eJxTZIEyTOKiXVyDzioO2U9twW0fuIf4LhAtgLptpK45lhO-8Nlgg1Mf_6cDlttMRl-4tM_4WHBBlhA7W9k5oxhHuIQSw-Yts2TGgjp27XfWhzKM2twrfxgUEEUzaMBaN1d_07tY24N7DZRdYa1_AXNMdb8r0Y7lYNX1-nvKACNzBKlwnmpVYxqswTLLKGZUMnydyRYxHLIztoA-45zYqi2HaryO1ogGTJnhsfEdfgp5oCvHIsaufsUlze5cpErpH7S6KFNzEWaDyVMA2aLrK1_zNZAKShX2312y1YWn7PLNVULvglbW1649ljpS-r2YdwdpiBjPRjt0wUHIDJgbrSv7SMmy-D2gL6N6xaum1YbLLJ4r70VOmKuy2u7ugT8MDRMI1-wPJO3aNVFRk6FY1LjyBvdPDuiV5mVdYQmcbyT3vrs6cS8S4vcaJKm7P4RWsZc9P7aiFcB_4l6krTUUI2WeQmtFFfP4MQdKu9kaH9OBlhrddyzSwIsXrIegEkFU7pulNJ1viWUXxqMUja2Ebtz5nnhQ3fta7kWu7nVGg2F8feMKmc6-RCzLubqfet4Jzd9XJrIsBCs7f-rK3G1jint1AzqlcTA5KPDtCpkdnBwEX9fwH9eIfFtj89Ma4Zc1Bh_WCL-rEf2sRvjhi5GPaoTf1Oh_UiP8okb_gxp9sP5zGuHXNMKPafS-pQFIWWrEyILntZgcVLz8f6WKgxOsiZ7ArHa58p0Go_a7G2bIl38Deggfwg)

The first link opens the diagram-only view, without saved pan/zoom offsets.
Use zoom to inspect individual tables; the editable source is the same diagram
as the Markdown below. Detailed field explanations remain in the tables above.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#0b1220", "primaryColor": "#163354", "primaryTextColor": "#ffffff", "primaryBorderColor": "#64748b", "lineColor": "#a0aec0", "textColor": "#ffffff", "rowOdd": "#14283e", "rowEven": "#14283e"}}}%%
erDiagram
    Store o|--o{ User : store
    Store o|--o{ Invitation : store
    User o|--o{ Invitation : invited_by
    PartnerApplication o|--o| Store : application
    User o|--o{ PartnerApplication : decided_by
    User o|--o| Household : holder
    User o|--o{ Household : created_by
    User o|--o{ Household : verified_by
    Household ||--o{ Member : household
    Household ||--o{ HouseholdDraftEvent : household
    User ||--o{ HouseholdDraftEvent : actor
    Member ||--o{ IncomeNotice : member
    User ||--o{ IncomeNotice : recorded_by
    Household ||--o{ EligibilityDecision : household
    RuleSetVersion ||--o{ EligibilityDecision : ruleset_version
    User o|--o{ EligibilityDecision : decided_by
    User ||--o{ RuleSetVersion : created_by
    Store ||--o{ Listing : store
    Category ||--o{ Listing : category
    User ||--o{ Listing : safe_confirmed_by
    User ||--o{ Listing : created_by
    Listing ||--o{ Reservation : listing
    Household ||--o{ Reservation : household
    User ||--o{ Reservation : made_by
    User o|--o{ Reservation : confirmed_by
    User o|--o{ AuditEvent : actor
    User o|--o{ EmailLog : user

    User {
        string password "Django-managed encoded password hash, including hashing metadata; never the plain-text password. Django standard field: NULL is not allowed."
        datetime last_login "Most recent sign-in time; Django authentication metadata. Nullable."
        boolean is_superuser "Django permission bypass flag; distinct from the Iris admin role."
        string first_name "User first name."
        string last_name "User last name."
        boolean is_staff "Django admin-site access flag; distinct from the Iris role."
        boolean is_active "Whether the account is active."
        uuid id PK "Stable public user identifier."
        string email UK "Case-insensitive unique sign-in email."
        string phone "Contact phone number."
        string preferred_language "fr or en; default fr."
        string role "beneficiary, store_staff, store_manager, intake_worker, or admin."
        uuid store FK "Required for store staff and managers; nullable for other roles. Deletion is protected while users reference the store."
        datetime created_at "Creation time."
        datetime updated_at "Last-save time."
    }

    Invitation {
        uuid id PK "Stable UUID identifier."
        string email "Recipient email."
        string first_name "Recipient first name."
        string last_name "Recipient last name."
        string role "Role assigned on acceptance."
        uuid store FK "Optional store assignment. Nullable."
        string token_hash UK "SHA-256 hash of the invitation token; not the raw token."
        datetime expires_at "Expiration saved when issued, using the active invitations.expires_after_days rule."
        datetime accepted_at "Acceptance time; unset before acceptance. Nullable."
        uuid invited_by FK "Person who issued the invitation, when applicable. Nullable."
    }

    Store {
        uuid id PK "Stable UUID identifier."
        string name "Store name."
        string street_number "Civic number."
        string street_name "Street name."
        string unit "Unit or suite. Nullable."
        string city "City name."
        string postal_code "Postal code."
        string phone "Contact phone number."
        string email "Contact email."
        json opening_hours "Weekly schedule JSON, approval notes-only JSON, or empty placeholder."
        string pickup_instructions "Instructions for collecting goods. Nullable."
        boolean is_badr "Identifies the B.A.D.R. store."
        boolean is_active "Whether the store is active."
        uuid application FK, UK "Nullable one-to-one to the PartnerApplication that created the store (column application_id). Set by the US-13 approval; null for B.A.D.R. and manually created stores. PROTECT."
        datetime created_at "Store creation time."
        datetime updated_at "Last-save time."
    }

    PartnerApplication {
        uuid id PK "Primary key."
        string business_name "2 to 150 characters."
        string business_type "grocery, supermarket, bakery, restaurant, cafe, convenience_store, pharmacy, farm_producer, community_organization, other."
        string neq "Quebec enterprise number, exactly 10 digits."
        string street_number "Business address; postal code stored as A1A 1A1."
        string street_name "Business address; postal code stored as A1A 1A1."
        string unit "Business address; postal code stored as A1A 1A1."
        string city "Business address; postal code stored as A1A 1A1."
        string postal_code "Business address; postal code stored as A1A 1A1."
        string contact_first_name "Letters, spaces, apostrophes, hyphens."
        string contact_last_name "Letters, spaces, apostrophes, hyphens."
        string contact_role "Optional role."
        string contact_email "Lowercase; becomes the store manager's sign-in after approval."
        string contact_phone "Canadian number in E.164, for example +15145550123."
        string website "https:// added if missing."
        list goods_categories "Stable category codes; at least one, each active at submission."
        string expected_frequency "daily, weekly, monthly, occasional."
        string opening_hours "Free text, for example 'lun-ven 9 h-18 h'."
        string message "Optional additional information."
        boolean consent_contact "Consent to be contacted; must be true (Law 25 record, with created_at)."
        string language "fr (default) or en; language of the emails to the contact, who has no account."
        string status "submitted (default), approved, rejected."
        string decision_reason "Required when rejected."
        uuid decided_by FK "Administrator who decided (US-13). PROTECT."
        datetime decided_at "Decision time (US-13)."
        datetime created_at "Submission time."
    }

    Household {
        uuid id PK "Stable UUID identifier."
        uuid holder FK, UK "Optional holder User, distinct from the holder Member. Walk-in linking is refused by model validation; accepting its invitation does not populate this field. US-93 (#704, Releas..."
        string member_number UK "Optional short file number. Nullable."
        string channel "Registration channel: walk-in or online."
        string status "Household file status."
        string email "Optional holder email; without it a walk-in is served only at the counter. Nullable."
        string preferred_language "fr or en; used for emails."
        string phone "Household contact phone."
        string street_number "Civic number."
        string street_name "Street name."
        string unit "Optional apartment or unit."
        string city "City name."
        string postal_code "Validated, normalized Canadian postal code."
        string address_key "Normalized address, including unit, used to find possible duplicates."
        string search_email_key "Stored generated normalized email key; internal search field. Nullable."
        string search_number_key "Stored generated normalized member-number key; internal search field. Nullable."
        string search_address_key "Stored generated duplicate-address search key."
        string search_address_text "Stored generated full-address search text."
        string alternate_name "Optional alternate for pickups."
        string alternate_phone "Optional alternate for pickups."
        string alternate_email "Optional alternate for pickups."
        boolean identity_checked_in_person "Staff checked photo ID in person; nothing about the ID is stored."
        datetime consent_data_processing_at "When the person agreed to data processing (walk-in: notice read aloud); empty until given. Nullable."
        string consent_text_version "Version of the consent text that was read, for example 2026-11-v1. US-20 may move consents to a separate record later."
        datetime submitted_at "Submission time. Nullable."
        datetime approved_at "Approval time. Nullable."
        datetime expires_at "Approval expiration time. Nullable."
        string status_reason "Optional reason for the current status."
        uuid created_by FK "Person who created the household file. Nullable."
        uuid verified_by FK "Staff member who checked the identity. Nullable."
        datetime verified_at "Identity check time. Nullable."
        datetime anonymized_at "Time personal data was removed. Nullable."
        datetime created_at "Household file creation time."
        datetime updated_at "Last change to the file."
    }

    Member {
        uuid id PK "Stable UUID identifier."
        uuid household FK "Household containing this member."
        string first_name "Member first name."
        string last_name "Member last name."
        date date_of_birth "Used to determine age."
        string relation "Relationship within the household."
        string person_key "Normalized person identity used to find possible duplicates."
        string search_name_key "Stored generated normalized name key; excludes birth date."
        datetime created_at "When the member was added."
        datetime updated_at "Last change to the member."
    }

    HouseholdDraftEvent {
        bigint id PK "Bigint primary key."
        uuid household FK "Draft that was created or edited."
        uuid actor FK "Staff member who acted."
        string action "created, updated or submitted."
        string actor_role "Their role at that moment."
        datetime created_at "When it happened."
    }

    IncomeNotice {
        uuid id PK "Notice identifier used by the staff file link."
        uuid member FK "Member whose income evidence is recorded."
        string status "confirmed (values from a notice) or did_not_file."
        string source "Source of recorded values; staff entry uses staff."
        string file_ref "Opaque private storage reference (income-notices/<random>); never a URL or the uploaded file name."
        integer tax_year "Tax year represented. Nullable."
        bigint total_income_cents "Line 199 assessed income: Montant etabli; integer cents. Nullable."
        string name_on_notice "Name recorded on the notice."
        string postal_code_on_notice "Postal code recorded on the notice."
        date notice_date "Notice issuance date. Nullable."
        boolean seen_in_person "Whether staff saw the notice in person."
        string did_not_file_reason "Required explanation for a non-filing adult."
        uuid recorded_by FK "Staff user who recorded the entry."
        datetime created_at "When the entry was recorded."
        datetime superseded_at "When a newer entry replaced this one; empty for the current notice. Nullable."
    }

    EligibilityDecision {
        uuid id PK "Stable UUID identifier."
        uuid household FK "Household being assessed."
        integer household_size "Household size used for the calculation."
        list adult_incomes_cents "Snapshot of the adult income inputs, in cents."
        bigint household_income_cents "Sum of accepted adult incomes in cents."
        bigint threshold_cents "Applied income threshold in cents."
        integer threshold_year "Threshold reference year."
        bigint ruleset_version FK "Applied rule version."
        boolean eligible "Eligibility result."
        string decided_by_type "Whether the decision was made by a person or automatically."
        uuid decided_by FK "Decision maker, when applicable. Nullable."
        datetime created_at "Decision recording time."
    }

    RuleSetVersion {
        bigint id PK "Bigint primary key."
        string rule_type "Type of settings."
        integer version "Version number."
        json values "Versioned settings; JSONB documented."
        datetime effective_from "When the version takes effect."
        uuid created_by FK "Person who published the rule version."
        datetime created_at "Creation time."
    }

    Category {
        uuid id PK "Stable UUID identifier."
        string code UK "Category code."
        string name_fr "French category name."
        string name_en "English category name."
        boolean is_food "Whether food-safety rules apply."
        bigint default_value_cents "Default estimated monetary value in cents."
        boolean is_active "Whether the category is available for selection."
    }

    Listing {
        uuid id PK "Stable UUID identifier."
        uuid store FK "Offering store."
        uuid category FK "Goods category."
        string title "Listing title."
        string description "Optional description. Nullable."
        integer quantity_total "Total offered units."
        integer quantity_reserved "Reserved units."
        string unit "item or bundle."
        integer max_per_household "Quantity limit per household."
        datetime pickup_start "Pickup window start."
        datetime pickup_end "Pickup window end."
        date best_before "Required for food: pickup end date plus listing_safety.best_before_margin_days; non-food bypasses this safety check. Nullable."
        string photo_ref "Optional stored photo reference. Nullable."
        bigint estimated_value_cents "Optional estimated value in cents. Nullable."
        string status "published, closed or cancelled; sold out is derived from stock counters."
        uuid safe_confirmed_by FK "Person who confirmed listing safety."
        datetime safe_confirmed_at "Safety confirmation time."
        datetime published_at "Publication time."
        datetime cancelled_at "Time store deactivation cancelled the listing. Nullable."
        uuid created_by FK "User who posted the listing. PROTECT."
        datetime created_at "Creation time."
        datetime updated_at "Last-save time."
    }

    Reservation {
        uuid id PK "Stable UUID identifier."
        uuid listing FK "Reserved listing."
        uuid household FK "Receiving household."
        integer quantity "Reserved units."
        string pickup_code "Six-character collection code."
        string status "Reservation status."
        boolean late_cancel "Cancellation during the pickup window."
        string made_by_type "Whether the reservation was made by the household or staff."
        uuid made_by FK "Person who created the reservation."
        datetime picked_up_at "Collection confirmation time. Nullable."
        uuid confirmed_by FK "Person who confirmed collection. Nullable."
        datetime created_at "Reservation creation time."
        datetime updated_at "Reservation last-save time; bulk/status-only writes do not automatically refresh it."
    }

    AuditEvent {
        bigint id PK "Bigint primary key."
        uuid actor FK "Nullable for a saved automatic household eligibility decision only; then actor_role is system. Human actors are saved Users. PROTECT."
        string actor_role "Role at the time of the action."
        string action "Recorded action."
        string target_type "Affected record type."
        string target_id "Identifier of the affected record."
        json metadata "Event details without personal data."
        datetime created_at "Event recording time."
    }

    EmailLog {
        uuid id PK "One delivery's stable identifier across retries."
        string to_email "Recipient address. A failed validation record may retain a database-safe malformed address; empty when the input cannot be represented safely in this field."
        uuid user FK "Optional account; SET_NULL preserves delivery metadata when the user is deleted. Nullable."
        string template_key "Template used."
        string language "Captured recipient preference, fr or en."
        string status "pending, sending, retrying, sent or failed."
        integer attempts "Transport attempts started by the worker, initially zero; distinct from the queue's execution count."
        string error "Bounded internal error code; no provider exception text."
        datetime sent_at "Set after transport/provider acceptance; unset for other statuses. This is not inbox-delivery confirmation. Nullable."
        datetime created_at "Delivery record creation time."
        datetime updated_at "Last delivery-state update."
    }

```

## Module ownership

Each owner maintains its model and migrations and exposes services for writes and queries for reads. Other modules use those interfaces. The modules share the PostgreSQL database.

## Documented search approach

Staff search uses PostgreSQL pg_trgm, unaccent, and trigram indexes for partial and accent-insensitive matching.

US-63 implements this with stored generated columns on the owning tables:
`Household.search_email_key`, `search_number_key`, `search_address_key`,
`search_address_text`, and `Member.search_name_key`. PostgreSQL backfills and
maintains these derived values. Six GIN indexes cover those keys and the existing
normalized phone field. The immutable normalization wrapper pins the installed
unaccent function and dictionary. Existing extension schemas are preserved; new
extensions use `public`. Dictionary changes require recomputing stored keys.
These internal columns are excluded from API responses. Name search does not use
the DOB component of `person_key`.

Source: [Issue #553](https://github.com/B-A-D-R-SL/iris/issues/553).

## Migration order

Use the checked-in Django migration dependencies, not the earlier nine-stage
future-generation sketch. The custom User is in accounts' first migration;
Store precedes its User assignments; PartnerApplication precedes Store.application.
Documents needs Member; EligibilityDecision needs Household and RuleSetVersion;
Listing needs Store and Category; Reservation needs Household and Listing.
Household search/duplicate branches and audit publication/suspension branches
have explicit merge migrations.

| Module | Current migration leaf |
| --- | --- |
| accounts | `0005_invitation` |
| stores | `0005_shared_contact_validation` |
| households | `0007_shared_contact_validation` |
| reservations | `0002_reservation_timestamps_and_indexes` |
| audit | `0008_auditevent_store_actions` |
| eligibility | `0002_append_only` |
| categories, documents, rules, notifications, listings | `0001_initial` |

Applied databases receive new migrations for later changes; this documentation
update does not generate or apply migrations.

### Supporting tables

`accounts/0003_auth_cache` creates `accounts_auth_cache` with `cache_key` PK,
serialized `value`, `expires` and an expiry index. It backs authentication
rate limits across processes and is not an ORM business model. Django
admin/auth/session/allauth tables, inherited User group/permission many-to-many
join tables and Procrastinate job tables are infrastructure outside this ERD.

Sources: owning modules' models and migrations under
[`backend/modules`](../../backend/modules/); metadata and migration dependencies
checked without a database connection. The
[architecture evidence](../04-architecture/architecture.md#implementation-evidence)
links the Release 1 PRs and issues behind these changes.
