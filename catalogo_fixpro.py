"""
catalogo_fixpro.py
FixPro — Generador de catálogo PDF para clientes/Mauri (uso recurrente)
Cynthia para Mauri | Aristóbulo del Valle, Misiones

Genera:
  - Catalogo_FixPro_General.pdf  (todas las categorías chicas + "Varios")
  - Catalogo_FixPro_<RUBRO>.pdf  (una por cada rubro grande, ver UMBRAL_RUBRO_GRANDE)

Sin precios. Sin mención al proveedor. Marca de fábrica (NGK, Bosch, etc.) sí.
Foto real si existe en CARPETA_FOTOS, imagen genérica si no.

Doble clic en generar_catalogo.bat para correrlo.
"""

import os
import re
import struct
import base64
import math
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage
from PIL import ImageOps

# ───────────────────────── CONFIGURACIÓN ─────────────────────────────────────

CARPETA_DBF    = r"C:\TRESSOLSW"
CARPETA_FOTOS  = r"C:\TRESSOLSW\FOTOS"
CARPETA_SALIDA = r"C:\TRESSOLSW\fixpro\catalogo"

UMBRAL_RUBRO_GRANDE = 1000   # rubros con más productos que esto van en PDF separado
PRODUCTOS_POR_PAGINA = 9     # grilla 3x3 (categorías con fotos)
COLS, ROWS = 3, 3
PRODUCTOS_POR_PAGINA_LISTA = 80   # 4 columnas x 20 filas (categorías sin fotos, modo lista)
LISTA_COLS, LISTA_FILAS = 4, 20
UMBRAL_COBERTURA_FOTO = 0.05  # si una categoría tiene menos de 5% de fotos, se muestra en modo lista
FOTO_MAX_PX = 320            # tamaño máximo de cada foto reducida (ancho/alto)
FOTO_CALIDAD = 60            # calidad JPEG de las fotos reducidas (1-95)

# ───────────────────────── LECTOR DE DBF (idéntico a actualizar_fixpro.py) ──

def leer_dbf(ruta, encoding='latin-1'):
    """Lee un archivo .dbf de Visual FoxPro y devuelve lista de dicts."""
    registros = []
    with open(ruta, 'rb') as f:
        header = f.read(32)
        if len(header) < 32:
            raise ValueError(f"Archivo DBF inválido: {ruta}")

        num_records = struct.unpack('<I', header[4:8])[0]
        header_size = struct.unpack('<H', header[8:10])[0]
        record_size = struct.unpack('<H', header[10:12])[0]

        campos = []
        f.seek(32)
        while True:
            field_data = f.read(32)
            if not field_data or field_data[0] == 0x0D:
                break
            nombre = field_data[0:11].split(b'\x00')[0].decode('latin-1').strip()
            tipo   = chr(field_data[11])
            largo  = field_data[16]
            if nombre:
                campos.append((nombre, tipo, largo))

        f.seek(header_size)
        for _ in range(num_records):
            raw = f.read(record_size)
            if not raw:
                break
            if raw[0:1] == b'*':
                continue

            registro = {}
            pos = 1
            for nombre, tipo, largo in campos:
                valor_raw = raw[pos:pos + largo]
                if tipo == 'N':
                    try:
                        txt = valor_raw.decode('latin-1').strip()
                        valor = float(txt) if txt else 0
                    except Exception:
                        valor = 0
                elif tipo == '0':
                    valor = None
                else:
                    valor = valor_raw.decode(encoding, errors='replace').strip()
                registro[nombre] = valor
                pos += largo
            registros.append(registro)

    return registros


def sanitizar_codigo(codigo):
    """Igual a la lógica de vincular_fotos.py / sanitizeCode() en index.html."""
    return re.sub(r'[\\/:*?"<>|]', '_', codigo)

# ───────────────────────── LOGO (incrustado en base64, no depende de archivos externos) ──

