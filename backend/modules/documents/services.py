# AI contribution: 50% or more AI-generated
"""Public write interfaces for income notices: staff entry (T-03.18.2).

Other modules call these functions; they never write IncomeNotice rows directly.
Logs carry static event names only (docs/guides/observability.md, review rule 5).
"""

import logging
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, NoReturn
from uuid import UUID

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from adapters.file_store.base import FileStore, FileStoreUnavailable, StoredFileMissing
from adapters.file_store.registry import configured_store
from modules.accounts.queries import is_intake_staff
from modules.audit import services as audit_services
from modules.documents.domain.notice import (
    DidNotFile,
    FiledNotice,
    NoticeRulesBroken,
    detect_file_type,
    extension_for,
    parse_entry,
)
from modules.documents.messages import problem_messages
from modules.documents.models import IncomeNotice
from modules.rules import queries as rule_queries

logger = logging.getLogger("iris.documents")

NOTICE_PREFIX = "income-notices"
# BR-DOC-006: file links are signed for one staff user with this salt.
SIGNING_SALT = "documents.notice-file"


class NoticeServiceUnavailable(Exception):
    """Notices cannot be stored or opened right now; callers answer 503."""

    code = "storage_unavailable"
    message = _("Notice storage is unavailable. Try again later.")


class NoticeSettingsMissing(NoticeServiceUnavailable):
    """No active notice_upload rule: run `manage.py seed_rules`."""

    code = "notice_settings_missing"
    message = _("Notice settings are not set up yet. Ask an administrator.")


class NoticeFileNotFound(Exception):
    """No file to give: unknown notice, no file, or an invalid, expired or other's link."""


@dataclass(frozen=True)
class FileLink:
    token: str
    expires_at: datetime


@dataclass(frozen=True)
class NoticeFile:
    content: bytes
    content_type: str
    filename: str


@dataclass(frozen=True)
class UploadLimits:
    max_bytes: int
    link_minutes: int


def _require_staff(user: AbstractBaseUser) -> None:
    if not is_intake_staff(user):
        raise PermissionDenied(
            _("Only active intake workers and admins can manage notices.")
        )


def _upload_limits() -> UploadLimits:
    """BR-DOC-004 and BR-DOC-006 limits from the notice_upload rule; fail closed."""
    rule = rule_queries.active("notice_upload")
    if rule is None:
        logger.error("Notice rule missing", extra={"event": "notice_rule_missing"})
        raise NoticeSettingsMissing
    return UploadLimits(
        max_bytes=rule.values["max_bytes"], link_minutes=rule.values["link_minutes"]
    )


def _file_store() -> FileStore:
    try:
        return configured_store(settings.FILE_STORE_BACKEND)
    except FileStoreUnavailable as exc:
        logger.error("File store failed", extra={"event": "notice_file_store_failed"})
        raise NoticeServiceUnavailable from exc


def _field_errors(error: NoticeRulesBroken) -> ValidationError:
    return ValidationError(problem_messages(error))


def _store_upload(upload: UploadedFile, max_bytes: int, store: FileStore) -> str:
    """BR-DOC-004: read at most one byte over the limit, check it, store it privately."""
    upload.seek(0)
    content = upload.read(max_bytes + 1)
    try:
        file_type = detect_file_type(content, max_bytes)
    except NoticeRulesBroken as exc:
        raise _field_errors(exc) from exc
    try:
        return store.put(
            content, content_type=file_type.content_type, prefix=NOTICE_PREFIX
        )
    except FileStoreUnavailable as exc:
        logger.error("File store failed", extra={"event": "notice_file_store_failed"})
        raise NoticeServiceUnavailable from exc


def _delete_quietly(store: FileStore, reference: str) -> None:
    try:
        store.delete(reference)
    except FileStoreUnavailable:
        logger.error(
            "Notice file cleanup failed", extra={"event": "notice_file_cleanup_failed"}
        )


def _entry_fields(entry: FiledNotice | DidNotFile) -> dict[str, Any]:
    if isinstance(entry, DidNotFile):
        return {
            "status": IncomeNotice.Status.DID_NOT_FILE,
            "did_not_file_reason": entry.reason,
        }
    return {"status": IncomeNotice.Status.CONFIRMED, **asdict(entry)}


@transaction.atomic
def _save(
    member_id: UUID, fields: dict[str, Any], recorded_by: AbstractBaseUser
) -> IncomeNotice:
    """BR-DOC-005: the new entry replaces the member's current notice, kept as history."""
    superseded = IncomeNotice.objects.filter(
        member_id=member_id, superseded_at__isnull=True
    ).update(superseded_at=timezone.now())
    notice = IncomeNotice(
        member_id=member_id,
        source=IncomeNotice.Source.STAFF,
        recorded_by_id=recorded_by.pk,
        **fields,
    )
    notice.full_clean()
    notice.save()
    if superseded:
        logger.info("Notice superseded", extra={"event": "notice_superseded"})
    logger.info("Notice recorded", extra={"event": "notice_recorded"})
    return notice


@dataclass(frozen=True)
class PreparedNotice:
    """A checked entry whose file, if any, is already in private storage."""

    fields: dict[str, Any]
    store: FileStore | None = None


