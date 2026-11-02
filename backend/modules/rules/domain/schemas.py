# AI contribution: 50% or more AI-generated
"""JSON schemas and defaults for every supported business-rule type."""

from typing import Any, Final

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError

JSONSchema = dict[str, Any]


class RuleValidationError(ValueError):
    """Framework-independent validation failure for rule values."""

    def __init__(self, errors: dict[str, str | list[str]]) -> None:
        self.errors = errors
        super().__init__(str(errors))


RULE_TYPES: Final = (
    "lico_thresholds",
    "auto_approval",
    "priority",
    "tiers",
    "strikes",
    "reservations",
    "listing_safety",
    "listing_posting",
    "file_validity",
    "retention",
)


def _object_schema(properties: dict[str, JSONSchema]) -> JSONSchema:
    """Build a closed object schema whose listed properties are all required."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


RULE_SCHEMAS: Final[dict[str, JSONSchema]] = {
    "lico_thresholds": _object_schema(
        {
            "year": {"type": "integer", "minimum": 2000, "maximum": 9999},
            "source_url": {"type": "string", "format": "uri"},
            "retrieved_on": {"type": "string", "format": "date"},
            "thresholds": {
                "type": "object",
                "properties": {
                    str(size): {"type": "integer", "minimum": 1} for size in range(1, 8)
                },
                "required": [str(size) for size in range(1, 8)],
                "additionalProperties": False,
            },
        }
    ),
    "auto_approval": _object_schema(
        {
            "accepted_tax_years": {
                "type": "array",
                "items": {"type": "integer", "minimum": 2000, "maximum": 9999},
                "minItems": 1,
                "uniqueItems": True,
            },
            "minimum_field_confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
            "maximum_income_threshold_ratio": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
        }
    ),
    "priority": _object_schema(
        {
            "income_gap_max_points": {"type": "integer", "minimum": 0},
            "child_points": {"type": "integer", "minimum": 0},
            "children_max_points": {"type": "integer", "minimum": 0},
            "extra_member_points": {"type": "integer", "minimum": 0},
            "extra_members_max_points": {"type": "integer", "minimum": 0},
            "recent_pickup_penalty_points": {"type": "integer", "minimum": 0},
            "recent_pickup_lookback_days": {"type": "integer", "minimum": 1},
            "recent_pickup_max_penalty_points": {
                "type": "integer",
                "minimum": 0,
            },
        }
    ),
    "tiers": _object_schema(
        {
            "tier_1_min_score": {"type": "integer", "minimum": 0},
            "tier_2_min_score": {"type": "integer", "minimum": 0},
            "tier_2_delay_hours": {"type": "number", "minimum": 0},
            "tier_2_pickup_window_ratio": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
            "tier_3_delay_hours": {"type": "number", "minimum": 0},
            "tier_3_pickup_window_ratio": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
        }
    ),
    "strikes": _object_schema(
        {
            "warning_at": {"type": "integer", "minimum": 1},
            "tier_penalty_at": {"type": "integer", "minimum": 1},
            "tier_penalty_levels": {"type": "integer", "minimum": 1},
            "tier_penalty_days": {"type": "integer", "minimum": 1},
            "reservation_block_at": {"type": "integer", "minimum": 1},
            "reservation_block_days": {"type": "integer", "minimum": 1},
            "expires_after_days": {"type": "integer", "minimum": 1},
        }
    ),
    "reservations": _object_schema(
        {
            "max_active_per_household": {"type": "integer", "minimum": 1},
            "pickup_code_length": {"type": "integer", "minimum": 1},
        }
    ),
    "listing_safety": _object_schema(
        {
            "best_before_margin_days": {"type": "integer", "minimum": 0},
            "prohibited_category_codes": {
                "type": "array",
                "items": {
                    "type": "string",
                    "minLength": 1,
                    "pattern": "^[a-z0-9][a-z0-9_-]*$",
                },
                "uniqueItems": True,
            },
        }
    ),
    "listing_posting": _object_schema(
        {
            "title_min_length": {"type": "integer", "minimum": 2, "maximum": 80},
            "title_max_length": {"type": "integer", "minimum": 2, "maximum": 80},
            "description_max_length": {"type": "integer", "minimum": 1, "maximum": 500},
            "quantity_max": {"type": "integer", "minimum": 1, "maximum": 999},
            "max_per_household": {"type": "integer", "minimum": 1, "maximum": 10},
            "estimated_value_max_cents": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100_000,
            },
            "pickup_start_max_days": {"type": "integer", "minimum": 1},
            "pickup_min_minutes": {"type": "integer", "minimum": 1},
            "pickup_max_minutes": {"type": "integer", "minimum": 1},
            "photo_max_bytes": {"type": "integer", "minimum": 1},
            "photo_max_dimension": {"type": "integer", "minimum": 1},
        }
    ),
    "file_validity": _object_schema(
        {
            "approved_months": {"type": "integer", "minimum": 1},
            "renewal_banner_days": {"type": "integer", "minimum": 0},
            "reminder_days": {
                "type": "array",
                "items": {"type": "integer", "minimum": 0},
                "minItems": 1,
                "uniqueItems": True,
            },
        }
    ),
    "retention": _object_schema(
        {
            "notice_files_days": {"type": "integer", "minimum": 1},
            "unrenewed_files_months": {"type": "integer", "minimum": 1},
            "email_logs_months": {"type": "integer", "minimum": 1},
            "audit_events_years": {"type": "integer", "minimum": 1},
            "assistant_chats_days": {"type": "integer", "minimum": 1},
        }
    ),
}

# Defaults come from the acceptance criteria of the user stories that consume
# them. LICO values are deliberately loaded from SET-08's reviewed CSV instead.
DEFAULT_RULE_VALUES: Final[dict[str, dict[str, Any]]] = {
    "auto_approval": {
        "accepted_tax_years": [2025],
        "minimum_field_confidence": 0.90,
        "maximum_income_threshold_ratio": 0.95,
    },
    "priority": {
        "income_gap_max_points": 60,
        "child_points": 6,
        "children_max_points": 24,
        "extra_member_points": 2,
        "extra_members_max_points": 10,
        "recent_pickup_penalty_points": 3,
        "recent_pickup_lookback_days": 14,
        "recent_pickup_max_penalty_points": 15,
    },
    "tiers": {
        "tier_1_min_score": 60,
        "tier_2_min_score": 35,
        "tier_2_delay_hours": 2,
        "tier_2_pickup_window_ratio": 0.25,
        "tier_3_delay_hours": 4,
        "tier_3_pickup_window_ratio": 0.50,
    },
    "strikes": {
        "warning_at": 1,
        "tier_penalty_at": 2,
        "tier_penalty_levels": 1,
        "tier_penalty_days": 30,
        "reservation_block_at": 3,
        "reservation_block_days": 14,
        "expires_after_days": 90,
    },
    "reservations": {
        "max_active_per_household": 3,
        "pickup_code_length": 6,
    },
    "listing_safety": {
        "best_before_margin_days": 0,
        "prohibited_category_codes": [],
    },
    "listing_posting": {
        "title_min_length": 2,
        "title_max_length": 80,
        "description_max_length": 500,
        "quantity_max": 999,
        "max_per_household": 10,
        "estimated_value_max_cents": 100_000,
        "pickup_start_max_days": 7,
        "pickup_min_minutes": 30,
        "pickup_max_minutes": 720,
        "photo_max_bytes": 5 * 1024 * 1024,
        "photo_max_dimension": 1280,
    },
    "file_validity": {
        "approved_months": 12,
        "renewal_banner_days": 30,
        "reminder_days": [30, 7],
    },
    "retention": {
        "notice_files_days": 30,
        "unrenewed_files_months": 12,
        "email_logs_months": 12,
        "audit_events_years": 2,
        "assistant_chats_days": 30,
    },
}

_FORMAT_CHECKER: Final = FormatChecker()
_VALIDATORS: Final = {
    rule_type: Draft202012Validator(schema, format_checker=_FORMAT_CHECKER)
    for rule_type, schema in RULE_SCHEMAS.items()
}


def validate_rule_values(rule_type: str, values: dict[str, Any]) -> None:
    """Validate values for a known rule type and report every schema error."""
    validator = _VALIDATORS.get(rule_type)
    if validator is None:
        supported = ", ".join(RULE_TYPES)
        raise RuleValidationError(
            {
                "rule_type": f"Unknown rule type '{rule_type}'. Expected one of: {supported}."
            }
        )

    errors = sorted(validator.iter_errors(values), key=_error_sort_key)
    if errors:
        raise RuleValidationError(
            {"values": [_format_error(error) for error in errors]}
        )
    if rule_type == "listing_posting" and (
        values["title_min_length"] > values["title_max_length"]
        or values["pickup_min_minutes"] > values["pickup_max_minutes"]
    ):
        raise RuleValidationError(
            {"values": ["Posting minimums cannot exceed maximums."]}
        )


def _error_sort_key(error: JSONSchemaValidationError) -> tuple[str, str]:
    path = ".".join(str(part) for part in error.absolute_path)
    return path, error.message


def _format_error(error: JSONSchemaValidationError) -> str:
    path = ".".join(str(part) for part in error.absolute_path) or "$"
    return f"{path}: {error.message}"
