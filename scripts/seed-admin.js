// Crea (o actualiza a rol admin) la cuenta de Mauri.
//
// Pasos:
//   1. vercel env pull .env.local        (trae las credenciales de la base)
//   2. npm install dotenv                (si no lo tenés ya)
//   3. Completar el DNI real abajo
//   4. node -r dotenv/config scripts/seed-admin.js
//   5. BORRAR el DNI de este archivo después de correrlo (no dejarlo en el repo)

const { sql } = require('@vercel/postgres');
const bcrypt = require('bcryptjs');

const NOMBRE = 'Mauricio';
const APELLIDO = 'Fischer';
const DNI = 'CAMBIAR_POR_DNI_REAL';

function normalizarUsuario(nombre, apellido) {
  return `${nombre} ${apellido}`
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()
    .replace(/\s+/g, ' ');
}

async function main() {
  if (DNI === 'CAMBIAR_POR_DNI_REAL') {
    console.error('Completá la constante DNI antes de correr este script.');
    process.exit(1);
  }

  const usuario = normalizarUsuario(NOMBRE, APELLIDO);
  const dni_hash = await bcrypt.hash(DNI, 10);

  await sql`
    INSERT INTO clientes (nombre, apellido, usuario, dni_hash, rol)
    VALUES (${NOMBRE}, ${APELLIDO}, ${usuario}, ${dni_hash}, 'admin')
    ON CONFLICT (usuario) DO UPDATE SET dni_hash = EXCLUDED.dni_hash, rol = 'admin'
  `;

  console.log(`Listo. Usuario de Mauri: "${usuario}" (rol admin)`);
}

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
