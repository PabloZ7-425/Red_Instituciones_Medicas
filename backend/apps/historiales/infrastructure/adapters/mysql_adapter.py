import os

import mysql.connector

from apps.historiales.domain.ports import DatabaseAdapter
from .mysql_clinical import MySQLClinical


class MySQLAdapter(MySQLClinical, DatabaseAdapter):
    def _connect(self):
        return mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "mysql"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            database=os.getenv("MYSQL_DB", "pediatrico"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            connection_timeout=3,
        )

    def health_check(self):
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()[0] == 1
            cursor.close()
            return result
        finally:
            connection.close()
