-- FixPro - Fase 2: clientes y precios personalizados
-- Ejecutar UNA SOLA VEZ contra la base Vercel Postgres del proyecto.

CREATE TABLE IF NOT EXISTS clientes (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  apellido VARCHAR(100) NOT NULL,
  usuario VARCHAR(150) NOT NULL UNIQUE,  -- nombre+apellido normalizado (ver lib/auth.js)
  dni_hash VARCHAR(200) NOT NULL,
  rol VARCHAR(20) NOT NULL DEFAULT 'cliente', -- 'cliente' | 'admin'
  coeficiente_default NUMERIC(6,4),  -- NULL = usa el global de la app
  descuento_default NUMERIC(5,4),    -- NULL = usa el global de la app (0 a 1)
  activo BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Fila única con los valores default de toda la app (hoy hardcodeados: 0.50 y 1.21)
CREATE TABLE IF NOT EXISTS config_global (
  id INTEGER PRIMARY KEY DEFAULT 1,
  coeficiente_default NUMERIC(6,4) NOT NULL DEFAULT 1.21,
  descuento_default NUMERIC(5,4) NOT NULL DEFAULT 0.50,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (id = 1)
);
INSERT INTO config_global (id, coeficiente_default, descuento_default)
VALUES (1, 1.21, 0.50)
ON CONFLICT (id) DO NOTHING;

-- Excepciones por rubro que aplican a TODOS los clientes
-- (reemplaza el hardcode actual de BR/RR/ER del script de carga).
-- IMPORTANTE: revisar que rubro_key coincida EXACTO (mayus/minus) con tu campo "rk".
CREATE TABLE IF NOT EXISTS overrides_rubro_global (
  rubro_key VARCHAR(50) PRIMARY KEY,
  coeficiente NUMERIC(6,4) NOT NULL,
  descuento NUMERIC(5,4) NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO overrides_rubro_global (rubro_key, coeficiente, descuento) VALUES
  ('br', 1.21, 0.00),
  ('rr', 1.21, 0.00),
  ('er', 1.21, 0.00)
ON CONFLICT (rubro_key) DO NOTHING;

-- Excepciones por rubro específicas de UN cliente (pisan todo lo anterior)
CREATE TABLE IF NOT EXISTS overrides_rubro_cliente (
  id SERIAL PRIMARY KEY,
  cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
  rubro_key VARCHAR(50) NOT NULL,
  coeficiente NUMERIC(6,4) NOT NULL,
  descuento NUMERIC(5,4) NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (cliente_id, rubro_key)
);

CREATE INDEX IF NOT EXISTS idx_overrides_cliente ON overrides_rubro_cliente(cliente_id);
