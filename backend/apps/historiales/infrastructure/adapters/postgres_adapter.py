import os

import psycopg

from apps.historiales.domain.ports import DatabaseAdapter
from apps.historiales.infrastructure.adapters.postgres_clinical import PostgreSQLClinical


class PostgreSQLAdapter(PostgreSQLClinical, DatabaseAdapter):
    def _connect(self):
        return psycopg.connect(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            dbname=os.getenv("POSTGRES_DB", "hospital"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD"),
            connect_timeout=3,
        )

    def health_check(self):
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone()[0] == 1
