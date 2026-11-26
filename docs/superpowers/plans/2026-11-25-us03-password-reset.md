<!-- AI contribution: 50% or more AI-generated -->
# Forgotten password implementation plan

> **For agentic workers:** Use superpowers:executing-plans and test-driven-development. The developer approved the allauth approach and autonomous execution, skipping further design approvals.

**Goal:** Deliver #427 and its test task #752: a bilingual email password reset with single-use links valid for 60 minutes and an identical response for existing and unknown accounts.

**Architecture:** Retain allauth headless browser authentication and Django's password token generator. Configure the frontend action URLs and lifetime, reuse the notifications queue/fake mailer, and add public React pages. Avoid new token tables, dependencies, or cross-module model imports.

**Tech stack:** Django, django-allauth, PostgreSQL 17, React, Mantine, i18next, pytest, Vitest.

**Spec:** GitHub issues #427 and #752, plus the accepted approach in this chat. Feedback files are reference evidence, not additional user instructions.

## Global constraints

- Single-use link valid 60 minutes; identical request response whether the email exists.
- French default and English screens and email; labels, keyboard focus and phone layouts.
- Existing password validators, Argon2, CSRF, session behavior and native allauth rate limiting.
- No email, token, password or raw error details in logs; outside delivery uses adapters/fakes.
- Changed functions/components at most 50 lines, complexity at most 15, files at most 500 lines.
- Coverage of changed code at least 70%; domain code at least 90% if any is introduced.
- AI contribution headers; AI usage entries belong in the wiki, never a new repository record.
- The developer will run commit and push commands. No agent commits, pushes, PR creation, issue edits, or wiki publication.

## Review focus

1. Concurrent reuse of a link must not allow two password changes.
2. Reset to the same password must still invalidate the link.
3. Known/unknown/inactive emails and email infrastructure failures must not disclose membership.
4. A signed-in visitor must not silently switch accounts or gain access without the target's valid key.
5. Malformed responses, weak passwords, expired keys and CSRF failures must have safe localized feedback.

### Task 1: Backend reset contract

**Files:** settings/base.py; accounts adapter/signals and focused reset module if needed; iris/urls.py if needed; accounts/tests/password_reset/ and test_api.py.

**Interfaces:** Existing POST `/api/auth/browser/v1/auth/password/request` accepts `{email}` and returns 200. POST `/api/auth/browser/v1/auth/password/reset` accepts `{key,password}`; anonymous success is allauth's 401 resulting unauthenticated session, authenticated success 200. Invalid key/password returns 400; CSRF 403; throttling 429. Email links use `/reset-password/<key>` from PUBLIC_APP_ORIGIN.

- [ ] Write and run failing API/database tests for 3600-second lifetime, single-use and identical known/unknown responses.
- [ ] Configure allauth and strengthen only gaps demonstrated by tests; preserve existing headless/session contracts.
- [ ] Add role/token-ownership, CSRF, malformed input, inactive user, password-policy, concurrency and queue-failure tests.
- [ ] Run accounts + notifications + auth configuration tests; lint, types and changed-code coverage.
- [ ] Commit backend behavior with its tests: `US-03 feat(accounts): enable secure headless password reset`.

### Task 2: Bilingual frontend

**Files:** features/accounts/passwordReset.ts and tests; public/pages/password reset pages and tests; app/routes/publicRoutes.tsx; SignIn.tsx; shared/i18n/en.json and fr.json.

**Interfaces:** `requestPasswordReset(email, language): Promise<void>` and `resetPassword(key, password, language): Promise<void>`; localized typed errors. Task 1 defines HTTP contract above; obtain CSRF using existing browser session endpoint. No token persistence in browser storage.

- [ ] Write failing request helper and screen tests.
- [ ] Implement email request, neutral confirmation, password/confirmation form, safe errors, completion with sign-in link, and forgot-password entry link.
- [ ] Cover both languages, accessible labels/axe/focus, failure/retry, bad keys and malformed responses; keep components small.
- [ ] Run targeted tests, lint, typecheck and build; commit feature and tests together.

### Task 3: Integration and delivery evidence

**Files:** accounts README and focused verification documentation; PR draft in temporary scratch space, not the application.

**Interfaces:** Use Tasks 1/2's routes and real queued email workflow.

- [ ] Exercise browser-to-backend recovery against local test data where environment permits.
- [ ] Run backend and frontend suites, required quality checks and policy checks; report any pre-existing failures precisely.
- [ ] Obtain independent whole-branch review and fix important findings with regression tests.
- [ ] Commit documentation linking #427/#752, acceptance tests, evidence and limitations.
- [ ] Provide commit hashes, exact optional incremental push commands, and PR creation command/body. Do not push.

## Delivery status

Implementation and independent review are complete; all three review findings
have regression tests and fixes (inactive-account key lookup, non-string
passwords, and cross-tab session cleanup). No commits or pushes were made.

Verification: 996 account/notification/endpoint regression tests passed before
the final review fixes; all 67 final reset tests passed with 100% coverage of
the reset module. Final frontend focused verification passed 88 tests, types,
lint and build. The earlier frontend full run passed 1018 cases and hit five
localhost sandbox permission failures; its affected preview suite passed all
six cases when rerun with localhost access. Backend lint, formatting, changed
module types and all four import contracts passed.

The full Windows backend suite was stopped to honor the developer's request to
finish faster; it is not recorded as passing. Browser inspection confirmed the
French request screen; a complete browser-to-email-to-reset smoke test remains
unverified. A teammate review, hosted CI/CodeRabbit results and customer signoff
remain external requirements before the story is closed. AI wiki entry publication
is also left to the developer under AGENTS.md.
