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
These only shape the interface: **every endpoint must still check permissions on the server.**

## Theme

Grayscale on purpose: meaning comes from icons, borders and text, never colour alone.
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
value added to `src/shared/i18n/fr.json` and `en.json` (the test fails if a key is missing in
one of them). Shared keys live under `app.*` (shell) and `shared.*` (fields, states).

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

## Not done here

- Persisting the chosen language in the profile (US-08) and signing out (T-01.01.3).
- `/api/me/` comes from US-01. Until it is on `main`, everyone is treated as signed out; after it
  merges, replace the hand-written `CurrentUser` type with the generated one.
