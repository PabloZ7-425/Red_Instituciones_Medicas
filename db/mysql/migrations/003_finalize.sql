-- ALL preflight runs before the first ALTER. DDL is not transactionally reversible.
DROP PROCEDURE IF EXISTS b4_finalize;
DELIMITER //
CREATE PROCEDURE b4_finalize()
BEGIN
  IF EXISTS(SELECT 1 FROM tratamiento t LEFT JOIN consulta_diagnostico d
            ON d.id=t.consulta_diagnostico_id AND d.consulta_id=t.consulta_id WHERE d.id IS NULL)
     OR EXISTS(SELECT 1 FROM receta r LEFT JOIN tratamiento t
            ON t.id=r.tratamiento_id AND t.consulta_id=r.consulta_id WHERE t.id IS NULL)
     OR EXISTS(SELECT 1 FROM consulta c JOIN cita a ON a.id=c.cita_id
            WHERE c.paciente_id<>a.paciente_id OR c.medico_id<>a.medico_id)
     OR EXISTS(SELECT 1 FROM control_de_crecimiento WHERE
            (peso_kg IS NULL)<>(talla_cm IS NULL) OR peso_kg<=0 OR talla_cm<=0)
     OR EXISTS(SELECT 1 FROM aplicacion_vacuna a LEFT JOIN medico m ON m.id=a.medico_id
            WHERE a.medico_id IS NOT NULL AND m.id IS NULL)
     OR EXISTS(SELECT 1 FROM control_de_crecimiento a LEFT JOIN medico m ON m.id=a.medico_id
            WHERE a.medico_id IS NOT NULL AND m.id IS NULL)
     OR EXISTS(SELECT 1 FROM consulta WHERE observaciones IS NULL OR CHAR_LENGTH(TRIM(observaciones))=0)
     OR EXISTS(SELECT 1 FROM diagnostico WHERE descripcion IS NULL OR CHAR_LENGTH(TRIM(descripcion))=0)
     OR EXISTS(SELECT 1 FROM tratamiento WHERE indicaciones IS NULL OR CHAR_LENGTH(TRIM(indicaciones))=0)
     OR EXISTS(SELECT 1 FROM detalle_receta WHERE dosis IS NULL OR frecuencia IS NULL
            OR CHAR_LENGTH(TRIM(dosis))=0 OR CHAR_LENGTH(TRIM(frecuencia))=0) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Pendientes historicos; cierre bloqueado sin alterar restricciones';
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='cita' AND index_name='uq_cita_origen') THEN
    ALTER TABLE cita ADD CONSTRAINT uq_cita_origen UNIQUE(paciente_id,medico_id,id);
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND constraint_name='fk_consulta_cita_origen') THEN
    ALTER TABLE consulta ADD CONSTRAINT fk_consulta_cita_origen FOREIGN KEY(paciente_id,medico_id,cita_id) REFERENCES cita(paciente_id,medico_id,id);
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='consulta_diagnostico' AND index_name='uq_ocurrencia_consulta') THEN
    ALTER TABLE consulta_diagnostico ADD CONSTRAINT uq_ocurrencia_consulta UNIQUE(consulta_id,id);
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='tratamiento' AND index_name='uq_tratamiento_consulta') THEN
    ALTER TABLE tratamiento ADD CONSTRAINT uq_tratamiento_consulta UNIQUE(consulta_id,id);
  END IF;
  ALTER TABLE tratamiento MODIFY consulta_diagnostico_id INT NOT NULL;
  ALTER TABLE receta MODIFY tratamiento_id INT NOT NULL;
  IF NOT EXISTS(SELECT 1 FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND constraint_name='fk_tratamiento_origen') THEN
    ALTER TABLE tratamiento ADD CONSTRAINT fk_tratamiento_origen FOREIGN KEY(consulta_id,consulta_diagnostico_id) REFERENCES consulta_diagnostico(consulta_id,id);
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND constraint_name='fk_receta_origen') THEN
    ALTER TABLE receta ADD CONSTRAINT fk_receta_origen FOREIGN KEY(consulta_id,tratamiento_id) REFERENCES tratamiento(consulta_id,id);
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND constraint_name='fk_vacuna_profesional') THEN
    ALTER TABLE aplicacion_vacuna ADD CONSTRAINT fk_vacuna_profesional FOREIGN KEY(medico_id) REFERENCES medico(id);
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND constraint_name='fk_crecimiento_profesional') THEN
    ALTER TABLE control_de_crecimiento ADD CONSTRAINT fk_crecimiento_profesional FOREIGN KEY(medico_id) REFERENCES medico(id);
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND constraint_name='ck_crecimiento_unidades') THEN
    ALTER TABLE control_de_crecimiento ADD CONSTRAINT ck_crecimiento_unidades CHECK(
      (peso_kg IS NULL AND talla_cm IS NULL) OR (peso_kg IS NOT NULL AND talla_cm IS NOT NULL AND peso_kg>0 AND talla_cm>0));
  END IF;
  INSERT IGNORE INTO pediatria_schema_version VALUES(1);
END//
DELIMITER ;
CALL b4_finalize();
DROP PROCEDURE b4_finalize;
