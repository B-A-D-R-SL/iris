# Glossary

French and English terms used in Iris screens and documentation. Translation keys follow `area.screen.element` for example, `store.newListing.title`.

| Concept | Français (screens) | English (screens) | Code name | Meaning |
| --- | --- | --- | --- | --- |
| Household | Foyer | Household | `household` | The people living at one address who apply together |
| Account holder | Personne responsable | Account holder | `holder` | The adult who owns the household account |
| Member | Membre du foyer | Household member | `member` | Any person in the household, holder included |
| Alternate | Personne remplaçante | Alternate | `alternate` | Person allowed to pick up for the household |
| Household file | Dossier | File | `household` (status) | The household's application and its status |
| Notice of assessment | Avis de cotisation | Notice of assessment | `income_notice` | Revenu Québec document proving an adult's income |
| Total income (line 199) | Revenu total (ligne 199) | Total income (line 199) | `total_income_cents` | The amount used for eligibility |
| Tax year | Année d'imposition | Tax year | `tax_year` | The year the notice covers |
| Low income cut-off | Seuil de faible revenu (SFR) | Low income cut-off (LICO) | `lico_thresholds` | Statistics Canada threshold by household size |
| Eligibility | Admissibilité | Eligibility | `eligibility` | Whether the household is under the threshold |
| Review | Vérification par l'équipe | Review by staff | `review_case` | A file or event a person must decide |
| Partner store | Commerce partenaire | Partner store | `store` | A business (or B.A.D.R.) that posts surplus |
| Partner application | Demande de partenariat | Partner application | `partner_application` | A business asking to join |
| Listing | Offre | Listing | `listing` | Surplus posted by a store |
| Reservation | Réservation | Reservation | `reservation` | A household holding units of a listing |
| Pickup code | Code de cueillette | Pickup code | `pickup_code` | 6-character code shown at the store |
| Pickup window | Plage de cueillette | Pickup window | `pickup_start`, `pickup_end` | When the goods can be picked up |
| No-show | Absence | No-show | `no_show` | Reserved but not picked up in the window |
| Strike | Avertissement | Strike | `strike` | Consequence of a no-show |
| Priority tier | Niveau de priorité | Priority tier | `tier` | 1, 2 or 3; decides how early a listing is seen (staff only) |
| Intake worker | Intervenant·e à l'accueil | Intake worker | `intake_worker` | B.A.D.R. staff at the counter |
| Admin | Coordonnateur·trice | Admin | `admin` | B.A.D.R. coordinator |
| Best before | Meilleur avant | Best before | `best_before` | Date on food packaging |
| Need | Besoin | Need | `need` | An item a household is looking for |

## Status labels

Status codes from `business-rules.md` and their screen labels.

| Area | Code | Français | English |
| --- | --- | --- | --- |
| Household file | `draft` | Brouillon | Draft |
| Household file | `submitted` | Demande soumise | Submitted |
| Household file | `review_required` | Vérification par l'équipe requise | Staff review required |
| Household file | `awaiting_visit` | Visite en personne requise | In-person visit required |
| Household file | `approved` | Approuvé | Approved |
| Household file | `renewal_needed` | Renouvellement requis | Renewal required |
| Household file | `suspended` | Suspendu | Suspended |
| Household file | `rejected` | Refusé | Rejected |
| Listing | `published` | Publiée | Published |
| Listing | `closed` | Terminée | Closed |
| Listing | `cancelled` | Annulée | Cancelled |
| Reservation | `reserved` | Réservée | Reserved |
| Reservation | `picked_up` | Récupérée | Picked up |
| Reservation | `cancelled` | Annulée | Cancelled |
| Reservation | `cancelled_by_store` | Annulée par le commerce | Cancelled by store |
| Reservation | `no_show` | Absence | No-show |

## Additional screen terms

Terms used in the application screens.

