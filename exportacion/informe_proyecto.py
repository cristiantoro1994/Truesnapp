# Generador del informe consolidado en PDF de un proyecto completo.
# Genera un documento de 1-2 páginas con:
#   - Cabecera con marca TrueSnapp
#   - Datos del proyecto y del autor
#   - Resumen estadístico (fotos totales, optimizadas, certificadas)
#   - Tabla detallada con cada foto, hash y estado
#   - Pie con URL de verificación pública
# El PDF se genera en memoria y se devuelve como bytes para que el
# generador del ZIP lo añada al paquete completo.


import io
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors as rl_colors

from utils.helpers import (
    listar_imagenes,
    ruta_imagen_optimizada,
    existe_version_optimizada,
    ruta_certificado,
    existe_certificado,
)
from blockchain.certificar import calcular_hash, hash_corto



# Constantes de diseño


# Colores corporativos TrueSnapp
COLOR_AZUL = HexColor("#1E88E5")
COLOR_TEXTO = HexColor("#2C3E50")
COLOR_GRIS = HexColor("#7F8C8D")
COLOR_VERDE = HexColor("#27AE60")
COLOR_NARANJA = HexColor("#F39C12")
COLOR_FONDO_TABLA = HexColor("#F4F6F8")

# Tamaños de fuente
TAM_TITULO = 22
TAM_SUBTITULO = 14
TAM_SECCION = 13
TAM_ETIQUETA = 11
TAM_VALOR = 10
TAM_PEQUENO = 8

MARGEN_X = 2 * cm
MARGEN_Y = 2 * cm


# Función principal


def generar_informe_pdf(proyecto, autor=None):
    """
    Genera un informe PDF consolidado del proyecto.

    Parámetros:
      proyecto: diccionario con datos del proyecto (id, nombre).
      autor:    nombre del autor del proyecto (opcional, se obtiene
                desde la sesión si no se pasa).

    Devuelve:
      - bytes con el contenido del PDF si todo salió bien.
      - None si hubo cualquier error.
    """
    if proyecto is None:
        return None

    try:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        ancho, alto = A4

        # Recolectamos los datos a mostrar
        datos = _recolectar_datos_proyecto(proyecto, autor)

        # Dibujamos cada sección 
        cursor_y = alto

        cursor_y = _dibujar_cabecera(c, ancho, cursor_y)
        cursor_y = _dibujar_datos_proyecto(c, datos, cursor_y)
        cursor_y = _dibujar_resumen(c, datos, cursor_y)
        cursor_y = _dibujar_tabla_fotos(c, datos, cursor_y, ancho, alto)
        _dibujar_pie(c, ancho)

        #  Cerrar y devolver bytes 
        c.showPage()
        c.save()

        contenido_pdf = buffer.getvalue()
        buffer.close()

        return contenido_pdf

    except Exception as error:
        print(f"[Informe proyecto] Error: {error}")
        return None


# Recolección de datos


def _recolectar_datos_proyecto(proyecto, autor):
    """
    Recopila toda la información del proyecto necesaria para el informe.

    Devuelve un diccionario con:
      - nombre del proyecto, autor, fecha
      - contadores (total, optimizadas, certificadas)
      - lista de fotos con sus datos (nombre, hash, estado)
    """
    imagenes = listar_imagenes(proyecto)

    fotos_info = []
    contador_optimizadas = 0
    contador_certificadas = 0

    for ruta_imagen in imagenes:
        nombre_limpio = _quitar_id(ruta_imagen.name)

        # ¿Está optimizada?
        opt = existe_version_optimizada(ruta_imagen, proyecto)
        if opt:
            contador_optimizadas += 1

        # ¿Está certificada?
        cert = existe_certificado(ruta_imagen, proyecto)
        if cert:
            contador_certificadas += 1

        # Hash de la versión optimizada (si existe)
        hash_corto_str = "—"
        if opt:
            ruta_opt = ruta_imagen_optimizada(ruta_imagen, proyecto)
            hash_completo = calcular_hash(ruta_opt)
            if hash_completo:
                hash_corto_str = hash_corto(hash_completo)

        # Estado para la tabla
        if cert:
            estado = "Certificada"
        elif opt:
            estado = "Optimizada"
        else:
            estado = "Sin procesar"

        fotos_info.append({
            "nombre": nombre_limpio,
            "hash_corto": hash_corto_str,
            "estado": estado,
            "optimizada": opt,
            "certificada": cert,
        })

    return {
        "nombre_proyecto": proyecto.get("nombre", "Proyecto"),
        "autor": autor or "—",
        "fecha": datetime.now(),
        "total_fotos": len(imagenes),
        "fotos_optimizadas": contador_optimizadas,
        "fotos_certificadas": contador_certificadas,
        "fotos": fotos_info,
    }


