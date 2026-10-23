-- =========================================================
-- HOSPITAL GENERAL - PostgreSQL 16 - modelo B3 y control de version.
-- usuario se conserva como tabla heredada; la identidad vigente es Django/B2.
-- No autenticar mediante esta tabla ni exponerla al rol hospital_runtime.
-- =========================================================
CREATE TABLE especialidad (
    activo_operativo BOOLEAN NOT NULL DEFAULT TRUE,
    id_especialidad SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    nivel_complejidad INTEGER NOT NULL
);

CREATE TABLE medico (
    id_medico SERIAL PRIMARY KEY,
    id_especialidad INTEGER NOT NULL,
    nombre_completo VARCHAR(150) NOT NULL,
    colegiado VARCHAR(50) NOT NULL UNIQUE,
    telefono VARCHAR(20),
    correo VARCHAR(150),
    tipo_contrato VARCHAR(50),
    habilitado BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_medico_especialidad FOREIGN KEY (id_especialidad) REFERENCES especialidad(id_especialidad)
);

CREATE TABLE enfermero (
    activo_operativo BOOLEAN NOT NULL DEFAULT TRUE,
    id_enfermero SERIAL PRIMARY KEY,
    nombre_completo VARCHAR(150) NOT NULL,
    licencia_enfermeria VARCHAR(50) NOT NULL UNIQUE,
    nivel_academico VARCHAR(100)
);

CREATE TABLE pabellon_edificio (
    activo_operativo BOOLEAN NOT NULL DEFAULT TRUE,
    id_pabellon SERIAL PRIMARY KEY,
    nombre_pabellon VARCHAR(100) NOT NULL,
    director_responsable INTEGER,
    CONSTRAINT fk_pabellon_medico FOREIGN KEY (director_responsable) REFERENCES medico(id_medico)
);

CREATE TABLE habitacion (
    activo_operativo BOOLEAN NOT NULL DEFAULT TRUE,
    id_habitacion SERIAL PRIMARY KEY,
    id_pabellon INTEGER NOT NULL,
    numero_habitacion VARCHAR(20) NOT NULL UNIQUE,
    tipo_atencion VARCHAR(100),
    CONSTRAINT fk_habitacion_pabellon FOREIGN KEY (id_pabellon) REFERENCES pabellon_edificio(id_pabellon)
);

CREATE TABLE cama (
    activo_operativo BOOLEAN NOT NULL DEFAULT TRUE,
    id_cama SERIAL PRIMARY KEY,
    id_habitacion INTEGER NOT NULL,
    codigo_cama VARCHAR(30) NOT NULL UNIQUE,
    estado_limpieza VARCHAR(50) NOT NULL,
    CONSTRAINT fk_cama_habitacion FOREIGN KEY (id_habitacion) REFERENCES habitacion(id_habitacion)
);

CREATE TABLE quirofano (
    activo_operativo BOOLEAN NOT NULL DEFAULT TRUE,
    id_quirofano SERIAL PRIMARY KEY,
    id_pabellon INTEGER NOT NULL,
    nombre_sala VARCHAR(100) NOT NULL,
    equipamiento_especial TEXT,
    CONSTRAINT fk_quirofano_pabellon FOREIGN KEY (id_pabellon) REFERENCES pabellon_edificio(id_pabellon)
);

CREATE TABLE paciente (
    id_paciente SERIAL PRIMARY KEY,
    dpi_cui VARCHAR(20) NOT NULL UNIQUE,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE NOT NULL,
    sexo VARCHAR(20),
    tipo_sangre VARCHAR(10),
    numero_poliza_seguro VARCHAR(100),
    estado VARCHAR(20) NOT NULL DEFAULT 'activo',
    motivo_baja VARCHAR(200),
    fecha_baja DATE,
    CONSTRAINT chk_paciente_estado CHECK (estado IN ('activo','inactivo','archivado')),
    CONSTRAINT paciente_archivo_coherente CHECK (estado <> 'archivado' OR
      (motivo_baja IS NOT NULL AND length(btrim(motivo_baja)) BETWEEN 1 AND 200 AND fecha_baja IS NOT NULL))
);

CREATE TABLE ingreso_hospitalario (
    id_ingreso SERIAL PRIMARY KEY,
    id_paciente INTEGER NOT NULL,
    id_medico_responsable INTEGER NOT NULL,
    id_cama INTEGER NOT NULL,
    fecha_hora_ingreso TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_hora_alta TIMESTAMP,
    ingreso_utc TIMESTAMPTZ NOT NULL,
    alta_utc TIMESTAMPTZ,
    tipo_ingreso VARCHAR(50) NOT NULL,
    CONSTRAINT fk_ingreso_paciente FOREIGN KEY (id_paciente) REFERENCES paciente(id_paciente),
    CONSTRAINT fk_ingreso_medico FOREIGN KEY (id_medico_responsable) REFERENCES medico(id_medico),
    CONSTRAINT fk_ingreso_cama FOREIGN KEY (id_cama) REFERENCES cama(id_cama),
    CONSTRAINT chk_fechas_ingreso CHECK (fecha_hora_alta IS NULL OR fecha_hora_alta >= fecha_hora_ingreso),
    CONSTRAINT ingreso_utc_coherente CHECK ((fecha_hora_alta IS NULL) = (alta_utc IS NULL) AND (alta_utc IS NULL OR alta_utc >= ingreso_utc))
);

