# AI contribution: 50% or more AI-generated
"""The document reader interface that a later story ports into the Django backend."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ReadField[T]:
    """One value read from a notice, with the reader's confidence in it."""

    value: T | None  # None: could not be read
    confidence: float  # 0.0 to 1.0


UNREAD: ReadField = ReadField(value=None, confidence=0.0)  # a field the reader could not read


@dataclass(frozen=True)
class NoticeReading:
    """The fields Iris needs from a notice of assessment."""

    full_name: ReadField[str]  # as printed, e.g. "Zoé Jessica Lapointe"
    street_number: ReadField[str]
    street_name: ReadField[str]
    unit: ReadField[str]  # "" when the notice prints no unit
    postal_code: ReadField[str]  # "H2X 4N1"
    tax_year: ReadField[int]
    total_income_cents: ReadField[int]  # line 199, Montant établi
    notice_date: ReadField[dt.date]


class DocumentReadError(Exception):
    """The service failed or its answer is unusable: the household enters the values by hand."""


class DocumentReader(Protocol):
    """Reads a notice of assessment. `content_type` is a PDF, PNG or JPEG media type."""

    def read_notice(self, content: bytes, content_type: str) -> NoticeReading: ...


@runtime_checkable
class MeteredReader(DocumentReader, Protocol):
    """A spike reader that reports what its last call cost."""

    last_cost_usd: float