LOGO_B64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAUDBAQEAwUEBAQFBQUGBwwIBwcHBw8LCwkMEQ8SEhEPERETFhwXExQaFRERGCEYGh0dHx8fExciJCIeJBweHx7/2wBDAQUFBQcGBw4ICA4eFBEUHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh7/wAARCAFNAfQDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD7KooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAoopGIVSzEADkk9qAForEuvFOiQOUF2J3HBEKlv16frSR+J9NYFmWeNAMlnUAAep5p2Yro3KKr6deWuo2Fvf2UyT2txGssMqfddGGQR7EVYpDCisrxB4i0XQFiOr38dr5xIjDAktjrwKyf8AhYvgz/oOQ/8Aft/8K5amNw1KXLOok/No6qWBxNWPNTpya7pNnV0Vyn/CxfBn/Qch/wC/b/4Vf0TxZ4e1u8NppeordTBS5VEbgepJGBRDHYapJRhUi2+zQ54DFU4uU6Ukl1aZuUUUV1HIFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQBDe3MNnayXVw4SKNSzMewryvX9d1DxBdMm54bEHCQKcZ929TXRfEO8muLn+y4jiGCITze7MSEH4YJ/EVz2lWZGOKuK6kSfQfplgAANteTfGDxPq3i/xHF8I/h9++vbp/L1W6Q/JEg+8hYdFA5c/wDAe5rsPjt4k17wx4WsrHwvYzT6zrl19gtHjGWiYjOVH949B6cntXW/s8/Cm1+G3hlpLwpc+ItQAfUbrO7B6iJT/dBPJ7nJ9Kpuwkrnd+DNFHhzwlpOgLcN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PgtYj/X67ct/uQKv8ya4qnFPEFT+Hh1H1kjtp8NZBT/iYly9Is8ti+EPwZ07B1HxlrGqMOq2wVQfyQ/zrQttJ+BukYNl4Hu9VkXo97OxB+oLEfpXqtt8IPDEf+vuNRn9jKFB/IVsWfw48G2wGNFjmI7zSM/8zivPqY7ibE/FUjD7zup4PhjDbQnP7l/wTyez8e2Gkr5fhnwVoGkn+Ex24L/oBUj+I/if4gJ+yDUQjcAWtt5a/wDfWP617hYaHo1hj7FpdnbkdDHCoP54rQHAxXHLJ8fiHfE4uT9NDrWd5fh9MLg4rzlr/X3nglr8NPG+ryCXVZ0hz1a6uTI35DNdRpHwZ02La2qarcXDd0hQRr+Zya9UorWjw1gKb5pRcn/ed/8AgGNfinMai5YSUF2irf8ABOf0Twb4Z0fDWWkW4kHSSRfMf82zW+AB0ApaK9ulQp0Y8tOKS8lY8KtXqVpc1STb83cKKKK1MgooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooA//9k="

def obtener_logo():
    data = base64.b64decode(LOGO_B64)
    return ImageReader(BytesIO(data)), (1280, 853)  # tamaño original aproximado, para aspect ratio

# ───────────────────────── ÍCONO GENÉRICO "SIN FOTO" (incrustado en base64) ──

ICONO_GENERICO_B64 = "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"

def obtener_icono_generico():
    data = base64.b64decode(ICONO_GENERICO_B64)
    return ImageReader(BytesIO(data))

# ───────────────────────── PALETA FIXPRO ─────────────────────────────────────

NAVY        = colors.Color(0/255, 96/255, 170/255)
NAVY_DARK   = colors.Color(1/255, 53/255, 128/255)
ORANGE      = colors.Color(245/255, 102/255, 0/255)
GRAY_LIGHT  = colors.Color(0.92, 0.92, 0.92)
GRAY_TEXT   = colors.Color(0.32, 0.32, 0.32)
GRAY_MED    = colors.Color(0.55, 0.55, 0.55)
WHITE       = colors.white

PALETA_INDICE = [
    NAVY, ORANGE,
    colors.Color(0.75, 0.20, 0.20),
    colors.Color(0.25, 0.55, 0.35),
    colors.Color(0.45, 0.35, 0.65),
    colors.Color(0.85, 0.60, 0.10),
    colors.Color(0.20, 0.50, 0.60),
    colors.Color(0.55, 0.35, 0.20),
]

W, H = A4

# ───────────────────────── CARGA Y PREPARACIÓN DE DATOS ─────────────────────

def construir_indice_fotos(carpeta):
    indice = {}
    if not os.path.isdir(carpeta):
        print(f"      AVISO: no se encontró la carpeta de fotos {carpeta}")
        return indice
    for nombre in os.listdir(carpeta):
        base, ext = os.path.splitext(nombre)
        if ext.lower() not in ('.jpg', '.jpeg', '.png'):
            continue
        clave = sanitizar_codigo(base.strip()).upper()
        indice[clave] = os.path.join(carpeta, nombre)
    return indice