CREATE TABLE movimiento_cama (
    id_movimiento SERIAL PRIMARY KEY,
    id_ingreso INTEGER NOT NULL,
    id_cama INTEGER NOT NULL,
    fecha_hora_inicio TIMESTAMP NOT NULL,
    fecha_hora_fin TIMESTAMP,
    motivo_traslado VARCHAR(200),
    CONSTRAINT fk_movimiento_ingreso FOREIGN KEY (id_ingreso) REFERENCES ingreso_hospitalario(id_ingreso),
    CONSTRAINT fk_movimiento_cama FOREIGN KEY (id_cama) REFERENCES cama(id_cama),
    CONSTRAINT chk_movimiento_fechas CHECK (fecha_hora_fin IS NULL OR fecha_hora_fin >= fecha_hora_inicio)
);

CREATE TABLE emergencia (
    id_emergencia SERIAL PRIMARY KEY,
    id_ingreso INTEGER NOT NULL UNIQUE,
    fecha_hora_llegada TIMESTAMP NOT NULL,
    motivo_consulta TEXT NOT NULL,
    nivel_triaje VARCHAR(30),
    observaciones TEXT,
    CONSTRAINT fk_emergencia_ingreso FOREIGN KEY (id_ingreso) REFERENCES ingreso_hospitalario(id_ingreso)
);

CREATE TABLE cita (
    id_cita SERIAL PRIMARY KEY,
    id_paciente INTEGER NOT NULL,
    id_medico INTEGER NOT NULL,
    fecha_hora TIMESTAMP NOT NULL,
    estado VARCHAR(30) NOT NULL,
    CONSTRAINT cita_parentesco_unico UNIQUE (id_cita,id_paciente,id_medico),
    CONSTRAINT fk_cita_paciente FOREIGN KEY (id_paciente) REFERENCES paciente(id_paciente),
    CONSTRAINT fk_cita_medico FOREIGN KEY (id_medico) REFERENCES medico(id_medico)
);

CREATE TABLE consulta (
    id_consulta SERIAL PRIMARY KEY,
    id_paciente INTEGER NOT NULL,
    id_medico INTEGER NOT NULL,
    id_cita INTEGER UNIQUE,
    fecha DATE NOT NULL,
    notas_evolucion TEXT,
    CONSTRAINT consulta_notas_requeridas CHECK (notas_evolucion IS NOT NULL AND length(btrim(notas_evolucion)) BETWEEN 1 AND 5000),
    CONSTRAINT fk_consulta_paciente FOREIGN KEY (id_paciente) REFERENCES paciente(id_paciente),
    CONSTRAINT fk_consulta_medico FOREIGN KEY (id_medico) REFERENCES medico(id_medico),
    CONSTRAINT fk_consulta_cita FOREIGN KEY (id_cita) REFERENCES cita(id_cita),
    CONSTRAINT fk_consulta_cita_contexto FOREIGN KEY (id_cita,id_paciente,id_medico) REFERENCES cita(id_cita,id_paciente,id_medico)
);

CREATE TABLE signos_vitales (
    id_signos SERIAL PRIMARY KEY,
    id_ingreso INTEGER NOT NULL,
    id_enfermero INTEGER NOT NULL,
    fecha_hora_medicion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    presion_arterial VARCHAR(20),
    frecuencia_cardiaca INTEGER,
    oximetria INTEGER,
    CONSTRAINT fk_signos_ingreso FOREIGN KEY (id_ingreso) REFERENCES ingreso_hospitalario(id_ingreso),
    CONSTRAINT fk_signos_enfermero FOREIGN KEY (id_enfermero) REFERENCES enfermero(id_enfermero),
    CONSTRAINT chk_frecuencia_cardiaca CHECK (frecuencia_cardiaca IS NULL OR frecuencia_cardiaca > 0),
    CONSTRAINT chk_oximetria CHECK (oximetria IS NULL OR oximetria BETWEEN 0 AND 100)
);

