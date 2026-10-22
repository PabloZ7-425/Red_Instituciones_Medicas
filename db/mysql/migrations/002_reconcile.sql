-- Populate pediatria_conciliacion only from confirmed evidence, after expansion.
-- Never select MIN()/first diagnosis or invent dates. This phase is DML atomic.
DROP PROCEDURE IF EXISTS b4_reconcile;
DELIMITER //
CREATE PROCEDURE b4_reconcile()
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  START TRANSACTION;
  IF EXISTS(SELECT 1 FROM pediatria_conciliacion m LEFT JOIN tratamiento t ON t.id=m.id
            LEFT JOIN consulta_diagnostico d ON d.id=m.origen_id
            WHERE m.tipo='tratamiento' AND (t.id IS NULL OR d.id IS NULL OR t.consulta_id<>d.consulta_id
              OR (t.consulta_diagnostico_id IS NOT NULL AND t.consulta_diagnostico_id<>m.origen_id)))
     OR EXISTS(SELECT 1 FROM pediatria_conciliacion m LEFT JOIN receta r ON r.id=m.id
            LEFT JOIN tratamiento t ON t.id=m.origen_id
            WHERE m.tipo='receta' AND (r.id IS NULL OR t.id IS NULL OR r.consulta_id<>t.consulta_id
              OR (r.tratamiento_id IS NOT NULL AND r.tratamiento_id<>m.origen_id))) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Conciliacion incompatible; revisar evidencia sin cambiar historia';
  END IF;
  UPDATE tratamiento t JOIN pediatria_conciliacion m ON m.tipo='tratamiento' AND m.id=t.id
    SET t.consulta_diagnostico_id=m.origen_id WHERE t.consulta_diagnostico_id IS NULL;
  UPDATE receta r JOIN pediatria_conciliacion m ON m.tipo='receta' AND m.id=r.id
    SET r.tratamiento_id=m.origen_id WHERE r.tratamiento_id IS NULL;
  COMMIT;
END//
DELIMITER ;
CALL b4_reconcile();
DROP PROCEDURE b4_reconcile;
