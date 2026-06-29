// Helpers de autenticación y cálculo de precio para el frontend.
// Incluir con <script src="/js/auth-client.js"></script> antes de usar el catálogo.

async function fixproLogin(nombre, apellido, dni) {
  const res = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nombre, apellido, dni }),
  });
  if (!res.ok) {
    const { error } = await res.json().catch(() => ({}));
    throw new Error(error || 'No se pudo iniciar sesión');
  }
  return res.json(); // { ok, rol }
}

async function fixproLogout() {
  await fetch('/api/logout', { method: 'POST' });
  window.location.href = '/login.html';
}

// Pide la configuración de precio del cliente logueado.
// Si no hay sesión válida, redirige sola a /login.html y devuelve null.
async function fixproObtenerMiConfig() {
  const res = await fetch('/api/mi-config');
  if (res.status === 401) {
    window.location.href = '/login.html';
    return null;
  }
  if (!res.ok) throw new Error('No se pudo obtener la configuración de precios');
  return res.json();
}

// producto: objeto del _RAW con al menos { p: precio_lista, rk: rubro_key }
// miConfig: resultado de fixproObtenerMiConfig()
//
// Orden de resolución (el primero que aplica, gana):
//   1. Override de ESTE cliente para este rubro
//   2. Coeficiente/descuento propio de este cliente (si lo tiene configurado)
//   3. Override GLOBAL para este rubro (ej. BR/RR/ER)
//   4. Default global de la app
function fixproCalcularPrecio(producto, miConfig) {
  const rk = producto.rk;

  const overrideCliente = miConfig.overridesCliente.find(o => o.rubro_key === rk);
  if (overrideCliente) {
    return producto.p * (1 - overrideCliente.descuento) * overrideCliente.coeficiente;
  }

  if (miConfig.clienteDefault) {
    return producto.p * (1 - miConfig.clienteDefault.descuento) * miConfig.clienteDefault.coeficiente;
  }

  const overrideGlobal = miConfig.overridesGlobal.find(o => o.rubro_key === rk);
  if (overrideGlobal) {
    return producto.p * (1 - overrideGlobal.descuento) * overrideGlobal.coeficiente;
  }

  return producto.p * (1 - miConfig.global.descuento) * miConfig.global.coeficiente;
}
