# AI contribution: 50% or more AI-generated
"""Privacy checks shared by business services."""

import re

SENSITIVE_HOUSEHOLD_REASON = re.compile(
    r"\b(?:sin|social insurance|nas|assurance sociale|income|salary|revenu|salaire|"
    r"immigration|permanent resident|citizen|refugee|réfugié|refugie|passport|"
    r"passeport|document text|texte de document|contact|named?|nommée?)\b"
    r"|[\w.+-]+@[\w.-]+\.[a-z]{2,}"
    r"|\b\d{3}[ -]?\d{3}[ -]?\d{3}\b"
    r"|(?:\$|\bCAD\b)\s*\d"
    r"|\b(?:earns?|gagne|income|salary|revenu|salaire)\D{0,12}\d{4,}\b",
    re.IGNORECASE,
)


def household_reason_contains_sensitive_data(reason: str) -> bool:
    """Detect common personal, identity, document and financial details."""
    return SENSITIVE_HOUSEHOLD_REASON.search(reason) is not None
