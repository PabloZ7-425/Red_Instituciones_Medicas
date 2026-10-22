"""Explicit B1 test double. Does not certify a database's transactions or durability."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import date
from threading import RLock

from apps.historiales.application.validation import normalizar_busqueda
from apps.historiales.domain.errors import Conflicto, PersistenciaNoDisponible, RecursoNoEncontrado
from apps.historiales.domain.ports import HistorialRepository, MedicamentoCatalogo


class MemoryHarness:
    def __init__(self):
        self.lock = RLock()
        self.data = {}
        self.sequence = 0

    def repo(self, contexto):
        return MemoryRepository(contexto=contexto, harness=self)

    def inactive(self, repo, paciente_id):
        with self.lock:
            repo._find(paciente_id)["estado"] = "inactivo"

    def fail_next(self, repo):
        repo.failure = True

    def gate_next(self, repo, entered, release):
        repo.gate = (entered, release)

    def close(self):
        self.data.clear()


class MemoryRepository(HistorialRepository, MedicamentoCatalogo):
    def __init__(self, *, contexto, harness):
        self.contexto, self.harness = contexto, harness
        self.failure = False
        self.gate = None
        self.medicine_id = "DEMO-M-1"

    def _find(self, key):
        row = self.harness.data.get(key)
        if row is None or row["institution"] != self.contexto.institucion:
            raise RecursoNoEncontrado()
        return row

    def _root(self, key):
        row = self._find(key)
        while "parent" in row:
            row = self._find(row["parent"])
        return row

    def _output(self, row):
        return deepcopy({k: v for k, v in row.items() if k not in {"kind", "parent", "institution"}})

    def _insert(self, kind, dto, parent=None, **extra):
        self.harness.sequence += 1
        row = dict(dto, **extra, id=str(self.harness.sequence), kind=kind,
                   institution=self.contexto.institucion)
        if parent is not None:
            row["parent"] = parent
        self.harness.data[row["id"]] = row
        return self._output(row)

    @contextmanager
    def _transaction(self):
        with self.harness.lock:
            before = deepcopy(self.harness.data)
            try:
                if self.gate:
                    entered, release = self.gate
                    self.gate = None
                    entered.set()
                    if not release.wait(5):
                        raise AssertionError("Transaction test gate timed out")
                yield
                if self.failure:
                    self.failure = False
                    raise PersistenciaNoDisponible()
            except BaseException:
                self.harness.data = before
                raise

    def registrar_paciente(self, paciente):
        with self._transaction():
            if any(r["kind"] == "paciente" and r["institution"] == self.contexto.institucion
                   and r["identificacion"] == paciente["identificacion"] for r in self.harness.data.values()):
                raise Conflicto()
            return self._insert("paciente", paciente, estado="activo", motivo_archivo=None, fecha_archivo=None)

    def _page(self, rows, q, limit, offset, fields, order):
        q = normalizar_busqueda(q)
        rows = [r for r in rows if any(normalizar_busqueda(r[f]).startswith(q) for f in fields)]
        rows.sort(key=order)
        return {"count": len(rows), "limit": limit, "offset": offset, "results": deepcopy(rows[offset:offset+limit])}

    def listar_pacientes(self, *, q="", limit=20, offset=0):
        with self.harness.lock:
            rows = [self._output(r) for r in self.harness.data.values()
                    if r["kind"] == "paciente" and r["institution"] == self.contexto.institucion]
            return self._page(rows, q, limit, offset, ("identificacion", "nombres", "apellidos"),
                              lambda r: (r["identificacion"], r["id"]))

    def obtener_historial(self, paciente_id):
        with self.harness.lock:
            root = self._find(paciente_id)
            if root["kind"] != "paciente":
                raise RecursoNoEncontrado()

            def children(parent, kind, child_kind=None, child_field=None):
                rows = [self._output(r) for r in self.harness.data.values()
                        if r.get("parent") == parent and r["kind"] == kind]
                rows.sort(key=(lambda r: (r["fecha"], r["id"])) if kind == "consulta" else lambda r: r["id"])
                for row in rows:
                    if child_kind:
                        row[child_field] = children(row["id"], child_kind,
                            {"diagnostico": "tratamiento", "tratamiento": "receta"}.get(child_kind),
                            {"diagnostico": "tratamientos", "tratamiento": "recetas"}.get(child_kind))
                return rows

            return {"paciente": self._output(root),
                    "consultas": children(paciente_id, "consulta", "diagnostico", "diagnosticos")}

    def _write_child(self, parent_id, dto, parent_kind, kind, parent_field, **extra):
        with self._transaction():
            parent = self._find(parent_id)
            if parent["kind"] != parent_kind:
                raise RecursoNoEncontrado()
            if self._root(parent_id)["estado"] != "activo":
                raise Conflicto()
            if kind == "receta" and dto["medicamento_id"] != self.medicine_id:
                raise RecursoNoEncontrado()
            if kind == "consulta" and dto.get("cita_id"):
                raise RecursoNoEncontrado()
            return self._insert(kind, dto, parent_id, **{parent_field: parent_id}, **extra)

    def registrar_consulta(self, paciente_id, consulta):
        return self._write_child(paciente_id, {"cita_id": None, **consulta}, "paciente", "consulta", "paciente_id")

    def registrar_diagnostico(self, consulta_id, diagnostico):
        return self._write_child(consulta_id, diagnostico, "consulta", "diagnostico", "consulta_id")

    def registrar_tratamiento(self, diagnostico_id, tratamiento):
        return self._write_child(diagnostico_id, tratamiento, "diagnostico", "tratamiento", "diagnostico_id")

    def registrar_receta(self, tratamiento_id, receta):
        return self._write_child(tratamiento_id, {"via_administracion": None, **receta}, "tratamiento", "receta", "tratamiento_id")

    def archivar_paciente(self, paciente_id, motivo):
        with self._transaction():
            row = self._find(paciente_id)
            if row["kind"] != "paciente":
                raise RecursoNoEncontrado()
            if row["estado"] == "archivado":
                if row["motivo_archivo"] != motivo:
                    raise Conflicto()
            else:
                row.update(estado="archivado", motivo_archivo=motivo, fecha_archivo=date(2026, 1, 2).isoformat())
            return self._output(row)

    def listar_medicamentos(self, *, q="", limit=20, offset=0):
        return self._page([{"id": self.medicine_id, "nombre": "DEMO no administrar", "presentacion": None}],
                          q, limit, offset, ("nombre",), lambda r: (normalizar_busqueda(r["nombre"]), r["id"]))
