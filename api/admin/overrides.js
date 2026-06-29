const { sql } = require('../../lib/db');
const { obtenerSesion } = require('../../lib/auth');

// body esperado:
// {
//   rubro_key: "br",
//   coeficiente: 1.21,        // requerido en POST, ignorado en DELETE
//   descuento: 0.00,          // requerido en POST, ignorado en DELETE
//   alcance: "global" | "clientes",
//   cliente_ids: [3, 7, 12]   // requerido si alcance === "clientes"
// }

module.exports = async (req, res) => {
  const sesion = obtenerSesion(req);
  if (!sesion || sesion.rol !== 'admin') {
    res.status(403).json({ error: 'No autorizado' });
    return;
  }

  if (req.method !== 'POST' && req.method !== 'DELETE') {
    res.status(405).json({ error: 'Método no permitido' });
    return;
  }

  const { rubro_key, coeficiente, descuento, alcance, cliente_ids } = req.body || {};
  if (!rubro_key || !alcance) {
    res.status(400).json({ error: 'Faltan rubro_key o alcance' });
    return;
  }

  if (req.method === 'DELETE') {
    if (alcance === 'global') {
      await sql`DELETE FROM overrides_rubro_global WHERE rubro_key = ${rubro_key}`;
    } else if (alcance === 'clientes' && Array.isArray(cliente_ids) && cliente_ids.length) {
      await sql`DELETE FROM overrides_rubro_cliente WHERE rubro_key = ${rubro_key} AND cliente_id = ANY(${cliente_ids})`;
    } else {
      res.status(400).json({ error: 'Falta cliente_ids para alcance "clientes"' });
      return;
    }
    res.status(200).json({ ok: true });
    return;
  }

  // POST = crear o actualizar (upsert)
  if (coeficiente == null || descuento == null) {
    res.status(400).json({ error: 'Faltan coeficiente o descuento' });
    return;
  }

  if (alcance === 'global') {
    await sql`
      INSERT INTO overrides_rubro_global (rubro_key, coeficiente, descuento)
      VALUES (${rubro_key}, ${coeficiente}, ${descuento})
      ON CONFLICT (rubro_key) DO UPDATE SET
        coeficiente = EXCLUDED.coeficiente,
        descuento = EXCLUDED.descuento,
        updated_at = now()
    `;
    res.status(200).json({ ok: true, alcance: 'global' });
    return;
  }

  if (alcance === 'clientes' && Array.isArray(cliente_ids) && cliente_ids.length) {
    for (const cliente_id of cliente_ids) {
      await sql`
        INSERT INTO overrides_rubro_cliente (cliente_id, rubro_key, coeficiente, descuento)
        VALUES (${cliente_id}, ${rubro_key}, ${coeficiente}, ${descuento})
        ON CONFLICT (cliente_id, rubro_key) DO UPDATE SET
          coeficiente = EXCLUDED.coeficiente,
          descuento = EXCLUDED.descuento,
          updated_at = now()
      `;
    }
    res.status(200).json({ ok: true, alcance: 'clientes', afectados: cliente_ids.length });
    return;
  }

  res.status(400).json({ error: 'Falta cliente_ids para alcance "clientes"' });
};
