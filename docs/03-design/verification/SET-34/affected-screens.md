<!-- AI contribution: 50% or more AI-generated -->

# SET-34 global theme impact

This inventory is for the route tree in `frontend/src/app/App.tsx` on this PR,
including its merge of main at `ea428cd`. A route that is still a placeholder is
listed explicitly: it receives the shared shell/theme, not an unimplemented feature.
New screens added on other branches must be checked when they adopt this theme.

## Overrides and their consumers

All routes receive navy text, white body, muted/placeholder/error/focus colours,
font sizing and the warm `gray = irisSand` scale. Mantine components that use an
internal gray default (borders, disabled states, menu labels/items, select/date
popovers, stepper separators) therefore inherit that scale too. This is global,
even when no source file for a screen changed in SET-34.

| Override | Current consumers / state to inspect |
| --- | --- |
| Card, cream background | Welcome cards; partner-application success card |
| Paper, cream background | Household search result cards (`SearchResults`) |
| Modal, white content/header | Categories add/edit (`CategoryDialog`), deactivate confirmation |
| Drawer, white content/header | New listing category sheet (`CategoryPicker`) |
| Table, border/stripe/hover tokens | Categories and audit results |
| Checkbox, accessible unchecked border | Partner application consent; walk-in holder identity/consent; listing no-best-before-date; category add/edit food flag |
| Radio, accessible unchecked border | Partner donation frequency; new listing category sheet |
| Chip, white/green selected background | Partner accepted categories; new listing pickup day |
| Input/InputWrapper, border/error/disabled/focus/labels | Sign-in; invitation; partner application; household search; all walk-in steps; category add/edit; audit filters; listing fields, category picker and IntegerField |
| Button/variant resolver, filled/light/outline semantic colours | Public calls to action, forms, staff actions, category danger actions, retry/back actions; default buttons also receive distinct sand hover |
| ActionIcon/default hover | IntegerField decrement/increment on new listing; default variants use surface-raised → default-hover |
| Menu and subtle ActionIcon, inherited Mantine colours | AppBar account dropdown on household/store routes; SignOutButton in public/staff headers and account menus; these sign-out icons are **subtle**, not default |
| SegmentedControl | Language switch on public/staff headers; new listing item/bundle selector |
| Alert/Notice | Form failures, success messages, permission/search errors, walk-in saved/not-found states; icons and bold errors remain |
| Badge | Shared household/category statuses; category type badge |
| AppShell and custom navigation CSS | Public/staff header, staff sidebar, mobile bottom navigation, selected tabs |

## Every routed screen

The shared shell column includes the global defaults above. The last column lists
additional components in the screen itself, including reachable dialogs/states.

| Route | Screen / shell | Additional affected components |
| --- | --- | --- |
| `/` | Welcome / public | Card, Button, links |
| `/sign-in` | Sign-in / public | Inputs, Button, Notice, validation/error text |
| `/invitation/:token` | Invitation / public | Password inputs/toggles, Button, Notice/error/success |
| `/partner/apply` | Partner application / public | Inputs/selects, Chip, Radio, Checkbox, Button, Notice; Card on success |
| `/forgot-password` | Placeholder / public | EmptyState text/icon |
| `/sign-up` | Placeholder / public | EmptyState text/icon |
| `/privacy` | Placeholder / public | EmptyState text/icon |
| unmatched `*` | Not found / public | EmptyState, outline back button |
| `/home` | Placeholder / household | AppBar account Menu, subtle icons, bottom navigation, EmptyState |
| `/listings` | Placeholder / household | AppBar account Menu, subtle icons, bottom navigation, EmptyState |
| `/listings/:id` | Placeholder / household | AppBar back icon/account Menu, bottom navigation, EmptyState |
| `/reservations` | Placeholder / household | AppBar account Menu, subtle icons, bottom navigation, EmptyState |
| `/profile` | Placeholder / household | AppBar account Menu, subtle icons, bottom navigation, EmptyState |
| `/store` | Placeholder / store | AppBar account Menu, subtle icons, bottom navigation, EmptyState |
| `/store/confirm` | Placeholder / store | AppBar account Menu, subtle icons, bottom navigation, EmptyState |
| `/store/listings` | Placeholder / store | AppBar account Menu, subtle icons, bottom navigation, EmptyState |
| `/store/listings/new` | New listing / store | AppBar/Menu, inputs, IntegerField default icons, SegmentedControl, Chip, Checkbox, category Drawer/Radio, date popovers, Button, Notice |
| `/staff/households` | Search / staff | Search input, Paper result cards, StatusBadge, Button, Notice/empty/loading states |
| `/staff/walk-in` | New walk-in / staff | Holder inputs/select/date and Checkbox; address inputs; member inputs/select/date and remove buttons; review text/edit buttons; Stepper, Notice and save/continue buttons |
| `/staff/walk-in/:id` | Resume walk-in / staff | Same steps; saved summary/resume actions; loading, not-found and error notices |
| `/staff/review` | Placeholder / staff | EmptyState text/icon |
| `/staff/partners` | Placeholder / staff | EmptyState text/icon |
| `/staff/stores` | Placeholder / staff | EmptyState text/icon |
| `/staff/categories` | Categories / staff | Striped/hover Table, badges, buttons; add/edit Modal inputs/Checkbox; confirmation Modal and danger button |
| `/staff/audit` | Audit / staff | Filter inputs, buttons, striped/hover Table, Notice/loading/empty/error states |
| `/staff` | Redirect | Redirects to `/staff/households`; no independent screen |

Role guards and the app error boundary also use themed loading/error/empty states
and buttons. Shared DateField/Select dropdowns and NumberInput inherit the theme;
no backend permissions or workflow decisions were changed.

## Review evidence and hover checks

The [original archive](screenshots.zip) contains the 76 pre-SET-34/main vs SET-34
captures described in the [verification README](README.md). The supplemental
[review archive](ammar-review.zip) compares PR head `ea428cd` against these fixes:

- AppBar account dropdown at 360 px, French and English.
- CategoryDialog add and edit at 1024 px, French and English.
- HolderStep at 360 and 1024 px with one checked and one unchecked checkbox.
- New listing IntegerField at 360 px, with a hovered default increment icon.
- Staff SignOutButton (subtle) and danger confirmation hover at 1024 px.
- A rendered matrix of filled/light buttons for all six aliases and default Button/
  ActionIcon, with computed normal/hover foreground/background measurements.

The archive records 32 route captures, two matrix captures and `browser-results.json`.
These are representative states for the inventory, not a claim that every possible
state of every route has a screenshot. Only fictional API responses were used;
requests were intercepted and no real server changes were made.
