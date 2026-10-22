SELECT 'paciente' AS entidad, count(*) AS cantidad FROM paciente
UNION ALL SELECT 'consulta',count(*) FROM consulta
UNION ALL SELECT 'ingreso_hospitalario',count(*) FROM ingreso_hospitalario
UNION ALL SELECT 'medico',count(*) FROM medico;
SELECT count(*) AS camas_con_ingresos_activos_duplicados FROM
  (SELECT id_cama FROM ingreso_hospitalario WHERE fecha_hora_alta IS NULL GROUP BY id_cama HAVING count(*)>1) x;
SELECT count(*) AS pacientes_con_ingresos_activos_duplicados FROM
  (SELECT id_paciente FROM ingreso_hospitalario WHERE fecha_hora_alta IS NULL GROUP BY id_paciente HAVING count(*)>1) x;
DO $$
DECLARE missing BIGINT;
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='consulta' AND column_name='fecha') THEN
    EXECUTE 'SELECT count(*) FROM consulta WHERE fecha IS NULL' INTO missing;
    RAISE NOTICE 'Consultas con fecha pendiente: %', missing;
  ELSE
    RAISE NOTICE 'Falta expandir consulta.fecha; todas las consultas historicas requieren fecha confirmada';
  END IF;
END $$;
