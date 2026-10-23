-- Explicit maintenance after inventory/backup; does not rewrite clinical history.
ALTER TABLE especialidad ADD COLUMN IF NOT EXISTS activo_operativo BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE enfermero ADD COLUMN IF NOT EXISTS activo_operativo BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE pabellon_edificio ADD COLUMN IF NOT EXISTS activo_operativo BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE habitacion ADD COLUMN IF NOT EXISTS activo_operativo BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE cama ADD COLUMN IF NOT EXISTS activo_operativo BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE quirofano ADD COLUMN IF NOT EXISTS activo_operativo BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE medicamento ADD COLUMN IF NOT EXISTS activo_operativo BOOLEAN NOT NULL DEFAULT TRUE;

-- AUC-06: new invoices start as Borrador; existing states and rows stay intact.
-- Apply the constraint replacement atomically, with writers stopped and backup.
BEGIN;
ALTER TABLE factura DROP CONSTRAINT IF EXISTS chk_factura_estado;
ALTER TABLE factura ADD CONSTRAINT chk_factura_estado CHECK (estado IN ('Borrador','Pendiente','Parcial','Pagada','Anulada'));
COMMIT;