CREATE TABLE diagnostico (
    id_diagnostico SERIAL PRIMARY KEY,
    id_ingreso INTEGER,
    id_consulta INTEGER,
    codigo_cie10 VARCHAR(20),
    descripcion TEXT NOT NULL,
    CONSTRAINT diagnostico_consulta_textos CHECK (id_consulta IS NULL OR (codigo_cie10 IS NOT NULL AND length(btrim(codigo_cie10)) BETWEEN 1 AND 20 AND length(btrim(descripcion)) BETWEEN 1 AND 5000)),
    CONSTRAINT fk_diagnostico_ingreso FOREIGN KEY (id_ingreso) REFERENCES ingreso_hospitalario(id_ingreso),
    CONSTRAINT fk_diagnostico_consulta FOREIGN KEY (id_consulta) REFERENCES consulta(id_consulta),
    CONSTRAINT chk_origen_diagnostico CHECK (
        (id_ingreso IS NOT NULL AND id_consulta IS NULL) OR (id_ingreso IS NULL AND id_consulta IS NOT NULL))
);

CREATE TABLE cirugia (
    id_cirugia SERIAL PRIMARY KEY,
    id_ingreso INTEGER NOT NULL,
    id_quirofano INTEGER NOT NULL,
    fecha_hora_inicio TIMESTAMP NOT NULL,
    fecha_hora_fin TIMESTAMP,
    riesgo_quirurgico VARCHAR(30),
    estado VARCHAR(30) NOT NULL,
    CONSTRAINT fk_cirugia_ingreso FOREIGN KEY (id_ingreso) REFERENCES ingreso_hospitalario(id_ingreso),
    CONSTRAINT fk_cirugia_quirofano FOREIGN KEY (id_quirofano) REFERENCES quirofano(id_quirofano),
    CONSTRAINT chk_cirugia_fechas CHECK (fecha_hora_fin IS NULL OR fecha_hora_fin >= fecha_hora_inicio)
);

CREATE TABLE equipo_quirurgico (
    id_cirugia INTEGER NOT NULL,
    id_medico INTEGER NOT NULL,
    rol_en_cirugia VARCHAR(100) NOT NULL,
    PRIMARY KEY (id_cirugia, id_medico),
    CONSTRAINT fk_equipo_cirugia FOREIGN KEY (id_cirugia) REFERENCES cirugia(id_cirugia),
    CONSTRAINT fk_equipo_medico FOREIGN KEY (id_medico) REFERENCES medico(id_medico)
);

CREATE TABLE tratamiento (
    id_tratamiento SERIAL PRIMARY KEY,
    id_diagnostico INTEGER NOT NULL,
    indicaciones_generales TEXT,
    CONSTRAINT tratamiento_indicaciones_requeridas CHECK (indicaciones_generales IS NOT NULL AND length(btrim(indicaciones_generales)) BETWEEN 1 AND 5000),
    CONSTRAINT fk_tratamiento_diagnostico FOREIGN KEY (id_diagnostico) REFERENCES diagnostico(id_diagnostico)
);

CREATE TABLE medicamento (
    activo_operativo BOOLEAN NOT NULL DEFAULT TRUE,
    id_medicamento SERIAL PRIMARY KEY,
    nombre_comercial VARCHAR(150) NOT NULL,
    principio_activo VARCHAR(150) NOT NULL,
    presentacion VARCHAR(100),
    stock_farmacia INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT chk_stock_farmacia CHECK (stock_farmacia >= 0)
);

CREATE TABLE receta_prescripcion (
    id_receta SERIAL PRIMARY KEY,
    id_tratamiento INTEGER NOT NULL,
    id_medicamento INTEGER NOT NULL,
    dosis VARCHAR(100) NOT NULL,
    frecuencia VARCHAR(100) NOT NULL,
    via_administracion VARCHAR(100),
    CONSTRAINT fk_receta_tratamiento FOREIGN KEY (id_tratamiento) REFERENCES tratamiento(id_tratamiento),
    CONSTRAINT fk_receta_medicamento FOREIGN KEY (id_medicamento) REFERENCES medicamento(id_medicamento)
);

CREATE TABLE despacho_farmacia (
    id_despacho SERIAL PRIMARY KEY,
    id_receta INTEGER NOT NULL,
    fecha_hora_despacho TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cantidad_entregada INTEGER NOT NULL,
    CONSTRAINT fk_despacho_receta FOREIGN KEY (id_receta) REFERENCES receta_prescripcion(id_receta),
    CONSTRAINT chk_cantidad_entregada CHECK (cantidad_entregada > 0)
);

CREATE TABLE aplicacion_enfermeria (
    id_aplicacion SERIAL PRIMARY KEY,
    id_despacho INTEGER NOT NULL,
    id_enfermero INTEGER NOT NULL,
    fecha_hora_aplicada TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observaciones_paciente TEXT,
    CONSTRAINT fk_aplicacion_despacho FOREIGN KEY (id_despacho) REFERENCES despacho_farmacia(id_despacho),
    CONSTRAINT fk_aplicacion_enfermero FOREIGN KEY (id_enfermero) REFERENCES enfermero(id_enfermero)
);

