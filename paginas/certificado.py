# Pantalla del certificado blockchain de una foto.
# Muestra los detalles de la certificación:
#   - Miniatura de la foto certificada
#   - Hash SHA-256 (en versión corta, opción de ver completo)
#   - Fecha y hora de certificación
#   - Red blockchain (Bitcoin vía OpenTimestamps)
#   - Botón de verificación pública (abre opentimestamps.org)
#   - Botón de descarga del comprobante .ots


import streamlit as st
from datetime import datetime
from pathlib import Path

from utils.helpers import (
    listar_imagenes,
    ruta_imagen_optimizada,
    ruta_certificado,
    existe_certificado,
)
from blockchain.certificar import calcular_hash, hash_corto
from exportacion.descargar_certificado import generar_pdf_certificado

def mostrar():
    """Muestra los detalles del certificado de la foto seleccionada."""

    # Botón de volver siempre arriba 
    if st.button("← Volver a la galería", key="volver_certificado"):
        st.session_state.foto_certificado = None
        st.session_state.pagina = "galeria"
        st.rerun()

    #  Buscamos el proyecto y la foto seleccionada 
    proyecto = obtener_proyecto_actual()

    if proyecto is None:
        st.warning("No se encontró el proyecto. Volviendo al dashboard...")
        st.session_state.pagina = "dashboard"
        st.rerun()
        return

    ruta_foto_str = st.session_state.get("foto_certificado", None)
    if ruta_foto_str is None:
        st.warning("No se ha seleccionado ninguna foto. Volviendo a la galería...")
        st.session_state.pagina = "galeria"
        st.rerun()
        return

    ruta_foto = Path(ruta_foto_str)

    #  Comprobamos que la foto realmente está certificada 
    if not existe_certificado(ruta_foto, proyecto):
        st.error("Esta foto no tiene certificado. Vuelve a la galería.")
        return

    # Cabecera 
    st.markdown("# 📜 Certificado Blockchain")
    st.markdown("---")

    #  Datos del certificado 
    mostrar_detalles_certificado(ruta_foto, proyecto)


def obtener_proyecto_actual():
    """
    Devuelve el proyecto seleccionado, verificando que pertenezca al
    usuario logueado.

    Si el usuario intenta acceder a un proyecto que no es suyo (por
    ejemplo, manipulando el estado), devolvemos None y la galería
    redirigirá al dashboard.
    """
    from utils.proyectos import obtener_proyecto

    proyecto_id = st.session_state.get("proyecto_actual")
    usuario_id = st.session_state.get("usuario_id")

    if proyecto_id is None or usuario_id is None:
        return None

    return obtener_proyecto(proyecto_id, usuario_id)


