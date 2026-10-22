"""Real MySQL harness; only generated test_b4_* databases and b4r_* users."""
import os
import re
import secrets
import uuid
from contextlib import contextmanager
from pathlib import Path

import mysql.connector

from apps.historiales.infrastructure.adapters.mysql_adapter import MySQLAdapter


def execute_script(connection, source):
    """Read the project's SQL client DELIMITER format without splitting routines."""
    delimiter, statement = ";", ""
    with connection.cursor(buffered=True) as c:
        for line in source.splitlines():
            if line.strip().startswith("--") or not line.strip():
                continue
            if line.upper().startswith("DELIMITER "):
                if statement.strip():
                    raise ValueError("Incomplete SQL before DELIMITER")
                delimiter = line.split()[1]
                continue
            statement += line + "\n"
            if statement.rstrip().endswith(delimiter):
                c.execute(statement.rstrip()[:-len(delimiter)])
                while c.nextset():
                    pass
                statement = ""
        if statement.strip():
            raise ValueError("Incomplete SQL script")


class MySQLHarness:
    def __init__(self, *, legacy=False):
        if os.environ.get("PEDIATRIA_TEST_DB") != "test_b4_pediatria":
            raise RuntimeError("Se requiere destino aislado PEDIATRIA_TEST_DB=test_b4_pediatria")
        self.database = "test_b4_" + uuid.uuid4().hex
        self.role = "b4r_" + uuid.uuid4().hex[:24]  # MySQL user identifiers <=32 characters.
        self.password = secrets.token_urlsafe(32)
        self.kwargs = dict(host=os.environ.get("MYSQL_HOST", "mysql"), port=3306,
                           user="root", password=os.environ["MYSQL_ROOT_PASSWORD"], connection_timeout=5)
        self.schema_dir = Path(os.environ.get("PEDIATRIA_SCHEMA_DIR", "/mysql-schema"))
        self.closed = False
        with self.connect(admin=True) as conn:
            with conn.cursor() as c:
                c.execute(f"CREATE DATABASE `{self.database}` CHARACTER SET utf8mb4")
                c.execute(f"CREATE USER '{self.role}'@'%' IDENTIFIED BY %s", (self.password,))
        try:
            path = Path(__file__).parents[1] / "fixtures/mysql_legacy.sql" if legacy else self.schema_dir / "init.sql"
            with self.connect() as conn:
                execute_script(conn, path.read_text(encoding="utf-8"))
                with conn.cursor() as c:
                    c.execute("INSERT INTO especialidad(id,nombre) VALUES(1,'DEMO')")
                    c.execute("""INSERT INTO medico(id,nombre,apellido,colegiado,especialidad_id)
                                 VALUES(1,'DEMO','Uno','DEMO-1',1),(2,'DEMO','Dos','DEMO-2',1)""")
                    c.execute("INSERT INTO medicamento(nombre) VALUES('DEMO no administrar')")
                    c.execute("INSERT INTO vacuna(nombre) VALUES('DEMO sin uso clínico')")
                self.grant_runtime(conn)
        except BaseException:
            self.close()
            raise

    @contextmanager
    def connect(self, *, runtime=False, admin=False):
        kwargs = self.kwargs | ({} if admin else {"database": self.database})
        if runtime:
            kwargs.update(user=self.role, password=self.password)
        conn = mysql.connector.connect(**kwargs)
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def sql(self, statement, params=()):
        with self.connect() as conn:
            with conn.cursor(buffered=True) as c:
                c.execute(statement, params)
                return c.fetchall() if c.with_rows else c.lastrowid

    def migrate(self, phase):
        with self.connect() as conn:
            execute_script(conn, (self.schema_dir / "migrations" / phase).read_text(encoding="utf-8"))
            self.grant_runtime(conn)

    def grant_runtime(self, conn):
        grants = (self.schema_dir / "runtime_role.sql").read_text(encoding="utf-8")
        grants = grants[grants.index("GRANT SELECT"):]
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='pediatria_schema_version'")
            if not c.fetchone()[0]:
                grants = "\n".join(line for line in grants.splitlines() if "pediatria_schema_version" not in line)
        grants = grants.replace("pediatrico.", self.database + ".").replace("pediatria_runtime", self.role)
        execute_script(conn, grants)

    def repo(self, contexto):
        harness = self

        class InstrumentedMySQL(MySQLAdapter):
            fail = False
            header_fail = False
            gate = None

            def _connect(self):
                conn = mysql.connector.connect(**(harness.kwargs | {
                    "database": harness.database, "user": harness.role, "password": harness.password}))
                self.last_pid = conn.connection_id
                return conn

            def _lock_patient(self, cursor, number, *, active=True):
                row = super()._lock_patient(cursor, number, active=active)
                if self.gate:
                    entered, release = self.gate
                    self.gate = None
                    entered.set()
                    if not release.wait(10):
                        raise AssertionError("Root lock gate timed out")
                return row

            def _after_write(self, cursor):
                if self.fail:
                    self.fail = False
                    cursor.execute("SELECT b4_injected_failure_after_mutation")

            def _after_header(self, cursor):
                if self.header_fail:
                    self.header_fail = False
                    cursor.execute("SELECT b4_injected_failure_between_header_and_detail")

        return InstrumentedMySQL(contexto=contexto)

    def fail_next(self, repo):
        repo.fail = True

    def gate_next(self, repo, entered, release):
        repo.gate = (entered, release)

    def inactive(self, repo, paciente_id):
        from apps.historiales.infrastructure.adapters.mysql_clinical import internal
        self.sql("UPDATE paciente SET estado='inactivo' WHERE id=%s", (internal(paciente_id, "P"),))

    def close(self):
        if self.closed:
            return
        if not re.fullmatch(r"test_b4_[a-f0-9]{32}", self.database) or not re.fullmatch(r"b4r_[a-f0-9]{24}", self.role):
            raise RuntimeError("Se cancela limpieza fuera del destino aislado")
        with self.connect(admin=True) as conn:
            with conn.cursor() as c:
                c.execute(f"DROP DATABASE `{self.database}`")
                c.execute(f"DROP USER '{self.role}'@'%'")
        self.closed = True
