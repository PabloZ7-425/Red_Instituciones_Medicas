import os

import mysql.connector

from apps.historiales.domain.ports import DatabaseAdapter


class MySQLAdapter(DatabaseAdapter):
    def health_check(self):
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "mysql"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            database=os.getenv("MYSQL_DB", "pediatrico"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            connection_timeout=3,
        )
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            return cursor.fetchone()[0] == 1
        finally:
            connection.close()
