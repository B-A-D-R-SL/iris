# Forms and fields

Every form in Iris, field by field. **Field** is the name used in the API and the database; it is also the layer name in the Figma wireframes. Labels are the exact text shown on screen (French first, English second). Validation runs in the front end for quick feedback **and** in the back end, which is the authority.

This page publishes the **partner application**, **store** and **listing** forms (SET-11, #402). French text comes from the [wireframes](https://www.figma.com/design/mxXyzEOGl4nuDVdYeoRNPA/Wireframes); English text follows the [glossary](../01-project/glossary.md).

## Shared rules

Field types:

| Type | Format and validation | Stored as |
| --- | --- | --- |
| `name` | 1 to 100 characters, letters, spaces, apostrophes and hyphens; trimmed | text |
| `email` | Valid address, at most 254 characters, lowercase | text |
| `phone` | Canadian number, 10 digits, shown as (514) 555-0123 | text in E.164, for example `+15145550123` |
| `postal_code` | Canadian format `A1A 1A1` (space optional when typing) | text, uppercase with one space |
| `url` | Web address; `https://` added if missing | text |
| `date` | Calendar picker; shown and typed as YYYY-MM-DD | date |
| `time` | 24-hour clock, HH:MM | combined with a date into a date-time |
| `money` | Dollars and cents, 0 or more, at most 2 decimals; shown as `0,00 $` in French | integer cents |

On every form:

- A line at the top says "Tous les champs sont obligatoires, sauf ceux marqués « facultatif ». / All fields are required unless marked “optional”." Optional labels end with « (facultatif) / (optional) ».
- Long text fields show a character counter, for example `0 / 300`.
- Errors appear under each field after the user taps the main button. An alert at the top counts them ("Vérifiez 4 champs / Check 4 fields") and focus moves to it. Values already typed are kept.
- Error messages are short and say how to fix the value.

## Address fields

Used by the partner application and the store form.

| Field | Français | English | Type | Required | Rules |
| --- | --- | --- | --- | --- | --- |
| `street_number` | Numéro civique | Street number | text | Yes | 1 to 10 characters, digits with an optional letter or fraction, for example `1234` or `1234A` |
| `street_name` | Rue | Street | text | Yes | 2 to 120 characters, for example `rue Saint-Denis` |
| `unit` | App. | Apt. | text | No | At most 10 characters |
| `city` | Ville | City | text | Yes | Default `Montréal` |
| `postal_code` | Code postal | Postal code | postal_code | Yes | May be outside Montréal |

## Partner application form

Public page **Devenir partenaire / Become a partner** (`/partner/apply`). No account is needed. Rate limit: 5 submissions per hour per IP address. Wireframes: Partner page, flow P1.

The form has four groups: **Votre entreprise / Your business**, **Adresse / Address**, **Personne-ressource / Contact person** and **Vos dons / Your donations**.

| Field | Français | English | Type | Required | Rules |
| --- | --- | --- | --- | --- | --- |
| `business_name` | Nom de l’entreprise | Business name | text | Yes | 2 to 150 characters |
| `business_type` | Type d’entreprise | Business type | choice (drop-down) | Yes | `grocery` (Épicerie / Grocery), `supermarket` (Supermarché / Supermarket), `bakery` (Boulangerie / Bakery), `restaurant` (Restaurant), `cafe` (Café), `convenience_store` (Dépanneur / Convenience store), `pharmacy` (Pharmacie / Pharmacy), `farm_producer` (Ferme ou producteur / Farm or producer), `community_organization` (Organisme communautaire / Community organization), `other` (Autre / Other) |
| `neq` | Numéro d’entreprise du Québec (NEQ) | Quebec enterprise number (NEQ) | text | No | Exactly 10 digits |
| `website` | Site Web | Website | url | No | |
| `street_number`, `street_name`, `unit`, `city`, `postal_code` | see [Address fields](#address-fields) | | | Yes except `unit` | |
| `contact_first_name` | Prénom | First name | name | Yes | |
| `contact_last_name` | Nom de famille | Last name | name | Yes | |
| `contact_role` | Fonction | Role | text | No | At most 100 characters, for example "propriétaire, gérant·e" |
| `contact_email` | Courriel | Email address | email | Yes | Becomes the store manager’s sign-in. Help text: "Si votre demande est acceptée, ce courriel servira à vous connecter. / If your application is accepted, you will use this email to sign in." |
| `contact_phone` | Téléphone | Phone number | phone | Yes | |
| `goods_categories` | Types de produits offerts | Types of goods offered | multi-choice (chips) | Yes | At least one active [category](#categories). Help text: "Choisissez au moins un type. / Choose at least one type." |
| `expected_frequency` | Fréquence prévue des dons | Expected donation frequency | choice (chips) | Yes | `daily` (Chaque jour / Daily), `weekly` (Chaque semaine / Weekly), `monthly` (Chaque mois / Monthly), `occasional` (À l’occasion / Occasionally) |
| `opening_hours` | Heures d’ouverture | Opening hours | long text | Yes | At most 300 characters, for example "lun-ven 9 h-18 h, sam 10 h-16 h" |
| `message` | Message | Message | long text | No | At most 1,000 characters |
| `consent_contact` | J’accepte que B.A.D.R. communique avec moi au sujet de cette demande. | I agree that B.A.D.R. may contact me about this application. | checkbox | Yes | Followed by "Vos renseignements servent seulement à traiter cette demande. / Your information is used only to process this application." and a link to the privacy policy |

Button: **Envoyer ma demande / Send my application**.

After sending:

- A confirmation screen is shown, and the contact gets the email `partner_application_received`. Admins see the application in the staff area.
- While an application from the same `contact_email` is `submitted`, a second one is refused (see the last row of the table below).

Error messages:

| Field | Français | English |
| --- | --- | --- |
| `business_name` | Entrez le nom de l’entreprise (2 à 150 caractères). | Enter the business name (2 to 150 characters). |
| `neq` | Le NEQ compte exactement 10 chiffres. Vous pouvez aussi laisser ce champ vide. | The NEQ has exactly 10 digits. You can also leave this field empty. |
| `postal_code` | Entrez un code postal comme H2X 1Y4. | Enter a postal code like H2X 1Y4. |
| `contact_email` | Entrez un courriel comme nom@exemple.ca. | Enter an email like name@example.ca. |
| `goods_categories` | Choisissez au moins un type de produits. | Choose at least one type of goods. |
| `consent_contact` | Cochez cette case pour envoyer la demande. | Tick this box to send the application. |
| Alert at the top | **Vérifiez {n} champs.** Les champs à corriger sont indiqués plus bas. Ce que vous avez déjà rempli est conservé. | **Check {n} fields.** The fields to fix are shown below. What you already filled in is kept. |
| Application already open | **Une demande est déjà en cours.** Une demande faite avec {email} attend déjà une réponse de B.A.D.R. Vous n’avez rien d’autre à faire : nous vous écrirons par courriel. | **An application is already in progress.** An application made with {email} is already waiting for an answer from B.A.D.R. You have nothing else to do: we will write to you by email. |

## Store form

Used by admins (all fields) and store managers (only phone, email, opening hours and pickup instructions). Not in the wireframes yet: the store profile is drawn in a later task.

| Field | Français | English | Type | Required | Rules |
| --- | --- | --- | --- | --- | --- |
| `name` | Nom du magasin | Store name | text | Yes | 2 to 150 characters |
| `street_number`, `street_name`, `unit`, `city`, `postal_code` | see [Address fields](#address-fields) | | | Yes except `unit` | |
| `phone` | Téléphone | Phone number | phone | Yes | |
| `email` | Courriel | Email address | email | Yes | |
| `opening_hours` | Heures d’ouverture | Opening hours | weekly schedule | Yes | For each weekday: closed, or open and close times (HH:MM) |
| `pickup_instructions` | Instructions pour la cueillette | Pickup instructions | text | No | At most 300 characters, for example "Porte arrière, sonnez / Back door, ring the bell" |
| `is_active` | Actif | Active | toggle | Admin only | Deactivating cancels open listings |

## Listing form

One phone screen (`/store/listings/new`) to post a listing. The same form is used to edit and to repost a listing. Wireframes: Store page, flows S1, S3 and S5.

Defaults: pickup today 16:00 to 18:00, quantity 1, unit `item`, 1 per household.

| Field | Français | English | Type | Required | Rules |
| --- | --- | --- | --- | --- | --- |
| `photo` | Photo | Photo | image | No | JPG or PNG up to 5 MB, resized to 1280 px. Button "Prendre ou choisir une photo / Take or choose a photo" |
| `title` | Titre | Title | text | Yes | 2 to 80 characters, for example "Pains de la veille" |
| `category` | Catégorie | Category | choice (bottom sheet) | Yes | Active [categories](#categories), food first. Prohibited items have no category; the sheet links to their list |
| `description` | Description | Description | long text | No | At most 500 characters |
| `quantity` | Quantité | Quantity | integer (stepper) | Yes | 1 to 999. Help text: "De 1 à 999 / From 1 to 999" |
| `unit` | Unité | Unit | choice (segmented) | Yes | `item` (Article / Item), `bundle` (Lot / Bundle) |
| `max_per_household` | Maximum par foyer | Maximum per household | integer (stepper) | Yes | 1 to 10. Help text: "De 1 à 10. Un foyer peut réserver jusqu’à ce nombre. / From 1 to 10. A household can reserve up to this number." |
| Pickup day (screen only) | Jour | Day | choice (chips) | Yes | Aujourd’hui / Today, Demain / Tomorrow, Autre date / Other date (date picker). Combined with the times below |
| `pickup_start` | Début | Start | time | Yes | Under the heading **Cueillette / Pickup**. No earlier than now, no later than 7 days ahead. Stored as a date-time |
| `pickup_end` | Fin | End | time | Yes | 30 minutes to 12 hours after the start. Stored as a date-time. Help text under both times: "De 30 min à 12 h, au plus 7 jours à l’avance. / 30 min to 12 h, at most 7 days ahead." |
| Place (screen only) | Lieu | Place | read-only | | The store’s address, from the store form. Help text: "L’adresse de votre commerce. / Your business’s address." |
| `best_before` | Meilleur avant | Best before | date | Food categories | Hidden until a food category is chosen. On or after the pickup end date (margin 0 days, setting). Help text: "Pour les aliments : le jour de la fin de la cueillette ou après. / For food: the day the pickup ends or later." |
| `estimated_value` | Valeur estimée | Estimated value | money | No | $0 to $1,000. If empty, category default × quantity. Help text: "Si vide, Iris utilise la valeur par défaut de la catégorie. / If empty, Iris uses the category’s default value." |
| `safe_and_allowed` | Je confirme que ces produits sont sécuritaires et permis. | I confirm these goods are safe and allowed. | checkbox | Yes, on every post | Stored with who and when. Link: "Voir la liste des produits interdits / See the list of prohibited items" |

Button: **Publier l’offre / Publish listing**, fixed at the bottom of the phone screen. After publishing, the store lands on **Mes offres / My listings** with "Offre publiée / Listing published".

**Edit (S3).** Same form, pre-filled, with a back arrow. Button: **Enregistrer les modifications / Save changes**. Rules:

- The quantity can’t go below the units already reserved. When there are reservations, an info alert says so before any change: "**{n} réservations en cours.** La quantité ne peut pas descendre sous {n}. Les foyers qui ont réservé gardent leur code. / **{n} reservations in progress.** The quantity can’t go below {n}. Households who reserved keep their code."
- Each change is written to the audit log with who and when.

**Repost (S5).** Opens the form from an ended listing. Every field is copied except the day, the times, the best-before date and the safety box (left empty and unticked). An info alert says what is left to do: "**Copiée de « {title} ».** Choisissez le jour et les heures, puis cochez la confirmation. / **Copied from “{title}”.** Choose the day and times, then tick the confirmation." Publishing creates a new listing; the old one stays under the ended listings.

Error messages:

| Field | Français | English |
| --- | --- | --- |
| `title` | Entrez un titre de 2 à 80 caractères. | Enter a title of 2 to 80 characters. |
| `pickup_end` | La cueillette dure de 30 min à 12 h. | The pickup lasts 30 min to 12 h. |
| `best_before` | Choisissez le {date} ou après (fin de la cueillette). | Choose {date} or later (end of pickup). |
| `safe_and_allowed` | Cochez cette case pour publier. | Tick this box to publish. |
| `quantity` (edit) | Entrez {n} ou plus : {n} articles sont déjà réservés. | Enter {n} or more: {n} items are already reserved. |
| Alert at the top | **Vérifiez {n} champs.** Les champs à corriger sont indiqués plus bas. | **Check {n} fields.** The fields to fix are shown below. |
| Alert at the top (edit, quantity too low) | **Quantité trop basse.** Il y a déjà {n} articles réservés. Entrez {n} ou plus, ou annulez l’offre. | **Quantity too low.** {n} items are already reserved. Enter {n} or more, or cancel the listing. |

## Categories

Used by `goods_categories` (partner application) and `category` (listing). Seed file: `backend/modules/categories/data/categories.yaml`. Admins can add, rename or deactivate categories (US-35).

| Code | Français | English | Food |
| --- | --- | --- | --- |
| `fruits_vegetables` | Fruits et légumes | Fruits and vegetables | Yes |
| `bakery` | Boulangerie | Bakery | Yes |
| `dairy_eggs` | Produits laitiers et œufs | Dairy and eggs | Yes |
| `meat_fish` | Viandes et poissons | Meat and fish | Yes |
| `prepared_meals` | Plats préparés | Prepared meals | Yes |
| `dry_goods` | Épicerie sèche | Dry goods | Yes |
| `canned_goods` | Conserves | Canned goods | Yes |
| `frozen` | Surgelés | Frozen food | Yes |
| `beverages` | Boissons | Beverages | Yes |
| `baby_food` | Alimentation pour bébé | Baby food | Yes |
| `hygiene` | Hygiène personnelle | Personal hygiene | No |
| `household_cleaning` | Produits ménagers | Household cleaning | No |
| `baby_care` | Soins pour bébé | Baby care | No |
| `clothing` | Vêtements | Clothing | No |
| `school_supplies` | Fournitures scolaires | School supplies | No |
| `other` | Autre | Other | No |


