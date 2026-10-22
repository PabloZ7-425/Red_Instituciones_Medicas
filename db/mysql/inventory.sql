-- Counts only, no clinical identities or legacy passwords in logs.
SELECT 'paciente' AS entidad,COUNT(*) AS filas FROM paciente
UNION ALL SELECT 'consulta',COUNT(*) FROM consulta
UNION ALL SELECT 'consulta_diagnostico',COUNT(*) FROM consulta_diagnostico
UNION ALL SELECT 'tratamiento',COUNT(*) FROM tratamiento
UNION ALL SELECT 'receta',COUNT(*) FROM receta
UNION ALL SELECT 'detalle_receta',COUNT(*) FROM detalle_receta
UNION ALL SELECT 'tutor',COUNT(*) FROM tutor
UNION ALL SELECT 'paciente_tutor',COUNT(*) FROM paciente_tutor
UNION ALL SELECT 'aplicacion_vacuna',COUNT(*) FROM aplicacion_vacuna
UNION ALL SELECT 'control_de_crecimiento',COUNT(*) FROM control_de_crecimiento;
