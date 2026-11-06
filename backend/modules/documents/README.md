<!-- AI contribution: 50% or more AI-generated -->
# Documents module

**Owner pair:** Registration
**Status:** T-03.18.2 (#468): staff-entered notices of assessment, private storage and staff file links

## Responsibility

Own `IncomeNotice`: each adult's notice of assessment (Revenu Québec, line 199
total income) or the reason the adult did not file, and the private file of the
notice. Other modules read notices through `queries.py` and write them only
through `services.py`.

## Layers

| File | Responsibility |
| --- | --- |
| `domain/notice.py` | Pure rules BR-DOC-001 to BR-DOC-004: required values, tax year and notice date, non-filing reason, file type from its first bytes and size |
| `messages.py` | French and English text for each rule problem |
| `models.py` | `IncomeNotice`, with the one-current-notice and shape constraints |
| `services.py` | `record_staff_notice`, `issue_file_link`, `open_file` |
| `queries.py` | `current_notices` |
| `api/` | Staff file link and download endpoints, `{code, message, fields}` errors |
| `tests/` | Rules, model, service and API tests (#467) |

The walk-in endpoint that records a notice lives in `households`, because only
`households` may check the household and member (it calls `documents`, never
the reverse; see the import-linter contracts in `backend/pyproject.toml`).

## Public interfaces

- `services.record_staff_notice(member_id, values, upload, recorded_by, *, file_store=None) -> IncomeNotice`:
  checks the rules, stores a filed notice's file, supersedes the member's current
  notice and saves the new one. Raises `ValidationError` (field errors),
  `PermissionDenied` (not active staff) or `NoticeServiceUnavailable` (no
  `notice_upload` rule or no storage). Callers check the member first
  (`households.services.record_walk_in_notice`).
- `services.issue_file_link(notice_id, staff_user) -> FileLink(token, expires_at)`:
  a link signed for that staff user, recorded in the audit log as a `view` of
  `income_notice`. Raises `NoticeFileNotFound` when the notice has no file.
- `services.open_file(token, staff_user) -> NoticeFile(content, content_type, filename)`:
  the file behind a valid, unexpired link of the same user.
- `queries.current_notices(member_ids) -> dict[member_id, IncomeNotice]`: the
  current notice of each member, for approval (#469).

## Endpoints

| Method | Path | Who | Result |
| --- | --- | --- | --- |
| GET | `/api/staff/notices/{id}/file/` | Active intake worker or admin | `{url, expires_at}`; 404 if the notice has no file |
| GET | `/api/staff/notice-files/{token}/` | The staff user the link was issued to | The file as an attachment (`nosniff`, `private, no-store`); 404 if invalid, expired or someone else's |

Other roles get 403, signed-out visitors 401. Unavailable storage answers 503
`storage_unavailable`; a missing `notice_upload` rule answers 503
`notice_settings_missing`. Messages follow `Accept-Language`. The download
ignores the client's `Accept` header (the file sets its type); its OpenAPI
response is a binary PDF, JPEG or PNG. Who counts as intake staff comes from
`accounts.queries.is_intake_staff`.

## Rules and settings

The rules BR-DOC-001 to BR-DOC-007 are in
[business-rules.md](../../../docs/02-requirements/business-rules.md). The file
size limit (`max_bytes`, 10 MB) and the link lifetime (`link_minutes`, 5) come
from the `notice_upload` rule type; run `python manage.py seed_rules` once on a
database that does not have it yet. A link keeps the lifetime it was issued
with (signed into it), even if the rule changes later. Files go through `adapters/file_store`,
chosen by `FILE_STORE_BACKEND` (Azure Blob in local and production settings,
the in-memory fake in tests); an empty setting makes uploads and downloads
answer 503.

## Privacy, audit and logging

- Files are stored under random names, never the uploaded file name; the
  container is private and Iris never returns a storage URL.
- Issuing a file link is audited (`audit.services.record`, empty metadata).
- Logs carry static event names only (`notice_recorded`, `notice_superseded`,
  `notice_file_link_issued`, `notice_file_downloaded`, refused-link warnings,
  storage errors), never income, names, postal codes, reasons, tokens or file
  names (review rule 5, `docs/guides/observability.md`).
- Superseded notices and their files are kept; deleting them belongs to
  scheduled deletion (US-74).

## Not in this module yet

Listing the notices in the walk-in draft (#470), approval (#469), photo
metadata removal and the five-page limit (US-21), AI reading (US-22).
