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
