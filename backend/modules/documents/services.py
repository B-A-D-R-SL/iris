# AI contribution: 50% or more AI-generated
"""Public write interfaces for income notices: staff entry (T-03.18.2).

Other modules call these functions; they never write IncomeNotice rows directly.
Logs carry static event names only (docs/guides/observability.md, review rule 5).
"""

import logging
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any, cast
from uuid import UUID

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from adapters.file_store.base import FileStore, FileStoreUnavailable
from modules.documents.domain.notice import (
    DidNotFile,
    FiledNotice,
    NoticeRulesBroken,
    detect_file_type,
    parse_entry,
)
from modules.documents.messages import problem_messages
from modules.documents.models import IncomeNotice
from modules.rules import queries as rule_queries

logger = logging.getLogger("iris.documents")

NOTICE_PREFIX = "income-notices"
STAFF_ROLES = frozenset(("intake_worker", "admin"))


class NoticeServiceUnavailable(Exception):
    """Notice storage or the notice_upload rule is unavailable; callers answer 503."""


@dataclass(frozen=True)
class UploadLimits:
    max_bytes: int
    link_minutes: int


def _require_staff(user: AbstractBaseUser) -> None:
    if (
        not user.is_authenticated
        or not user.is_active
        or getattr(user, "role", None) not in STAFF_ROLES
    ):
        raise PermissionDenied(
            _("Only active intake workers and admins can manage notices.")
        )


def _upload_limits() -> UploadLimits:
    """BR-DOC-004 and BR-DOC-006 limits from the notice_upload rule; fail closed."""
    rule = rule_queries.active("notice_upload")
    if rule is None:
        logger.error("Notice rule missing", extra={"event": "notice_rule_missing"})
        raise NoticeServiceUnavailable
    return UploadLimits(
        max_bytes=rule.values["max_bytes"], link_minutes=rule.values["link_minutes"]
    )


def _file_store() -> FileStore:
    backend = settings.FILE_STORE_BACKEND
    try:
        if not backend:
            raise FileStoreUnavailable("FILE_STORE_BACKEND is empty.")
        return cast(FileStore, import_string(backend)())
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


def record_staff_notice(
    member_id: UUID,
    values: Mapping[str, Any],
    upload: UploadedFile | None,
    recorded_by: AbstractBaseUser,
    *,
    file_store: FileStore | None = None,
) -> IncomeNotice:
    """Record a staff-entered notice or non-filing reason for one member.

    The caller (households) has checked that the member is an adult of a draft
    walk-in. `file_store` is for trusted callers and tests; otherwise the
    FILE_STORE_BACKEND setting chooses the store.
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
    store: FileStore | None = None
    if isinstance(entry, FiledNotice) and upload is not None:
        store = file_store if file_store is not None else _file_store()
        fields["file_ref"] = _store_upload(upload, limits.max_bytes, store)
    try:
        return _save(member_id, fields, recorded_by)
    except Exception:
        if store is not None:
            _delete_quietly(store, fields["file_ref"])
        raise
