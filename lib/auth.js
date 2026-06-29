const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const cookie = require('cookie');

const JWT_SECRET = process.env.JWT_SECRET;
const COOKIE_NAME = 'fixpro_session';

if (!JWT_SECRET) {
  // No tiramos error duro para no romper el build, pero esto va a fallar en runtime
  // hasta que se configure la variable de entorno JWT_SECRET en Vercel.
  console.warn('[fixpro] Falta la variable de entorno JWT_SECRET');
}

// "Juan Pérez" -> "juan perez" (sin tildes, sin espacios duplicados)
function normalizarUsuario(nombre, apellido) {
  return `${nombre} ${apellido}`
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()
    .replace(/\s+/g, ' ');
}

async function hashDni(dni) {
  return bcrypt.hash(String(dni).trim(), 10);
}

async function verificarDni(dni, hash) {
  return bcrypt.compare(String(dni).trim(), hash);
}

function generarToken(payload) {
  // payload esperado: { id, usuario, rol }
  return jwt.sign(payload, JWT_SECRET, { expiresIn: '30d' });
}

function verificarToken(token) {
  try {
    return jwt.verify(token, JWT_SECRET);
  } catch {
    return null;
  }
}

function setSessionCookie(res, token) {
  res.setHeader('Set-Cookie', cookie.serialize(COOKIE_NAME, token, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * 24 * 30, // 30 días
  }));
}

function clearSessionCookie(res) {
  res.setHeader('Set-Cookie', cookie.serialize(COOKIE_NAME, '', {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  }));
}

function obtenerSesion(req) {
  const cookies = cookie.parse(req.headers.cookie || '');
  const token = cookies[COOKIE_NAME];
  if (!token) return null;
  return verificarToken(token); // null si no es válido o expiró
}

module.exports = {
  normalizarUsuario,
  hashDni,
  verificarDni,
  generarToken,
  verificarToken,
  setSessionCookie,
  clearSessionCookie,
  obtenerSesion,
};
