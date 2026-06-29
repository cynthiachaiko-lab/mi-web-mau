# FixPro — Fase 2: clientes y precios personalizados

## 1. Crear la base de datos
Dashboard de Vercel → proyecto `mi-web-mau` → pestaña **Storage** → **Create Database** → Postgres.
Esto agrega automáticamente las variables de entorno (`POSTGRES_URL`, etc.) al proyecto — no hay que tocarlas a mano.

## 2. Cargar el esquema
Desde el editor SQL del dashboard de Postgres en Vercel (o cualquier cliente Postgres usando la `POSTGRES_URL`),
ejecutar el contenido de `sql/schema.sql` una sola vez.

**Importante:** revisar que los valores `'br'`, `'rr'`, `'er'` en `overrides_rubro_global` coincidan
EXACTO (mayúsculas/minúsculas) con el formato real de tu campo `rk` en el catálogo.

## 3. Dependencias
Agregar a `package.json` (crear uno si no existe en el repo):
```json
{
  "dependencies": {
    "@vercel/postgres": "^0.10.0",
    "bcryptjs": "^2.4.3",
    "jsonwebtoken": "^9.0.2",
    "cookie": "^0.6.0"
  }
}
```

## 4. Variable de entorno para sesiones
Vercel → Settings → Environment Variables:
```
JWT_SECRET = <cadena larga y random, ej. generada con: openssl rand -hex 32>
```

## 5. Crear la cuenta admin de Mauri
Localmente:
```
vercel env pull .env.local
npm install dotenv
```
Editar `scripts/seed-admin.js`, poner el DNI real de Mauri en la constante `DNI`. Después:
```
node -r dotenv/config scripts/seed-admin.js
```
**Borrar el DNI del script apenas termine de correr** — no dejarlo hardcodeado en el repo.

## 6. Archivos a copiar al repo
```
api/login.js
api/logout.js
api/mi-config.js
api/admin/clientes.js
api/admin/config-global.js
api/admin/overrides.js
lib/db.js
lib/auth.js
public/js/auth-client.js   →  servir como /js/auth-client.js
login.html
```

## 7. Integrar con index.html
Sin tocar el array `_RAW`, agregar antes del script que renderiza el catálogo:
```html
<script src="/js/auth-client.js"></script>
<script>
  let miConfig = null;
  fixproObtenerMiConfig().then(cfg => {
    if (!cfg) return; // ya redirigió a /login.html
    miConfig = cfg;
    // disparar acá el render del catálogo que ya tenés, reemplazando
    // el cálculo fijo (precio * 0.50 * 1.21) por:
    //   fixproCalcularPrecio(producto, miConfig)
  });
</script>
```
Agregar también un botón/link de "Cerrar sesión" que llame a `fixproLogout()`.

## Endpoints creados

| Endpoint | Método | Quién | Qué hace |
|---|---|---|---|
| `/api/login` | POST | público | valida nombre+apellido+DNI, crea sesión |
| `/api/logout` | POST | cualquiera | cierra sesión |
| `/api/mi-config` | GET | logueado | coeficiente/descuento/overrides del cliente actual |
| `/api/admin/clientes` | GET/POST/PUT/DELETE | admin | alta, baja, edición de clientes |
| `/api/admin/config-global` | GET/PUT | admin | coeficiente/descuento default de toda la app |
| `/api/admin/overrides` | POST/DELETE | admin | excepciones por rubro — globales o para clientes específicos |

`POST /api/admin/overrides` body ejemplo:
```json
{
  "rubro_key": "filtros",
  "coeficiente": 1.15,
  "descuento": 0.40,
  "alcance": "clientes",
  "cliente_ids": [3, 7]
}
```
Con `"alcance": "global"` se aplica a todos los clientes que no tengan su propio override para ese rubro.

## Qué falta para la próxima fase
- Pantalla de admin con UI (hoy los endpoints de `/api/admin/*` se probarían con curl/Postman).
- Botón visible de "cerrar sesión" en `index.html`.
