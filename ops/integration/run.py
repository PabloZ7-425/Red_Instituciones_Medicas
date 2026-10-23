"""Reproduce A/B on dedicated Docker services; never writes shared databases."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from unittest.mock import patch

REPO = Path("/workspace")
ROOT = REPO / "work/a5-runtime"
JAR = "/opt/firestore.jar"


def run(*args, env=None, cwd=None):
    subprocess.run(args, check=True, env=env, cwd=cwd or REPO)


def wait_port(port):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError(f"Dedicated port {port} not ready")


def replica(port, name, host="127.0.0.1"):
    from pymongo import MongoClient
    from pymongo.errors import OperationFailure
    wait_port(port)
    with MongoClient(f"mongodb://127.0.0.1:{port}/?directConnection=true", serverSelectionTimeoutMS=3000) as client:
        try:
            config = client.admin.command("replSetGetConfig")["config"]
            if config["_id"] != name or config["members"][0]["host"] != f"{host}:{port}":
                raise RuntimeError("Unexpected dedicated replica set")
        except OperationFailure as error:
            if error.code != 94:
                raise
            client.admin.command({"replSetInitiate": {"_id": name, "members": [{"_id": 0, "host": f"{host}:{port}"}]}})
        for _ in range(100):
            if client.admin.command("hello").get("isWritablePrimary"):
                return
            time.sleep(0.2)
    raise RuntimeError("Dedicated replica did not become PRIMARY")


def server(args, name, env=None, cwd=None):
    handle = (ROOT / (name + ".log")).open("w")
    process = subprocess.Popen(args, stdout=handle, stderr=subprocess.STDOUT, env=env, cwd=cwd or REPO)
    return process, handle


def configure():
    run(sys.executable, "docs/jennifer/a5/configure.py", "--runtime", str(ROOT), "--pablo-ref", "HEAD", "--jennifer-ref", "HEAD")
    path = ROOT / "private.json"
    passwords = json.loads(path.read_text())
    passwords.update(postgres=os.environ["PABLO_TEST_POSTGRES_PASSWORD"], mysql=os.environ["PABLO_TEST_MYSQL_PASSWORD"])
    path.write_text(json.dumps(passwords))
    path.chmod(0o600)
    print("Dedicated sources configured; no credentials printed", flush=True)


def validate():
    for port in (15435, 3306):
        wait_port(port)
    replica(27039, "a5")
    replica(27038, "a3")
    replica(27017, "rs0", "mongo")
    processes = []
    try:
        processes.append(server(["java", "-jar", JAR, "--host=127.0.0.1", "--port=8093", "--project_id=demo-jennifer-a5"], "firestore"))
        wait_port(8093)
        run(sys.executable, "docs/jennifer/a5/prepare.py", "--runtime", str(ROOT))
        config = json.loads((ROOT / "server.json").read_text())
        pw = json.loads((ROOT / "private.json").read_text())
        env = os.environ | config
        env["PYTHONPATH"] = str(ROOT) + ":" + str(ROOT / "backend")
        run(sys.executable, "docs/jennifer/a5/check_startup.py", "--runtime", str(ROOT), env=env)
        # Separate test databases; migrator/runtime receive no CREATEDB capability.
        import psycopg
        from psycopg import sql
        with psycopg.connect(host="127.0.0.1", port=15435, dbname="postgres", user="postgres", password=pw["postgres"], autocommit=True) as conn:
            for name, owner in (("test_b3_hospital", "postgres"), ("test_b2_identidad", "identidad_migrator")):
                conn.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(name), sql.Identifier(owner)))
        env.update(TEST_HOSPITAL_POSTGRES="1", TEST_PEDIATRIA_MYSQL="1", TEST_IDENTITY_POSTGRES="1",
                   TEST_MONGO_REPLICA="1", MONGO_INFRA_TEST_DB="test_b5_infra",
                   HOSPITAL_TEST_DB="test_b3_hospital", HOSPITAL_SCHEMA_DIR=str(ROOT / "db/postgres"),
                   PEDIATRIA_TEST_DB="test_b4_pediatria", PEDIATRIA_SCHEMA_DIR=str(ROOT / "db/mysql"),
                   PG_USER="postgres", PG_PASSWORD=pw["postgres"], MYSQL_ROOT_PASSWORD=pw["mysql"],
                   IDENTITY_MIGRATOR_PASSWORD=pw["identity_migrator"],
                   A3_NOSQL_TESTS="1", A3_MONGO_TEST_URI="mongodb://127.0.0.1:27038/?replicaSet=a3",
                   A3_MONGO_SCHEMA=str(ROOT / "db/mongo/clinical_schema.py"),
                   MONGO_URI="mongodb://mongo:27017/laboratorio?replicaSet=rs0")
        labels = ["apps.historiales." + path.stem for path in sorted((ROOT / "backend/apps/historiales").glob("test*.py"))
                  if path.stem != "test_recovery_nosql"] + ["apps.identidad"]
        run(sys.executable, str(ROOT / "backend/manage.py"), "test", *labels, "--settings=config.test_settings", "--keepdb", "-v", "1", env=env)
        run(sys.executable, str(ROOT / "backend/manage.py"), "audit_clinical_providers", "--require-all", env=os.environ | config | {"PYTHONPATH": env["PYTHONPATH"]})
        run("npm", "install", "--package-lock=false", cwd=ROOT / "frontend")
        test_files = [str(path) for path in sorted((ROOT / "frontend/tests").glob("*.test.js"))]
        run("node", "--test", *test_files, cwd=ROOT)
        build_env = os.environ | {"VITE_API_URL": "http://127.0.0.1:18005/api", "VITE_CLINICAL_MODE": "mock"}
        run("npm", "run", "build", cwd=ROOT / "frontend", env=build_env)
        processes.append(server([sys.executable, str(REPO / "docs/jennifer/a5/serve.py"), "--runtime", str(ROOT)], "backend"))
        processes.append(server(["npm", "run", "preview", "--", "--host", "127.0.0.1", "--port", "18173"], "frontend", cwd=ROOT / "frontend"))
        wait_port(18005)
        wait_port(18173)
        wire = os.environ | {"A5_RUNTIME": str(ROOT), "A5_REAL_HTTP": "1", "A5_BROWSER_PASSWORD": "DEMO-only-isolated-A5-2026", "BROWSER_URL": "http://127.0.0.1:18173/"}
        for role in ("admin", "secretaria", "enfermero", "laboratorista"):
            role_env = wire | ({"A4_HTTP_BROWSER_ROLE": role} if role != "admin" else {})
            run("node", "tests/browser-real.mjs", env=role_env, cwd=ROOT / "frontend")
        for script in ("test_http.py", "test_specialties.py"):
            run(sys.executable, str(REPO / "docs/jennifer/a5" / script), env=wire)
        print("VALIDATION COMPLETE: native contracts, SQL, HTTP, four-engine browser and role flows", flush=True)
    finally:
        for process, handle in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            handle.close()


def recovery():
    """Run A's cold recovery suite with only its explicitly guarded services."""
    replica(27039, "recovery")
    replica(27049, "recoveryTarget")
    directory = REPO / "work/recovery"
    directory.mkdir(exist_ok=True)
    bins = REPO / "work/bin"
    bins.mkdir(exist_ok=True)
    for name in ("mongodump", "mongorestore"):
        run("docker", "cp", "jennifer-recovery-mongo:/usr/bin/" + name, str(bins / name))
        (bins / name).chmod(0o700)
    process, handle = server(["java", "-jar", JAR, "--host=127.0.0.1", "--port=8093", "--project_id=demo-clinical-recovery"], "firestore-recovery")
    try:
        wait_port(8093)
        import specialty_recovery
        extra = directory / "specialty"
        extra.mkdir()
        with patch.dict(os.environ, {"FIRESTORE_EMULATOR_HOST": "127.0.0.1:8093"}):
            prepared = specialty_recovery.prepare(ROOT, bins, extra)
        env = os.environ | {"PYTHONPATH": str(ROOT / "backend"), "RECOVERY_NOSQL_TESTS": "1",
                            "FIRESTORE_RECOVERY_SOURCE_PID": str(process.pid), "FIRESTORE_RECOVERY_JAR": JAR,
                            "MONGO_DUMP_BIN": str(bins / "mongodump"), "MONGO_RESTORE_BIN": str(bins / "mongorestore")}
        run(sys.executable, "-m", "unittest", "apps.historiales.test_recovery_nosql", "-v", env=env)
        specialty_recovery.verify(ROOT, bins, extra, prepared, server)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=15)
        handle.close()