def cargar_datos():
    print("[1/4] Leyendo categorías y marcas...")
    rubros_raw = leer_dbf(os.path.join(CARPETA_DBF, "RUBROS.DBF"))
    mapa_rubros = {r['LI'].strip(): r['TITULO'].strip() for r in rubros_raw}

    marcas_raw = leer_dbf(os.path.join(CARPETA_DBF, "marcas.dbf"))
    mapa_marcas = {m['MARCA'].strip(): m['NOMBRE'].strip() for m in marcas_raw}
    print(f"      {len(mapa_rubros)} categorías, {len(mapa_marcas)} marcas")

    print("[2/4] Leyendo arti.dbf...")
    articulos = leer_dbf(os.path.join(CARPETA_DBF, "arti.dbf"))
    print(f"      {len(articulos)} filas leídas")

    print("[3/4] Indexando fotos en", CARPETA_FOTOS)
    indice_fotos = construir_indice_fotos(CARPETA_FOTOS)
    print(f"      {len(indice_fotos)} fotos encontradas")

    print("[4/4] Procesando productos...")
    productos = []
    sin_precio = 0
    con_foto = 0

    for art in articulos:
        codigo = art.get('CODIGO', '').strip()
        if not codigo:
            continue
        precio_lista = art.get('PRECIO', 0)
        if not precio_lista or precio_lista <= 0:
            sin_precio += 1
            continue

        descrip = art.get('DESCRIP', '').strip()
        rubro_cod = art.get('RUBRO', '').strip()
        marca_cod = art.get('MARCA', '').strip()

        rubro_texto = mapa_rubros.get(rubro_cod, rubro_cod) if rubro_cod else ''
        marca_texto = mapa_marcas.get(marca_cod, marca_cod) if marca_cod else ''

        clave_foto = sanitizar_codigo(codigo).upper()
        ruta_foto = indice_fotos.get(clave_foto)
        if ruta_foto:
            con_foto += 1

        productos.append({
            'codigo': codigo,
            'descrip': descrip if descrip else codigo,
            'rubro': rubro_texto,
            'marca': marca_texto,
            'foto': ruta_foto,
        })

    print(f"      ✓ {len(productos)} productos válidos")
    print(f"      ✓ {con_foto} con foto ({con_foto/len(productos)*100:.1f}%)")
    print(f"      • {sin_precio} sin precio (ignorados)")
    return productos


def agrupar_productos(productos):
    grupos = {}
    varios = []
    for p in productos:
        if p['rubro']:
            grupos.setdefault(p['rubro'], []).append(p)
        else:
            varios.append(p)
    return grupos, varios


def dividir_varios(varios):
    varios_ordenados = sorted(varios, key=lambda p: p['descrip'].upper())
    secciones = {'Varios / Sin categoría (A-F)': [],
                 'Varios / Sin categoría (G-M)': [],
                 'Varios / Sin categoría (N-Z)': []}
    for p in varios_ordenados:
        letra = p['descrip'][0:1].upper() if p['descrip'] else '?'
        if letra <= 'F':
            secciones['Varios / Sin categoría (A-F)'].append(p)
        elif letra <= 'M':
            secciones['Varios / Sin categoría (G-M)'].append(p)
        else:
            secciones['Varios / Sin categoría (N-Z)'].append(p)
    return secciones


def separar_grandes(grupos, umbral):
    grandes = {k: v for k, v in grupos.items() if len(v) >= umbral}
    normales = {k: v for k, v in grupos.items() if len(v) < umbral}
    return grandes, normales


def es_modo_lista(productos):
    """True si la categoría tiene muy poca (o ninguna) cobertura de fotos:
    en ese caso conviene mostrarla como lista compacta de códigos, no grilla con fotos."""
    if not productos:
        return False
    con_foto = sum(1 for p in productos if p['foto'])
    return (con_foto / len(productos)) < UMBRAL_COBERTURA_FOTO


def productos_por_pagina_de(modo_lista):
    return PRODUCTOS_POR_PAGINA_LISTA if modo_lista else PRODUCTOS_POR_PAGINA


def contar_paginas_necesarias(cantidad_productos, modo_lista=False):
    por_pagina = productos_por_pagina_de(modo_lista)
    return max(1, math.ceil(cantidad_productos / por_pagina))

# ───────────────────────── DIBUJO: FOTOS ─────────────────────────────────────

_cache_fotos = {}

def cargar_foto_reducida(ruta):
    if ruta in _cache_fotos:
        return _cache_fotos[ruta]
    try:
        img = PILImage.open(ruta)
        img = ImageOps.exif_transpose(img)  # corrige fotos que vienen rotadas (común en fotos de celular)
        img = img.convert('RGB')
        img.thumbnail((FOTO_MAX_PX, FOTO_MAX_PX))
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=FOTO_CALIDAD)
        buf.seek(0)
        resultado = (ImageReader(buf), img.size)
    except Exception:
        resultado = (None, None)
    _cache_fotos[ruta] = resultado
    return resultado


def dibujar_foto_o_generica(c, prod, box_x, box_y, box_w, box_h, icono_generico):
    reader, size = (None, None)
    if prod['foto']:
        reader, size = cargar_foto_reducida(prod['foto'])

    c.setFillColor(GRAY_LIGHT)
    c.rect(box_x, box_y, box_w, box_h, fill=1, stroke=0)

    if reader:
        img_w, img_h = size
        escala = min(box_w / img_w, box_h / img_h)
        dw, dh = img_w * escala, img_h * escala
        dx = box_x + (box_w - dw) / 2
        dy = box_y + (box_h - dh) / 2
        c.drawImage(reader, dx, dy, width=dw, height=dh, mask='auto')
    else:
        # ícono genérico real, centrado, a ~55% de la altura del recuadro
        icono_h = box_h * 0.55
        icono_w = icono_h  # el ícono es cuadrado
        ix = box_x + (box_w - icono_w) / 2
        iy = box_y + (box_h - icono_h) / 2 + 1*mm
        c.drawImage(icono_generico, ix, iy, width=icono_w, height=icono_h, mask='auto')

