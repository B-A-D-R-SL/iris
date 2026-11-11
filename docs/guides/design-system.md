<!-- AI contribution: 50% or more AI-generated -->

# Design system and app shell (SET-16)

How to build a screen that fits Iris. Everything here follows the
[wireframes](https://www.figma.com/design/mxXyzEOGl4nuDVdYeoRNPA/Wireframes) (Components page),
[forms-and-fields.md](../02-requirements/forms-and-fields.md) and the permission matrix in
[business-rules.md](../02-requirements/business-rules.md).

## Where things are

| Folder | What it holds |
| --- | --- |
| `frontend/src/app/` | Routes (`App.tsx`), theme, providers, layouts per area, navigation and role guards |
| `frontend/src/areas/<area>/` | Screens: `public`, `household`, `store`, `staff` |
| `frontend/src/features/<module>/` | API hooks per module, for example `accounts/currentUser.ts` |
| `frontend/src/shared/forms/` | Shared form fields and validation rules |
| `frontend/src/shared/ui/` | Loading, empty and error states, `Notice`, `LanguageSwitch` |
| `frontend/src/test/render.tsx` | Test helpers: render with providers, fake signed-in user, accessibility check |

## Add your screen

1. Create it in `src/areas/<area>/`.
2. In `src/app/App.tsx`, replace the `PlaceholderScreen` of your route with your screen.
3. Household and store screens start with their own app bar: `<AppBar title={t("…")} />`.
   A sub-screen adds a back arrow to its parent screen in the same area, for example
   `backTo="/listings"` on a household listing detail and `backTo="/store/listings"` on a store
   listing edit. Staff and public screens start with `<Title order={1}>`.

Menus and guards already exist. `src/app/navigation.ts` decides which roles see which tab;
`RequireRole` sends signed-out visitors to `/sign-in` and other roles to their own home.
After sign-in, it returns a visitor to the requested protected path when the role permits it.
These only shape the interface: **every endpoint must still check permissions on the server.**

## Theme

Colour tokens come from the Figma
[Foundations · Iris colour](https://www.figma.com/design/mxXyzEOGl4nuDVdYeoRNPA/Wireframes)
page (SET-33). Screens use tokens, never shade numbers directly. Applying them in
`theme.ts` is SET-34; until then the running app still uses the grayscale theme.

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

**Status colours** (strong shade for icon, text and border; light shade for badge and alert background):

| Record | Status and tone |
| --- | --- |
| Household file | Draft: neutral · Submitted: info · Awaiting visit: info · Review required: warning · Renewal needed: warning · Approved: success · Suspended: danger · Rejected: danger |
| Listing | Published: success · Sold out: neutral · Closed: neutral · Cancelled: neutral |
| Reservation | Reserved: info · Picked up: success · Cancelled: neutral · Cancelled by store: warning · No-show: danger |
| Partner application | Submitted: info · Approved: success · Rejected: danger |
| Store, category | Active: success · Deactivated or inactive: neutral |
| Pickup scan result | Confirmed: success · Late pickup: warning · Unknown code, other store, already picked up, cancelled: danger |

**Rules:** colour is never the only signal (every status keeps its icon and label; links stay underlined); one filled `primary` button per screen; `danger` only for destructive actions and blocking errors.

Buttons are 48 px and inputs 44 px with 16 px text (touch targets, no iOS zoom). Use Mantine
components with their defaults; pass `size="sm"` only for compact controls. Icons come from
`@tabler/icons-react` (the wireframes use the same set). One filled `Button` per screen (main
action), `variant="outline"` for secondary, `variant="subtle"` for tertiary.

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
