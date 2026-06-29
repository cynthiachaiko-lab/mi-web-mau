// Endpoint temporal de inicialización. SE BORRA DESPUÉS DE CORRERLO UNA VEZ.
const { sql } = require('../lib/db');

module.exports = async (req, res) => {
  const { secret } = req.query;
  if (secret !== 'setup-fixpro-2026') {
    return res.status(403).json({ error: 'forbidden' });
  }

  const results = [];

  const statements = [
    `CREATE TABLE IF NOT EXISTS clientes (
      id SERIAL PRIMARY KEY,
      nombre VARCHAR(100) NOT NULL,
      apellido VARCHAR(100) NOT NULL,
      usuario VARCHAR(150) NOT NULL UNIQUE,
      dni_hash VARCHAR(200) NOT NULL,
      rol VARCHAR(20) NOT NULL DEFAULT 'cliente',
      coeficiente_default NUMERIC(6,4),
      descuento_default NUMERIC(5,4),
      activo BOOLEAN NOT NULL DEFAULT true,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )`,
    `CREATE TABLE IF NOT EXISTS config_global (
      id INTEGER PRIMARY KEY DEFAULT 1,
      coeficiente_default NUMERIC(6,4) NOT NULL DEFAULT 1.21,
      descuento_default NUMERIC(5,4) NOT NULL DEFAULT 0.50,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CHECK (id = 1)
    )`,
    `INSERT INTO config_global (id, coeficiente_default, descuento_default)
     VALUES (1, 1.21, 0.50) ON CONFLICT (id) DO NOTHING`,
    `CREATE TABLE IF NOT EXISTS overrides_rubro_global (
      rubro_key VARCHAR(50) PRIMARY KEY,
      coeficiente NUMERIC(6,4) NOT NULL,
      descuento NUMERIC(5,4) NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )`,
    `INSERT INTO overrides_rubro_global (rubro_key, coeficiente, descuento) VALUES
      ('br', 1.21, 0.00), ('rr', 1.21, 0.00), ('er', 1.21, 0.00)
     ON CONFLICT (rubro_key) DO NOTHING`,
    `CREATE TABLE IF NOT EXISTS overrides_rubro_cliente (
      id SERIAL PRIMARY KEY,
      cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
      rubro_key VARCHAR(50) NOT NULL,
      coeficiente NUMERIC(6,4) NOT NULL,
      descuento NUMERIC(5,4) NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (cliente_id, rubro_key)
    )`,
    `CREATE INDEX IF NOT EXISTS idx_overrides_cliente ON overrides_rubro_cliente(cliente_id)`,
  ];

  for (const stmt of statements) {
    try {
      await sql.query(stmt);
      results.push({ ok: true, stmt: stmt.trim().substring(0, 50) });
    } catch (e) {
      results.push({ ok: false, stmt: stmt.trim().substring(0, 50), error: e.message });
    }
  }

  return res.status(200).json({ done: true, results });
};
