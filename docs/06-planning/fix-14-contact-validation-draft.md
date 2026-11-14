<!-- AI contribution: 50% or more AI-generated -->

**Draft: FIX-14 — shared phone/postal rules and auth/store cleanup**

Implement [issue #640](https://github.com/B-A-D-R-SL/iris/issues/640) by making the existing contact-data paths agree with [forms-and-fields.md](../02-requirements/forms-and-fields.md), preserving the frontend improvements already merged in [PR #695](https://github.com/B-A-D-R-SL/iris/pull/695). The user approved this proposal against base `71bdd41`, and it has now been implemented locally. The original plan below is retained for traceability; the implementation record at the end describes adjustments and verification.

The relevant system constraints are the modular monolith's public module boundaries, pure Python domain code, backend-authoritative validation, French/English field errors, and support for incomplete walk-in drafts. See the [architecture](../04-architecture/architecture.md), [review rules](../05-process/review-rules.md), [design system](../guides/design-system.md), [API contract](../03-design/api.md), and [database schema](../03-design/database-schema.md).

1. **Treat CodeRabbit's comment as a request to prove parity.**

   In its [PR #695 walkthrough and linked-issue check](https://github.com/B-A-D-R-SL/iris/pull/695#issuecomment-6836228189), CodeRabbit links this issue and says the frontend changes do not establish agreement with the backend. It specifically leaves phone/postal parity unconfirmed. The comment also questions enabling size limits before prerequisite fixes; those limits are already enabled in the current code, with a `SignOutButton` exception assigned to FIX-14.

   Preserve #695's acceptance of lowercase/unspaced postal codes and familiar phone formatting, its Canadian postal-letter restrictions, its frontend layer rule, and its existing tests. Complete the backend contract and add evidence that both sides agree. Other PR #695 findings about navigation authorization and unrelated oversized screens belong to their respective tasks.

   The differences found before implementation were:

   | Path | Current behavior | Required change |
   | --- | --- | --- |
   | [Store model](../../backend/modules/stores/models.py) | Accepts any E.164 phone; postal regex accepts letters excluded by the household/frontend rules; formats postal codes independently. | Use the shared Canadian contact rules and normalization. |
   | [Partner application serializer](../../backend/modules/stores/api/serializers.py) and model | Uses another phone regex; direct API requests require canonical phone input; postal validation uses the broad store regex. | Use the same normalizers, including for requests that bypass the frontend. |
   | [Household serializer](../../backend/modules/households/api/serializers.py) and model | Normalizes formatted phones but accepts a national number beginning with 0 or 1, unlike the frontend. | Use the shared phone rule; retain draft behavior. |
   | [Frontend validators](../../frontend/src/shared/forms/validators.ts) | Already includes #695's case/spacing improvements and rejects invalid postal letters and phone prefixes. | Keep these improvements and prove agreement with the completed backend rule. |
   | [Frontend formatters](../../frontend/src/shared/forms/formats.ts) | Strip invalid characters and truncate input before validation. | Preserve invalid input long enough to reject it instead of silently submitting a different value. |

2. **Write down the exact contact contract and its test cases first.**

   The requirements specify a ten-digit Canadian phone stored as E.164 and a Canadian postal code stored uppercase with one space. Use the following interpretation, consistent with the established frontend/partner checks:

   | Input | Expected result |
   | --- | --- |
   | `5145550123`, `(514) 555-0123`, `514.555.0123`, `15145550123`, `+1 514 555 0123` | Accept and store `+15145550123`. |
   | `+447911123456`, `+10145550123`, `+11235550123`, seven digits, extra digits, letters or an extension | Reject. |
   | `H2X 1Y4`, `h2x1y4`, surrounding/repeated whitespace | Accept and store `H2X 1Y4`. |
   | `D2X 1Y4`, `H2O 1Y4`, `H2X 1U4`, `W2X 1Y4`, `Z2X 1Y4`, `H2X-1Y4`, extra/missing characters | Reject. |
   | An already canonical value normalized again | Return exactly the same value. |
   | Empty/whitespace/null values | Apply each field's existing required/optional rules; keep blank draft addresses valid. |

   Use the existing national-number first-digit restriction of 2–9. This remains format validation; a new area-code registry or external phone lookup is unnecessary for FIX-14.

   The existing US-17 postal helper also performs Unicode NFKD/accent folding. Preserve that normalization during extraction, mirror it in the frontend postal path, and test it explicitly. Make canonical digit checks ASCII on both sides after postal folding: fullwidth `Ｈ２Ｘ１Ｙ４` becomes `H2X 1Y4`, whereas `H٢X 1Y4` remains invalid. Python's `\d` currently accepts decimal digits that JavaScript's `\d` rejects. Record this deliberate tightening of undocumented digit acceptance. Do not change street/person folding or household duplicate-key construction.

   Put representative input/expected-result cases in one small language-neutral fixture, consumed by pytest and Vitest. Keep field-specific requiredness separate from the shared format cases. This provides concrete parity evidence for the CodeRabbit concern without introducing runtime schema generation.

3. **Extract a neutral backend utility and use it everywhere relevant.**

   Suggested structure:

   - `backend/modules/common/domain/contact.py`: pure `normalize_phone`, the moved US-17 `normalize_postal_code`, and typed value errors.
   - `backend/modules/common/validators.py`: Django validator adapters that delegate to those functions.
   - `backend/modules/common/api/fields.py`: DRF fields that normalize input and translate errors before canonical length validation.

   This is a shared utility package, with no business models or new Django application. The existing import-linter independence contract enumerates business modules; a neutral sibling package avoids a stores-to-households dependency. Keep `common.domain` within the existing domain-purity rule and verify the resulting graph with `lint-imports`. Framework adapters stay outside `domain/`.

   Move the implementation from [households/domain/address.py](../../backend/modules/households/domain/address.py), rather than copying it. Extract its folding support neutrally or keep postal folding self-contained; the shared helper must not import household internals transitively. Keep `normalize_address` calling that implementation and update callers, tests, and the [household error mapping](../../backend/modules/households/messages.py). Preserve the `InvalidPostalCode` type identity wherever it is used for translated messages.

   Replace the duplicated phone/postal patterns and normalizers in:

   - Store and PartnerApplication model fields and validation.
   - Partner application input fields, including `contact_phone`.
   - Household model phone/postal validation and holder/address serializer fields.
   - Household address-key normalization and related imports.

   Normalize before field-length and format checks. DRF's partner fields currently allow only seven postal characters and sixteen phone characters before `validate_*`, whereas household fields have different raw limits. Merely changing the `validate_*` methods would still reject otherwise accepted formatted input too early. Shared DRF fields should return normalized text from `to_internal_value`, then validate its canonical length.

   Likewise, Django `full_clean()` runs field validation before `Model.clean()`. Normalize nonempty contact values before that stage, for example in `clean_fields()` before delegating to Django, respecting excluded fields. Keep the shared validators as the format authority. Rely on the existing service/admin validation boundaries; this task does not require changing every model's `save()` behavior. Preserve household blank/partial draft handling and unchanged address keys for equivalent valid addresses.

   Keep the current API error envelopes and field names: partner errors remain on `contact_phone`/`postal_code`; walk-in errors retain dotted keys such as `address.postal_code`. Keep messages translated through installed locale catalogs and verify French and English. Do not move translations into an unregistered shared app and assume Django will discover them.

   Generate new reversible `AlterField` migrations where model validators change. Leave applied migrations unchanged. Check factories/seeds for newly rejected values; do not silently rewrite or delete existing records. Any legacy-data remediation should be identified explicitly before adding a data migration.

4. **Finish frontend parity through the actual fields and payloads.**

   Reuse normalization helpers within `shared/forms` so validators and input components follow the same contract. Keep the `app → areas → features → shared` import direction.

   Address a gap beyond the standalone tests added in #695: `normalizePostalCode()` currently turns `H2X-1Y4` or an overlong value into a valid code, and `phoneDigits()` removes arbitrary nondigits and takes only the first ten digits. The validators can therefore reject raw input while the form silently repairs it into a different accepted submission. Existing formatter tests explicitly expect some of this truncation and need to change.

   Accept the documented formatting, retain useful partial-input display, and preserve invalid characters/extra digits for validation rather than deleting them. Keep partial-edit formatting separate from strict complete-value normalization so ordinary typing and deletion remain usable. Review `PostalCodeField`'s `maxLength` alongside this change so pasted overlong input cannot be silently converted to a valid code. Preserve display of stored E.164 values.

   Cover both `PhoneField` and `PostalCodeField` with typing and paste tests, then verify partner and walk-in submissions. An invalid foreign/overlong phone or malformed postal code must not produce a valid request containing an altered value. Include the shared fixture cases in validator tests as well.

5. **Remove the dormant two-factor sign-in flow until US-09.**

   The current screen already shows its code step only when the server reports `mfa_authenticate`; this partially satisfies the issue's permitted gating option. However, [auth/api.ts](../../frontend/src/shared/auth/api.ts) still exports a request to `/api/auth/browser/v1/auth/2fa/authenticate`, and the backend does not install `allauth.mfa`. The [auth-routing guide](../guides/auth-routing.md) places MFA enrollment in later work.

   Recommended choice: remove the unused code flow for Release 1. Update `api.ts`, `authContext.ts`, `AuthProvider.tsx`, `SignIn.tsx`, the corresponding auth/sign-in tests, and unused French/English code-entry messages. Remove `loginWithCode`, `verifyCode`, the MFA result/state, and the code-entry UI. Keep the password login and session operations.

   Replace mocked successful MFA tests with an unexpected-challenge regression: if password login receives an unsupported challenge, show the existing translated unavailable error, make no two-factor request, and do not navigate as authenticated. Preserve CSRF initialization, invalid-credential and lockout handling, native HTTP 429 handling, existing-session HTTP 409 behavior, profile-lookup retry, role landing pages, query-cache clearing, and cross-tab session synchronization.

6. **Complete the small cleanup items without changing their behavior.**

   - Refactor [SignOutButton](../../frontend/src/shared/auth/SignOutButton.tsx), currently 51 lines, into focused functions of at most 50 lines. A small sign-out action hook or control component is sufficient. Preserve pending/disabled state and visible failure feedback; reuse the existing sign-out regression tests. Remove only its entry from `OVER_THE_LIMIT` in `frontend/eslint.config.js`.
   - Reduce the 52-line admin test at [stores/tests/test_admin.py](../../backend/modules/stores/tests/test_admin.py) using the existing store factory/admin fixture and a short form-data helper. Retain permission, real admin form submission, and persisted-value assertions. Existing platform tests already cover dev-admin bootstrapping.
   - Delete [stores/tests/test_api.py at the base revision](https://github.com/B-A-D-R-SL/iris/blob/71bdd41/backend/modules/stores/tests/test_api.py), which contains only placeholder documentation. Preserve the real partner application API tests in their separate files. The Store REST API remains US-14.

7. **Validate the behavior and document the evidence.**

   Add meaningful coverage for:

   - Shared valid/invalid/normalization cases, canonical idempotence, whitespace, Unicode behavior, and field-specific blank handling.
   - Store/partner model and admin validation, walk-in create/patch storage, and partner submission through approval into the resulting Store.
   - Stable household duplicate keys and continued saving of incomplete drafts.
   - French/English errors with existing API shapes.
   - Actual frontend typing/paste/submission behavior and absence of any two-factor request.

   Update existing expectations that deliberately reject newly supported formatting: the partner API test currently rejects bare `5145550123`, and a Store model test rejects a hyphenated local number. Replace them with acceptance/storage assertions and retain genuinely invalid cases.

   Run targeted suites first: shared contact tests; household address/walk-in/duplicate tests; store model/admin/partner API/decision tests; frontend formats/validators/fields, PartnerApply, WalkIn, auth API, SignIn, and lint-rule tests. Then run the relevant [CI gates](../../.github/workflows/ci.yml): backend Ruff, formatting, mypy, import-linter, missing-migration check, and pytest coverage; frontend ESLint, Prettier, TypeScript, Vitest coverage, and production build. Regenerate/check OpenAPI-derived types if field schema metadata changes. Require green checks on the actual PR head.

   Update the forms contract with any clarified prefix/Unicode behavior, the design-system parity wording, the auth-routing guide, the household/store README references, and the API documentation for accepted direct-request formats. Add a short architecture note identifying the shared utility if needed. Complete the AI contribution declarations and `AI_USAGE.md` entry when implementing; do not record proposed tests as already passed.

   Suggested commits: `FIX-14 refactor(validation): share Canadian contact rules`, `FIX-14 fix(forms): align field normalization and validation`, and `FIX-14 fix(auth): remove dormant MFA and finish cleanup`. The final PR should include `Closes #640`, the AI contribution level and assisted files, and a short table of parity cases with their actual test results. This directly answers CodeRabbit's unresolved validation concern.

**Implementation record**

The approved scope is implemented. These details changed or became more specific during implementation:

- Added `modules.common.forms.ContactField` and a Store admin ModelForm in addition to the planned adapters. ModelForm validates raw text before model validation, so changing `clean_fields()` alone would still reject formatted admin input too early.
- The shared DRF input fields omit `max_length` metadata. Strict normalizers already enforce exact canonical lengths, while an input schema with `maxLength: 7` or `12` would incorrectly forbid accepted formatting. Model storage lengths are unchanged.
- Household address-key derivation now runs after contact field validation in `clean_fields()`. It respects excluded address fields and preserves blank/partial drafts; the underlying address-key algorithm is unchanged.
- Preserved Python's existing whitespace and nonzero Unicode combining-class behavior. JavaScript's `\s` and `\p{M}` differ, so the frontend uses matching whitespace handling and generated character classes. It also rejects characters unassigned in the backend's Unicode version before JavaScript can fold newer compatibility characters into valid ASCII. Regenerate these tables with the backend Python runtime using `frontend/scripts/generate-unicode-combining.py` when changing that runtime. Shared cases include nonbreaking/control whitespace, rejected FEFF, fullwidth digits, Arabic-Indic digits, accents, a combining-class-zero mark and the newer outlined Latin H.
- Frontend formatters retain invalid/overlong input, and the postal field no longer truncates pasted text through `maxLength`. Partial editing remains separate from complete-value validation. Required contact composites also reject whitespace recognized by Python but missed by JavaScript's `trim()`.
- Reused existing installed French/English catalog messages; no new backend locale catalog was needed. Removed unused frontend MFA translations with the dormant flow.
- Added reversible validator-state migrations `stores.0005_shared_contact_validation` and `households.0007_shared_contact_validation`; existing records are not rewritten or deleted.
- The formerly 52-line admin test is now 19 lines with a 15-line form-data helper. `SignOutButton` is 33 lines and its action hook is 22 lines; its size exception is removed. The placeholder Store API test file is deleted.

**Verification results**

- Backend: final changed-path suite **63 passed**; shared contact/requiredness/Unicode-version suite **15 passed**. An earlier broader focused run had 256 passing tests; its two new fixture setup failures were corrected and covered by the final passing run.
- Backend Ruff, formatting, mypy, all four import contracts, missing-migration check and production deployment check pass.
- Frontend: **48 contact cases**, all shared-field/formatter/validator tests, **17 walk-in tests**, **9 partner-form tests** and **22 sign-in tests** pass. ESLint, formatting, TypeScript and the production build pass.
- The final API schema validates and generated frontend types remain up to date. API-generation regression checks: **8 passed, 1 skipped** (the Python-specific case is skipped when supplying schema through stdin).
- The full frontend run encountered five loading/wait failures in the existing listing suite. All **21 listing tests pass** when rerun using a disposable local Testing Library configuration with `asyncUtilTimeout: 5000`. Repository test settings and assertions were not changed.
- **Full coverage runs were stopped at the user's request because of limited time.** The backend run ended with **738 passed, no failures**, approximately 29% complete; much of its runtime was spent hashing fixture passwords with Argon2. Full-suite completion, final coverage percentages and CI status are not claimed.

Tests used cached Docker images, refreshed locked frontend dependencies and a separate temporary PostgreSQL database. The running application and its database were untouched. Source implementation is complete; full CI remains to be run when time permits.
