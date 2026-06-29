const { sql } = require('../lib/db');
const { obtenerSesion } = require('../lib/auth');

module.exports = async (req, res) => {
  const sesion = obtenerSesion(req);
  if (!sesion) {
    res.status(401).json({ error: 'No autenticado' });
    return;
  }

  const [clienteResult, globalResult, overridesGlobalResult, overridesClienteResult] = await Promise.all([
    sql`SELECT nombre, apellido, coeficiente_default, descuento_default, rol, activo FROM clientes WHERE id = ${sesion.id}`,
    sql`SELECT coeficiente_default, descuento_default FROM config_global WHERE id = 1`,
    sql`SELECT rubro_key, coeficiente, descuento FROM overrides_rubro_global`,
    sql`SELECT rubro_key, coeficiente, descuento FROM overrides_rubro_cliente WHERE cliente_id = ${sesion.id}`,
  ]);

  const cliente = clienteResult.rows[0];
  if (!cliente || !cliente.activo) {
    res.status(401).json({ error: 'Cuenta no encontrada o inactiva' });
    return;
  }

  // Si el cliente tiene su propio coeficiente Y descuento configurados, eso pisa
  // el default global entero (no se mezcla parcialmente).
  const clienteDefault = (cliente.coeficiente_default != null && cliente.descuento_default != null)
    ? { coeficiente: Number(cliente.coeficiente_default), descuento: Number(cliente.descuento_default) }
    : null;

  res.status(200).json({
    nombre: `${cliente.nombre} ${cliente.apellido}`,
    rol: cliente.rol,
    clienteDefault,
    global: {
      coeficiente: Number(globalResult.rows[0].coeficiente_default),
      descuento: Number(globalResult.rows[0].descuento_default),
    },
    overridesGlobal: overridesGlobalResult.rows,
    overridesCliente: overridesClienteResult.rows,
  });
};
