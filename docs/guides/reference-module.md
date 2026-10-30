
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

## Backend architecture

| File | Responsibility |
| --- | --- |
| `models.py` | Category database model and fields |
| `domain/rules.py` | Pure best-before-date validation |
| `services.py` | Validated writes and transactions |
| `queries.py` | Read-only database access |
| `api/serializers.py` | API response serialization |
| `api/views.py` | HTTP endpoint and permissions |
| `api/urls.py` | Module URL routing |
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

`get_active_category(code)`
- Retrieves one active category.
- Raises Category.DoesNotExist when unavailable.

### Services

`save_category(category)`
- Validates and saves a Category.
- Prevents changing an existing category's stable code.
- Runs inside a database transaction.

`get_or_create_category(category)`
- Validates category fields and safely creates missing categories.
- Preserves existing records when seed commands overlap.

`deactivate_category(category_id)`
- Deactivates a category without deleting its record.
- Preserves existing data for historical references.

All application writes should use these services rather than
directly modifying Category records.

### Domain

`validate_best_before_date(...)`
- Contains no Django imports.
- Requires food categories to have a best-before date.
- Checks the date against the pickup end date.
- Accepts a configurable safety margin.
- Does not query settings or the database.

The calling Listings service will eventually supply the
category information and active listing-safety rule values.

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

Creating and editing categories through the staff interface
belongs to US-35, not this reference implementation.

## Frontend

`features/categories/api.ts`
- Fetches the public API.
- Validates the response structure.

`features/categories/CategoriesPage.tsx`
- Displays active categories.
- Uses the current interface language.
- Handles loading, empty results, and errors.
- Uses the existing Mantine design system.

Route: `/staff/categories`

The route is currently admin-only, even though its underlying
GET endpoint is public.

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

- Category editing and deletion policies belong to US-35.
- Listing publication will enforce category-specific food safety.
- Category codes must not be modified through direct ORM updates.
- Full module-boundary enforcement is delivered by SET-14.
- The staff page requires a working authenticated admin session.
- The Categories endpoint itself is public and operational.
