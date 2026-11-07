<!-- AI contribution: 50% or more AI-generated -->

# SET-33 — Release 1 colour prototype specification

**Status:** Design handoff draft; not evidence of completed Figma screens or accessibility sign-off.  
**Issue:** [#651](https://github.com/B-A-D-R-SL/iris/issues/651)  
**Figma source:** [Iris Wireframes](https://www.figma.com/design/mxXyzEOGl4nuDVdYeoRNPA/Wireframes)  
**Scope:** Release 1, light theme, English staff tablet (1024 px) and French public/household/store mobile (360 px). Include one translation-length test frame per area in the other language.

## Sources of truth and precedence

1. The *running implementation* plus [forms-and-fields](../02-requirements/forms-and-fields.md) win over old wireframes where they conflict. Compare to the actual code before declaring a frame complete.
2. [Business rules](../02-requirements/business-rules.md) and [glossary](../01-project/glossary.md) determine allowed actions, labels, statuses, eligibility, and category data. Values identified as defaults or still pending owner confirmation are **not final stakeholder policy**.
3. [Design system](../guides/design-system.md), Mantine theme, and the existing Figma Components page determine component sizes, typography and layouts.
4. The target for all new screens is issue [#651](https://github.com/B-A-D-R-SL/iris/issues/651); #652 implements colour in the application code, **not** in the Figma deliverable.
5. Existing Figma pages (Staff, Household, Store, Partner, Registration) are preserved unchanged as historical wireframes; new coloured designs go in `R1 · Staff`, `R1 · Public`, `R1 · Household`, `R1 · Store`.

## Palette matching existing B.A.D.R. Figma variables

These are **actual values from the existing `Brand · B.A.D.R.` Figma variable collection**. Do not introduce another unrelated palette. The next design-system step is to make ten-shade Mantine-compatible palettes and a linked semantic-token collection in Figma; this table is the specification, **not a claim that those new variables have been installed**.

| Semantic token | Existing Figma colour | Hex | Intended use |
| --- | --- | --- | --- |
| primary, text | `brand/navy` | `#013751` | Primary action, headings, links, active navigation and focus |
| on-primary | white | `#FFFFFF` | Text and icons on primary button |
| text-muted | `brand/slate` | `#4A6070` | Secondary text and placeholders |
| surface | `brand/cream` | `#FAF1EC` | App background |
| surface-raised | white | `#FFFFFF` | Cards, dialogs, drawers |
| border (proposed; verify against final theme) | new semantic token | `#7B8281` | Input and control boundaries |
| success | `brand/green-700` | `#237A2C` | Success labels, icons, borders |
| success light | `brand/green-50` | `#E6F4E4` | Success badge/alert background |
| warning | `brand/orange-800` | `#A35400` | Warning labels, icons, borders |
| warning light | `brand/orange-50` | `#FFF0DC` | Warning badge/alert background |
| danger | `brand/red-700` | `#C2290E` | Destructive actions / blocking errors |
| danger light | `brand/red-50` | `#FDEBE6` | Danger badge/alert background |
| info | `brand/blue-700` | `#00679F` | Info labels, icons, borders |
| info light | `brand/blue-50` | `#E3F1FA` | Info badge/alert background |

### Computed contrast ratios (WCAG formula)

| Pair | Contrast | Threshold | Result |
| --- | ---: | ---: | --- |
| Navy on cream | 11.32:1 | 4.5:1 text | Pass |
| White on navy | 12.60:1 | 4.5:1 text | Pass |
| Slate on cream | 5.90:1 | 4.5:1 text | Pass |
| Border `#7B8281` on cream | 3.52:1 | 3:1 controls | Pass |
| Dark green on pale green | 4.73:1 | 4.5:1 text | Pass |
| Dark orange on pale amber | 4.90:1 | 4.5:1 text | Pass |
| Dark red on pale red | 5.03:1 | 4.5:1 text | Pass |
| Dark blue on pale blue | 5.30:1 | 4.5:1 text | Pass |

**Warning:** These measured colour-pair ratios do **not** prove the finished screens conform to WCAG AA. Check actual icon/control adjacent colours, focus rings, disabled states, hover states and all text/background combinations; conduct a manual colour-vision simulation using Stark or equivalent. `brand/sand-500 #978C83` on cream is only ~2.95:1 and must **not** be used for normal text. Keep words and meaningful icons alongside colour. Links must remain underlined.

## Existing design constraints

- Inter sizes `12/14/16/18/22` px. Buttons 48 px tall, fields 44 px tall with 16 px entry text, existing corner radius and Tabler icons; one filled primary action per screen.
- Staff header is 56 px tall, side nav 220 px; in the running code it collapses below the desktop/tablet breakpoint. Reuse Figma `Staff/Top bar`, `Staff/Side nav`, `Badge`, `Button`, `Field` and `Alert` components instead of unrelated drawn UI.
- Admin-only areas: review queue, partner approvals, stores, categories and audit. Intake workers can find households and conduct walk-in registration. This distinction is implemented in `frontend/src/app/navigation.ts`.
- Use invented identities/addresses; no real household data or realistic notice documents. All flow frames show route, story ID, key rule, and an error branch. Staff copies use English with at least one French test frame.

## Firas — Staff screen checklist

The pre-existing *Staff* page includes W1 Find a household, W2 Review a flagged application, W3 Walk-in registration and W4 Partner application review. **W2 is out of Release 1** except as historical material; don't spend Release 1 effort polishing it. Duplicate only in-scope screens to a new `R1 · Staff` page.

### New screens for developer handoff first

**1. Stores `/staff/stores` (US-14; #454):** list active/deactivated stores with status words and icons; store detail/edit drawer or page with exact `forms-and-fields.md` Store form: name, street number, street, optional unit, city, postal code, phone, email, weekly opening hours, optional pickup instructions and admin-only active toggle. Include missing-required-field error example, loading and empty states. Deactivate button uses danger and opens a confirmation that **open listings are cancelled and reservation holders emailed**; no strike for cancellation. Show deactivated result and the status clearly. Figma link must be posted to #454 by November 8.

**2. Household suspension `/staff/households/:id` (US-32; #489):** extend W1 Household record. Only admins can Suspend or Reactivate. Suspension demands a reason, shows blocking error if missing, confirmation warns that **open reservations are cancelled without strikes and holder notified by email**, then shows a Suspended badge, banner and Reactivate. Figma link must be posted to #489 by November 8.

**3. Tax notices and decision `/staff/walk-in` after household step (US-18; #470):** for each adult show photo/upload of a notice (JPG, PNG, PDF; ≤10 MB), tax year, total income **line 199**, or "Did not file" with required reason, and a "Notice seen in person" checkbox. Include failed upload with readable recovery. Decision summary: Eligible → approve for 12 months and send set-password email *when holder has email*; Not eligible → rejection with reason (calm danger alert, **not a full red page**); review reason → review queue. Money is shown in Canadian dollars; do not hardcode income thresholds. Phone camera capture must be supported in developer implementation (#470). Link to #470 by November 8.

### Remaining Release 1 staff flows

**4. Find household `/staff/households` (US-63; #554):** W1 search automatically updates results after 300 ms, **remove the old Search button** in new R1 screens. Show matching results, statuses and no results, with filters.

**5. Walk-in registration `/staff/walk-in` (US-17/US-25):** use running app and forms-and-fields, not W3's outdated fields. Steps: account holder, address, household members, review. Identity verification and privacy consent required to proceed; allow incomplete draft. Holder 18+, members up to 15 including holder; possible-duplicate warning; draft saved and submitted states.

**6. Partner applications `/staff/partners` (US-13):** W4 list, status filters, oldest first, detail drawer, Approve confirmation (creates store and emails manager invitation), and **Reject requires reason and confirmation**. Leave W4 clarification states labelled `After Release 1`.

**7. Categories `/staff/categories` (US-35):** list `code`, `name_fr`, `name_en`, `is_food`, `default_value_cents`, `is_active`; add/edit/deactivate; immutable code after creation; prevent deletion, including in-use categories; active/inactive labels and empty/error states. Seed values are in business-rules.md and forms-and-fields.md.

**8. Audit `/staff/audit` (US-62):** filters for who/what/when/record, results and no-results state. **No personal data in audit event payload text.**

**9. Staff shell:** top bar, nav item hover/active, language switch; show separate admin and intake-worker navigation. Confirm active menu matches actual routes. Include one French content-length frame.

### Required prototype links

Prototype with at least one complete positive path and an error path per flow. Use Present mode. Add per-frame notes containing route and user-story ID. Post developer links on #454, #489 and #470 only after those actual Figma nodes exist.

## Anthony — Release 1 coverage

On new `R1 · Public`, `R1 · Household` and `R1 · Store` pages, create from running app/appropriate wireframe: app shells, Welcome, Sign in, Not Found, **Accept invitation** (new; #431, password rules/expired/used), Become partner, Browse listings, Listing detail + reserve, Post listing, Confirm pickup. Include French primary frames, one English length test per area and one error branch per flow.

Specific behaviour from #651: listings visibly show store, pickup window, units left, best-before and photo; sold out, max three active reservations and unavailable household are explicit. Reservation confirmation shows a **six-character** pickup code. Store scan confirmation displays first name + last initial and a rapid large icon/text result; unknown/other store/already picked up/cancelled are danger, late pickup warning. Add coloured end frames from later-release My reservations/My listings where Release 1 flow requires them.

## Status-to-tone mapping

- Household: Draft neutral; Submitted and Awaiting visit info; Review required and Renewal needed warning; Approved success; Suspended and Rejected danger.
- Listing: Published success; Sold out, Closed and Cancelled neutral.
- Reservation: Reserved info; Picked up success; Cancelled neutral; Cancelled by store warning; No-show danger.
- Partner application: Submitted info; Approved success; Rejected danger.
- Store/category: Active success; Inactive/deactivated neutral.
- Pickup scan: Confirmed success; Late pickup warning; Unknown code, other store, already picked up and cancelled danger.

## Acceptance and handoff

1. Foundations page: actual 10-shade Mantine colour variables, semantic aliases, token values, rationale, contrast measurements and colour-blindness simulation result.
2. Components page: real reusable states for filled/outline/subtle buttons, fields, alerts, badges, cards, tables, drawers, dialogs, filters, app bars/nav, loading/empty/error.
3. New R1 pages contain all applicable frames and every specified state. Original wireframes unchanged.
4. Links to new frames on #431/#454/#470/#489; reviewer comments on #651; stakeholder feedback recorded.
5. Export correct named PNGs to `docs/03-design/mockups/` and update design-system.md and wiki pages when Figma screens are final.
6. Documentation PR uses `[PR] SET-33: ...`, `Closes #651`, AI declaration and `AI_USAGE.md` update; substantive teammate review, green CI and merge commit (no squash).

**This handoff is not itself completion of #651.** Do not close #651 until every Figma screen, reviewed prototype, export and wiki item is verified.