| Area | Français | English | Meaning |
| --- | --- | --- | --- |
| Accounts | Connexion | Sign in | Sign in to an account |
| Accounts | Déconnexion | Sign out | Sign out of an account |
| Accounts | Créer un compte | Create an account | Create a household account |
| Accounts | Mot de passe oublié? | Forgot your password? | Request a password reset |
| Accounts | Code de vérification | Verification code | Two-factor sign-in for staff |
| Accounts | Invitation | Invitation | Invitation for a staff or store account |
| Households | Inscription en personne | Walk-in registration | Registration completed with staff |
| Households | Demande en ligne | Online application | Application submitted online |
| Households | Membre adulte | Adult household member | Household member aged 18 or older |
| Households | Personne à charge | Dependant | Household member under 18 |
| Households | Renouvellement | Renewal | Renew an expired household file |
| Households | Date d'expiration | Expiry date | Date the household file expires |
| Households | Consentement | Consent | Permission to use data for a stated purpose |
| Households | Déclaration de revenus | Tax return | Tax return, not the notice of assessment |
| Households | Vérification de l'identité | Identity verification | ID checked in person; ID details are not stored |
| Partners | Devenir partenaire | Become a partner | Public partner application |
| Partners | Demande approuvée | Application approved | Approved partner application |
| Partners | Demande refusée | Application rejected | Rejected partner application |
| Listings | Produits excédentaires | Surplus goods | Goods a store can offer |
| Listings | Catégorie | Category | Goods category |
| Listings | Quantité disponible | Units available | Quantity still available |
| Listings | Article | Item | One item |
| Listings | Lot | Bundle | A group of items |
| Listings | Publier une offre | Post a listing | Publish an offer |
| Reservations | Confirmer la cueillette | Confirm pickup | Store confirms that goods were collected |
| Reservations | Code QR | QR code | QR code for a reservation |
| Reservations | Historique des cueillettes | Pickup history | Past pickups |
| Priority | Priorité | Priority | Order in which households see listings |
| Priority | Pointage de priorité | Priority score | Staff-only score; not shown to households |
| Priority | Règles de priorité | Priority rules | Rules for access to listings |
| Staff | File de vérification | Review queue | Cases waiting for staff review |
| Staff | Journal d'audit | Audit log | Record of access and decisions |
| Staff | Paramètres des règles | Rule settings | Settings with a recorded version history |
| Reporting | Tableau de bord | Dashboard | Summary of platform activity |
| Reporting | Exporter en CSV | Export to CSV | Download report data |
| Reporting | Valeur estimée redistribuée | Estimated value redistributed | Value of goods collected |
| Privacy | Politique de confidentialité | Privacy policy | How personal information is used and protected |
| Privacy | Télécharger mes données | Download my data | Download personal information |
| Privacy | Demander une correction | Request a correction | Request to correct personal information |
| Privacy | Examen par une personne | Human review | Staff review of an automated decision |
| Privacy | Fermer mon compte | Close my account | Request to close an account |
| Needs | Mes besoins | My needs | Goods a household needs |
| Needs | Correspondance | Match | Offer matching a stated need |
| Assistant | Assistant de ressources communautaires | Community resource assistant | Help based on approved community resources |
| Assistant | Source approuvée | Approved source | Resource checked by staff |
| Furniture | Offre de meuble | Furniture offer | Furniture offered by a donor |
| Furniture | Donateur | Donor | Person donating furniture |

## Form labels

Labels from `forms-and-fields.md`, grouped by form. Repeated labels are kept where they appear on different screens.

