# AI contribution: 50% or more AI-generated
# I have drafted a plan for implementation, then reviewed and tested the code
"""Create the B.A.D.R. store with placeholder details until they are confirmed."""

from typing import Any

from django.core.management.base import BaseCommand

from modules.stores.services import ensure_badr_store


class Command(BaseCommand):
    """Seed the first B.A.D.R. Store without overwriting staff changes."""

    help = "Create the B.A.D.R. store once, preserving later edits on repeat runs."

    def handle(self, *args: Any, **options: Any) -> None:
        """Report whether the B.A.D.R. Store was created or already existed."""
        store, created = ensure_badr_store()
        action = "Created" if created else "Already exists"
        self.stdout.write(self.style.SUCCESS(f"{action}: {store.name} store."))
