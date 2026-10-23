-- Owner maintenance only; resumable and idempotent on the selected database.
-- Inventory/backup and stop writers before applying. No clinical rows are rewritten.
SET @ops_upgrade_sql = (SELECT IF(COUNT(*)=0,
  'ALTER TABLE especialidad ADD COLUMN activo_operativo BOOLEAN NOT NULL DEFAULT TRUE',
  'SELECT 1') FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='especialidad' AND COLUMN_NAME='activo_operativo');
PREPARE ops_upgrade_statement FROM @ops_upgrade_sql;
EXECUTE ops_upgrade_statement;
DEALLOCATE PREPARE ops_upgrade_statement;
SET @ops_upgrade_sql = (SELECT IF(COUNT(*)=0,
  'ALTER TABLE tutor ADD COLUMN activo_operativo BOOLEAN NOT NULL DEFAULT TRUE',
  'SELECT 1') FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='tutor' AND COLUMN_NAME='activo_operativo');
PREPARE ops_upgrade_statement FROM @ops_upgrade_sql;
EXECUTE ops_upgrade_statement;
DEALLOCATE PREPARE ops_upgrade_statement;
SET @ops_upgrade_sql = (SELECT IF(COUNT(*)=0,
  'ALTER TABLE vacuna ADD COLUMN activo_operativo BOOLEAN NOT NULL DEFAULT TRUE',
  'SELECT 1') FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='vacuna' AND COLUMN_NAME='activo_operativo');
PREPARE ops_upgrade_statement FROM @ops_upgrade_sql;
EXECUTE ops_upgrade_statement;
DEALLOCATE PREPARE ops_upgrade_statement;
SET @ops_upgrade_sql = (SELECT IF(COUNT(*)=0,
  'ALTER TABLE tipo_examen ADD COLUMN activo_operativo BOOLEAN NOT NULL DEFAULT TRUE',
  'SELECT 1') FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='tipo_examen' AND COLUMN_NAME='activo_operativo');
PREPARE ops_upgrade_statement FROM @ops_upgrade_sql;
EXECUTE ops_upgrade_statement;
DEALLOCATE PREPARE ops_upgrade_statement;
