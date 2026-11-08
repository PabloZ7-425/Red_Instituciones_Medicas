import argparse
import json
import os
import secrets
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import django

from hospital_postgresql import configurar as configurar_hospital
from laboratorio_mongodb import configurar as configurar_laboratorio
from odontologia_firestore import configurar as configurar_odontologia
from pediatria_mysql import configurar as configurar_pediatria

INSTITUCIONES = {
    "hospital": ("H", configurar_hospital),
    "pediatrico": ("P", configurar_pediatria),
    "laboratorio": ("L", configurar_laboratorio),
    "odontologica": ("O", configurar_odontologia),
}
GUATEMALA = ZoneInfo("America/Guatemala")


def utc(dia, hora):
    return datetime.combine(dia, time(hora), GUATEMALA).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class Carga:
    utc = staticmethod(utc)

    def __init__(self, institucion, codigo, fecha):
        self.institucion = institucion
        self.codigo = codigo
        self.fecha = fecha
        self.anterior = fecha - timedelta(days=7)
        self.altas = 0
        self.paso = "configuración"
        self.conectar()

    def conectar(self, profesional=None):
        from apps.historiales.domain.context import ContextoClinico
        from apps.operaciones.repository import OperationsRepository

        self.repo = OperationsRepository(ContextoClinico(self.institucion, "carga-institucional", "admin", profesional))
        self.clinica = self.repo.core

    def registros(self, recurso, paciente=None):
        offset = 0
        while True:
            pagina = self.repo.page(recurso, patient=paciente, limit=100, offset=offset)
            yield from pagina["results"]
            offset += len(pagina["results"])
            if not pagina["results"] or offset >= pagina["count"]:
                return

    def uno(self, recurso, registros, coincide, crear):
        self.paso = recurso
        existentes = [fila for fila in registros if coincide(fila)]
        if len(existentes) > 1:
            raise RuntimeError(f"Hay más de un registro para el identificador de la carga en {recurso}")
        if existentes:
            return existentes[0]
        fila = crear()
        self.altas += 1
        return fila

    def guardar(self, recurso, claves, paciente=None, **datos):
        return self.uno(recurso, self.registros(recurso, paciente),
                        lambda fila: all(fila["values"].get(clave) == datos[clave] for clave in claves),
                        lambda: self.repo.save(recurso, datos))

    def id(self, recurso, claves, paciente=None, **datos):
        return self.guardar(recurso, claves, paciente, **datos)["id"]

    def estado(self, recurso, fila, estado, **campos):
        if fila["values"]["estado"].lower() == estado.lower():
            return fila
        self.paso = recurso
        return self.repo.save(recurso, {"estado": estado, **campos}, identifier=fila["id"], version=fila["version"])

    def personal(self, especialidad, nombres, apellidos):
        colegiado = f"RIM-{self.codigo}-M01"
        if self.codigo == "H":
            area = self.id("especialidad", ("nombre",), nombre=especialidad, nivel_complejidad=1)
            recurso = "medico"
            datos = dict(nombre_completo=f"{nombres} {apellidos}", id_especialidad=area, colegiado=colegiado, habilitado=True)
        elif self.codigo == "P":
            area = self.id("especialidad", ("nombre",), nombre=especialidad)
            recurso = "medico"
            datos = dict(nombre=nombres, apellido=apellidos, especialidad_id=area, colegiado=colegiado, estado="activo")
        else:
            recurso = "profesional"
            datos = dict(nombre=f"{nombres} {apellidos}", colegiado=colegiado, habilitado=True, activo=True)
        fila = self.guardar(recurso, ("colegiado",), **datos)
        if any(fila["values"].get(k) is False for k in ("activo", "habilitado")) or fila["values"].get("estado") == "inactivo":
            raise RuntimeError("El profesional de la carga está deshabilitado")
        self.profesional = str(self.repo.internal(recurso, fila["id"]))
        self.conectar(self.profesional)
        return fila["id"]

    def medicamento(self, nombre):
        if self.codigo == "H":
            return self.id("medicamento", ("nombre_comercial",), nombre_comercial=nombre, principio_activo="Simulado",
                           presentacion="Caja", stock_farmacia=50)
        if self.codigo == "P":
            return self.id("medicamento", ("nombre",), nombre=nombre, presentacion="Frasco", estado="activo")
        return self.id("medicamento", ("nombre",), nombre=nombre, presentacion="Caja", activo=True)

    def paciente(self, numero, nombres, apellidos, nacimiento):
        self.paso = "paciente"
        identificacion = f"RIM-{self.codigo}-{numero:03}"
        datos = dict(identificacion=identificacion, nombres=nombres, apellidos=apellidos, fecha_nacimiento=nacimiento)
        existentes = self.clinica.listar_pacientes(q=identificacion, limit=100)["results"]
        fila = self.uno("paciente", existentes, lambda item: item["identificacion"] == identificacion,
                        lambda: self.clinica.registrar_paciente(datos))
        if any(fila.get(clave) != valor for clave, valor in datos.items()):
            raise RuntimeError(f"El expediente {identificacion} pertenece a otros datos")
        return fila["id"]

    def cita(self, paciente, profesional, dia, hora, motivo, estado="programada"):
        if self.codigo == "H":
            datos = dict(id_paciente=paciente, id_medico=profesional, fecha_hora=utc(dia, hora))
        elif self.codigo == "P":
            datos = dict(paciente_id=paciente, medico_id=profesional, fecha=dia.isoformat(), hora=f"{hora:02}:00:00")
        else:
            datos = dict(paciente_id=paciente, profesional_id=profesional, fecha_hora=utc(dia, hora))
        return self.id("cita", tuple(datos), paciente, **datos, estado=estado, **({"motivo": motivo} if self.codigo != "H" else {}))

    def atencion(self, paciente, cita, medicamento, nota, indicacion):
        historial = self.clinica.obtener_historial(paciente)
        consulta = self.uno("consulta", historial["consultas"], lambda item: item.get("cita_id") == cita,
                            lambda: self.clinica.registrar_consulta(paciente, dict(fecha=self.anterior.isoformat(), notas_evolucion=nota, cita_id=cita)))
        diagnostico = self.uno("diagnostico", consulta.get("diagnosticos", []), lambda item: item["descripcion"] == "Control de seguimiento",
                               lambda: self.clinica.registrar_diagnostico(consulta["id"], dict(codigo_cie10="Z09", descripcion="Control de seguimiento")))
        tratamiento = self.uno("tratamiento", diagnostico.get("tratamientos", []), lambda item: item["indicaciones_generales"] == indicacion,
                               lambda: self.clinica.registrar_tratamiento(diagnostico["id"], dict(indicaciones_generales=indicacion)))
        receta = self.uno("receta", tratamiento.get("recetas", []), lambda item: item["medicamento_id"] == medicamento,
                          lambda: self.clinica.registrar_receta(tratamiento["id"], dict(medicamento_id=medicamento, dosis="Simulada", frecuencia="Según ficha de demostración")))
        return consulta["id"], tratamiento["id"], receta["id"]

    def jornada(self, profesional, pacientes, medicamento, motivo, nota, indicacion):
        primera, segunda, tercera, cuarta = [self.paciente(indice, *persona) for indice, persona in enumerate(pacientes, 1)]
        anterior = self.cita(primera, profesional, self.anterior, 10, motivo)
        self.cita(segunda, profesional, self.fecha, 9, motivo)
        self.cita(tercera, profesional, self.fecha + timedelta(days=2), 11, motivo)
        self.cita(cuarta, profesional, self.fecha, 14, motivo, "cancelada")
        return (primera, segunda, tercera, cuarta), self.atencion(primera, anterior, medicamento, nota, indicacion)

    def factura(self, paciente, consulta, servicio=None, metodo=None, poliza=None, autorizacion=None):
        hospital = self.codigo == "H"
        referencias = dict(id_paciente=paciente, id_consulta=consulta) if hospital else dict(paciente_id=paciente, consulta_id=consulta)
        factura = self.id("factura", tuple(referencias), paciente, **referencias, impuestos="0.00")
        if hospital:
            self.id("detalle_factura", ("id_factura", "concepto"), paciente, id_factura=factura, concepto="Atención ambulatoria",
                    cantidad=1, precio_unitario="150.00")
        else:
            self.id("detalle_factura", ("factura_id", "servicio_id"), paciente, factura_id=factura, servicio_id=servicio,
                    cantidad=1, precio_unitario="150.00", monto_cubierto="60.00")
        fila = next(item for item in self.registros("factura", paciente) if item["id"] == factura)
        if fila["values"]["estado"].lower() == "borrador":
            self.paso = "emitir factura"
            self.repo.financial_action("factura", factura, "emitir", fila["version"])
        if hospital:
            self.id("pago", ("id_factura", "monto"), paciente, id_factura=factura, monto="65.00", metodo_pago="Efectivo")
        else:
            self.id("reclamacion_seguro", ("numero_reclamo",), paciente, factura_id=factura, poliza_paciente_id=poliza,
                    autorizacion_id=autorizacion, numero_reclamo="RIM-P-RECLAMO", monto_reclamado="60.00", estado="pendiente")
            self.id("pago", ("factura_id", "monto", "tipo_pagador"), paciente, factura_id=factura, metodo_pago_id=metodo,
                    monto="45.00", tipo_pagador="paciente")


