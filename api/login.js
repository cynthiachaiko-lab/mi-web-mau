const { sql } = require('../lib/db');
const { normalizarUsuario, verificarDni, generarToken, setSessionCookie } = require('../lib/auth');

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Método no permitido' });
    return;
  }

  const { nombre, apellido, dni } = req.body || {};
  if (!nombre || !apellido || !dni) {
    res.status(400).json({ error: 'Faltan datos' });
    return;
  }

  const usuario = normalizarUsuario(nombre, apellido);

  const { rows } = await sql`
    SELECT id, usuario, dni_hash, rol, activo
    FROM clientes
    WHERE usuario = ${usuario}
    LIMIT 1
  `;

  const cliente = rows[0];
  if (!cliente || !cliente.activo) {
    res.status(401).json({ error: 'Usuario o DNI incorrecto' });
    return;
  }

  const valido = await verificarDni(dni, cliente.dni_hash);
  if (!valido) {
    res.status(401).json({ error: 'Usuario o DNI incorrecto' });
    return;
  }

  const token = generarToken({ id: cliente.id, usuario: cliente.usuario, rol: cliente.rol });
  setSessionCookie(res, token);

  res.status(200).json({ ok: true, rol: cliente.rol });
};