# ───────────────────────── DIBUJO: TEXTO CON WRAP ────────────────────────────

def envolver_texto(c, texto, max_w, font, size, max_lineas=2):
    c.setFont(font, size)
    palabras = texto.split()
    lineas = []
    actual = ""
    for palabra in palabras:
        prueba = (actual + " " + palabra).strip()
        if c.stringWidth(prueba, font, size) <= max_w:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
        if len(lineas) >= max_lineas:
            break
    if actual and len(lineas) < max_lineas:
        lineas.append(actual)
    if len(lineas) == max_lineas and c.stringWidth(" ".join(palabras), font, size) > max_w:
        ultima = lineas[-1]
        while c.stringWidth(ultima + "...", font, size) > max_w and len(ultima) > 3:
            ultima = ultima[:-1]
        lineas[-1] = ultima + "..."
    return lineas


def envolver_texto_completo(c, texto, max_w, font, tamanos_y_maxlineas):
    """tamanos_y_maxlineas: lista de (tamano_fuente, maximo_de_lineas_que_entran_en_el_espacio),
    ordenada de fuente más grande a más chica. Devuelve el primer ajuste donde el texto
    entra completo (sin '...'); si ninguno alcanza, usa el último (más chico) y ahí sí corta."""
    for size, max_lineas in tamanos_y_maxlineas:
        c.setFont(font, size)
        palabras = texto.split()
        lineas = []
        actual = ""
        cabe = True
        for palabra in palabras:
            prueba = (actual + " " + palabra).strip()
            if c.stringWidth(prueba, font, size) <= max_w:
                actual = prueba
            else:
                if actual:
                    lineas.append(actual)
                actual = palabra
                if len(lineas) > max_lineas:
                    cabe = False
                    break
        if cabe and actual:
            lineas.append(actual)
        if cabe and len(lineas) <= max_lineas:
            return lineas, size
    # último recurso: el ajuste más chico de la lista, cortado con "..."
    size_final, max_lineas_final = tamanos_y_maxlineas[-1]
    return envolver_texto(c, texto, max_w, font, size_final, max_lineas_final), size_final

# ───────────────────────── DIBUJO: PIE DE PÁGINA (con número de página) ─────