| Screen / form | Field (API name) | Français | English |
| --- | --- | --- | --- |
| Sign in | `email` | Courriel | Email address |
| Sign in | `password` | Mot de passe | Password |
| Sign in | `code` | Code de vérification | Verification code |
| Household account sign-up | `email` | Courriel | Email address |
| Household account sign-up | `password` | Mot de passe | Password |
| Household account sign-up | `password_confirm` | Confirmer le mot de passe | Confirm password |
| Household account sign-up | `preferred_language` | Langue | Language |
| Household account sign-up | `accept_terms` | J'accepte les conditions d'utilisation et la politique de confidentialité | I accept the terms of use and the privacy policy |
| Step 1: Account holder | `first_name` | Prénom | First name |
| Step 1: Account holder | `last_name` | Nom de famille | Last name |
| Step 1: Account holder | `date_of_birth` | Date de naissance | Date of birth |
| Step 1: Account holder | `email` | Courriel | Email address |
| Step 1: Account holder | `phone` | Téléphone | Phone number |
| Step 1: Account holder | `preferred_language` | Langue de communication | Preferred language |
| Step 2: Address | `street_number` | Numéro civique | Street number |
| Step 2: Address | `street_name` | Rue | Street name |
| Step 2: Address | `unit` | Appartement | Apartment / unit |
| Step 2: Address | `city` | Ville | City |
| Step 2: Address | `province` | Province | Province |
| Step 2: Address | `postal_code` | Code postal | Postal code |
| Step 3: Household members | `first_name` | Prénom | First name |
| Step 3: Household members | `last_name` | Nom de famille | Last name |
| Step 3: Household members | `date_of_birth` | Date de naissance | Date of birth |
| Step 3: Household members | `relation` | Lien avec la personne responsable | Relation to the account holder |
| Step 4: Consent | `consent_data_processing` | J'accepte que B.A.D.R. utilise ces renseignements pour vérifier mon admissibilité | I agree that B.A.D.R. uses this information to check my eligibility |
| Step 4: Consent | `consent_ai_reading` | J'accepte qu'un logiciel lise mes avis de cotisation pour remplir les champs | I agree that software reads my notices of assessment to fill in the fields |
| Step 4: Consent | `consent_digest_emails` | Je veux recevoir un courriel quotidien des nouvelles offres | I want a daily email of new listings |
| Step 5: Notices of assessment | `file` | Avis de cotisation de Revenu Québec | Revenu Québec notice of assessment |
| Step 5: Notices of assessment | `did_not_file` | Cette personne n'a pas produit de déclaration de revenus | This person did not file a tax return |
| Step 5: Notices of assessment | `did_not_file_reason` | Expliquez pourquoi | Explain why |
| Step 5: Notices of assessment | `tax_year` | Année d'imposition | Tax year |
| Step 5: Notices of assessment | `total_income` | Revenu total (ligne 199) | Total income (line 199) |
| Step 5: Notices of assessment | `notice_first_name` / `notice_last_name` | Nom sur l'avis | Name on the notice |
| Step 5: Notices of assessment | `notice_postal_code` | Code postal sur l'avis | Postal code on the notice |
| Step 5: Notices of assessment | `notice_date` | Date de l'avis | Notice date |
| Walk-in registration | `email` | Courriel | Email address |
| Walk-in registration | `identity_checked_in_person` | Pièce d'identité avec photo vérifiée en personne | Photo ID checked in person |
| Walk-in registration | `notice_seen_in_person` (per adult) | Avis vu en personne | Notice seen in person |
| Partner application form | `business_name` | Nom de l'entreprise | Business name |
| Partner application form | `business_type` | Type d'entreprise | Business type |
| Partner application form | `neq` | Numéro d'entreprise du Québec (NEQ) | Quebec enterprise number (NEQ) |
| Partner application form | `contact_first_name` | Prénom de la personne-ressource | Contact first name |
| Partner application form | `contact_last_name` | Nom de la personne-ressource | Contact last name |
| Partner application form | `contact_role` | Fonction | Role |
| Partner application form | `contact_email` | Courriel | Email address |
| Partner application form | `contact_phone` | Téléphone | Phone number |
| Partner application form | `website` | Site Web | Website |
| Partner application form | `goods_categories` | Types de produits offerts | Types of goods offered |
| Partner application form | `expected_frequency` | Fréquence prévue des dons | Expected donation frequency |
| Partner application form | `opening_hours` | Heures d'ouverture | Opening hours |
| Partner application form | `message` | Message | Message |
| Partner application form | `consent_contact` | J'accepte que B.A.D.R. communique avec moi au sujet de cette demande | I agree that B.A.D.R. contacts me about this application |
| Store form | `name` | Nom du magasin | Store name |
| Store form | `phone` | Téléphone | Phone number |
| Store form | `email` | Courriel | Email address |
| Store form | `opening_hours` | Heures d'ouverture | Opening hours |
| Store form | `pickup_instructions` | Instructions pour la cueillette | Pickup instructions |
| Store form | `is_active` | Actif | Active |
| Listing form | `title` | Titre | Title |
| Listing form | `category` | Catégorie | Category |
| Listing form | `description` | Description | Description |
| Listing form | `quantity` | Quantité | Quantity |
| Listing form | `unit` | Unité | Unit |
| Listing form | `max_per_household` | Maximum par foyer | Maximum per household |
| Listing form | `pickup_start` | Début de la cueillette | Pickup starts |
| Listing form | `pickup_end` | Fin de la cueillette | Pickup ends |
| Listing form | `best_before` | Meilleur avant | Best before |
| Listing form | `photo` | Photo | Photo |
| Listing form | `estimated_value` | Valeur estimée | Estimated value |
| Listing form | `safe_and_allowed` | Je confirme que ces produits sont sécuritaires et permis | I confirm these goods are safe and allowed |
| Staff invitation | `email` | Courriel | Email address |
| Staff invitation | `first_name` | Prénom | First name |
| Staff invitation | `last_name` | Nom de famille | Last name |
| Staff invitation | `role` | Rôle | Role |
| Alternate for pickups | `alternate_name` | Nom de la personne remplaçante | Alternate's name |
| Alternate for pickups | `alternate_phone` | Téléphone de la personne remplaçante | Alternate's phone |
| Alternate for pickups | `alternate_email` | Courriel de la personne remplaçante | Alternate's email |
| Need form | `category` | Catégorie | Category |
| Need form | `detail` | Précision | Detail |
| Need form | `is_active` | Actif | Active |
| Furniture offer form | `title` | Titre | Title |
| Furniture offer form | `furniture_type` | Type de meuble | Furniture type |
| Furniture offer form | `description` | Description | Description |
| Furniture offer form | `dimensions` | Dimensions (L × P × H, cm) | Dimensions (W × D × H, cm) |
| Furniture offer form | `condition` | État | Condition |
| Furniture offer form | `photos` | Photos | Photos |
| Furniture offer form | `pickup_area` | Secteur (3 premiers caractères du code postal) | Area (first 3 characters of postal code) |
| Furniture offer form | `donor_name`, `donor_email`, `donor_phone` | Vos coordonnées | Your contact details |

## Translation keys

Keys use `area.screen.element`. Use camelCase for names containing more than one word.

| Key | Français | English |
| --- | --- | --- |
| `auth.login.title` | Connexion | Sign in |
| `auth.login.email` | Courriel | Email address |
| `household.registration.firstName` | Prénom | First name |
| `store.newListing.title` | Titre | Title |
| `reservation.confirmation.pickupCode` | Code de cueillette | Pickup code |

## Sources

- `Iris-Requirements.md`
- `business-rules.md`
- `forms-and-fields.md`
- `screens.md`