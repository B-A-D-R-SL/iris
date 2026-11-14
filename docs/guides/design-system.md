<!-- AI contribution: 50% or more AI-generated -->

# Design system and app shell (SET-16)

How to build a screen that fits Iris. Everything here follows the
[wireframes](https://www.figma.com/design/mxXyzEOGl4nuDVdYeoRNPA/Wireframes) (Components page),
[forms-and-fields.md](../02-requirements/forms-and-fields.md) and the permission matrix in
[business-rules.md](../02-requirements/business-rules.md).

## Where things are

| Folder | What it holds |
| --- | --- |
| `frontend/src/app/` | Routes, one module per area in `routes/` (`App.tsx` puts them together), theme, providers, layouts, navigation and role guards |
| `frontend/src/areas/<area>/` | Screens: `public`, `household`, `store`, `staff` |
| `frontend/src/features/<module>/` | API calls and hooks per backend module, for example `listings/api.ts` |
| `frontend/src/shared/auth/` | The signed-in user (`currentUser.ts`), roles and their groups (`roles.ts`), sign-in and sign-out |
| `frontend/src/shared/forms/` | Shared form fields and validation rules |
| `frontend/src/shared/ui/` | `AppBar`, loading, empty and error states, `Notice`, `LanguageSwitch` |
| `frontend/src/test/render.tsx` | Test helpers: render with providers, fake signed-in user, accessibility check |

## Layers

The four folders are layers, from top to bottom: **`app`, then `areas`, then `features`, then
`shared`**. A file imports from its own layer or from the layers below it, never from a layer
above. So `shared` knows nothing about screens, and a screen never reaches into the app shell.
When code in a lower layer needs something from above, move that thing down. That is why
`AppBar` lives in `shared/ui` and `homePathFor` in `shared/auth/roles.ts`.

ESLint enforces the rule (`no-restricted-imports` in `frontend/eslint.config.js`) and fails CI
on an upward import. Tests are exempt, because they render the whole app.

## Size

ESLint also fails a function in `src/` that is longer than 50 lines or has a complexity above
15, as the code review rule asks. Tests are exempt. Files that were already over the limits are
listed in `OVER_THE_LIMIT` in `frontend/eslint.config.js` with their size today, so they cannot
grow. The pull request that splits a file removes its line; do not add a new file to the list.

## Add your screen

1. Create it in `src/areas/<area>/`.
2. Add its route to your area's module in `src/app/routes/`: `publicRoutes.tsx`,
   `householdRoutes.tsx`, `storeRoutes.tsx` or `staffRoutes.tsx`. A screen that is not built has
   no route and no tab, so there are no placeholder screens. The one exception is `/privacy`,
   which the partner form's consent text links to until the policy text exists.
3. If your screen has a tab, add it to `src/app/navigation.ts` with the roles that may open it.
4. Household and store screens start with their own app bar: `<AppBar title={t("…")} />` from
   `shared/ui`. A sub-screen adds a back arrow to its parent screen in the same area, for
   example `backTo="/listings"` on a household listing detail. Staff and public screens start
   with `<Title order={1}>`.

Menus and guards already exist. `src/app/navigation.ts` decides which roles see which tab. The
role groups come from `src/shared/auth/roles.ts`, built from the generated API `Role` type: a
role added to the API must be given an area there before the app compiles. `RequireRole` sends
signed-out visitors to `/sign-in` and other roles to their own home (`homePathFor`), which is
the first built screen of their area: `/listings`, `/store/listings/new` or `/staff/households`.
The story that builds an area's home screen changes it there.
After sign-in, it returns a visitor to the requested protected path when the role permits it.
These only shape the interface: **every endpoint must still check permissions on the server.**

## Theme

Colour tokens come from the Figma
[Foundations · Iris colour](https://www.figma.com/design/mxXyzEOGl4nuDVdYeoRNPA/Wireframes?node-id=249-2)
page (SET-33; [repository export](../03-design/mockups/Foundations.png)). Screens use tokens, never shade numbers directly. `tokens.ts` copies the exported palettes and semantic/component tokens;
`theme.ts` applies them through SET-34.

| Token | Used for | Hex | Mantine colour and shade |
| --- | --- | --- | --- |
| `primary` | Filled button, links, checked controls, selected icons, focus ring | `#237A2C` | `irisGreen.9` |
| `on-primary` | Text and icons on primary and destructive buttons | `#FFFFFF` | white |
| `text` | Body text, headings, labels | `#013751` | `irisNavy.9` |
| `text-muted` | Secondary text, helper text, captions | `#455968` | `irisSlate.9` |
| `surface` | Page and input background | `#FFFFFF` | white |
| `surface-raised` | Cards, panels, read-only fields, image placeholders | `#FEF3EA` | `irisSand.0` |
| `border` | Card and divider borders (decorative) | `#EEE6E0` | `irisSand.1` |
| `success` strong / light | Success text, icons and borders / badge and alert background | `#237A2C` / `#DEF3E0` | `irisGreen.9` / `irisGreen.1` |
| `warning` strong / light | Warning text and icons / badge and alert background | `#AD5900` / `#FFF4E2` | `irisOrange.9` / `irisOrange.0` |
| `danger` strong / light | Errors, error borders, destructive buttons / badge and alert background | `#BD250B` / `#FFECE7` | `irisRed.8` / `irisRed.0` |
| `info` strong / light | Info text and icons / badge and alert background | `#0070B2` / `#E5F9FF` | `irisBlue.9` / `irisBlue.0` |

Neutral strong/light tokens are specified in the component-token table under
[Colour in code](#colour-in-code-set-34).

**Status colours** (strong shade for icon, text and border; light shade for badge and alert background):

| Record | Status and tone |
| --- | --- |
| Household file | Draft: neutral · Submitted: info · Awaiting visit: info · Review required: warning · Renewal needed: warning · Approved: success · Suspended: danger · Rejected: danger |
| Listing | Published: success · Sold out: neutral · Closed: neutral · Cancelled: neutral |
| Reservation | Reserved: info · Picked up: success · Cancelled: neutral · Cancelled by store: warning · No-show: danger |
| Partner application | Submitted: info · Approved: success · Rejected: danger |
| Store, category | Active: success · Deactivated or inactive: neutral |
| Pickup scan result | Confirmed: success · Late pickup: warning · Unknown code, other store, already picked up, cancelled: danger |

**Rules:** colour is never the only signal (every status keeps its label and each non-neutral tone keeps its icon; links stay underlined); one filled `primary` button per screen; `danger` for destructive actions, blocking errors and statuses assigned danger in the map.

Buttons are 48 px and inputs 44 px with 16 px text (touch targets, no iOS zoom). Use Mantine
components with their defaults; pass `size="sm"` only for compact controls. Icons come from
`@tabler/icons-react` (the wireframes use the same set). One filled `Button` per screen (main
action), `variant="outline"` for secondary, `variant="subtle"` for tertiary.

### Colour in code (SET-34)

`frontend/src/app/tokens.ts` owns all colour values and the stable application palettes:
`iris`, `success`, `warning`, `danger` and `info`. The theme registers them and exposes
semantic aliases through `--iris-*` variables. Use `c="dimmed"` for secondary text,
`<StatusBadge record="household" status={household.status} />` for record statuses and
`<Notice type="error">` for messages. Use `FieldError` for inline errors. Never put a
hex value, named colour or numbered grey in a component or CSS module.

The seven original Foundations palettes (`irisGreen`, `irisNavy`, `irisSand`,
`irisSlate`, `irisOrange`, `irisRed`, `irisBlue`) are registered alongside the stable
application aliases. `iris` and `success` both use `irisGreen`; `warning`, `danger`,
`info` and `neutral` use orange, red, blue and sand respectively. Mantine's internal
`gray` defaults also use the warm sand scale. Shade numbers occur
only in `tokens.ts`; application code uses semantic names and CSS variables.

Foundations' component-token note supplies the values missing from its main table:

| Token | Value | Source / use |
| --- | --- | --- |
| `input-border` | `#968A81` | irisSand.5; interactive input boundaries, including on raised surfaces |
| `text-placeholder` | `#627482` | irisSlate.7; placeholders on white input backgrounds |
| `neutral` strong / light | `#013751` / `#EEE6E0` | body text / neutral-badge background; neutral has no icon |
| `primary-light` | `#DEF3E0` | irisGreen.1; selected navigation background, with navy text |
| `primary-hover` / `primary-pressed` | `#1D6824` / `#17561D` | darker primary-button states from Foundations |
| `warning-border` | `#F98A0F` | irisOrange.6; decorative warning alert border |

`border` is decorative (cards/dividers), and is intentionally exempt from the control
contrast threshold. Use `--iris-input-border` for controls, never `--iris-border`.
`--mantine-color-dimmed` uses `text-muted`; `--mantine-color-placeholder` uses the
explicit Foundations component token `text-placeholder`. The contrast tests cover
both text backgrounds, the four status pairs, neutral/selected states, filled-button
states, placeholders on white inputs, input borders on both surfaces and focus rings.
No placeholder palettes or temporary neutral success/warning fallbacks remain.

Interaction tokens extend (and do not change) the 70 Foundations swatches. Filled
success uses the published primary hover; danger uses red.9. Warning, info and neutral
already use their darkest palette shade, so their filled hover is a 15% black mix
(`#934C00`, `#005F97`, `#012F45`). Light hover uses the next stronger tint (green.2,
orange.1, red.1, blue.1, sand.2) with the corresponding darker hover text to preserve
4.5:1 contrast. Default controls use sand.1 on hover over sand.0. These additional
component states are implementation choices for hover feedback, not new SET-33 swatches.

Household and category status wording lives only under `shared.status`, including
search results and the category administration table. Search response validation uses
`statusTones.household`, not a second translation map.

`statusTones.ts` is the single status-to-tone map copied from #651. Household and listing
statuses use the current generated API enums; reservation and partner application enums
must be adopted when their endpoints expose them. The `partnerApplication` record name
uses the translation namespace convention. Labels use `shared.status.<record>.<status>`
in both languages, keeping backend snake_case status codes verbatim. Unknown statuses
show the raw value in a neutral badge and log only the record and status.

Check every built screen at 360 px (staff also at 1024 px) against the SET-33 exports.
Obtain the required teammate review and CI checks before merging; post the badge usage
line to the team chat after merge.

## Forms

Use `@mantine/form` (default controlled mode) with the shared fields and rules:

```tsx
const form = useForm({
  initialValues: { title: "", phone: "", estimatedValue: null as number | null },
  validate: {
    title: allOf(isRequired(), hasLength({ min: 2, max: 80 })),
    phone: allOf(isRequired(), isPhone()),
    estimatedValue: isMoneyInRange({ maxCents: 100_000 }),
  },
});

<form noValidate onSubmit={form.onSubmit(save)}>
  <TextField label={t("store.newListing.title")} {...form.getInputProps("title")} />
  <PhoneField label={t("store.details.phone")} {...form.getInputProps("phone")} />
  <MoneyField label={t("store.newListing.estimatedValue")} optional {...form.getInputProps("estimatedValue")} />
</form>
```

| Field | Value it gives the form (what the API stores) |
| --- | --- |
| `TextField` | `string`; `multiline` + `maxLength` shows a "0 / 500" counter |
| `DateField` | `"YYYY-MM-DD"` or `null` |
| `PostalCodeField` | `"H2X 1Y4"` (uppercase, one space) |
| `PhoneField` | `"+15145550123"` (E.164) once 10 digits are typed |
| `MoneyField` | integer cents or `null` (shown `0,00 $` / `$0.00`) |
| `IntegerField` | a whole number between `min` and `max`, with − and + buttons for one thumb |
| `FileUpload` | a `File` or `null`; check it with `isAcceptedFile({ types, maxMb })` |

- Fields are required unless `optional`; the label then ends with « (facultatif) ».
- Rules return messages that translate themselves, so errors follow the language switch.
  Empty values pass every rule except `isRequired()`.
- `isPostalCode()` and `isPhone()` follow the backend rule: case and spaces don't count, so
  `h2x1y4` and `(514) 555-0123` pass. Postal codes use Canada Post letters (no D, F, I, O, Q
  or U), like `normalize_postal_code` on the server.
- Put server field errors in `form.setErrors({ field: message })`; they get the same style.
- Count errors at the top with `<Notice type="error" title={…} />` (forms-and-fields.md).

## Loading, empty and error states

```tsx
const { data, isPending, isError, refetch } = useQuery(…);
if (isPending) return <LoadingState />;
if (isError) return <ErrorState onRetry={() => void refetch()} />;
if (data.length === 0) return <EmptyState title={t("…")} description={t("…")} action={…} />;
```

Say plainly why something is empty and what to do next; never show technical details.

## Translations

Every visible text goes through `t("area.screen.element")`, with the French and the English
value added to matching area files under `src/shared/i18n/fr/` and `en/`.
The tests check every file for matching keys and empty strings. Shared keys live
in `common.json` under `app.*` (shell) and `shared.*` (fields, states).
See [the glossary](../01-project/glossary.md#translation-keys) for the file map.

## Tests

```tsx
mockCurrentUser(testUser("store_staff"));               // or "signed-out" / "server-error"
const { container } = renderWithProviders(<App />, { route: "/store/listings/new" });
await expectNoAxeViolations(container);                 // WCAG checks (NFR-03)
```

## Installable on a phone

`public/manifest.webmanifest` and the icons in `public/icons/` let Android offer
"Add to home screen" / "Install"; iOS uses `apple-touch-icon.png` from Safari's share menu.
Browsers only offer installation over HTTPS (or `localhost`), so test it on staging.

## Follow-up work

- Persisting the chosen language in the profile belongs to US-08.
- US-01 implements sign-out and `/api/me/`; `CurrentUser` uses the generated API type.
