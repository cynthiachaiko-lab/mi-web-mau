// Endpoint temporal para crear cuenta admin. SE BORRA DESPUÉS DE CORRERLO.
const { sql } = require('../lib/db');
const bcrypt = require('bcryptjs');

function normalizar(nombre, apellido) {
  return `${nombre} ${apellido}`
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().trim().replace(/\s+/g, ' ');
}

module.exports = async (req, res) => {
  const { secret } = req.query;
  if (secret !== process.env.JWT_SECRET?.slice(0, 12)) {
    return res.status(403).json({ error: 'forbidden' });
  }

  const NOMBRE = 'Mauricio';
  const APELLIDO = 'Fischer';
  const DNI = '34837107';

  const usuario = normalizar(NOMBRE, APELLIDO);
  const dni_hash = await bcrypt.hash(DNI, 10);

  try {
    await sql`
      INSERT INTO clientes (nombre, apellido, usuario, dni_hash, rol)
      VALUES (${NOMBRE}, ${APELLIDO}, ${usuario}, ${dni_hash}, 'admin')
      ON CONFLICT (usuario) DO UPDATE SET dni_hash = EXCLUDED.dni_hash, rol = 'admin'
    `;
    return res.status(200).json({ ok: true, usuario, rol: 'admin' });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};
