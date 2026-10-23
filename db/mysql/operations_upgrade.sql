-- Explicit maintenance: apply once on schemas without these columns.
ALTER TABLE especialidad ADD COLUMN activo_operativo BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE tutor ADD COLUMN activo_operativo BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE vacuna ADD COLUMN activo_operativo BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE tipo_examen ADD COLUMN activo_operativo BOOLEAN NOT NULL DEFAULT TRUE;
