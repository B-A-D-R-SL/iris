# AI contribution: 50% or more AI-generated
"""Lazy operator translations that are safe before Django's app registry loads."""

import gettext
import os
from functools import lru_cache
from pathlib import Path

from django.utils.functional import lazy


@lru_cache(maxsize=2)
def _catalog(language: str) -> gettext.NullTranslations:
    return gettext.translation(
        "django",
        localedir=Path(__file__).parent / "locale",
        languages=[language],
        fallback=True,
    )


def _translate(message: str) -> str:
    language = os.environ.get("IRIS_OPERATOR_LANGUAGE", "en")
    return _catalog(language if language in {"fr", "en"} else "en").gettext(message)


# Standard gettext does not need Django apps/settings, including during import errors.
operator_gettext = lazy(_translate, str)