# Dibujo de la cabecera


def _dibujar_cabecera(c, ancho, cursor_y):
    """Banda superior azul + título principal del informe."""
    # Banda azul
    c.setFillColor(COLOR_AZUL)
    c.rect(0, cursor_y - 1.5 * cm, ancho, 1.5 * cm, fill=1, stroke=0)

    # Marca TrueSnapp en blanco
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(ancho / 2, cursor_y - 1 * cm, "TrueSnapp")

    cursor_y -= 1.5 * cm

    # Título principal
    c.setFillColor(COLOR_TEXTO)
    c.setFont("Helvetica-Bold", TAM_TITULO)
    c.drawCentredString(ancho / 2, cursor_y - 1 * cm, "INFORME DEL PROYECTO")

    cursor_y -= 1.5 * cm

    # Línea separadora
    c.setStrokeColor(COLOR_GRIS)
    c.setLineWidth(0.5)
    c.line(MARGEN_X, cursor_y, ancho - MARGEN_X, cursor_y)

    return cursor_y - 0.6 * cm


# Dibujo de los datos del proyecto


def _dibujar_datos_proyecto(c, datos, cursor_y):
    """Bloque con: proyecto, autor, fecha."""
    fecha_str = _formatear_fecha(datos["fecha"])

    filas = [
        ("Proyecto:", datos["nombre_proyecto"]),
        ("Autor:", datos["autor"]),
        ("Generado:", fecha_str),
    ]

    for etiqueta, valor in filas:
        c.setFillColor(COLOR_GRIS)
        c.setFont("Helvetica-Bold", TAM_ETIQUETA)
        c.drawString(MARGEN_X, cursor_y, etiqueta)

        c.setFillColor(COLOR_TEXTO)
        c.setFont("Helvetica", TAM_VALOR)
        c.drawString(MARGEN_X + 3 * cm, cursor_y, valor)

        cursor_y -= 0.55 * cm

    cursor_y -= 0.3 * cm

    # Línea separadora
    c.setStrokeColor(COLOR_GRIS)
    c.line(MARGEN_X, cursor_y, A4[0] - MARGEN_X, cursor_y)

    return cursor_y - 0.6 * cm


# Dibujo del resumen estadístico


def _dibujar_resumen(c, datos, cursor_y):
    """Bloque con los contadores (total, optimizadas, certificadas)."""
    # Título de sección
    c.setFillColor(COLOR_AZUL)
    c.setFont("Helvetica-Bold", TAM_SECCION)
    c.drawString(MARGEN_X, cursor_y, "RESUMEN")
    cursor_y -= 0.6 * cm

    filas = [
        ("Total de fotografías:", str(datos["total_fotos"])),
        ("Optimizadas con IA:", str(datos["fotos_optimizadas"])),
        ("Certificadas en blockchain:", str(datos["fotos_certificadas"])),
    ]

    for etiqueta, valor in filas:
        c.setFillColor(COLOR_TEXTO)
        c.setFont("Helvetica", TAM_VALOR)
        c.drawString(MARGEN_X, cursor_y, f"• {etiqueta}")

        c.setFont("Helvetica-Bold", TAM_VALOR)
        c.drawString(MARGEN_X + 6 * cm, cursor_y, valor)

        cursor_y -= 0.55 * cm

    cursor_y -= 0.3 * cm

    # Línea separadora
    c.setStrokeColor(COLOR_GRIS)
    c.line(MARGEN_X, cursor_y, A4[0] - MARGEN_X, cursor_y)

    return cursor_y - 0.6 * cm


