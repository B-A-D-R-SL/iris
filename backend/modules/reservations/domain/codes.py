# AI contribution: 50% or more AI-generated
"""Pickup codes (US-41, BR-RES-010). Plain Python, no Django.

The code is fixed at 6 characters. The team pack defines it that way: the
business rules say "6 characters" with no *(setting)* marker, the database
design makes ``pickup_code`` a ``char(6)``, and US-41's acceptance criteria
say "6-character pickup code". It is not a rule setting: a longer code could
not be stored in the column.
"""

from collections.abc import Callable, Sequence

# No look-alike characters: no I, L, O, 0 or 1.
PICKUP_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
PICKUP_CODE_LENGTH = 6

Chooser = Callable[[Sequence[str]], str]


def new_pickup_code(choose: Chooser) -> str:
    """A new code of PICKUP_CODE_LENGTH characters from PICKUP_CODE_ALPHABET.

    ``choose`` picks one character from a sequence. Production passes
    ``secrets.choice``, so codes cannot be guessed; tests pass a fake.
    """
    # rule: BR-RES-010 six characters from the pickup alphabet.
    code = "".join(choose(PICKUP_CODE_ALPHABET) for _ in range(PICKUP_CODE_LENGTH))
    if len(code) != PICKUP_CODE_LENGTH or not set(code) <= set(PICKUP_CODE_ALPHABET):
        raise ValueError("The chooser must return one alphabet character at a time.")
    return code