def acceso(path):
    from django.contrib.auth import get_user_model

    if path.is_symlink():
        raise RuntimeError("La ruta de accesos es un enlace")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    cuentas = {nombre: {"username": f"admin.{nombre}", "password": secrets.token_urlsafe(24)} for nombre in INSTITUCIONES}
    if get_user_model().objects.filter(username__in=[cuenta["username"] for cuenta in cuentas.values()]).exists():
        raise RuntimeError("Ya existen cuentas de esta carga. Recupera su archivo privado de accesos")
    datos = {"fecha": datetime.now(GUATEMALA).date().isoformat(), "cuentas": cuentas}
    with open(path, "x", encoding="utf-8", opener=lambda filename, flags: os.open(filename, flags, 0o600)) as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)
    return datos


def guardar_cuenta(carga, cuenta):
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from apps.identidad.models import PerfilInstitucional, Profesional

    with transaction.atomic():
        profesional, _ = Profesional.objects.get_or_create(institucion=carga.institucion,
            referencia_externa=carga.profesional, defaults={"habilitado": True})
        if not profesional.habilitado:
            raise RuntimeError("El vínculo profesional está deshabilitado")
        usuarios = get_user_model().objects
        usuario = usuarios.filter(username=cuenta["username"]).first()
        if usuario is None:
            usuario = usuarios.create_user(**cuenta)
            PerfilInstitucional.objects.create(usuario=usuario, institucion=carga.institucion, rol="admin", profesional=profesional)
        else:
            perfil = PerfilInstitucional.objects.get(usuario=usuario)
            if not (usuario.is_active and not usuario.is_superuser and not usuario.is_staff and usuario.check_password(cuenta["password"])
                    and perfil.activo and perfil.institucion == carga.institucion and perfil.rol == "admin" and perfil.profesional_id == profesional.pk):
                raise RuntimeError("La cuenta existente no coincide con los accesos de la carga")


