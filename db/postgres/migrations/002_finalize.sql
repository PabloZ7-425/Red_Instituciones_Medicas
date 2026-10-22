-- Run in a transaction, only after inventory/backup and documented reconciliation.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM consulta WHERE fecha IS NULL) THEN
    RAISE EXCEPTION 'B3: consultas con fecha civil pendiente de conciliacion';
  END IF;
  IF EXISTS (SELECT 1 FROM ingreso_hospitalario WHERE ingreso_utc IS NULL
             OR (fecha_hora_alta IS NULL) <> (alta_utc IS NULL)) THEN
    RAISE EXCEPTION 'B3: timestamps de ingresos pendientes de conciliacion explicita';
  END IF;
END $$;
ALTER TABLE consulta ALTER COLUMN fecha SET NOT NULL;
ALTER TABLE ingreso_hospitalario ALTER COLUMN ingreso_utc SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS cita_parentesco_unico ON cita(id_cita,id_paciente,id_medico);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='consulta'::regclass AND conname='fk_consulta_cita_contexto') THEN
    ALTER TABLE consulta ADD CONSTRAINT fk_consulta_cita_contexto FOREIGN KEY(id_cita,id_paciente,id_medico)
      REFERENCES cita(id_cita,id_paciente,id_medico);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='paciente'::regclass AND conname='paciente_archivo_coherente') THEN
    ALTER TABLE paciente ADD CONSTRAINT paciente_archivo_coherente CHECK (estado <> 'archivado' OR
      (motivo_baja IS NOT NULL AND length(btrim(motivo_baja)) BETWEEN 1 AND 200 AND fecha_baja IS NOT NULL));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='consulta'::regclass AND conname='consulta_notas_requeridas') THEN
    ALTER TABLE consulta ADD CONSTRAINT consulta_notas_requeridas CHECK (notas_evolucion IS NOT NULL AND length(btrim(notas_evolucion)) BETWEEN 1 AND 5000);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='diagnostico'::regclass AND conname='diagnostico_consulta_textos') THEN
    ALTER TABLE diagnostico ADD CONSTRAINT diagnostico_consulta_textos CHECK
      (id_consulta IS NULL OR (codigo_cie10 IS NOT NULL AND length(btrim(codigo_cie10)) BETWEEN 1 AND 20 AND length(btrim(descripcion)) BETWEEN 1 AND 5000));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='tratamiento'::regclass AND conname='tratamiento_indicaciones_requeridas') THEN
    ALTER TABLE tratamiento ADD CONSTRAINT tratamiento_indicaciones_requeridas CHECK (indicaciones_generales IS NOT NULL AND length(btrim(indicaciones_generales)) BETWEEN 1 AND 5000);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='ingreso_hospitalario'::regclass AND conname='ingreso_utc_coherente') THEN
    ALTER TABLE ingreso_hospitalario ADD CONSTRAINT ingreso_utc_coherente CHECK
      ((fecha_hora_alta IS NULL) = (alta_utc IS NULL) AND (alta_utc IS NULL OR alta_utc >= ingreso_utc));
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS ingreso_cama_activa_unica ON ingreso_hospitalario(id_cama) WHERE fecha_hora_alta IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ingreso_paciente_activo_unico ON ingreso_hospitalario(id_paciente) WHERE fecha_hora_alta IS NULL;
CREATE INDEX IF NOT EXISTS idx_diagnostico_consulta ON diagnostico(id_consulta);
CREATE INDEX IF NOT EXISTS idx_tratamiento_diagnostico ON tratamiento(id_diagnostico);
CREATE INDEX IF NOT EXISTS idx_receta_tratamiento ON receta_prescripcion(id_tratamiento);
CREATE TABLE IF NOT EXISTS hospital_schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO hospital_schema_version(version) VALUES ('B3-1.0.0') ON CONFLICT DO NOTHING;