def resume_recovery():
    # Source servers remain stopped. Restore only the verified native artifacts
    # into a new UUID database and a new JVM; never restart/seed the source.
    import sys
    from uuid import uuid4
    import specialty_recovery
    sys.path.insert(0, str(ROOT / "backend"))
    state = json.loads(subprocess.check_output(["docker", "inspect", "jennifer-recovery-mongo"]))[0]
    if state["State"]["Running"]:
        raise RuntimeError("Cold resume requires the source to remain stopped")
    try:
        with socket.create_connection(("127.0.0.1", 8093), timeout=0.3):
            raise RuntimeError("Cold resume requires the source JVM to remain stopped")
    except OSError:
        pass
    extra = REPO / "work/recovery/specialty"
    prepared = (
        specialty_recovery.module("resume_mongo", ROOT / "db/mongo/clinical_recovery.py"),
        specialty_recovery.module("resume_firestore", ROOT / "db/firebase/clinical_recovery.py"),
        f"mongodb://127.0.0.1:27049/specialty_recovery_{uuid4().hex}?replicaSet=recoveryTarget",
        "demo-specialty-recovery", None,
    )
    specialty_recovery.verify(ROOT, REPO / "work/bin", extra, prepared, server)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("configure", "validate", "recovery", "recovery-resume"))
    args = parser.parse_args()
    {"configure": configure, "validate": validate, "recovery": recovery, "recovery-resume": resume_recovery}[args.phase]()
