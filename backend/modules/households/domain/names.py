# AI contribution: 50% or more AI-generated
"""Short names shown outside the intake team. Plain strings, no Django."""


def short_name(first_name: str, last_name: str) -> str | None:
    """First name and last initial: "Fatou" and "Diallo" give "Fatou D." (BR-RES-003)."""
    first, last = first_name.strip(), last_name.strip()
    initial = f"{last[0].upper()}." if last else ""
    return " ".join(part for part in (first, initial) if part) or None


def short_full_name(full_name: str) -> str | None:
    """The same for a name kept in one field, such as the alternate's."""
    parts = full_name.split()
    if not parts:
        return None
    return short_name(parts[0], parts[-1] if len(parts) > 1 else "")
