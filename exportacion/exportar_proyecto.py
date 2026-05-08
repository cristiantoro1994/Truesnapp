# exportacion/exportar_proyecto.py
# =====================================================================
# Generador del archivo ZIP de exportacion de un proyecto completo.


import io
import zipfile
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from utils.helpers import (
    listar_imagenes,
    ruta_imagen_optimizada,
    existe_version_optimizada,
    ruta_certificado,
    existe_certificado,
)
from exportacion.informe_proyecto import generar_informe_pdf


def generar_zip_proyecto(proyecto, autor=None):
    """
    Empaqueta todo el contenido de un proyecto en un archivo ZIP.
    Devuelve los bytes del ZIP, o None si hay error.
    """
    if proyecto is None:
        return None

    try:
        imagenes = listar_imagenes(proyecto)

        # Filtramos solo las fotos optimizadas
        imagenes_optimizadas = [
            img for img in imagenes
            if existe_version_optimizada(img, proyecto)
        ]

        if not imagenes_optimizadas:
            return None

        # Creamos el ZIP en memoria
        buffer = io.BytesIO()

        with zipfile.ZipFile(
            buffer,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as zip_archivo:

            # Carpeta 1: fotos optimizadas
            for indice, ruta_original in enumerate(imagenes_optimizadas, start=1):
                _agregar_foto_al_zip(
                    zip_archivo,
                    ruta_original,
                    proyecto,
                    indice,
                )

            # Carpeta 2: certificados blockchain
            for ruta_original in imagenes_optimizadas:
                if existe_certificado(ruta_original, proyecto):
                    _agregar_certificado_al_zip(
                        zip_archivo,
                        ruta_original,
                        proyecto,
                    )

            # Informe consolidado en PDF
            informe_pdf = generar_informe_pdf(proyecto, autor=autor)
            if informe_pdf is not None:
                zip_archivo.writestr("informe_truesnapp.pdf", informe_pdf)

        # Devolvemos los bytes del ZIP
        contenido_zip = buffer.getvalue()
        buffer.close()

        return contenido_zip

    except Exception as error:
        print(f"[Exportar proyecto] Error: {error}")
        return None


def nombre_archivo_zip(proyecto):
    """
    Genera el nombre del archivo ZIP de exportacion.
    Formato: truesnapp_[nombre]_[YYYY-MM-DD].zip
    """
    nombre_proyecto = proyecto.get("nombre", "proyecto")
    nombre_limpio = _limpiar_nombre_para_archivo(nombre_proyecto)

    fecha = datetime.now().strftime("%Y-%m-%d")

    return f"truesnapp_{nombre_limpio}_{fecha}.zip"


def _agregar_foto_al_zip(zip_archivo, ruta_original, proyecto, indice):
    """Anade una foto optimizada al ZIP."""
    ruta_optimizada = ruta_imagen_optimizada(ruta_original, proyecto)

    if not ruta_optimizada.exists():
        return

    nombre_limpio = _quitar_id_del_nombre(ruta_optimizada.name)
    prefijo = f"{indice:02d}_"
    nombre_en_zip = f"01_fotos_optimizadas/{prefijo}{nombre_limpio}"

    contenido = ruta_optimizada.read_bytes()
    zip_archivo.writestr(nombre_en_zip, contenido)


def _agregar_certificado_al_zip(zip_archivo, ruta_original, proyecto):
    """Anade el comprobante .ots de una foto certificada al ZIP."""
    ruta_ots = ruta_certificado(ruta_original, proyecto)

    if not ruta_ots.exists():
        return

    nombre_limpio = _quitar_id_del_nombre(ruta_original.name)
    nombre_sin_extension = Path(nombre_limpio).stem

    nombre_en_zip = (
        f"02_certificados/{nombre_sin_extension}/"
        f"{nombre_sin_extension}.ots"
    )

    contenido = ruta_ots.read_bytes()
    zip_archivo.writestr(nombre_en_zip, contenido)


def _quitar_id_del_nombre(nombre_archivo):
    """Quita el ID unico del inicio del nombre del archivo."""
    if "_" in nombre_archivo:
        partes = nombre_archivo.split("_", 1)
        if len(partes) == 2:
            return partes[1]
    return nombre_archivo


def _limpiar_nombre_para_archivo(nombre):
    """Limpia un nombre para que sea valido como nombre de archivo."""
    if not nombre:
        return "proyecto"

    nombre_normalizado = unicodedata.normalize("NFKD", nombre)
    nombre_sin_acentos = "".join(
        c for c in nombre_normalizado if not unicodedata.combining(c)
    )

    nombre_minus = nombre_sin_acentos.lower()
    nombre_guiones = re.sub(r"\s+", "_", nombre_minus)
    nombre_final = re.sub(r"[^a-z0-9_]", "", nombre_guiones)

    if not nombre_final:
        return "proyecto"

    return nombre_final