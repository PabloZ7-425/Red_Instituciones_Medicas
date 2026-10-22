import os
from datetime import date
from unittest import TestCase, skipUnless

from apps.historiales.domain.context import ContextoClinico
from apps.historiales.testing.repository_contract import CONSULTA, PACIENTE, DIAGNOSTICO, TRATAMIENTO


@skipUnless(os.getenv("TEST_PEDIATRIA_MYSQL") == "1", "B4 requiere MySQL real aislado")
class MySQLMigrationTests(TestCase):
    def setUp(self):
        from apps.historiales.testing.mysql import MySQLHarness
        self.harness = MySQLHarness(legacy=True)
        self.addCleanup(self.harness.close)

    def seed_legacy(self):
        h = self.harness
        h.sql("""INSERT INTO paciente(id,nombre,apellidos,identificacion,fecha_nacimiento)
                 VALUES(1,'DEMO','Conservado','DEMO-1','2000-01-01')""")
        h.sql("INSERT INTO cita(id,paciente_id,medico_id,fecha,estado) VALUES(1,1,1,'2020-01-02','atendida'),(2,1,1,'2020-01-03','atendida')")
        h.sql("INSERT INTO consulta(id,paciente_id,medico_id,cita_id,fecha,observaciones) VALUES(1,1,1,1,'2020-01-02','DEMO'),(2,1,1,2,'2020-01-03','DEMO')")
        h.sql("INSERT INTO diagnostico(id,codigo,descripcion) VALUES(10,'DEMO','Conservado'),(20,'DEMO2','Conservado2')")
        h.sql("INSERT INTO consulta_diagnostico(id,consulta_id,diagnostico_id) VALUES(101,1,10),(102,1,20),(103,2,10)")
        h.sql("INSERT INTO tratamiento(id,nombre,indicaciones,consulta_id) VALUES(201,'Nombre histórico','DEMO',1),(202,'Otro','DEMO',1)")
        h.sql("INSERT INTO receta(id,consulta_id,fecha) VALUES(301,1,'2020-01-05')")
        h.sql("INSERT INTO detalle_receta(id,receta_id,medicamento_id,dosis,frecuencia) VALUES(401,301,1,'DEMO1','DEMO1'),(402,301,1,'DEMO2','DEMO2')")
        h.sql("INSERT INTO tutor(id,nombres,apellidos,parentesco,dpi) VALUES(1,'DEMO','Tutor','Dato histórico no inferido','DEMO')")
        h.sql("INSERT INTO paciente_tutor(paciente_id,tutor_id) VALUES(1,1)")
        h.sql("INSERT INTO control_de_crecimiento(paciente_id,fecha,peso,talla,altura,percentil) VALUES(1,'2020-01-02',12.5,75,76,50)")

    def test_ambiguous_history_blocks_finalize_until_evidence_and_preserves_all_details(self):
        import mysql.connector
        self.seed_legacy()
        h = self.harness
        h.migrate("001_expand.sql")
        h.migrate("001_expand.sql")
        h.migrate("002_reconcile.sql")
        with self.assertRaises(mysql.connector.DatabaseError):
            h.migrate("003_finalize.sql")
        self.assertEqual(h.sql("SELECT consulta_diagnostico_id FROM tratamiento"), [(None,), (None,)])
        self.assertEqual(h.sql("SELECT is_nullable FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='tratamiento' AND column_name='consulta_diagnostico_id'"), [("YES",)])
        self.assertEqual(h.sql("SELECT COUNT(*) FROM pediatria_schema_version"), [(0,)])
        h.sql("""INSERT INTO pediatria_conciliacion(tipo,id,origen_id,evidencia) VALUES
                 ('tratamiento',201,102,'Ficha sintética 201: vínculo confirmado'),
                 ('tratamiento',202,101,'Ficha sintética 202: vínculo confirmado'),
                 ('receta',301,201,'Ficha sintética 301: vínculo confirmado')""")
        h.migrate("002_reconcile.sql")
        h.migrate("003_finalize.sql")
        h.migrate("003_finalize.sql")
        self.assertEqual(h.sql("SELECT nombre,consulta_diagnostico_id FROM tratamiento ORDER BY id"), [("Nombre histórico", 102), ("Otro", 101)])
        self.assertEqual(h.sql("SELECT fecha FROM receta"), [(date(2020, 1, 5),)])
        repo = h.repo(ContextoClinico("pediatrico", "U", "admin", "1"))
        history = repo.obtener_historial("PED-P-1")
        branches = history["consultas"][0]["diagnosticos"]
        self.assertEqual(branches[0]["id"], "PED-D-101")
        self.assertEqual(branches[0]["tratamientos"][0]["id"], "PED-T-202")
        rows = branches[1]["tratamientos"][0]["recetas"]
        self.assertEqual([r["id"] for r in rows], ["PED-R-401", "PED-R-402"])
        follow = repo.obtener_seguimiento("PED-P-1")
        self.assertIsNone(follow["tutores"][0]["parentesco"])
        self.assertEqual(follow["tutores"][0]["parentesco_legacy"], "Dato histórico no inferido")
        self.assertIsNone(follow["crecimiento"][0]["peso_kg"])
        self.assertEqual(follow["crecimiento"][0]["mediciones_legacy"],
                         {"peso": "12.50", "talla": "75.00", "altura": "76.00", "percentil": "50.00"})

    def test_wrong_evidence_rolls_back_reconciliation_and_never_replaces_confirmed_links(self):
        import mysql.connector
        self.seed_legacy()
        h = self.harness
        h.migrate("001_expand.sql")
        h.sql("""INSERT INTO pediatria_conciliacion VALUES('tratamiento',201,101,'DEMO'),('tratamiento',202,103,'DEMO vínculo cruzado')""")
        with self.assertRaises(mysql.connector.DatabaseError):
            h.migrate("002_reconcile.sql")
        self.assertEqual(h.sql("SELECT consulta_diagnostico_id FROM tratamiento"), [(None,), (None,)])
        h.sql("UPDATE pediatria_conciliacion SET origen_id=102 WHERE id=202")
        h.migrate("002_reconcile.sql")
        h.sql("UPDATE pediatria_conciliacion SET origen_id=102 WHERE id=201")
        with self.assertRaises(mysql.connector.DatabaseError):
            h.migrate("002_reconcile.sql")
        self.assertEqual(h.sql("SELECT consulta_diagnostico_id FROM tratamiento WHERE id=201"), [(101,)])

    def test_new_schema_and_empty_legacy_migrate_idempotently_and_accept_the_core(self):
        h = self.harness
        for _ in range(2):
            for phase in ("001_expand.sql", "002_reconcile.sql", "003_finalize.sql"):
                h.migrate(phase)
        repo = h.repo(ContextoClinico("pediatrico", "U", "admin", "1"))
        p = repo.registrar_paciente(PACIENTE)
        c = repo.registrar_consulta(p["id"], CONSULTA)
        d = repo.registrar_diagnostico(c["id"], DIAGNOSTICO)
        repo.registrar_tratamiento(d["id"], TRATAMIENTO)
        self.assertEqual(h.sql("SELECT version FROM pediatria_schema_version"), [(1,)])
        from apps.historiales.testing.mysql import MySQLHarness
        fresh = MySQLHarness()
        self.addCleanup(fresh.close)
        for phase in ("001_expand.sql", "002_reconcile.sql", "003_finalize.sql"):
            fresh.migrate(phase)
        # Compare columns and constraint definitions, excluding database names.
        columns = """SELECT table_name,column_name,column_type,is_nullable,column_default,collation_name
                     FROM information_schema.columns WHERE table_schema=DATABASE() ORDER BY table_name,ordinal_position"""
        # Incremental ADD may change physical column order; relational meaning is unchanged.
        self.assertEqual(sorted(h.sql(columns)), sorted(fresh.sql(columns)))
        constraints = """SELECT table_name,constraint_name,constraint_type FROM information_schema.table_constraints
                         WHERE constraint_schema=DATABASE() ORDER BY table_name,constraint_name"""
        self.assertEqual(h.sql(constraints), fresh.sql(constraints))

    def test_partial_schema_never_serves_or_mutates_clinical_records(self):
        from apps.historiales.domain.errors import PersistenciaNoDisponible
        h = self.harness
        h.migrate("001_expand.sql")
        repo = h.repo(ContextoClinico("pediatrico", "U", "admin", "1"))
        for method, args in (("listar_pacientes", ()), ("registrar_paciente", (PACIENTE,))):
            with self.assertRaises(PersistenciaNoDisponible):
                getattr(repo, method)(*args)
        self.assertEqual(h.sql("SELECT COUNT(*) FROM paciente"), [(0,)])
