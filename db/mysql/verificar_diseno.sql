-- Investigación C0 sobre fixtures/mysql_legacy.sql. No es una migración.
-- Copia preservada en backend/apps/historiales/fixtures/mysql_legacy.sql.
-- init.sql ya incorpora B4; no volver a aplicar este experimento sobre él.
-- DDL MySQL tiene commit implícito: ejecutar solo en la instancia temporal.
ALTER TABLE consulta MODIFY COLUMN cita_id INT NULL;
ALTER TABLE consulta_diagnostico
    ADD CONSTRAINT uq_consulta_diagnostico UNIQUE (consulta_id, diagnostico_id),
    ADD CONSTRAINT uq_ocurrencia_consulta UNIQUE (consulta_id, id);
ALTER TABLE tratamiento ADD COLUMN consulta_diagnostico_id INT NULL;
ALTER TABLE tratamiento
    ADD CONSTRAINT fk_tratamiento_origen
        FOREIGN KEY (consulta_id, consulta_diagnostico_id)
        REFERENCES consulta_diagnostico (consulta_id, id),
    ADD CONSTRAINT uq_tratamiento_consulta UNIQUE (consulta_id, id);
ALTER TABLE receta ADD COLUMN tratamiento_id INT NULL;
ALTER TABLE receta
    ADD CONSTRAINT fk_receta_origen
        FOREIGN KEY (consulta_id, tratamiento_id)
        REFERENCES tratamiento (consulta_id, id);

-- La copia está vacía: en una base poblada se requiere conciliación explícita.
ALTER TABLE tratamiento MODIFY COLUMN consulta_diagnostico_id INT NOT NULL;
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
    INSERT INTO consulta_diagnostico (id, consulta_id, diagnostico_id)
    VALUES (101, 1, 1), (102, 2, 2), (103, 2, 1);
    INSERT INTO tratamiento (id, nombre, consulta_id, consulta_diagnostico_id)
    VALUES (1, 'DEMO válido', 1, 101);
    SET fallo = FALSE;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1452 SET fallo = TRUE;
        INSERT INTO tratamiento (id, nombre, consulta_id, consulta_diagnostico_id)
        VALUES (2, 'DEMO cruzado', 1, 102);
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

    -- El mismo catálogo diagnóstico en dos consultas produce ocurrencias distintas.
    INSERT INTO tratamiento (id, nombre, consulta_id, consulta_diagnostico_id)
    VALUES (3, 'DEMO segunda ocurrencia', 2, 103);
    IF (SELECT count(*) FROM consulta_diagnostico WHERE diagnostico_id = 1) <> 2
       OR (SELECT consulta_diagnostico_id FROM tratamiento WHERE id = 1) <> 101
       OR (SELECT consulta_diagnostico_id FROM tratamiento WHERE id = 3) <> 103 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'FALLO: ocurrencias ambiguas';
    END IF;
    SET fallo = FALSE;
    BEGIN
        DECLARE CONTINUE HANDLER FOR 1452 SET fallo = TRUE;
        INSERT INTO tratamiento (id, nombre, consulta_id, consulta_diagnostico_id)
        VALUES (4, 'DEMO ocurrencia ajena del mismo código', 1, 103);
    END;
    IF NOT fallo THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'FALLO: mismo código mezcla consultas';
    END IF;
    SELECT 'OK 7: código compartido conserva ocurrencias independientes' AS resultado;
    ROLLBACK;
END//
DELIMITER ;
CALL verificar_diseno_pablo();
DROP PROCEDURE verificar_diseno_pablo;
