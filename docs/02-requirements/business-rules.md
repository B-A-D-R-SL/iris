# Business rules

Every rule Iris applies, with its default value. Values marked *(setting)* are stored in the rule settings module (`rules`) and can be changed by an admin without a developer; changing one creates a new version, so past decisions stay reproducible. Code never hard-codes these values: business-rule functions in `domain/` receive them as arguments.

Decisions taken where B.A.D.R. had not specified anything are marked **Default**. They can be changed later through the settings or an ADR.

Each owner publishes their section of this document in their own pull request. This version contains the listing categories and the prohibited items (SET-12); the other sections (roles, eligibility, reservations, priority, strikes, notifications, retention) are added by their owners.

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
