# AI contribution: 50% or more AI-generated
"""Option A: Azure AI Document Intelligence `prebuilt-layout` plus our own parser."""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlparse

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError, ServiceRequestError, ServiceResponseError

from layout_parser import LayoutDocument, parse_layout
from reader import DocumentReadError, NoticeReading

logger = logging.getLogger(__name__)

MODEL_ID = "prebuilt-layout"
TIMEOUT_SECONDS = 60  # US-22 budget per notice
# Poll every second when the service sends no Retry-After. The SDK's generated default is 30 s
# (1.0.2's public client lowers it to 1 s); passing it pins the timing whatever the client.
POLLING_SECONDS = 1
_SERVICE_ERRORS = (HttpResponseError, ServiceRequestError, ServiceResponseError)
_ENV_ENDPOINT = "AZURE_DI_ENDPOINT"
_ENV_KEY = "AZURE_DI_KEY"
_ENV_PRICE = "AZURE_DI_PRICE_PER_PAGE_USD"


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"environment variable {name} is not set")
    return value


class AzureLayoutReader:
    """Reads a notice with Document Intelligence layout, then parses the labelled lines.

    Exposes `last_cost_usd` (pages x price), `last_result` (the raw AnalyzeResult as a dict, kept
    even when parsing it fails, for `run.py --record`) and `settings` (model and endpoint host,
    never the key). Each analyze result is deleted from the service after the call.
    """

    def __init__(
        self, client: DocumentIntelligenceClient, price_per_page_usd: float, endpoint_host: str
    ) -> None:
        self._client = client
        self.price_per_page_usd = price_per_page_usd
        self.settings = {"model": MODEL_ID, "endpoint host": endpoint_host}
        self.last_cost_usd = 0.0
        self.last_result: dict[str, Any] | None = None

    @classmethod
    def from_env(cls) -> AzureLayoutReader:
        """Build from AZURE_DI_ENDPOINT, AZURE_DI_KEY and AZURE_DI_PRICE_PER_PAGE_USD."""
        endpoint = _require_env(_ENV_ENDPOINT)
        key = _require_env(_ENV_KEY)
        price_text = _require_env(_ENV_PRICE)
        try:
            price = float(price_text)
        except ValueError:
            raise ValueError(f"environment variable {_ENV_PRICE} is not a number") from None
        client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))
        return cls(client, price, urlparse(endpoint).hostname or "unknown")

    def read_notice(self, content: bytes, content_type: str) -> NoticeReading:
        # content_type is not passed on: the SDK (1.0.2) sends bytes as application/octet-stream
        # and ignores it.
        self.last_cost_usd = 0.0
        self.last_result = None
        operation_id: str | None = None
        try:
            poller = self._client.begin_analyze_document(
                MODEL_ID, content, polling_interval=POLLING_SECONDS
            )
            operation_id = poller.details["operation_id"]
            result = poller.result(timeout=TIMEOUT_SECONDS)
            if result is None or not poller.done():
                raise DocumentReadError("analysis timed out")
            raw = result.as_dict()
            self.last_result = raw
            self.last_cost_usd = len(raw.get("pages") or []) * self.price_per_page_usd
            return parse_layout(LayoutDocument.from_analyze_result(raw))
        except _SERVICE_ERRORS + (TimeoutError,) as exc:
            raise DocumentReadError(f"service call failed: {type(exc).__name__}") from exc
        except ValueError as exc:
            raise DocumentReadError(str(exc)) from exc
        finally:
            if operation_id is not None:
                self._delete_result(operation_id)

    def _delete_result(self, operation_id: str) -> None:
        """Ask the service to drop the analyzed notice now instead of keeping it 24 hours."""
        try:
            self._client.delete_analyze_result(MODEL_ID, operation_id)
        except _SERVICE_ERRORS as exc:
            logger.warning("azure_layout_delete_failed %s", type(exc).__name__)