def mostrar_detalles_certificado(ruta_foto, proyecto):
    """
    Muestra todos los detalles del certificado de una foto:
    miniatura, datos identificativos, hash, fecha, red blockchain,
    verificación pública y descarga del comprobante.
    """
    # 1. Miniatura de la foto certificada 
    ruta_optimizada = ruta_imagen_optimizada(ruta_foto, proyecto)

    if ruta_optimizada.exists():
        st.image(str(ruta_optimizada), use_container_width=True)

    st.markdown("")

    # 2. Datos del proyecto y la foto 
    nombre_foto = quitar_id_del_nombre(ruta_foto.name)

    st.markdown(f"**🏠 Proyecto:** {proyecto['nombre']}")
    st.markdown(f"**📷 Foto:** {nombre_foto}")

    st.markdown("---")

    # ----- 3. Hash SHA-256 (huella digital) -----
    st.markdown("### 🧬 Huella digital (SHA-256)")

    hash_completo = calcular_hash(ruta_optimizada)

    if hash_completo is None:
        st.error("No se pudo calcular la huella digital de la foto.")
        return

    # Por defecto mostramos hash corto (más legible)
    mostrar_completo = st.checkbox(
        "Mostrar hash completo",
        key=f"mostrar_completo_{ruta_foto.name}",
    )

    if mostrar_completo:
        st.code(hash_completo, language=None)
    else:
        st.code(hash_corto(hash_completo), language=None)

    st.caption(
        "La huella digital es un código único que representa esta foto. "
        "Si la imagen cambiara aunque fuera un solo píxel, esta huella "
        "sería completamente diferente."
    )

    st.markdown("---")

    #  4. Fecha de certificación 
    st.markdown("### 📅 Fecha de certificación")

    ruta_ots = ruta_certificado(ruta_foto, proyecto)
    fecha_certificado = obtener_fecha_certificado(ruta_ots)

    st.markdown(f"**{fecha_certificado}**")

    st.caption(
        "Esta es la fecha y hora exactas en que se registró la huella "
        "en la blockchain. Sirve como prueba notarial."
    )

    st.markdown("---")

    #  5. Red blockchain
    st.markdown("### 🪙 Red blockchain")

    st.markdown("**Bitcoin** (vía OpenTimestamps)")

    st.caption(
        "El registro está anclado en Bitcoin, la blockchain más antigua "
        "y segura del mundo. La confirmación definitiva tarda entre 1 y "
        "6 horas tras la certificación."
    )

    st.markdown("---")

    # 6. Verificación pública 
    st.markdown("### 🔗 Verificación pública")

    st.markdown(
        "Cualquier persona puede verificar este certificado de forma "
        "independiente, sin depender de TrueSnapp, en el verificador "
        "oficial de OpenTimestamps:"
    )

    st.link_button(
        "🌐 Abrir verificador público",
        url="https://opentimestamps.org",
        use_container_width=True,
    )

    st.caption(
        "Para verificar: descarga el comprobante .ots, súbelo en el sitio "
        "junto con la foto optimizada original, y comprueba que la huella "
        "coincide."
    )

    st.markdown("---")

    #  7. Descarga del comprobante .ots 
    st.markdown("### 💾 Comprobante de certificación")

    st.markdown(
        "Guarda este archivo. Es la prueba que demuestra que la foto "
        "fue certificada en la fecha indicada."
    )

    try:
        contenido_ots = ruta_ots.read_bytes()

        st.download_button(
            label="📥 Descargar comprobante (.ots)",
            data=contenido_ots,
            file_name=f"{Path(nombre_foto).stem}.ots",
            mime="application/octet-stream",
            use_container_width=True,
        )
    except Exception as error:
        st.error(f"No se pudo leer el comprobante: {error}")

    st.markdown("---")

    #  8. Descarga del certificado en PDF 
    st.markdown("### 📄 Certificado en formato PDF")

    st.markdown(
        "Descarga un certificado bonito y profesional en PDF, listo "
        "para imprimir o enviar a un huésped, agencia o portal."
    )

    # Generamos el PDF en memoria
    datos_pdf = {
        "nombre_proyecto": proyecto["nombre"],
        "nombre_foto": nombre_foto,
        "ruta_imagen": ruta_optimizada,
        "hash": hash_completo,
        "fecha": datetime.fromtimestamp(ruta_ots.stat().st_mtime),
        "red": "Bitcoin",
        "protocolo": "OpenTimestamps",
    }

    contenido_pdf = generar_pdf_certificado(datos_pdf)

    if contenido_pdf is not None:
        st.download_button(
            label="📄 Descargar certificado en PDF",
            data=contenido_pdf,
            file_name=f"certificado_{Path(nombre_foto).stem}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.error("No se pudo generar el certificado PDF.")
def obtener_fecha_certificado(ruta_ots):
    """
    Devuelve la fecha de creación del archivo .ots como string legible.

    Formato: "4 de mayo de 2026, 22:55"
    """
    try:
        timestamp = ruta_ots.stat().st_mtime
        fecha = datetime.fromtimestamp(timestamp)

        meses = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]

        return (
            f"{fecha.day} de {meses[fecha.month - 1]} de {fecha.year}, "
            f"{fecha.hour:02d}:{fecha.minute:02d}"
        )
    except Exception:
        return "Fecha no disponible"


def quitar_id_del_nombre(nombre_archivo):
    """Quita el ID único del inicio del nombre del archivo."""
    if "_" in nombre_archivo:
        partes = nombre_archivo.split("_", 1)
        if len(partes) == 2:
            return partes[1]
    return nombre_archivo