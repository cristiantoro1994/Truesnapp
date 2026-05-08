# Pantalla de descarga consolidada del proyecto.
# Muestra:
#   - Resumen del proyecto (contadores)
#   - Qué incluye el ZIP
#   - Botón para descargar todo el proyecto en un ZI
# El ZIP incluye:
#   - Fotos optimizadas con marca de agua
#   - Certificados blockchain (.ots)
#   - Informe profesional en PDF


import streamlit as st

from utils.helpers import (
    listar_imagenes,
    existe_version_optimizada,
    existe_certificado,
)
from utils.proyectos import obtener_proyecto
from exportacion.exportar_proyecto import (
    generar_zip_proyecto,
    nombre_archivo_zip,
)


def mostrar():
    """Muestra la pantalla de descargas del proyecto."""

    #  Botón de volver 
    if st.button("← Volver a la galería", key="volver_descargas"):
        st.session_state.pagina = "galeria"
        st.rerun()

    #  Verificar sesión y proyecto 
    proyecto = obtener_proyecto_actual()

    if proyecto is None:
        st.warning("No se encontró el proyecto. Volviendo al dashboard...")
        st.session_state.pagina = "dashboard"
        st.rerun()
        return

    #  Cabecera 
    st.markdown("# 📦 Descarga del proyecto")
    st.markdown(f"### 🏠 {proyecto['nombre']}")
    st.markdown("---")

    #  Resumen del proyecto 
    mostrar_resumen(proyecto)

    st.markdown("---")

    #  Qué incluye la descarga 
    mostrar_contenido_zip()

    st.markdown("---")

    # Botón de descarga 
    mostrar_boton_descarga(proyecto)


def obtener_proyecto_actual():
    """Devuelve el proyecto seleccionado, verificando propiedad."""
    proyecto_id = st.session_state.get("proyecto_actual")
    usuario_id = st.session_state.get("usuario_id")

    if proyecto_id is None or usuario_id is None:
        return None

    return obtener_proyecto(proyecto_id, usuario_id)


def mostrar_resumen(proyecto):
    """Muestra los contadores del proyecto: total, optimizadas, certificadas."""
    imagenes = listar_imagenes(proyecto)
    total = len(imagenes)
    optimizadas = sum(
        1 for img in imagenes if existe_version_optimizada(img, proyecto)
    )
    certificadas = sum(
        1 for img in imagenes if existe_certificado(img, proyecto)
    )

    st.markdown("### 📊 Resumen del proyecto")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="📷 Fotografías",
            value=total,
        )

    with col2:
        st.metric(
            label="✨ Optimizadas",
            value=optimizadas,
        )

    with col3:
        st.metric(
            label="🔐 Certificadas",
            value=certificadas,
        )


def mostrar_contenido_zip():
    """Lista lo que incluye el archivo ZIP descargable."""
    st.markdown("### 📦 ¿Qué incluye la descarga?")

    st.markdown(
        "<div style='background-color: #F8F9FA; padding: 1.2rem; "
        "border-radius: 10px; border: 1px solid #E1E4E8;'>"
        "<p style='margin: 0.3rem 0; color: #2C3E50;'>"
        "✓ <strong>Fotografías optimizadas</strong> "
        "(con la marca de agua TrueSnapp)</p>"
        "<p style='margin: 0.3rem 0; color: #2C3E50;'>"
        "✓ <strong>Certificados blockchain</strong> "
        "(archivos .ots verificables)</p>"
        "<p style='margin: 0.3rem 0; color: #2C3E50;'>"
        "✓ <strong>Informe profesional en PDF</strong> "
        "(resumen del proyecto con todos los datos)</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.caption(
        "El archivo ZIP está organizado en subcarpetas para facilitar "
        "su uso. Puedes subir las fotos directamente a Airbnb, Booking "
        "u otros portales sin más procesamiento."
    )


def mostrar_boton_descarga(proyecto):
    """Genera y ofrece la descarga del ZIP del proyecto."""
    st.markdown("### 📥 Descargar")

    #  Verificación previa: ¿hay fotos optimizadas? 
    imagenes = listar_imagenes(proyecto)
    optimizadas = sum(
        1 for img in imagenes if existe_version_optimizada(img, proyecto)
    )

    if optimizadas == 0:
        st.warning(
            "⚠️ Este proyecto aún no tiene fotos optimizadas. "
            "Vuelve a la galería y optimiza al menos una foto antes "
            "de descargar."
        )
        return

    #  Generamos el ZIP en memoria 
    autor = st.session_state.get("usuario_nombre", "Usuario")

    with st.spinner("📦 Preparando el archivo ZIP..."):
        contenido_zip = generar_zip_proyecto(proyecto, autor=autor)

    if contenido_zip is None:
        st.error(
            "❌ No se pudo generar el archivo. Inténtalo de nuevo "
            "o contacta con soporte."
        )
        return

    #  Botón de descarga 
    nombre = nombre_archivo_zip(proyecto)
    tamano_mb = len(contenido_zip) / (1024 * 1024)

    st.download_button(
        label=f"📥 Descargar todo el proyecto (ZIP, {tamano_mb:.1f} MB)",
        data=contenido_zip,
        file_name=nombre,
        mime="application/zip",
        use_container_width=True,
        type="primary",
    )

    st.caption(
        f"El archivo se guardará como **{nombre}** en tu carpeta de descargas."
    )