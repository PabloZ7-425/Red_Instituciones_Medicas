-- =========================================================
-- CENTRO MEDICO PEDIATRICO - MySQL 8.4 (InnoDB)
-- Generado desde clinica_pediatrica_correciones.drawio
-- 35 tablas
-- Adiciones respecto al diagrama: paciente.motivo_baja / fecha_baja (baja logica),
-- UNIQUE en colegiado, identificacion, correo de usuario y (serie, numero) de factura.
-- =========================================================
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE especialidad (
  id INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE medico (
  id INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  apellido VARCHAR(100) NOT NULL,
  colegiado VARCHAR(100) NOT NULL,
  telefono VARCHAR(100) NULL,
  correo VARCHAR(150) NULL,
  estado VARCHAR(100) NOT NULL DEFAULT 'activo',
  especialidad_id INT NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT uq_medico_colegiado UNIQUE (colegiado),
  CONSTRAINT fk_medico_especialidad FOREIGN KEY (especialidad_id) REFERENCES especialidad(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE rol (
  id INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  descripcion TEXT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE institucion (
  id INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  tipo VARCHAR(100) NULL,
  direccion TEXT NULL,
  telefono VARCHAR(100) NULL,
  estado VARCHAR(100) NOT NULL DEFAULT 'activo',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE usuario (
  id INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  apellido VARCHAR(100) NOT NULL,
  correo VARCHAR(150) NULL,
  contrasena VARCHAR(255) NOT NULL,
  fecha_registro DATE NULL,
  estado VARCHAR(100) NOT NULL DEFAULT 'activo',
  rol_id INT NOT NULL,
  institucion_id INT NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT uq_usuario_correo UNIQUE (correo),
  CONSTRAINT fk_usuario_rol FOREIGN KEY (rol_id) REFERENCES rol(id),
  CONSTRAINT fk_usuario_institucion FOREIGN KEY (institucion_id) REFERENCES institucion(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE paciente (
  id INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  apellidos VARCHAR(100) NOT NULL,
  identificacion VARCHAR(100) NOT NULL,
  fecha_nacimiento DATE NOT NULL,
  tipo_sangre VARCHAR(100) NULL,
  estado VARCHAR(100) NOT NULL DEFAULT 'activo',
  fecha_registro DATE NULL,
  motivo_baja VARCHAR(200) NULL,
  fecha_baja DATE NULL,
  PRIMARY KEY (id),
  CONSTRAINT uq_paciente_identificacion UNIQUE (identificacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE tutor (
  id INT NOT NULL AUTO_INCREMENT,
  nombres VARCHAR(100) NOT NULL,
  apellidos VARCHAR(100) NOT NULL,
  telefono VARCHAR(100) NULL,
  correo VARCHAR(150) NULL,
  parentesco VARCHAR(100) NULL,
  dpi VARCHAR(100) NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE paciente_tutor (
  id INT NOT NULL AUTO_INCREMENT,
  paciente_id INT NOT NULL,
  tutor_id INT NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT uq_paciente_tutor UNIQUE (paciente_id, tutor_id),
  CONSTRAINT fk_paciente_tutor_paciente FOREIGN KEY (paciente_id) REFERENCES paciente(id),
  CONSTRAINT fk_paciente_tutor_tutor FOREIGN KEY (tutor_id) REFERENCES tutor(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE cita (
  id INT NOT NULL AUTO_INCREMENT,
  fecha DATE NOT NULL,
  hora TIME NULL,
  motivo VARCHAR(100) NULL,
  estado VARCHAR(100) NULL,
  observaciones TEXT NULL,
  paciente_id INT NOT NULL,
  medico_id INT NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_cita_paciente FOREIGN KEY (paciente_id) REFERENCES paciente(id),
  CONSTRAINT fk_cita_medico FOREIGN KEY (medico_id) REFERENCES medico(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE consulta (
  id INT NOT NULL AUTO_INCREMENT,
  fecha DATE NOT NULL,
  motivo VARCHAR(100) NULL,
  observaciones TEXT NULL,
  paciente_id INT NOT NULL,
  medico_id INT NOT NULL,
  cita_id INT NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT uq_consulta_cita UNIQUE (cita_id),
  CONSTRAINT fk_consulta_paciente FOREIGN KEY (paciente_id) REFERENCES paciente(id),
  CONSTRAINT fk_consulta_medico FOREIGN KEY (medico_id) REFERENCES medico(id),
  CONSTRAINT fk_consulta_cita FOREIGN KEY (cita_id) REFERENCES cita(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE diagnostico (
  id INT NOT NULL AUTO_INCREMENT,
  codigo VARCHAR(100) NOT NULL,
  descripcion TEXT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE consulta_diagnostico (
  id INT NOT NULL AUTO_INCREMENT,
  consulta_id INT NOT NULL,
  diagnostico_id INT NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_consulta_diagnostico_consulta FOREIGN KEY (consulta_id) REFERENCES consulta(id),
  CONSTRAINT fk_consulta_diagnostico_diagnostico FOREIGN KEY (diagnostico_id) REFERENCES diagnostico(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE tratamiento (
  id INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  descripcion TEXT NULL,
  indicaciones TEXT NULL,
  fecha_inicio DATE NULL,
  fecha_fin DATE NULL,
  duracion VARCHAR(100) NULL,
  estado VARCHAR(100) NULL,
  consulta_id INT NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_tratamiento_consulta FOREIGN KEY (consulta_id) REFERENCES consulta(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE vacuna (
  id INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  descripcion TEXT NULL,
  numero_dosis INT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE aplicacion_vacuna (
  id INT NOT NULL AUTO_INCREMENT,
  fecha DATE NOT NULL,
  dosis INT NULL,
  lote VARCHAR(100) NULL,
  expiracion DATE NULL,
  observaciones TEXT NULL,
  paciente_id INT NOT NULL,
  vacuna_id INT NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_aplicacion_vacuna_paciente FOREIGN KEY (paciente_id) REFERENCES paciente(id),
  CONSTRAINT fk_aplicacion_vacuna_vacuna FOREIGN KEY (vacuna_id) REFERENCES vacuna(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE receta (
  id INT NOT NULL AUTO_INCREMENT,
  observaciones TEXT NULL,
  fecha DATE NOT NULL,
  consulta_id INT NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_receta_consulta FOREIGN KEY (consulta_id) REFERENCES consulta(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE medicamento (
  id INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  presentacion VARCHAR(100) NULL,
  concentracion VARCHAR(100) NULL,
  expiracion DATE NULL,
  estado VARCHAR(100) NOT NULL DEFAULT 'activo',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE detalle_receta (
  id INT NOT NULL AUTO_INCREMENT,
  receta_id INT NOT NULL,
  medicamento_id INT NOT NULL,
  cantidad INT NULL,
  dosis VARCHAR(100) NULL,
  frecuencia VARCHAR(100) NULL,
  duracion VARCHAR(100) NULL,
  via_administracion VARCHAR(100) NULL,
  indicaciones TEXT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_detalle_receta_receta FOREIGN KEY (receta_id) REFERENCES receta(id),
  CONSTRAINT fk_detalle_receta_medicamento FOREIGN KEY (medicamento_id) REFERENCES medicamento(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE tipo_examen (
  id INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  descripcion TEXT NULL,
  area VARCHAR(100) NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE examen (
  id INT NOT NULL AUTO_INCREMENT,
  fecha_solicitud DATE NULL,
  estado VARCHAR(100) NULL,
  prioridad VARCHAR(100) NULL,
  observaciones TEXT NULL,
  consulta_id INT NOT NULL,
  tipo_examen_id INT NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_examen_consulta FOREIGN KEY (consulta_id) REFERENCES consulta(id),
  CONSTRAINT fk_examen_tipo_examen FOREIGN KEY (tipo_examen_id) REFERENCES tipo_examen(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE resultado_examen (
  id INT NOT NULL AUTO_INCREMENT,
  examen_id INT NOT NULL,
  fecha_resultado DATE NULL,
  valor VARCHAR(100) NULL,
  unidad VARCHAR(100) NULL,
  rango_referencia VARCHAR(100) NULL,
  observaciones TEXT NULL,
  estado VARCHAR(100) NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_resultado_examen_examen FOREIGN KEY (examen_id) REFERENCES examen(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE control_de_crecimiento (
  id INT NOT NULL AUTO_INCREMENT,
  peso DECIMAL(6,2) NULL,
  talla DECIMAL(6,2) NULL,
  altura DECIMAL(6,2) NULL,
  percentil DECIMAL(6,2) NULL,
  fecha DATE NOT NULL,
  observaciones TEXT NULL,
  paciente_id INT NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_control_de_crecimiento_paciente FOREIGN KEY (paciente_id) REFERENCES paciente(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE antecedente_medico (
  id INT NOT NULL AUTO_INCREMENT,
  paciente_id INT NOT NULL,
  tipo VARCHAR(100) NULL,
  descripcion TEXT NULL,
  fecha_registro DATE NULL,
  estado VARCHAR(100) NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_antecedente_medico_paciente FOREIGN KEY (paciente_id) REFERENCES paciente(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE signos_vitales (
  id INT NOT NULL AUTO_INCREMENT,
  consulta_id INT NOT NULL,
  fecha_hora DATETIME NULL,
  temperatura DECIMAL(4,1) NULL,
  frecuencia_cardiaca INT NULL,
  frecuencia_respiratoria INT NULL,
  saturacion_oxigeno DECIMAL(5,2) NULL,
  presion_arterial VARCHAR(100) NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_signos_vitales_consulta FOREIGN KEY (consulta_id) REFERENCES consulta(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE servicio_medico (
  id INT NOT NULL AUTO_INCREMENT,
  codigo VARCHAR(100) NOT NULL,
  nombre VARCHAR(100) NOT NULL,
  descripcion TEXT NULL,
  precio_base DECIMAL(10,2) NULL,
  tipo_servicio VARCHAR(100) NULL,
  estado VARCHAR(100) NOT NULL DEFAULT 'activo',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE aseguradora (
  id INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  nit VARCHAR(100) NULL,
  telefono VARCHAR(100) NULL,
  correo VARCHAR(150) NULL,
  direccion TEXT NULL,
  estado VARCHAR(100) NOT NULL DEFAULT 'activo',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE plan_seguro (
  id INT NOT NULL AUTO_INCREMENT,
  aseguradora_id INT NOT NULL,
  nombre VARCHAR(100) NOT NULL,
  tipo_plan VARCHAR(100) NULL,
  deducible DECIMAL(10,2) NULL,
  limite_anual DECIMAL(10,2) NULL,
  estado VARCHAR(100) NOT NULL DEFAULT 'activo',
  PRIMARY KEY (id),
  CONSTRAINT fk_plan_seguro_aseguradora FOREIGN KEY (aseguradora_id) REFERENCES aseguradora(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE poliza_paciente (
  id INT NOT NULL AUTO_INCREMENT,
  paciente_id INT NOT NULL,
  plan_seguro_id INT NOT NULL,
  numero_poliza VARCHAR(100) NOT NULL,
  numero_afiliado VARCHAR(100) NULL,
  nombre_titular VARCHAR(100) NULL,
  fecha_inicio DATE NULL,
  fecha_fin DATE NULL,
  estado VARCHAR(100) NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_poliza_paciente_paciente FOREIGN KEY (paciente_id) REFERENCES paciente(id),
  CONSTRAINT fk_poliza_paciente_plan_seguro FOREIGN KEY (plan_seguro_id) REFERENCES plan_seguro(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE cobertura_servicio (
  id INT NOT NULL AUTO_INCREMENT,
  plan_seguro_id INT NOT NULL,
  servicio_id INT NOT NULL,
  porcentaje_cobertura DECIMAL(5,2) NULL,
  copago DECIMAL(10,2) NULL,
  limite_eventos INT NULL,
  requiere_autorizacion BOOLEAN NULL,
  estado VARCHAR(100) NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_cobertura_servicio_plan_seguro FOREIGN KEY (plan_seguro_id) REFERENCES plan_seguro(id),
  CONSTRAINT fk_cobertura_servicio_servicio FOREIGN KEY (servicio_id) REFERENCES servicio_medico(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE autorizacion_seguro (
  id INT NOT NULL AUTO_INCREMENT,
  poliza_paciente_id INT NOT NULL,
  consulta_id INT NOT NULL,
  numero_autorizacion VARCHAR(100) NOT NULL,
  fecha_solicitud DATE NULL,
  fecha_respuesta DATE NULL,
  monto_autorizado DECIMAL(10,2) NULL,
  estado VARCHAR(100) NULL,
  observaciones TEXT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_autorizacion_seguro_poliza_paciente FOREIGN KEY (poliza_paciente_id) REFERENCES poliza_paciente(id),
  CONSTRAINT fk_autorizacion_seguro_consulta FOREIGN KEY (consulta_id) REFERENCES consulta(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE factura (
  id INT NOT NULL AUTO_INCREMENT,
  paciente_id INT NOT NULL,
  consulta_id INT NOT NULL,
  serie VARCHAR(100) NULL,
  numero VARCHAR(100) NULL,
  fecha_emision DATETIME NULL,
  nit_receptor VARCHAR(100) NULL,
  nombre_receptor VARCHAR(100) NULL,
  direccion_receptor TEXT NULL,
  subtotal DECIMAL(10,2) NULL,
  descuento DECIMAL(10,2) NULL,
  impuestos DECIMAL(10,2) NULL,
  total_seguro DECIMAL(10,2) NULL,
  total_paciente DECIMAL(10,2) NULL,
  total DECIMAL(10,2) NULL,
  estado VARCHAR(100) NULL,
  PRIMARY KEY (id),
  CONSTRAINT uq_factura_serie_numero UNIQUE (serie, numero),
  CONSTRAINT fk_factura_paciente FOREIGN KEY (paciente_id) REFERENCES paciente(id),
  CONSTRAINT fk_factura_consulta FOREIGN KEY (consulta_id) REFERENCES consulta(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE reclamacion_seguro (
  id INT NOT NULL AUTO_INCREMENT,
  factura_id INT NOT NULL,
  poliza_paciente_id INT NOT NULL,
  autorizacion_id INT NULL,
  numero_reclamo VARCHAR(100) NOT NULL,
  fecha_envio DATE NULL,
  monto_reclamado DECIMAL(10,2) NULL,
  monto_aprobado DECIMAL(10,2) NULL,
  fecha_resolucion DATE NULL,
  estado VARCHAR(100) NULL,
  observaciones TEXT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_reclamacion_seguro_factura FOREIGN KEY (factura_id) REFERENCES factura(id),
  CONSTRAINT fk_reclamacion_seguro_poliza_paciente FOREIGN KEY (poliza_paciente_id) REFERENCES poliza_paciente(id),
  CONSTRAINT fk_reclamacion_seguro_autorizacion FOREIGN KEY (autorizacion_id) REFERENCES autorizacion_seguro(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE detalle_factura (
  id INT NOT NULL AUTO_INCREMENT,
  factura_id INT NOT NULL,
  servicio_id INT NOT NULL,
  cantidad INT NULL,
  precio_unitario DECIMAL(10,2) NULL,
  descuento DECIMAL(10,2) NULL,
  subtotal DECIMAL(10,2) NULL,
  monto_cubierto DECIMAL(10,2) NULL,
  monto_paciente DECIMAL(10,2) NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_detalle_factura_factura FOREIGN KEY (factura_id) REFERENCES factura(id),
  CONSTRAINT fk_detalle_factura_servicio FOREIGN KEY (servicio_id) REFERENCES servicio_medico(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE metodo_pago (
  id INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  descripcion TEXT NULL,
  estado VARCHAR(100) NOT NULL DEFAULT 'activo',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE pago (
  id INT NOT NULL AUTO_INCREMENT,
  factura_id INT NOT NULL,
  metodo_pago_id INT NOT NULL,
  fecha_hora DATETIME NULL,
  monto DECIMAL(10,2) NULL,
  tipo_pagador VARCHAR(100) NULL,
  referencia VARCHAR(100) NULL,
  estado VARCHAR(100) NULL,
  observaciones TEXT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_pago_factura FOREIGN KEY (factura_id) REFERENCES factura(id),
  CONSTRAINT fk_pago_metodo_pago FOREIGN KEY (metodo_pago_id) REFERENCES metodo_pago(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Reglas basicas de integridad
ALTER TABLE paciente ADD CONSTRAINT chk_paciente_estado CHECK (estado IN ('activo','inactivo','archivado'));
ALTER TABLE control_de_crecimiento ADD CONSTRAINT chk_crec_valores CHECK (peso > 0 AND talla > 0);
ALTER TABLE detalle_receta ADD CONSTRAINT chk_detrec_cantidad CHECK (cantidad IS NULL OR cantidad > 0);
ALTER TABLE pago ADD CONSTRAINT chk_pago_monto CHECK (monto > 0);
ALTER TABLE detalle_factura ADD CONSTRAINT chk_detfac_cantidad CHECK (cantidad > 0);

SET FOREIGN_KEY_CHECKS = 1;
