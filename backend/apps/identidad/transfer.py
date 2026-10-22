"""Explicit, transactional transfer of Django identities, never clinical data/sessions."""
import hashlib
import json
import os
import sqlite3
from itertools import chain
from pathlib import Path

from django.contrib.auth.hashers import identify_hasher, is_password_usable
from django.contrib.auth.models import Group, User
from django.core import serializers
from django.core.management import call_command, CommandError
from django.db import connections, transaction


def identity_payload(alias):
    users = User.objects.using(alias).order_by("pk")
    for password in users.values_list("password", flat=True):
        if is_password_usable(password):
            try:
                identify_hasher(password)
            except ValueError:
                raise CommandError("Hash no reconocido; se requiere conciliación antes del traslado") from None
    objects = chain(Group.objects.using(alias).order_by("pk"), users)
    return serializers.serialize("json", objects, use_natural_foreign_keys=True)


def fingerprint(payload):
    # Compare complete records, permissions, group relations and password hashes.
    records = json.loads(payload)
    for record in records:
        for field in ("groups", "user_permissions", "permissions"):
            if field in record["fields"]:
                record["fields"][field] = sorted(record["fields"][field], key=str)
    normalized = json.dumps(records, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(normalized.encode()).hexdigest()


def transfer(source, target, backup_dir):
    src, dst = connections[source], connections[target]
    if source == target or (
        src.settings_dict["ENGINE"], str(src.settings_dict["NAME"]), src.settings_dict.get("HOST")
    ) == (
        dst.settings_dict["ENGINE"], str(dst.settings_dict["NAME"]), dst.settings_dict.get("HOST")
    ):
        raise CommandError("Origen y destino deben ser distintos")
    if dst.vendor != "postgresql":
        raise CommandError("El destino técnico debe ser PostgreSQL")
    if src.vendor != "sqlite":
        raise CommandError("Este traslado requiere origen SQLite heredado")
    if User.objects.using(target).exists() or Group.objects.using(target).exists():
        raise CommandError("El destino debe estar vacío; no se sobrescriben cuentas")
    directory = Path(backup_dir).resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup = directory / "legacy.sqlite3"
    fixture = directory / "identidad.json"
    if backup.exists() or fixture.exists():
        raise CommandError("Use un directorio de respaldo nuevo; no se sobrescriben respaldos")
    # SQLite backup is consistent, even when the source has WAL pages.
    src.ensure_connection()
    reservation = os.open(backup, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(reservation)
    with sqlite3.connect(str(backup)) as destination:
        src.connection.backup(destination)
    # Export from the backup, not a live source which could change between reads.
    snapshot_settings = {
        **src.settings_dict, "NAME": f"file:{backup.as_posix()}?mode=ro", "OPTIONS": {"uri": True},
    }
    # ConnectionHandler is thread-local. Reuse the explicit source alias only in
    # this maintenance thread, then restore its original connection unconditionally.
    snapshot = type(src)(snapshot_settings, alias=source)
    connections[source] = snapshot
    try:
        # Inspect the immutable snapshot, so new B2 profiles cannot disappear
        # between the schema check and export. Extended transfers need a new plan.
        if "identidad_perfilinstitucional" in snapshot.introspection.table_names():
            with snapshot.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM identidad_perfilinstitucional")
                if cursor.fetchone()[0]:
                    raise CommandError("El origen contiene perfiles B2; requiere un traslado ampliado")
        payload = identity_payload(source)
    finally:
        snapshot.close()
        connections[source] = src
    descriptor = os.open(fixture, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(payload)
    with transaction.atomic(using=target):
        # Serialize transfers against this explicit destination, without taking any clinical locks.
        with dst.cursor() as cursor:
            cursor.execute("LOCK TABLE auth_user, auth_group IN ACCESS EXCLUSIVE MODE")
        if User.objects.using(target).exists() or Group.objects.using(target).exists():
            raise CommandError("El destino recibió cuentas durante el traslado; se cancela")
        if json.loads(payload):
            call_command("loaddata", str(fixture), database=target, verbosity=0)
        if fingerprint(identity_payload(target)) != fingerprint(payload):
            raise CommandError("La conciliación no coincide; traslado revertido")
        if fingerprint(identity_payload(source)) != fingerprint(payload):
            raise CommandError("El origen cambió durante el traslado; se cancela y revierte el destino")
    return {"users": User.objects.using(target).count(), "groups": Group.objects.using(target).count()}
