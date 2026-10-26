# AI contribution: 50% or more AI-generated
from datetime import datetime

from django.core.cache.backends.db import DatabaseCache
from django.db import connections
from django.db.backends.utils import CursorWrapper


class AuthCache(DatabaseCache):
    """Cull expired authentication records without evicting active ones."""

    def _cull(self, db: str, cursor: CursorWrapper, now: datetime, num: int) -> None:
        connection = connections[db]
        table = connection.ops.quote_name(self.cache_model_class._meta.db_table)
        cursor.execute(
            f"DELETE FROM {table} WHERE expires < %s",
            [connection.ops.adapt_datetimefield_value(now)],
        )