def prepare_staff_notice(
    values: Mapping[str, Any],
    upload: UploadedFile | None,
    recorded_by: AbstractBaseUser,
    *,
    file_store: FileStore | None = None,
) -> PreparedNotice:
    """Check an entry (BR-DOC-001 to 004) and store its file, before any lock is taken.

    Storing can take seconds, so callers hold no database lock meanwhile. Pass the
    result to save_prepared_notice, or to discard_prepared_notice if it is not saved.
    `file_store` is for trusted callers and tests; otherwise the FILE_STORE_BACKEND
    setting chooses the store.
    """
    _require_staff(recorded_by)
    limits = _upload_limits()
    try:
        entry = parse_entry(
            values, has_file=upload is not None, today=timezone.localdate()
        )
    except NoticeRulesBroken as exc:
        raise _field_errors(exc) from exc
    fields = _entry_fields(entry)
    if not isinstance(entry, FiledNotice) or upload is None:
        return PreparedNotice(fields)
    store = file_store if file_store is not None else _file_store()
    fields["file_ref"] = _store_upload(upload, limits.max_bytes, store)
    return PreparedNotice(fields, store)


def save_prepared_notice(
    member_id: UUID, prepared: PreparedNotice, recorded_by: AbstractBaseUser
) -> IncomeNotice:
    """Save a prepared entry as the member's current notice (BR-DOC-005).

    The caller has checked that the member is an adult of a draft walk-in.
    """
    _require_staff(recorded_by)
    return _save(member_id, prepared.fields, recorded_by)


def discard_prepared_notice(prepared: PreparedNotice) -> None:
    """Remove the stored file of an entry that will not be saved."""
    if prepared.store is not None:
        _delete_quietly(prepared.store, prepared.fields["file_ref"])


def record_staff_notice(
    member_id: UUID,
    values: Mapping[str, Any],
    upload: UploadedFile | None,
    recorded_by: AbstractBaseUser,
    *,
    file_store: FileStore | None = None,
) -> IncomeNotice:
    """Prepare and save a staff-entered notice or non-filing reason for one member."""
    prepared = prepare_staff_notice(values, upload, recorded_by, file_store=file_store)
    try:
        return save_prepared_notice(member_id, prepared, recorded_by)
    except Exception:
        discard_prepared_notice(prepared)
        raise


def _notice_with_file(notice_id: UUID | str) -> IncomeNotice:
    notice = IncomeNotice.objects.filter(pk=notice_id).exclude(file_ref="").first()
    if notice is None:
        raise NoticeFileNotFound
    return notice


def issue_file_link(notice_id: UUID, staff_user: AbstractBaseUser) -> FileLink:
    """BR-DOC-006: a link to one notice's file for this staff user, audited as a view."""
    _require_staff(staff_user)
    limits = _upload_limits()
    notice = _notice_with_file(notice_id)
    # The lifetime travels in the signed link, so a later rule change does not
    # lengthen or shorten links already handed out.
    token = TimestampSigner(salt=SIGNING_SALT).sign_object(
        {"n": str(notice.pk), "u": str(staff_user.pk), "m": limits.link_minutes}
    )
    audit_services.record(staff_user, "view", "income_notice", notice.pk, {})
    logger.info("Notice file link issued", extra={"event": "notice_file_link_issued"})
    return FileLink(token, timezone.now() + timedelta(minutes=limits.link_minutes))


def _linked_notice_id(token: str, staff_user: AbstractBaseUser) -> str:
    """The notice id a valid, unexpired link of this staff user points to."""
    signer = TimestampSigner(salt=SIGNING_SALT)
    try:
        payload = signer.unsign_object(token)  # signature only: read the lifetime
        minutes = payload.get("m") if isinstance(payload, dict) else None
        if not isinstance(minutes, int):
            _refuse_link("notice_file_link_invalid")
        signer.unsign_object(token, max_age=timedelta(minutes=minutes))
    except SignatureExpired as exc:
        _refuse_link("notice_file_link_expired", exc)
    except BadSignature as exc:
        _refuse_link("notice_file_link_invalid", exc)
    if payload.get("u") != str(staff_user.pk):
        _refuse_link("notice_file_link_wrong_user")
    return str(payload["n"])


def _refuse_link(event: str, cause: Exception | None = None) -> NoReturn:
    logger.warning("Notice file link refused", extra={"event": event})
    raise NoticeFileNotFound from cause


def open_file(
    token: str, staff_user: AbstractBaseUser, *, file_store: FileStore | None = None
) -> NoticeFile:
    """BR-DOC-006: the file behind a link, for the staff user it was issued to."""
    _require_staff(staff_user)
    notice = _notice_with_file(_linked_notice_id(token, staff_user))
    store = file_store if file_store is not None else _file_store()
    try:
        stored = store.read(notice.file_ref)
    except StoredFileMissing as exc:
        logger.error("Notice file missing", extra={"event": "notice_file_missing"})
        raise NoticeFileNotFound from exc
    except FileStoreUnavailable as exc:
        logger.error("File store failed", extra={"event": "notice_file_store_failed"})
        raise NoticeServiceUnavailable from exc
    logger.info("Notice file downloaded", extra={"event": "notice_file_downloaded"})
    filename = f"notice-{notice.tax_year}.{extension_for(stored.content_type)}"
    return NoticeFile(stored.content, stored.content_type, filename)
