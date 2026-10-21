-- Investigación C0 sobre copia aislada de init.sql. No es una migración.
-- El ejecutor debe crear una instancia temporal, sin volúmenes/puertos del proyecto.
BEGIN;

INSERT INTO especialidad VALUES (1, 'DEMO', 1);
INSERT INTO medico (id_medico, id_especialidad, nombre_completo, colegiado)
VALUES (1, 1, 'DEMO profesional', 'DEMO-1');
INSERT INTO paciente (id_paciente, dpi_cui, nombres, apellidos, fecha_nacimiento)
VALUES (1, 'DEMO-1', 'Paciente', 'DEMO', '2001-02-03');
INSERT INTO cita VALUES (1, 1, 1, '2026-10-18 10:00:00', 'atendida');
INSERT INTO consulta (id_consulta, id_paciente, id_medico, id_cita)
VALUES (1, 1, 1, 1);

ALTER TABLE consulta ADD COLUMN fecha DATE;
DO $$
BEGIN
    BEGIN
        ALTER TABLE consulta ALTER COLUMN fecha SET NOT NULL;
        RAISE EXCEPTION 'FALLO: fecha histórica desconocida aceptada';
    EXCEPTION WHEN not_null_violation THEN NULL;
    END;
    RAISE NOTICE 'OK 1: fecha histórica desconocida bloquea NOT NULL';
END $$;

-- Fecha confirmada únicamente para este fixture DEMO, distinta de la cita.
UPDATE consulta SET fecha = DATE '2026-10-19' WHERE id_consulta = 1;
ALTER TABLE consulta ALTER COLUMN fecha SET NOT NULL;

DO $$
DECLARE
    cantidad_antes INTEGER;
BEGIN
    IF (SELECT fecha FROM consulta WHERE id_consulta = 1) <> DATE '2026-10-19'
       OR (SELECT fecha FROM consulta WHERE id_consulta = 1)
          = (SELECT fecha_hora::date FROM cita WHERE id_cita = 1) THEN
        RAISE EXCEPTION 'FALLO: no se conserva fecha clínica explícita';
    END IF;
    RAISE NOTICE 'OK 2: fecha clínica independiente de la cita';

    BEGIN
        INSERT INTO consulta (id_consulta, id_paciente, id_medico) VALUES (2, 1, 1);
        RAISE EXCEPTION 'FALLO: consulta sin fecha aceptada';
    EXCEPTION WHEN not_null_violation THEN NULL;
    END;
    RAISE NOTICE 'OK 3: consulta sin fecha rechazada';

    BEGIN
        INSERT INTO paciente (id_paciente, dpi_cui, nombres, apellidos, fecha_nacimiento)
        VALUES (2, 'DEMO-1', 'Paciente', 'Duplicado DEMO', '2001-02-03');
        RAISE EXCEPTION 'FALLO: identificación duplicada aceptada';
    EXCEPTION WHEN unique_violation THEN NULL;
    END;
    RAISE NOTICE 'OK 4: identificación duplicada rechazada';

    BEGIN
        INSERT INTO consulta (id_consulta, id_paciente, id_medico, fecha)
        VALUES (3, 999, 1, '2026-10-19');
        RAISE EXCEPTION 'FALLO: paciente inexistente aceptado';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;
    RAISE NOTICE 'OK 5: FK conserva integridad';

    SELECT count(*) INTO cantidad_antes FROM consulta;
    BEGIN
        INSERT INTO consulta (id_consulta, id_paciente, id_medico, fecha)
        VALUES (4, 1, 1, '2026-10-20');
        INSERT INTO diagnostico (id_consulta, descripcion)
        VALUES (999, 'DEMO: debe fallar y revertir la consulta');
        RAISE EXCEPTION 'FALLO: diagnóstico huérfano aceptado';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;
    IF (SELECT count(*) FROM consulta) <> cantidad_antes THEN
        RAISE EXCEPTION 'FALLO: escritura parcial tras error de diagnóstico';
    END IF;
    RAISE NOTICE 'OK 6: error de hijo revierte escritura de consulta';
END $$;

ROLLBACK;
