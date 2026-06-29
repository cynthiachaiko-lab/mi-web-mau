const { sql } = require('../../lib/db');
const { obtenerSesion } = require('../../lib/auth');

module.exports = async (req, res) => {
  const sesion = obtenerSesion(req);
  if (!sesion || sesion.rol !== 'admin') {
    res.status(403).json({ error: 'No autorizado' });
    return;
  }

  if (req.method === 'GET') {
    const { rows } = await sql`SELECT coeficiente_default, descuento_default FROM config_global WHERE id = 1`;
    res.status(200).json(rows[0]);
    return;
  }

  if (req.method === 'PUT') {
    const { coeficiente_default, descuento_default } = req.body || {};
    await sql`
      UPDATE config_global SET
        coeficiente_default = COALESCE(${coeficiente_default}, coeficiente_default),
        descuento_default = COALESCE(${descuento_default}, descuento_default),
        updated_at = now()
      WHERE id = 1
    `;
    res.status(200).json({ ok: true });
    return;
  }

  res.status(405).json({ error: 'Método no permitido' });
};
