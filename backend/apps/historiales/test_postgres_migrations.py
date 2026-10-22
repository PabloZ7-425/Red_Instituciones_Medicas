import os
from unittest import TestCase, skipUnless

@skipUnless(os.getenv("TEST_HOSPITAL_POSTGRES") == "1", "B3 real requiere destino PostgreSQL aislado")
class PostgreSQLMigrationTests(TestCase):
    def setUp(self):
        from apps.historiales.testing.postgres import PostgreSQLHarness
        self.harness = PostgreSQLHarness(legacy=True)
        self.addCleanup(self.harness.close)
        with self.harness.connect() as conn:
            conn.execute("""INSERT INTO paciente(dpi_cui,nombres,apellidos,fecha_nacimiento)
                            VALUES('DEMO-MIG','Paciente','DEMO','2000-01-01')""")

    def run_phase(self, phase):
        path = self.harness.schema_dir / "migrations" / phase
        with self.harness.connect() as conn:
            conn.execute(path.read_text(encoding="utf-8"))

    def test_unknown_dates_block_finalization_without_fabrication_or_loss(self):
        import psycopg
        with self.harness.connect() as conn:
            conn.execute("INSERT INTO cita(id_paciente,id_medico,fecha_hora,estado) VALUES(1,1,'2020-01-01 10:00:00','atendida')")
            conn.execute("INSERT INTO consulta(id_paciente,id_medico,id_cita,notas_evolucion) VALUES(1,1,1,'DEMO original')")
        self.run_phase("001_expand.sql")
        from apps.historiales.domain.context import ContextoClinico
        from apps.historiales.domain.errors import PersistenciaNoDisponible
        with self.assertRaises(PersistenciaNoDisponible):
            self.harness.repo(ContextoClinico("hospital", "DEMO", "admin", "1")).obtener_historial("H-P-1")
        with self.assertRaises(psycopg.Error):
            self.run_phase("002_finalize.sql")
        with self.harness.connect() as conn:
            self.assertEqual(conn.execute("SELECT fecha,notas_evolucion FROM consulta").fetchone(), (None, "DEMO original"))
            # Confirmed date for this fixture ONLY; explicitly differs from the appointment.
            conn.execute("UPDATE consulta SET fecha='2020-01-02' WHERE id_consulta=1")
        self.run_phase("002_finalize.sql")
        self.run_phase("001_expand.sql")
        self.run_phase("002_finalize.sql")
        with self.harness.connect() as conn:
            self.assertEqual(str(conn.execute("SELECT fecha FROM consulta").fetchone()[0]), "2020-01-02")
            self.assertEqual(conn.execute("SELECT count(*) FROM hospital_schema_version").fetchone()[0], 1)
        with self.assertRaises(psycopg.errors.NotNullViolation), self.harness.connect() as conn:
            conn.execute("INSERT INTO consulta(id_paciente,id_medico,notas_evolucion) VALUES(1,1,'DEMO')")

    def test_legacy_admission_timezone_must_be_explicitly_confirmed(self):
        import psycopg
        with self.harness.connect() as conn:
            conn.execute("""INSERT INTO ingreso_hospitalario(id_paciente,id_medico_responsable,id_cama,
                            fecha_hora_ingreso,fecha_hora_alta,tipo_ingreso)
                            VALUES(1,1,1,'2020-01-01 06:00:00','2020-01-02 07:00:00','DEMO')""")
        self.run_phase("001_expand.sql")
        from apps.historiales.domain.context import ContextoClinico
        from apps.historiales.domain.errors import PersistenciaNoDisponible
        with self.assertRaises(PersistenciaNoDisponible):
            self.harness.repo(ContextoClinico("hospital", "DEMO", "admin", "1")).listar_ingresos("H-P-1")
        with self.assertRaises(psycopg.Error):
            self.run_phase("002_finalize.sql")
        with self.harness.connect() as conn:
            self.assertIsNone(conn.execute("SELECT ingreso_utc FROM ingreso_hospitalario").fetchone()[0])
            # This fixture explicitly confirms the old timestamps were Guatemala civil time.
            conn.execute("UPDATE ingreso_hospitalario SET ingreso_utc='2020-01-01T12:00:00Z',alta_utc='2020-01-02T13:00:00Z'")
        self.run_phase("002_finalize.sql")
        with self.harness.connect() as conn:
            self.assertEqual(conn.execute("SELECT fecha_hora_ingreso FROM ingreso_hospitalario").fetchone()[0].hour, 6)
            self.assertEqual(conn.execute("SELECT ingreso_utc FROM ingreso_hospitalario").fetchone()[0].hour, 12)

    def test_invalid_legacy_text_blocks_constraints_instead_of_silent_replacement(self):
        import psycopg
        with self.harness.connect() as conn:
            conn.execute("INSERT INTO consulta(id_paciente,id_medico,notas_evolucion) VALUES(1,1,NULL)")
        self.run_phase("001_expand.sql")
        with self.harness.connect() as conn:
            conn.execute("UPDATE consulta SET fecha='2020-01-01'")
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.run_phase("002_finalize.sql")
        with self.harness.connect() as conn:
            self.assertIsNone(conn.execute("SELECT notas_evolucion FROM consulta").fetchone()[0])
            nullable = conn.execute("""SELECT is_nullable FROM information_schema.columns
                        WHERE table_schema=%s AND table_name='consulta' AND column_name='fecha'""", (self.harness.schema,)).fetchone()[0]
            self.assertEqual(nullable, "YES")  # finalization DDL rolled back as a unit.
