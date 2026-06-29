const { sql } = require('../../lib/db');
const { obtenerSesion, normalizarUsuario, hashDni } = require('../../lib/auth');

function requiereAdmin(req, res) {
  const sesion = obtenerSesion(req);
  if (!sesion || sesion.rol !== 'admin') {
    res.status(403).json({ error: 'No autorizado' });
    return null;
  }
  return sesion;
}

module.exports = async (req, res) => {
  const sesion = requiereAdmin(req, res);
  if (!sesion) return;

  if (req.method === 'GET') {
    const { rows } = await sql`
      SELECT id, nombre, apellido, usuario, rol, coeficiente_default, descuento_default, activo, created_at
      FROM clientes
      ORDER BY apellido, nombre
    `;
    res.status(200).json(rows);
    return;
  }

  if (req.method === 'POST') {
    const { nombre, apellido, dni, rol = 'cliente', coeficiente_default = null, descuento_default = null } = req.body || {};
    if (!nombre || !apellido || !dni) {
      res.status(400).json({ error: 'Faltan datos (nombre, apellido, dni)' });
      return;
    }

    const usuario = normalizarUsuario(nombre, apellido);
    const dni_hash = await hashDni(dni);

    try {
      const { rows } = await sql`
        INSERT INTO clientes (nombre, apellido, usuario, dni_hash, rol, coeficiente_default, descuento_default)
        VALUES (${nombre}, ${apellido}, ${usuario}, ${dni_hash}, ${rol}, ${coeficiente_default}, ${descuento_default})
        RETURNING id, nombre, apellido, usuario, rol
      `;
      res.status(201).json(rows[0]);
    } catch (err) {
      if (String(err.message).includes('duplicate key')) {
        res.status(409).json({ error: 'Ya existe un cliente con ese nombre y apellido' });
      } else {
        console.error(err);
        res.status(500).json({ error: 'Error creando cliente' });
      }
    }
    return;
  }

  if (req.method === 'PUT') {
    const { id, coeficiente_default, descuento_default, activo, rol } = req.body || {};
    if (!id) {
      res.status(400).json({ error: 'Falta id' });
      return;
    }
    await sql`
      UPDATE clientes SET
        coeficiente_default = ${coeficiente_default ?? null},
        descuento_default = ${descuento_default ?? null},
        activo = COALESCE(${activo}, activo),
        rol = COALESCE(${rol}, rol)
      WHERE id = ${id}
    `;
    res.status(200).json({ ok: true });
    return;
  }

  if (req.method === 'DELETE') {
    const { id } = req.body || {};
    if (!id) {
      res.status(400).json({ error: 'Falta id' });
      return;
    }
    await sql`DELETE FROM clientes WHERE id = ${id}`;
    res.status(200).json({ ok: true });
    return;
  }

  res.status(405).json({ error: 'Método no permitido' });
};
