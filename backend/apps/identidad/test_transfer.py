import sqlite3
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.hashers import check_password
from django.contrib.sessions.models import Session
from django.core.management import CommandError
from django.db import connection
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from apps.identidad.models import PerfilInstitucional
from apps.identidad.transfer import fingerprint, identity_payload, transfer


@skipUnless(connection.vendor == "postgresql", "Traslado real requiere destino PostgreSQL; ejecutar con TEST_IDENTITY_POSTGRES=1")
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.PBKDF2PasswordHasher"])
class IdentityTransferTests(TransactionTestCase):
    databases = {"default", "legacy_fixture"}

    def setUp(self):
        self.directory = TemporaryDirectory(prefix="rim-b2-transfer-")
        self.addCleanup(self.directory.cleanup)
        self.source = "legacy_fixture"
        self.target = "default"

    def user(self):
        user = User(id=77, username="DEMO-migracion")
        user.set_password("DEMO-solo-ensayo-6912!")
        user.save(using=self.source)
        group = Group.objects.using(self.source).create(name="DEMO-equipo")
        group.permissions.add(Permission.objects.using(self.source).first())
        user.groups.add(group)
        user.user_permissions.add(Permission.objects.using(self.source).last())
        return user

    def test_transfer_preserves_hash_ids_groups_permissions_sequences_and_source(self):
        original = self.user()
        before = identity_payload(self.source)
        counts = transfer(self.source, self.target, self.directory.name)
        self.assertEqual(counts, {"users": 1, "groups": 1})
        moved = User.objects.get(username=original.username)
        self.assertEqual(moved.password, original.password)
        self.assertEqual(moved.pk, original.pk)
        self.assertTrue(moved.check_password("DEMO-solo-ensayo-6912!"))
        self.assertEqual(fingerprint(identity_payload(self.target)), fingerprint(before))
        self.assertEqual(identity_payload(self.source), before)
        self.assertGreater(User.objects.create_user("DEMO-posterior").pk, original.pk)
        # A consistent SQLite rollback copy survives; source was never modified.
        with sqlite3.connect(str(Path(self.directory.name) / "legacy.sqlite3")) as backup:
            self.assertEqual(backup.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            recovered_hash = backup.execute("SELECT password FROM auth_user WHERE id=77").fetchone()[0]
            self.assertEqual(recovered_hash, original.password)
            self.assertTrue(check_password("DEMO-solo-ensayo-6912!", recovered_hash))

    def test_transfer_does_not_copy_sessions_or_automatic_profiles(self):
        self.user()
        Session.objects.using(self.source).create(session_key="D" * 32, session_data="DEMO", expire_date=timezone.now() + timedelta(hours=1))
        transfer(self.source, self.target, self.directory.name)
        self.assertEqual(Session.objects.count(), 0)
        self.assertEqual(PerfilInstitucional.objects.count(), 0)

    def test_unusable_password_is_preserved(self):
        user = self.user()
        user.set_unusable_password()
        user.save(using=self.source)
        transfer(self.source, self.target, self.directory.name)
        target = User.objects.get(pk=77)
        self.assertFalse(target.has_usable_password())
        self.assertEqual(target.password, user.password)

    def test_unknown_hash_stops_before_import(self):
        user = self.user()
        user.password = "not-a-django-hash"
        user.save(using=self.source)
        with self.assertRaises(CommandError):
            transfer(self.source, self.target, self.directory.name)
        self.assertFalse(User.objects.exists())

    def test_nonempty_destination_is_never_overwritten(self):
        self.user()
        existing = User.objects.create_user("DEMO-existente")
        with self.assertRaises(CommandError):
            transfer(self.source, self.target, self.directory.name)
        self.assertEqual(list(User.objects.values_list("pk", flat=True)), [existing.pk])

    def test_failed_import_rolls_back_all_identity_rows(self):
        from django.core.management import call_command
        self.user()
        before = identity_payload(self.source)

        def fail_after_import(*args, **kwargs):
            call_command(*args, **kwargs)
            raise CommandError("DEMO fallo posterior a importación")

        with patch("apps.identidad.transfer.call_command", side_effect=fail_after_import), self.assertRaises(CommandError):
            transfer(self.source, self.target, self.directory.name)
        self.assertFalse(User.objects.exists())
        self.assertFalse(Group.objects.exists())
        self.assertEqual(identity_payload(self.source), before)

    def test_profiles_in_source_require_an_explicit_extended_plan(self):
        user = self.user()
        PerfilInstitucional.objects.using(self.source).create(usuario=user, institucion="hospital", rol="medico")
        with self.assertRaises(CommandError):
            transfer(self.source, self.target, self.directory.name)
        self.assertFalse(User.objects.exists())

    def test_changes_in_live_source_cancel_and_rollback_destination(self):
        from django.core.management import call_command
        self.user()

        def change_source_after_import(*args, **kwargs):
            call_command(*args, **kwargs)
            User.objects.using(self.source).filter(pk=77).update(first_name="DEMO-cambio-concurrente")

        with patch("apps.identidad.transfer.call_command", side_effect=change_source_after_import), self.assertRaises(CommandError):
            transfer(self.source, self.target, self.directory.name)
        self.assertFalse(User.objects.exists())
        self.assertEqual(User.objects.using(self.source).get(pk=77).first_name, "DEMO-cambio-concurrente")

    def test_existing_backup_is_never_overwritten(self):
        self.user()
        backup = Path(self.directory.name) / "legacy.sqlite3"
        backup.write_bytes(b"DEMO-respaldo-previo")
        with self.assertRaises(CommandError):
            transfer(self.source, self.target, self.directory.name)
        self.assertEqual(backup.read_bytes(), b"DEMO-respaldo-previo")
        self.assertFalse(User.objects.exists())
