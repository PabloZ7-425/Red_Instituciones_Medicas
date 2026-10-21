-- Investigación C0 sobre copia aislada de init.sql. No es una migración.
-- DDL MySQL tiene commit implícito: ejecutar solo en la instancia temporal.
ALTER TABLE consulta MODIFY COLUMN cita_id INT NULL;
ALTER TABLE consulta_diagnostico
    ADD CONSTRAINT uq_consulta_diagnostico UNIQUE (consulta_id, diagnostico_id);
ALTER TABLE tratamiento ADD COLUMN diagnostico_id INT NULL;
ALTER TABLE tratamiento
    ADD CONSTRAINT fk_tratamiento_origen
        FOREIGN KEY (consulta_id, diagnostico_id)
        REFERENCES consulta_diagnostico (consulta_id, diagnostico_id),
    ADD CONSTRAINT uq_tratamiento_consulta UNIQUE (consulta_id, id);
ALTER TABLE receta ADD COLUMN tratamiento_id INT NULL;
ALTER TABLE receta
    ADD CONSTRAINT fk_receta_origen
        FOREIGN KEY (consulta_id, tratamiento_id)
        REFERENCES tratamiento (consulta_id, id);

-- La copia está vacía: en una base poblada se requiere conciliación explícita.
ALTER TABLE tratamiento MODIFY COLUMN diagnostico_id INT NOT NULL;
ALTER TABLE receta MODIFY COLUMN tratamiento_id INT NOT NULL;

DELIMITER //
CREATE PROCEDURE verificar_diseno_pablo()
BEGIN
    DECLARE fallo BOOLEAN DEFAULT FALSE;
    START TRANSACTION;
    INSERT INTO especialidad (id, nombre) VALUES (1, 'DEMO');
    INSERT INTO medico (id, nombre, apellido, colegiado, especialidad_id)
    VALUES (1, 'Profesional', 'DEMO', 'DEMO-1', 1);
    INSERT INTO paciente (id, nombre, apellidos, identificacion, fecha_nacimiento)
    VALUES (1, 'Paciente', 'DEMO', 'DEMO-1', '2001-02-03');
    INSERT INTO consulta (id, fecha, paciente_id, medico_id, cita_id)
    VALUES (1, '2026-10-20', 1, 1, NULL), (2, '2026-10-20', 1, 1, NULL);
    IF (SELECT count(*) FROM consulta WHERE cita_id IS NULL) <> 2 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'FALLO: múltiples consultas sin cita';
    END IF;
    SELECT 'OK 1: dos consultas sin cita' AS resultado;

    INSERT INTO cita (id, fecha, paciente_id, medico_id)
    VALUES (1, '2026-10-20', 1, 1);
    INSERT INTO consulta (id, fecha, paciente_id, medico_id, cita_id)
    VALUES (3, '2026-10-20', 1, 1, 1);
    SET fallo = FALSE;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1062 SET fallo = TRUE;
        INSERT INTO consulta (id, fecha, paciente_id, medico_id, cita_id)
        VALUES (4, '2026-10-20', 1, 1, 1);
    END;
    IF NOT fallo THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'FALLO: cita duplicada aceptada';
    END IF;
    SELECT 'OK 2: cita conserva UNIQUE' AS resultado;

    SET fallo = FALSE;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1452 SET fallo = TRUE;
        INSERT INTO consulta (id, fecha, paciente_id, medico_id, cita_id)
        VALUES (5, '2026-10-20', 1, 1, 999);
    END;
    IF NOT fallo THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'FALLO: cita inexistente aceptada';
    END IF;
    SELECT 'OK 3: cita conserva FK' AS resultado;

    INSERT INTO diagnostico (id, codigo) VALUES (1, 'DEMO-1'), (2, 'DEMO-2');
    INSERT INTO consulta_diagnostico (consulta_id, diagnostico_id)
    VALUES (1, 1), (2, 2);
    INSERT INTO tratamiento (id, nombre, consulta_id, diagnostico_id)
    VALUES (1, 'DEMO válido', 1, 1);
    SET fallo = FALSE;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1452 SET fallo = TRUE;
        INSERT INTO tratamiento (id, nombre, consulta_id, diagnostico_id)
        VALUES (2, 'DEMO cruzado', 1, 2);
    END;
    IF NOT fallo THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'FALLO: diagnóstico de otra consulta';
    END IF;
    SELECT 'OK 4: diagnóstico cruzado rechazado' AS resultado;

    INSERT INTO receta (id, fecha, consulta_id, tratamiento_id)
    VALUES (1, '2026-10-20', 1, 1);
    SET fallo = FALSE;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1452 SET fallo = TRUE;
        INSERT INTO receta (id, fecha, consulta_id, tratamiento_id)
        VALUES (2, '2026-10-20', 2, 1);
    END;
    IF NOT fallo THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'FALLO: tratamiento de otra consulta';
    END IF;
    SELECT 'OK 5: tratamiento cruzado rechazado' AS resultado;

    -- DML con rollback explícito: los errores SQL no revierten toda la transacción solos.
    SAVEPOINT antes_receta;
    INSERT INTO receta (id, fecha, consulta_id, tratamiento_id)
    VALUES (3, '2026-10-20', 1, 1);
    SET fallo = FALSE;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1452 SET fallo = TRUE;
        INSERT INTO detalle_receta (receta_id, medicamento_id, dosis)
        VALUES (3, 999, 'DEMO');
    END;
    IF NOT fallo THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'FALLO: medicamento inexistente aceptado';
    END IF;
    ROLLBACK TO SAVEPOINT antes_receta;
    IF EXISTS (SELECT 1 FROM receta WHERE id = 3) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'FALLO: cabecera parcial tras rollback';
    END IF;
    SELECT 'OK 6: rollback explícito elimina cabecera parcial' AS resultado;
    ROLLBACK;
END//
DELIMITER ;
CALL verificar_diseno_pablo();
DROP PROCEDURE verificar_diseno_pablo;
