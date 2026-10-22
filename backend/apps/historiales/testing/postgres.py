"""Real PostgreSQL harness; restricted to test_b3_hospital and generated schemas."""
import os
import re
import secrets
import uuid
from pathlib import Path

import psycopg
from psycopg import sql

from apps.historiales.infrastructure.adapters.postgres_adapter import PostgreSQLAdapter


class PostgreSQLHarness:
    def __init__(self, *, legacy=False):
        if os.environ.get("HOSPITAL_TEST_DB") != "test_b3_hospital":
            raise RuntimeError("Se requiere destino aislado HOSPITAL_TEST_DB=test_b3_hospital")
        self.schema = "b3_" + uuid.uuid4().hex
        self.role = "b3r_" + uuid.uuid4().hex
        self.runtime_password = secrets.token_urlsafe(32)
        self.kwargs = dict(host=os.environ.get("POSTGRES_HOST", "postgres"),
                           port=os.environ.get("POSTGRES_PORT", "5432"), dbname="test_b3_hospital",
                           user=os.environ["PG_USER"], password=os.environ["PG_PASSWORD"], connect_timeout=3)
        self.schema_dir = Path(os.environ.get("HOSPITAL_SCHEMA_DIR", "/schema"))
        self.closed = False
        with psycopg.connect(**self.kwargs) as conn:
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
            conn.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD {}").format(
                sql.Identifier(self.role), sql.Literal(self.runtime_password)))
        try:
            if legacy:
                ddl = Path(__file__).parents[1] / "fixtures" / "postgres_legacy.sql"
            else:
                ddl = self.schema_dir / "init.sql"
            with self.connect() as conn:
                conn.execute(ddl.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO especialidad(id_especialidad,nombre,nivel_complejidad) VALUES(1,'DEMO',1)")
                conn.execute("""INSERT INTO medico(id_medico,id_especialidad,nombre_completo,colegiado)
                                VALUES(1,1,'DEMO profesional','DEMO-PRO'),(2,1,'DEMO profesional 2','DEMO-PRO2')""")
                conn.execute("INSERT INTO medicamento(nombre_comercial,principio_activo) VALUES('DEMO no administrar','DEMO')")
                conn.execute("INSERT INTO pabellon_edificio(nombre_pabellon) VALUES('DEMO')")
                conn.execute("INSERT INTO habitacion(id_pabellon,numero_habitacion) VALUES(1,'DEMO-1')")
                conn.execute("""INSERT INTO cama(id_habitacion,codigo_cama,estado_limpieza)
                                VALUES(1,'DEMO-CAMA-1','limpia'),(1,'DEMO-CAMA-2','limpia')""")
                # Apply the provider's actual grant statements to a private test
                # role/schema, without changing the production role or password.
                grants = (self.schema_dir / "runtime_role.sql").read_text(encoding="utf-8")
                grants = grants[grants.index("GRANT USAGE ON SCHEMA public"):]
                grants = grants.replace("SCHEMA public", "SCHEMA " + self.schema).replace("hospital_runtime", self.role)
                conn.execute(grants)
        except BaseException:
            self.close()
            raise

    def connect(self, *, runtime=False):
        kwargs = self.kwargs | ({"user": self.role, "password": self.runtime_password} if runtime else {})
        return psycopg.connect(**kwargs, options=f"-c search_path={self.schema},pg_catalog")

    def repo(self, contexto):
        harness = self

        class InstrumentedPostgreSQL(PostgreSQLAdapter):
            fail = False
            gate = None

            def _connect(self):
                conn = harness.connect(runtime=True)
                self.last_pid = conn.info.backend_pid
                return conn

            def _lock_patient(self, cursor, number, *, active=True):
                result = super()._lock_patient(cursor, number, active=active)
                if self.gate:
                    entered, release = self.gate
                    self.gate = None
                    entered.set()
                    if not release.wait(5):
                        raise AssertionError("Root-lock gate timed out")
                return result

            def _after_write(self, cursor):
                if self.fail:
                    self.fail = False
                    cursor.execute("SELECT b3_injected_failure_after_mutation")

        return InstrumentedPostgreSQL(contexto=contexto)

    def fail_next(self, repo):
        repo.fail = True

    def gate_next(self, repo, entered, release):
        repo.gate = (entered, release)

    def inactive(self, repo, paciente_id):
        from apps.historiales.infrastructure.adapters.postgres_clinical import internal
        with self.connect() as conn:
            conn.execute("UPDATE paciente SET estado='inactivo' WHERE id_paciente=%s", (internal(paciente_id, "P"),))

    def close(self):
        if self.closed:
            return
        if (not re.fullmatch(r"b3_[a-f0-9]{32}", self.schema)
                or not re.fullmatch(r"b3r_[a-f0-9]{32}", self.role)
                or self.kwargs["dbname"] != "test_b3_hospital"):
            raise RuntimeError("Se cancela limpieza fuera del destino aislado")
        with psycopg.connect(**self.kwargs) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
            conn.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(self.role)))
        self.closed = True
