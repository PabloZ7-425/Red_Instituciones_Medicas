-- Only maintenance receives app_password. No access to the legacy usuario table.
SELECT 'CREATE ROLE hospital_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='hospital_runtime') \gexec
ALTER ROLE hospital_runtime NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'app_password';
SELECT format('GRANT CONNECT ON DATABASE %I TO hospital_runtime', current_database()) \gexec
GRANT USAGE ON SCHEMA public TO hospital_runtime;
GRANT SELECT ON paciente,consulta,diagnostico,tratamiento,receta_prescripcion,medicamento,medico,cita,cama,ingreso_hospitalario,movimiento_cama TO hospital_runtime;
GRANT INSERT,UPDATE ON paciente,consulta,diagnostico,tratamiento,receta_prescripcion,ingreso_hospitalario TO hospital_runtime;
GRANT UPDATE ON cita,movimiento_cama TO hospital_runtime;
GRANT USAGE,SELECT ON SEQUENCE paciente_id_paciente_seq,consulta_id_consulta_seq,
  diagnostico_id_diagnostico_seq,tratamiento_id_tratamiento_seq,receta_prescripcion_id_receta_seq,
  ingreso_hospitalario_id_ingreso_seq TO hospital_runtime;