# Dibujo de la tabla de fotografías


def _dibujar_tabla_fotos(c, datos, cursor_y, ancho, alto):
    """
    Dibuja una tabla con las fotos del proyecto.

    Si la lista no cabe en la página, se trunca con un mensaje
    indicando cuántas más hay (para mantener el informe a 1 página).
    """
    # Título de sección
    c.setFillColor(COLOR_AZUL)
    c.setFont("Helvetica-Bold", TAM_SECCION)
    c.drawString(MARGEN_X, cursor_y, "FOTOGRAFÍAS Y CERTIFICADOS")
    cursor_y -= 0.7 * cm

    # ----- Construimos los datos de la tabla -----
    encabezados = ["Fotografía", "Hash blockchain", "Estado"]

    filas_tabla = [encabezados]

    # Limitamos a un máximo razonable para que quepa en la página
    MAX_FOTOS_EN_TABLA = 18
    fotos_a_mostrar = datos["fotos"][:MAX_FOTOS_EN_TABLA]

    for foto in fotos_a_mostrar:
        # Recortamos el nombre si es muy largo
        nombre = foto["nombre"]
        if len(nombre) > 28:
            nombre = nombre[:25] + "..."

        filas_tabla.append([
            nombre,
            foto["hash_corto"],
            foto["estado"],
        ])

    #  Estilo de la tabla 
    estilo = TableStyle([
        # Fila de cabecera
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),

        # Filas de datos
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), COLOR_TEXTO),
        ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),

        # Fondo alterno para mejorar la lectura
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, COLOR_FONDO_TABLA]),

        # Bordes
        ("LINEBELOW", (0, 0), (-1, 0), 1, COLOR_AZUL),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, COLOR_GRIS),

        # Hash en monoespaciada
        ("FONTNAME", (1, 1), (1, -1), "Courier"),
        ("FONTSIZE", (1, 1), (1, -1), 8),
    ])

    tabla = Table(
        filas_tabla,
        colWidths=[7 * cm, 6 * cm, 4 * cm],
        style=estilo,
    )

    # Calculamos el alto de la tabla y la dibujamos
    alto_tabla = tabla.wrap(0, 0)[1]
    tabla.drawOn(c, MARGEN_X, cursor_y - alto_tabla)

    cursor_y -= alto_tabla + 0.3 * cm

    # Si truncamos la lista, avisamos
    fotos_restantes = len(datos["fotos"]) - MAX_FOTOS_EN_TABLA
    if fotos_restantes > 0:
        c.setFillColor(COLOR_GRIS)
        c.setFont("Helvetica-Oblique", TAM_PEQUENO)
        c.drawString(
            MARGEN_X,
            cursor_y,
            f"(... y {fotos_restantes} fotografía(s) más en este proyecto)"
        )
        cursor_y -= 0.4 * cm

    return cursor_y



# Dibujo del pie de página


def _dibujar_pie(c, ancho):
    """Pie con la URL de verificación pública y la marca de autoría."""
    pie_y = 1.8 * cm

    # Verificación pública
    c.setFillColor(COLOR_AZUL)
    c.setFont("Helvetica-Bold", TAM_PEQUENO)
    c.drawCentredString(
        ancho / 2,
        pie_y,
        "Verificación pública: https://opentimestamps.org",
    )

    # Autoría
    c.setFillColor(COLOR_GRIS)
    c.setFont("Helvetica-Oblique", TAM_PEQUENO)
    c.drawCentredString(
        ancho / 2,
        1 * cm,
        "Generado por TrueSnapp",
    )


# Funciones auxiliares


def _quitar_id(nombre_archivo):
    """Quita el ID único del inicio del nombre del archivo."""
    if "_" in nombre_archivo:
        partes = nombre_archivo.split("_", 1)
        if len(partes) == 2:
            return partes[1]
    return nombre_archivo


def _formatear_fecha(fecha):
    """Devuelve la fecha en formato '7 de mayo de 2026'."""
    if fecha is None:
        return "—"

    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]

    return f"{fecha.day} de {meses[fecha.month - 1]} de {fecha.year}"