
# Iris Reference Module — Categories

**Issue:** #377 (T-00.01.4)
**Implementation owner:** Danial Kouba
**Module:** `backend/modules/categories/`
**Frontend:** `frontend/src/features/categories/`

## Purpose

Categories is the reference implementation for the Iris modular
monolith. It demonstrates how a feature is divided into API,
services, queries, domain rules, database models, and tests.

Other modules should follow this separation of responsibilities.

## Adding files to a module

A module adds a file when the story that needs it starts, not before.
A new module starts with `__init__.py`, `apps.py` and a README that lists
the planned stories; `models.py`, `services.py`, `queries.py`, `domain/`,
`api/`, `tasks.py` and `tests/` come with the first story that uses them.
Do not commit empty files or files that hold only a TODO (FIX-06, #632).

## Backend architecture

| File | Responsibility |
| --- | --- |
| `models.py` | Category database model and fields |
| `domain/rules.py` | Pure default-value validation |
| `services.py` | Validated writes and transactions |
| `queries.py` | Read-only database access |
| `api/serializers.py` | API response serialization |
| `api/views.py`, `api/staff_views.py` | HTTP endpoints and permissions |
| `api/urls.py`, `api/staff_urls.py` | Module URL routing |
| `management/commands/seed_categories.py` | Seed initial data |
| `data/categories.yaml` | Reviewed bilingual category definitions |
| `tests/` | Tests for domain, service, API, and seed layers |

## Request flow

GET /api/categories/
    |
    v
api/views.py
    |
    v
queries.list_active_categories()
    |
    v
models.Category
    |
    v
api/serializers.py
    |
    v
JSON response

The API does not directly construct database queries.

## Public interfaces

### Queries

`list_active_categories()`
- Returns active categories in code order.
- Excludes inactive categories.

`list_all_categories()` and `get_category(code)`
- Every category, active or not, for the admin screen (US-35).

`for_listing_post(code)`
- Locks one category and returns the values listing posting checks.

### Services

`save_category(category)`
- Validates and saves a Category.
- Prevents changing an existing category's stable code.
- Runs inside a database transaction.

`get_or_create_category(category)`
- Validates category fields and safely creates missing categories.
- Preserves existing records when seed commands overlap.

`create_category(values, admin)` and `update_category(code, values, admin)`
- Admin only (US-35). `update_category` renames, changes the food flag
  or default value, and deactivates or reactivates a category.
- There is no delete: a deactivated category keeps its record, so
  existing listings still refer to it.

All application writes should use these services rather than
directly modifying Category records.

### Domain

`validate_default_value(value_cents, *, max_cents)`
- Contains no Django imports.
- Checks a category's default value is from 0 to the listing
  value limit (BR-CAT-001).
- Receives the limit from the caller; does not query settings
  or the database.

The food best-before rule (BR-LIST-003) is not a category rule.
It lives in `backend/modules/listings/domain/safety.py`, which
listing posting calls with the category's `is_food` flag and the
active `listing_safety` rule values.

## Category model

Fields:
- id: UUID primary key
- code: unique stable identifier
- name_fr: French display name
- name_en: English display name
- is_food: food classification
- default_value_cents: estimated default value in CAD cents
- is_active: availability for new listings

The public API does not expose the database UUID.

Category-code immutability is enforced by the service layer.
Direct ORM and bulk updates must not bypass this interface.

## Public API

GET /api/categories/

Authentication: none required.

Only active categories are returned.

Example response:

[
  {
    "code": "bakery",
    "name_fr": "Boulangerie",
    "name_en": "Bakery",
    "is_food": true,
    "default_value_cents": 400
  }
]

The endpoint is read-only.

Admins list, add and edit categories through
`/api/staff/categories/` and `/api/staff/categories/<code>/` (US-35).

## Frontend

`features/categories/api.ts`
- Fetches the public API.
- Validates the response structure.

`features/categories/adminApi.ts`
- Calls the staff API used by the admin screen.

`features/categories/CategoriesPage.tsx`
- Admin screen: every category, active or not, with add, edit,
  deactivate and reactivate.
- `useCategoryActions.ts` holds the dialog state and the
  deactivate/reactivate request; `CategoryTable.tsx`,
  `CategoryDialog.tsx` and `DeactivateCategoryModal.tsx` draw the
  table and the dialogs.
- Handles loading, empty results, and errors.

Route: `/staff/categories` (admin only).

## Seed data

Run from backend/:

    uv run python manage.py seed_categories

The command reads `data/categories.yaml`.

It creates missing categories without changing existing records.
Repeated execution does not create duplicates.

## Tests

Backend:

    uv run pytest modules/categories/tests/

Frontend:

    pnpm exec vitest run src/features/categories

The backend tests cover business rules, persistence, public API
responses, seed behavior, and validation errors.

The frontend tests cover API parsing, loading, errors, retry,
empty results, language switching, and route integration.

## Module boundaries

The intended dependency direction is:

API -> services / queries -> models
Services -> domain rules
Services -> other modules' public interfaces

Domain code must remain independent of Django.

Cross-module dependencies should use documented public
services.py and queries.py interfaces.

SET-14 (#405) implements and verifies these import boundaries
using import-linter and CI.

## Limitations and future work

- Categories are never deleted, only deactivated (US-35).
- Category codes must not be modified through direct ORM updates.
- The staff page requires a working authenticated admin session.
- The public categories endpoint needs no sign-in.