def dibujar_pie_pagina(c, numero_pagina):
    c.setFillColor(NAVY)
    c.rect(0, 0, W, 7*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(10*mm, 2.3*mm, "FixPro Repuestos · Soluciones rápidas y confiables")
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(W - 10*mm, 2.3*mm, str(numero_pagina))

# ───────────────────────── DIBUJO: PORTADA ───────────────────────────────────

def dibujar_portada(c, logo_reader, logo_ratio, numero_pagina):
    c.setFillColor(WHITE)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    logo_w = 120 * mm
    logo_h = logo_w * logo_ratio
    c.drawImage(logo_reader, (W - logo_w)/2, H - 95*mm, width=logo_w, height=logo_h, mask='auto')

    c.setFont("Helvetica-Bold", 32)
    c.setFillColor(NAVY_DARK)
    c.drawCentredString(W/2, H - 115*mm, "CATÁLOGO DE REPUESTOS")

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(ORANGE)
    c.drawCentredString(W/2, H - 126*mm, "Electromecánica Automotriz")

    c.setFont("Helvetica", 11)
    c.setFillColor(GRAY_TEXT)
    c.drawCentredString(W/2, H - 134*mm, "Aristóbulo del Valle, Misiones")
    c.drawCentredString(W/2, H - 141*mm, "Mostrá el código de cada producto para hacer tu pedido")

    c.setFont("Helvetica", 9)
    c.setFillColor(GRAY_TEXT)
    c.drawCentredString(W/2, 25*mm, f"Edición {datetime.now().year}")
    dibujar_pie_pagina(c, numero_pagina)
    c.showPage()

# ───────────────────────── DIBUJO: GRILLA DE PRODUCTOS ───────────────────────

def dibujar_pagina_grilla(c, productos_pagina, titulo_categoria, logo_reader, logo_ratio, icono_generico, numero_pagina):
    MARGIN = 10*mm
    GAP = 6*mm
    header_h = 18*mm
    card_w = (W - 2*MARGIN - (COLS-1)*GAP) / COLS
    card_h = (H - 2*MARGIN - header_h - (ROWS-1)*GAP) / ROWS

    c.setFillColor(NAVY)
    c.rect(0, H - header_h, W, header_h, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(WHITE)
    c.drawString(MARGIN, H - 12*mm, titulo_categoria[:48])
    logo_w3 = 28*mm
    logo_h3 = logo_w3 * logo_ratio
    c.drawImage(logo_reader, W - logo_w3 - 10*mm, H - 16*mm, width=logo_w3, height=logo_h3, mask='auto')

    start_y = H - header_h - MARGIN

    for i, prod in enumerate(productos_pagina):
        col = i % COLS
        row = i // COLS
        x = MARGIN + col * (card_w + GAP)
        y = start_y - card_h - row * (card_h + GAP)

        c.setFillColor(WHITE)
        c.setStrokeColor(GRAY_LIGHT)
        c.setLineWidth(1)
        c.roundRect(x, y, card_w, card_h, 3*mm, fill=1, stroke=1)

        # foto más chica que antes, para dejar más lugar a la especificación completa
        photo_h = card_h * 0.36
        photo_top = y + card_h - 5*mm
        dibujar_foto_o_generica(c, prod, x + 4*mm, photo_top - photo_h, card_w - 8*mm, photo_h, icono_generico)

        text_top = photo_top - photo_h - 6*mm
        text_w = card_w - 8*mm

        # código en badge naranja (autoajuste si el código es muy largo)
        codigo_lineas, codigo_size = envolver_texto_completo(c, prod['codigo'], text_w - 4*mm, "Helvetica-Bold", [(12,1), (10,1), (9,1)])
        c.setFillColor(ORANGE)
        c.roundRect(x + 4*mm, text_top - 7*mm, text_w, 8*mm, 1.8*mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", codigo_size)
        c.drawCentredString(x + card_w/2, text_top - 4.7*mm, codigo_lineas[0])

        # nombre/descripción COMPLETA: el tamaño y la cantidad de líneas se calculan
        # según el espacio real disponible en la tarjeta, reservando lugar para "Marca:"
        # así el texto NUNCA se desborda, sea cual sea el largo de la descripción.
        nombre_start = text_top - 16*mm
        reservado_marca = 7*mm if prod['marca'] else 2*mm
        espacio_disponible = nombre_start - y - reservado_marca
        opciones = []
        for size in (11, 10, 9, 8, 7):
            salto_size = size * 0.42 * mm + 2.2*mm
            max_lineas_size = max(1, int(espacio_disponible / salto_size))
            opciones.append((size, max_lineas_size))

        nombre_lineas, nombre_size = envolver_texto_completo(c, prod['descrip'], text_w, "Helvetica-Bold", opciones)
        c.setFillColor(NAVY_DARK)
        c.setFont("Helvetica-Bold", nombre_size)
        salto = nombre_size * 0.42 * mm + 2.2*mm
        ly = nombre_start
        for linea in nombre_lineas:
            c.drawString(x + 4*mm, ly, linea)
            ly -= salto

        if prod['marca']:
            c.setFillColor(GRAY_TEXT)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(x + 4*mm, max(ly - 1.5*mm, y + 2*mm), f"Marca: {prod['marca']}")

    dibujar_pie_pagina(c, numero_pagina)
    c.showPage()


# ───────────────────────── DIBUJO: PÁGINA EN MODO LISTA (sin fotos) ──────────

def dibujar_pagina_lista(c, productos_pagina, titulo_categoria, logo_reader, logo_ratio, numero_pagina):
    MARGIN = 10*mm
    GAP = 5*mm
    header_h = 18*mm
    subtitulo_h = 8*mm
    footer_h = 7*mm

    c.setFillColor(NAVY)
    c.rect(0, H - header_h, W, header_h, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(WHITE)
    c.drawString(MARGIN, H - 12*mm, titulo_categoria[:48])
    logo_w3 = 28*mm
    logo_h3 = logo_w3 * logo_ratio
    c.drawImage(logo_reader, W - logo_w3 - 10*mm, H - 16*mm, width=logo_w3, height=logo_h3, mask='auto')

    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(GRAY_MED)
    c.drawString(MARGIN, H - header_h - 5*mm, "Sin foto disponible para esta categoría — se pide por código")

    area_y_top = H - header_h - subtitulo_h
    area_y_bottom = footer_h + MARGIN
    cell_w = (W - 2*MARGIN - (LISTA_COLS-1)*GAP) / LISTA_COLS
    cell_h = (area_y_top - area_y_bottom) / LISTA_FILAS

    for i, prod in enumerate(productos_pagina):
        col = i % LISTA_COLS
        row = i // LISTA_COLS
        x = MARGIN + col * (cell_w + GAP)
        y = area_y_top - (row + 1) * cell_h

        c.setStrokeColor(GRAY_LIGHT)
        c.setLineWidth(0.7)
        c.line(x, y, x + cell_w, y)

        c.setFillColor(NAVY_DARK)
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(x, y + cell_h - 5.5*mm, prod['codigo'][:20])

        if prod['marca']:
            c.setFillColor(GRAY_TEXT)
            c.setFont("Helvetica", 8)
            c.drawString(x, y + 1.5*mm, prod['marca'][:26])

    dibujar_pie_pagina(c, numero_pagina)
    c.showPage()


def dibujar_pagina_segun_modo(c, productos_pagina, titulo_categoria, logo_reader, logo_ratio, icono_generico, modo_lista, numero_pagina):
    if modo_lista:
        dibujar_pagina_lista(c, productos_pagina, titulo_categoria, logo_reader, logo_ratio, numero_pagina)
    else:
        dibujar_pagina_grilla(c, productos_pagina, titulo_categoria, logo_reader, logo_ratio, icono_generico, numero_pagina)

# ───────────────────────── DIBUJO: PÁGINA LISTA EN FLUJO COMPARTIDO ──────────
# Varias categorías chicas en modo lista comparten la misma página, en vez de
# forzar salto de página por cada una (evita páginas casi en blanco).

HEADER_H_LISTA_FLUJO = 16*mm
SUBTITULO_H_LISTA_FLUJO = 8*mm


def dibujar_header_pagina_lista(c, logo_reader, logo_ratio):
    MARGIN = 10*mm
    c.setFillColor(NAVY)
    c.rect(0, H - HEADER_H_LISTA_FLUJO, W, HEADER_H_LISTA_FLUJO, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(WHITE)
    c.drawString(MARGIN, H - 11*mm, "CATÁLOGO POR CÓDIGO")
    logo_w3 = 26*mm
    logo_h3 = logo_w3 * logo_ratio
    c.drawImage(logo_reader, W - logo_w3 - 10*mm, H - 14.5*mm, width=logo_w3, height=logo_h3, mask='auto')
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(GRAY_MED)
    c.drawString(MARGIN, H - HEADER_H_LISTA_FLUJO - 5*mm, "Sin foto disponible para estas categorías — se piden por código")


def planificar_documento(secciones_ordenadas, modos):
    """Arma la secuencia completa de páginas: categorías en modo lista comparten
    página en flujo continuo; cada categoría en modo grilla sigue en sus propias
    páginas. Devuelve (paginas, pagina_inicio):
      - paginas: lista de páginas, cada una {'modo':'lista','eventos':[...]} o
        {'modo':'grilla','titulo':...,'productos':[...]}
      - pagina_inicio: dict titulo -> índice (0-based) de la página donde arranca."""
    paginas = []
    pagina_inicio = {}
    pagina_lista_actual = None
    restante = 0

    def cerrar_lista_actual():
        nonlocal pagina_lista_actual, restante
        if pagina_lista_actual is not None:
            paginas.append({'modo': 'lista', 'eventos': pagina_lista_actual})
            pagina_lista_actual = None
            restante = 0

    for titulo, productos in secciones_ordenadas:
        if not modos[titulo]:
            cerrar_lista_actual()
            pagina_inicio[titulo] = len(paginas)
            for k in range(0, len(productos), PRODUCTOS_POR_PAGINA):
                paginas.append({'modo': 'grilla', 'titulo': titulo,
                                 'productos': productos[k:k + PRODUCTOS_POR_PAGINA]})
            continue

        filas = [productos[i:i + LISTA_COLS] for i in range(0, len(productos), LISTA_COLS)]
        if pagina_lista_actual is None:
            pagina_lista_actual = []
            restante = LISTA_FILAS

        es_inicio = True
        i = 0
        while i < len(filas):
            if restante <= 0:
                cerrar_lista_actual()
                pagina_lista_actual = []
                restante = LISTA_FILAS
            pagina_lista_actual.append(('banda', titulo, es_inicio))
            if es_inicio:
                pagina_inicio[titulo] = len(paginas)
            es_inicio = False
            restante -= 1
            while i < len(filas) and restante > 0:
                pagina_lista_actual.append(('fila', filas[i]))
                i += 1
                restante -= 1
            if i < len(filas):
                cerrar_lista_actual()
                pagina_lista_actual = []
                restante = LISTA_FILAS

    cerrar_lista_actual()
    return paginas, pagina_inicio


def dibujar_pagina_lista_flujo(c, eventos, logo_reader, logo_ratio, numero_pagina):
    MARGIN = 10*mm
    GAP = 5*mm
    dibujar_header_pagina_lista(c, logo_reader, logo_ratio)

    content_top = H - HEADER_H_LISTA_FLUJO - SUBTITULO_H_LISTA_FLUJO
    content_bottom = 7*mm + MARGIN
    slot_h = (content_top - content_bottom) / LISTA_FILAS
    cell_w = (W - 2*MARGIN - (LISTA_COLS-1)*GAP) / LISTA_COLS

    y = content_top
    for evento in eventos:
        y -= slot_h
        if evento[0] == 'banda':
            _, titulo, es_inicio = evento
            texto = titulo if es_inicio else f"{titulo} (continuación)"
            c.setFillColor(ORANGE)
            c.roundRect(MARGIN, y + slot_h*0.12, W - 2*MARGIN, slot_h*0.76, 1.3*mm, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 10.5)
            c.drawString(MARGIN + 3*mm, y + slot_h*0.35, texto[:70])
        else:
            _, productos_fila = evento
            for col, prod in enumerate(productos_fila):
                x = MARGIN + col * (cell_w + GAP)
                c.setStrokeColor(GRAY_LIGHT)
                c.setLineWidth(0.7)
                c.line(x, y, x + cell_w, y)
                c.setFillColor(NAVY_DARK)
                c.setFont("Helvetica-Bold", 10.5)
                c.drawString(x, y + slot_h*0.55, prod['codigo'][:20])
                if prod['marca']:
                    c.setFillColor(GRAY_TEXT)
                    c.setFont("Helvetica", 8)
                    c.drawString(x, y + slot_h*0.12, prod['marca'][:26])

    dibujar_pie_pagina(c, numero_pagina)
    c.showPage()

# ───────────────────────── DIBUJO: ÍNDICE (clickeable) ───────────────────────

FILAS_POR_PAGINA_INDICE = 14

def calcular_paginas_indice(cantidad_entradas):
    if cantidad_entradas == 0:
        return 1
    return (cantidad_entradas + FILAS_POR_PAGINA_INDICE - 1) // FILAS_POR_PAGINA_INDICE


def dibujar_indice(c, entradas, logo_reader, logo_ratio, primera_pagina_numero):
    """entradas: lista de (titulo, pagina_final_real, color, clave_marcador).
    Dibuja el índice y deja cada fila clickeable (salta a la página de esa categoría)."""
    total = len(entradas)
    paginas = calcular_paginas_indice(total)
    idx = 0
    for pagina in range(paginas):
        c.setFillColor(NAVY)
        c.rect(0, H - 22*mm, W, 22*mm, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(WHITE)
        titulo_pag = "ÍNDICE" if paginas == 1 else f"ÍNDICE ({pagina+1}/{paginas})"
        c.drawString(15*mm, H - 14*mm, titulo_pag)
        logo_w2 = 36*mm
        logo_h2 = logo_w2 * logo_ratio
        c.drawImage(logo_reader, W - logo_w2 - 12*mm, H - 19*mm, width=logo_w2, height=logo_h2, mask='auto')

        y = H - 40*mm
        for _ in range(FILAS_POR_PAGINA_INDICE):
            if idx >= total:
                break
            titulo, pagina_final, color, clave = entradas[idx]
            c.setFillColor(color)
            c.roundRect(15*mm, y - 6*mm, 130*mm, 8*mm, 1.5*mm, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(18*mm, y - 3.5*mm, titulo[:48])
            c.setFillColor(NAVY_DARK)
            c.setFont("Helvetica-Bold", 10)
            c.drawRightString(W - 15*mm, y - 3.5*mm, f"Pág. {pagina_final}")

            # área clickeable: toda la fila (incluso fuera de la barra de color)
            c.linkRect("", clave, (14*mm, y - 7*mm, W - 14*mm, y + 2*mm), relative=0, thickness=0)

            y -= 11*mm
            idx += 1

        c.setFont("Helvetica-Oblique", 9)
        c.setFillColor(GRAY_TEXT)
        c.drawString(15*mm, 24*mm, "Tocá cualquier categoría para ir directo a esa página.")
        dibujar_pie_pagina(c, primera_pagina_numero + pagina)
        c.showPage()
    return paginas

# ───────────────────────── ARMADO DE PDFs ────────────────────────────────────

def generar_pdf_simple(ruta_salida, titulo_pdf, productos, logo_reader, logo_ratio, icono_generico):
    """Para los rubros 'grandes' separados: portada chica + grilla o lista, sin índice."""
    productos = sorted(productos, key=lambda p: (p['descrip'].upper(), p['codigo'].upper()))
    modo_lista = es_modo_lista(productos)
    por_pagina = productos_por_pagina_de(modo_lista)
    c = canvas.Canvas(ruta_salida, pagesize=A4)
    dibujar_portada(c, logo_reader, logo_ratio, 1)
    numero_pagina = 2
    for i in range(0, len(productos), por_pagina):
        bloque = productos[i:i + por_pagina]
        dibujar_pagina_segun_modo(c, bloque, titulo_pdf, logo_reader, logo_ratio, icono_generico, modo_lista, numero_pagina)
        numero_pagina += 1
    c.save()


def generar_pdf_general(ruta_salida, grupos_normales, secciones_varios, logo_reader, logo_ratio, icono_generico):
    # Orden de las secciones: alfabético por nombre de categoría
    secciones_ordenadas = list(grupos_normales.items())
    for nombre_varios in ['Varios / Sin categoría (A-F)', 'Varios / Sin categoría (G-M)', 'Varios / Sin categoría (N-Z)']:
        secciones_ordenadas.append((nombre_varios, secciones_varios[nombre_varios]))
    secciones_ordenadas.sort(key=lambda kv: kv[0].upper())

    # Dentro de cada categoría, productos también en orden alfabético (por descripción, código como desempate)
    secciones_ordenadas = [
        (titulo, sorted(productos, key=lambda p: (p['descrip'].upper(), p['codigo'].upper())))
        for titulo, productos in secciones_ordenadas
    ]

    modos = {titulo: es_modo_lista(productos) for titulo, productos in secciones_ordenadas}

    # Las categorías chicas en modo lista comparten página (flujo continuo);
    # las de modo grilla siguen cada una en sus propias páginas.
    paginas, pagina_inicio = planificar_documento(secciones_ordenadas, modos)

    cantidad_entradas = len(secciones_ordenadas)
    paginas_indice = calcular_paginas_indice(cantidad_entradas)
    offset = 1 + paginas_indice  # 1 página de portada + N de índice

    clave_de = {}
    entradas_indice = []
    for i, (titulo, productos) in enumerate(secciones_ordenadas):
        clave = f"sec_{i}"
        clave_de[titulo] = clave
        color = PALETA_INDICE[i % len(PALETA_INDICE)]
        entradas_indice.append((titulo, offset + 1 + pagina_inicio[titulo], color, clave))

    primeras_por_pagina = {}
    for titulo, idx in pagina_inicio.items():
        primeras_por_pagina.setdefault(idx, []).append(titulo)

    # Dibujado lineal: portada -> índice (clickeable) -> contenido (con marcadores)
    c = canvas.Canvas(ruta_salida, pagesize=A4)
    dibujar_portada(c, logo_reader, logo_ratio, 1)
    dibujar_indice(c, entradas_indice, logo_reader, logo_ratio, 2)

    numero_pagina = offset + 1
    for idx, pagina in enumerate(paginas):
        for titulo in primeras_por_pagina.get(idx, []):
            clave = clave_de[titulo]
            c.bookmarkPage(clave)            # destino del link del índice
            c.addOutlineEntry(titulo, clave, level=0)  # también en el panel de marcadores del lector PDF
        if pagina['modo'] == 'grilla':
            dibujar_pagina_grilla(c, pagina['productos'], pagina['titulo'], logo_reader, logo_ratio, icono_generico, numero_pagina)
        else:
            dibujar_pagina_lista_flujo(c, pagina['eventos'], logo_reader, logo_ratio, numero_pagina)
        numero_pagina += 1

    c.save()

# ───────────────────────── MAIN ──────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  FixPro — Generador de catálogo PDF (Tressols)")
    print("=" * 60)
    print()

    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    productos = cargar_datos()
    grupos, varios = agrupar_productos(productos)
    secciones_varios = dividir_varios(varios)

    print()
    print(f"      {len(grupos)} categorías con nombre, {len(varios)} productos sin categoría")

    grandes, normales = separar_grandes(grupos, UMBRAL_RUBRO_GRANDE)
    print(f"      {len(grandes)} categoría(s) grande(s) (>= {UMBRAL_RUBRO_GRANDE} productos): {list(grandes.keys())}")

    logo_reader, logo_size = obtener_logo()
    logo_ratio = logo_size[1] / logo_size[0]
    icono_generico = obtener_icono_generico()

    print()
    print("Generando catálogo general...")
    ruta_general = os.path.join(CARPETA_SALIDA, "Catalogo_FixPro_General.pdf")
    generar_pdf_general(ruta_general, normales, secciones_varios, logo_reader, logo_ratio, icono_generico)
    print(f"  ✓ {ruta_general}")

    for nombre_rubro, productos_rubro in grandes.items():
        nombre_archivo = re.sub(r'[^A-Za-z0-9]+', '_', nombre_rubro).strip('_')
        ruta_rubro = os.path.join(CARPETA_SALIDA, f"Catalogo_FixPro_{nombre_archivo}.pdf")
        print(f"Generando catálogo de '{nombre_rubro}' ({len(productos_rubro)} productos)...")
        generar_pdf_simple(ruta_rubro, nombre_rubro, productos_rubro, logo_reader, logo_ratio, icono_generico)
        print(f"  ✓ {ruta_rubro}")

    print()
    print("=" * 60)
    print("  ¡Listo! Revisá la carpeta:")
    print(f"  {CARPETA_SALIDA}")
    print("=" * 60)
    print()
    input("  Presioná Enter para cerrar...")


if __name__ == "__main__":
    main()