CREATE TABLE factura (
    id_factura SERIAL PRIMARY KEY,
    id_paciente INTEGER NOT NULL,
    id_ingreso INTEGER,
    id_consulta INTEGER,
    numero_factura VARCHAR(50) NOT NULL UNIQUE,
    fecha_emision TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subtotal NUMERIC(12,2) NOT NULL DEFAULT 0,
    impuestos NUMERIC(12,2) NOT NULL DEFAULT 0,
    total NUMERIC(12,2) NOT NULL DEFAULT 0,
    estado VARCHAR(30) NOT NULL DEFAULT 'Pendiente',
    CONSTRAINT fk_factura_paciente FOREIGN KEY (id_paciente) REFERENCES paciente(id_paciente),
    CONSTRAINT fk_factura_ingreso FOREIGN KEY (id_ingreso) REFERENCES ingreso_hospitalario(id_ingreso),
    CONSTRAINT fk_factura_consulta FOREIGN KEY (id_consulta) REFERENCES consulta(id_consulta),
    CONSTRAINT chk_factura_montos CHECK (subtotal >= 0 AND impuestos >= 0 AND total >= 0),
    CONSTRAINT chk_factura_origen CHECK (
        (id_ingreso IS NOT NULL AND id_consulta IS NULL) OR (id_ingreso IS NULL AND id_consulta IS NOT NULL)),
    CONSTRAINT chk_factura_estado CHECK (estado IN ('Borrador','Pendiente','Parcial','Pagada','Anulada'))
);

CREATE TABLE detalle_factura (
    id_detalle SERIAL PRIMARY KEY,
    id_factura INTEGER NOT NULL,
    concepto VARCHAR(200) NOT NULL,
    descripcion TEXT,
    cantidad INTEGER NOT NULL DEFAULT 1,
    precio_unitario NUMERIC(12,2) NOT NULL,
    subtotal NUMERIC(12,2) NOT NULL,
    CONSTRAINT fk_detalle_factura FOREIGN KEY (id_factura) REFERENCES factura(id_factura),
    CONSTRAINT chk_detalle_cantidad CHECK (cantidad > 0),
    CONSTRAINT chk_precio_unitario CHECK (precio_unitario >= 0),
    CONSTRAINT chk_detalle_subtotal CHECK (subtotal >= 0)
);

CREATE TABLE pago (
    id_pago SERIAL PRIMARY KEY,
    id_factura INTEGER NOT NULL,
    fecha_hora_pago TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    monto NUMERIC(12,2) NOT NULL,
    metodo_pago VARCHAR(50) NOT NULL,
    referencia_pago VARCHAR(100),
    estado VARCHAR(30) NOT NULL DEFAULT 'Procesado',
    CONSTRAINT fk_pago_factura FOREIGN KEY (id_factura) REFERENCES factura(id_factura),
    CONSTRAINT chk_pago_monto CHECK (monto > 0),
    CONSTRAINT chk_metodo_pago CHECK (metodo_pago IN ('Efectivo','Tarjeta','Transferencia','Cheque','Otro')),
    CONSTRAINT chk_pago_estado CHECK (estado IN ('Procesado','Pendiente','Anulado'))
);

-- ---------- Autenticacion (no estaba en el modelo original) ----------
CREATE TABLE usuario (
    id_usuario SERIAL PRIMARY KEY,
    nombre_usuario VARCHAR(80) NOT NULL UNIQUE,
    contrasena_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(30) NOT NULL,
    id_medico INTEGER,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_usuario_medico FOREIGN KEY (id_medico) REFERENCES medico(id_medico),
    CONSTRAINT chk_usuario_rol CHECK (rol IN ('medico','secretaria','enfermero','admin'))
);

CREATE INDEX idx_consulta_paciente ON consulta(id_paciente);
CREATE INDEX idx_cita_paciente ON cita(id_paciente);
CREATE INDEX idx_paciente_apellidos ON paciente(apellidos, nombres);

CREATE UNIQUE INDEX ingreso_cama_activa_unica ON ingreso_hospitalario(id_cama) WHERE fecha_hora_alta IS NULL;
CREATE UNIQUE INDEX ingreso_paciente_activo_unico ON ingreso_hospitalario(id_paciente) WHERE fecha_hora_alta IS NULL;
CREATE INDEX idx_diagnostico_consulta ON diagnostico(id_consulta);
CREATE INDEX idx_tratamiento_diagnostico ON tratamiento(id_diagnostico);
CREATE INDEX idx_receta_tratamiento ON receta_prescripcion(id_tratamiento);
CREATE TABLE hospital_schema_version (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
INSERT INTO hospital_schema_version(version) VALUES ('B3-1.0.0');
