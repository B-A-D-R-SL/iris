<!-- AI contribution: 50% or more AI-generated -->

# Seed data

`python manage.py seed` loads a fixed fictional dataset for an empty database and for staging. The random draw uses seed **18**, so the same categories always produce the same listings. Running it again does not duplicate rows and does not undo later edits.

It also runs the existing seeds it depends on: rule versions (`seed_rules`), listing categories (`seed_categories`), and the B.A.D.R. store (`seed_badr_store`).

## Agreed counts

| What | Count | Notes |
| --- | ---: | --- |
| Admin | 1 | `coordonnateur@example.test` |
| Intake workers | 2 | `accueil-1@example.test`, `accueil-2@example.test` |
| B.A.D.R. store | 1 | Created by the B.A.D.R. store seed. One store staff account: `personnel-badr@example.test` |
| Partner stores | 4 | `Commerce exemple 1` to `Commerce exemple 4`, each with one manager `gerant-exemple-N@example.test` |
| Households | 50 | Spread across every file status. 25 walk-in, 25 online |
| Listings | 30 | Six on each of the five stores |
| Reservations | 40 | Only on approved household files |

Every seed account uses the password `iris-seed-password` and preferred language `fr`. Docker still creates the separate local operator `admin@iris.local`. That account is not part of this dataset.

## Household status spread

| Status | Files |
| --- | ---: |
| `draft` | 6 |
| `submitted` | 7 |
| `review_required` | 6 |
| `awaiting_visit` | 6 |
| `approved` | 7 |
| `renewal_needed` | 6 |
| `suspended` | 6 |
| `rejected` | 6 |

Approved files expire in 365 days. Renewal-needed files are already past their expiry. Suspended files expire in 30 days.

## Reservation status spread

| Status | Reservations |
| --- | ---: |
| `reserved` | 20 |
| `picked_up` | 8 |
| `cancelled` | 4 |
| `cancelled_by_store` | 4 |
| `no_show` | 4 |

A listing's reserved quantity matches the reservations that are still `reserved`. Food listings have a best-before date on the pickup end date. Other listings leave it empty.

## No real personal data

Names are `Exemple`. Emails use `@example.test`. Phones use the fictional `555` range, such as `+15145551001`. Addresses are `rue Exemple`, Montreal, `H0H 0H0`.

Mock notices of assessment from SET-09 stay in the notice generator. This seed does not copy them onto household files, because the income-notice table is not part of this dataset.

## How to run

After migrations, from the backend container:

```bash
python manage.py seed
```

The command is safe on an empty database and on staging. Rows that already exist, including a B.A.D.R. store that staff have edited, are left as they are.
