#!/bin/bash
# Real pg_dump/pg_restore rehearsal. Only creates/drops explicitly isolated test DBs.
set -euo pipefail
umask 077
if [ "$PGDATABASE" != test_b3_hospital ]; then echo 'Requiere test_b3_hospital' >&2; exit 1; fi
suffix="$$_$(cat /proc/sys/kernel/random/uuid | cut -c1-8)"
source_db="test_b3_restore_src_$suffix"
restore_db="test_b3_restore_dst_$suffix"
source_created=0
restore_created=0
case "$source_db:$restore_db" in test_b3_restore_src_[0-9]*:test_b3_restore_dst_[0-9]*) ;; *) exit 1;; esac
cleanup() {
  if [ "$source_created" = 1 ]; then dropdb --if-exists "$source_db"; fi
  if [ "$restore_created" = 1 ]; then dropdb --if-exists "$restore_db"; fi
}
trap cleanup EXIT
createdb "$source_db"
source_created=1
createdb "$restore_db"
restore_created=1
export PGDATABASE="$source_db"
psql --set=ON_ERROR_STOP=1 --file=/legacy.sql > /dev/null
psql --set=ON_ERROR_STOP=1 <<'SQL' > /dev/null
INSERT INTO especialidad VALUES(1,'DEMO',1);
INSERT INTO medico(id_medico,id_especialidad,nombre_completo,colegiado) VALUES(1,1,'DEMO','DEMO-1');
INSERT INTO paciente(dpi_cui,nombres,apellidos,fecha_nacimiento) VALUES('DEMO-RESTORE','Paciente','DEMO','2000-01-01');
INSERT INTO cita(id_paciente,id_medico,fecha_hora,estado) VALUES(1,1,'2020-01-01 10:00:00','atendida');
INSERT INTO consulta(id_paciente,id_medico,id_cita,notas_evolucion) VALUES(1,1,1,'DEMO preservado');
SQL
export HOSPITAL_BACKUP_ROOT="/backups/rehearsal-$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir "$HOSPITAL_BACKUP_ROOT"
bash /schema/migrate.sh expand
if bash /schema/migrate.sh finalize > "$HOSPITAL_BACKUP_ROOT/finalize-pendiente.txt" 2>&1; then
  echo 'FALLO: finalizacion acepto fecha desconocida' >&2; exit 1
fi
psql --set=ON_ERROR_STOP=1 -c "UPDATE consulta SET fecha=DATE '2020-01-02' WHERE id_consulta=1" > /dev/null
bash /schema/migrate.sh finalize
dump_file=$(find "$HOSPITAL_BACKUP_ROOT" -path '*-expand-*' -name hospital.dump)
pg_restore --exit-on-error --dbname="$restore_db" "$dump_file"
export PGDATABASE="$restore_db"
psql --set=ON_ERROR_STOP=1 <<'SQL'
DO $$ BEGIN
  IF (SELECT count(*) FROM consulta WHERE notas_evolucion='DEMO preservado') <> 1
     OR (SELECT count(*) FROM paciente WHERE dpi_cui='DEMO-RESTORE') <> 1 THEN
    RAISE EXCEPTION 'FALLO: datos perdidos al restaurar';
  END IF;
  IF EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='consulta' AND column_name='fecha') THEN
    RAISE EXCEPTION 'FALLO: el backup no corresponde al esquema previo';
  END IF;
  RAISE NOTICE 'OK: backup restaurado en otra base; datos y esquema previos recuperados';
END $$;
SQL