def main():
    parser = argparse.ArgumentParser(description="Carga institucional en las bases locales de Docker")
    parser.add_argument("--accesos", required=True, type=Path)
    args = parser.parse_args()
    if (os.getenv("POSTGRES_HOST"), os.getenv("MYSQL_HOST"), urlsplit(os.getenv("MONGO_URI", "")).hostname,
            os.getenv("FIRESTORE_MODE"), os.getenv("FIRESTORE_EMULATOR_HOST")) != ("postgres", "mysql", "mongo", "emulator", "firestore:8080"):
        raise SystemExit("La carga requiere las cuatro bases locales de Docker Compose")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    datos = acceso(args.accesos)
    fecha = datetime.fromisoformat(datos["fecha"]).date()
    for institucion, (codigo, configurar) in INSTITUCIONES.items():
        carga = Carga(institucion, codigo, fecha)
        try:
            configurar(carga)
            carga.paso = "cuenta institucional"
            guardar_cuenta(carga, datos["cuentas"][institucion])
            recursos = {nombre: carga.repo.page(nombre, limit=1)["count"] for nombre in carga.repo.specs}
        except Exception as error:
            print(f"{institucion}: error en {carga.paso} ({type(error).__name__}). {getattr(error, 'fields', {})}", flush=True)
            raise SystemExit(1) from None
        print(f"{institucion}: {carga.altas} altas, {sum(bool(valor) for valor in recursos.values())}/{len(recursos)} tipos con datos", flush=True)


if __name__ == "__main__":
    main()
