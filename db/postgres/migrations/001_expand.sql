-- Expansion only. No inferred dates or overwritten historical timestamps.
ALTER TABLE consulta ADD COLUMN IF NOT EXISTS fecha DATE;
ALTER TABLE medico ADD COLUMN IF NOT EXISTS habilitado BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE ingreso_hospitalario ADD COLUMN IF NOT EXISTS ingreso_utc TIMESTAMPTZ;
ALTER TABLE ingreso_hospitalario ADD COLUMN IF NOT EXISTS alta_utc TIMESTAMPTZ;
