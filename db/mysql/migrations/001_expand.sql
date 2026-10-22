-- Restartable expansion. Every ALTER commits independently in MySQL.
DROP PROCEDURE IF EXISTS b4_expand;
DELIMITER //
CREATE PROCEDURE b4_expand()
BEGIN
  ALTER TABLE consulta MODIFY cita_id INT NULL;
  ALTER TABLE tratamiento MODIFY nombre VARCHAR(100) NULL;
  ALTER TABLE paciente MODIFY identificacion VARCHAR(100) COLLATE utf8mb4_0900_bin NOT NULL;
  IF NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='tratamiento' AND column_name='consulta_diagnostico_id') THEN
    ALTER TABLE tratamiento ADD consulta_diagnostico_id INT NULL;
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='receta' AND column_name='tratamiento_id') THEN
    ALTER TABLE receta ADD tratamiento_id INT NULL;
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='paciente_tutor' AND column_name='parentesco') THEN
    ALTER TABLE paciente_tutor ADD parentesco VARCHAR(100) NULL;
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='aplicacion_vacuna' AND column_name='medico_id') THEN
    ALTER TABLE aplicacion_vacuna ADD medico_id INT NULL;
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='control_de_crecimiento' AND column_name='peso_kg') THEN
    ALTER TABLE control_de_crecimiento ADD peso_kg DECIMAL(6,2) NULL;
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='control_de_crecimiento' AND column_name='talla_cm') THEN
    ALTER TABLE control_de_crecimiento ADD talla_cm DECIMAL(6,2) NULL;
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='control_de_crecimiento' AND column_name='medico_id') THEN
    ALTER TABLE control_de_crecimiento ADD medico_id INT NULL;
  END IF;
  CREATE TABLE IF NOT EXISTS pediatria_conciliacion (
    tipo VARCHAR(20) NOT NULL, id INT NOT NULL, origen_id INT NOT NULL,
    evidencia VARCHAR(500) NOT NULL, PRIMARY KEY(tipo,id),
    CHECK(tipo IN ('tratamiento','receta')), CHECK(CHAR_LENGTH(TRIM(evidencia))>0)
  ) ENGINE=InnoDB;
  CREATE TABLE IF NOT EXISTS pediatria_schema_version(version INT PRIMARY KEY);
END//
DELIMITER ;
CALL b4_expand();
DROP PROCEDURE b4_expand;
