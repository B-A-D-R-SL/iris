# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code

"""PostgreSQL field types used by the stores module."""

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import EmailField


class CitextEmailField(EmailField):
    """Validate email addresses in Django and store them as PostgreSQL citext."""

    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        """Use the schema's case-insensitive PostgreSQL column type."""
        return "citext"
