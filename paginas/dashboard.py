# Pantalla principal del usuario tras iniciar sesión.
# Muestra:
#   - Saludo personalizado con el nombre real del usuario.
#   - Botón "Nuevo proyecto".
#   - Tarjetas con los proyectos del usuario (leídos de la BD).
#   - Contadores reales por proyecto (fotos, optimizadas, certificadas).
#   - Botón "Cerrar sesión".
# IMPORTANTE: solo se muestran los proyectos del usuario actual,
# filtrando por usuario_id en la base de datos.


import streamlit as st
import shutil

from utils.helpers import (
    listar_imagenes,
    carpeta_proyecto,
    existe_version_optimizada,
    existe_certificado,
    cerrar_sesion,
)
from utils.proyectos import (
    listar_proyectos_usuario,
    eliminar_proyecto,
    obtener_proyecto,
)


def mostrar():
    """Muestra el dashboard con los proyectos del usuario actual."""

    #  Verificación de sesión 
    usuario_id = st.session_state.get("usuario_id")
    if usuario_id is None:
        st.warning("Debes iniciar sesión.")
        cerrar_sesion()
        st.rerun()
        return

    # Cabecera con saludo y cerrar sesión 
    cols_cabecera = st.columns([4, 1])

    with cols_cabecera[0]:
        nombre = st.session_state.get("usuario_nombre", "")
        st.markdown(f"## 👋 Hola, **{nombre}**")

    with cols_cabecera[1]:
        if st.button(
            "🚪 Salir",
            key="boton_cerrar_sesion",
            use_container_width=True,
        ):
            cerrar_sesion()
            st.rerun()

    st.markdown("---")

    #  Sección "Mis proyectos" 
    st.markdown("### 📁 Mis proyectos")

    # Botón para crear un proyecto nuevo
    if st.button(
        "➕ Nuevo proyecto",
        key="boton_nuevo_proyecto",
        type="primary",
    ):
        st.session_state.pagina = "nuevo_proyecto"
        st.rerun()

    st.markdown("")

    #  Lista de proyectos del usuario 
    proyectos = listar_proyectos_usuario(usuario_id)

    if not proyectos:
        st.markdown(
            "<div style='text-align: center; padding: 2rem; "
            "background-color: #F8F9FA; border-radius: 10px; "
            "border: 1px solid #E1E4E8; margin-top: 1rem;'>"
            "<p style='font-size: 1.1rem; color: #2C3E50; margin-bottom: 0.5rem;'>"
            "🌱 <strong>Empieza tu primer proyecto</strong></p>"
            "<p style='color: #7F8C8D; margin: 0;'>"
            "Crea un proyecto para cada alojamiento que quieras gestionar. "
            "Por ejemplo: <em>Casa Playa</em>, <em>Apartamento Centro</em>...</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # Mostramos cada proyecto como una tarjeta
    for proyecto in proyectos:
        mostrar_tarjeta_proyecto(proyecto, usuario_id)


def mostrar_tarjeta_proyecto(proyecto, usuario_id):
    """
    Muestra la tarjeta de un proyecto con:
      - Nombre del proyecto.
      - Contadores reales (fotos, optimizadas, certificadas).
      - Botón "Abrir" → galería.
      - Botón "🗑️" → eliminar (con confirmación).
    """
    proyecto_id = proyecto["id"]

    # Estado: confirmar borrado 
    pendiente_borrar = st.session_state.get("proyecto_a_borrar")

    with st.container(border=True):
        if pendiente_borrar == proyecto_id:
            # Modo confirmar borrado
            st.warning(
                f"⚠️ Vas a eliminar el proyecto **{proyecto['nombre']}**.\n\n"
                f"Esta acción borrará TODO: fotos originales, optimizadas "
                f"y certificados. **No se puede deshacer.**"
            )
            col_si, col_no = st.columns(2)
            with col_si:
                if st.button(
                    "🗑️ Sí, eliminar todo",
                    key=f"confirmar_eliminar_{proyecto_id}",
                    use_container_width=True,
                ):
                    eliminar_proyecto_completo(proyecto, usuario_id)
                    st.session_state.proyecto_a_borrar = None
                    st.rerun()
            with col_no:
                if st.button(
                    "Cancelar",
                    key=f"cancelar_eliminar_{proyecto_id}",
                    use_container_width=True,
                ):
                    st.session_state.proyecto_a_borrar = None
                    st.rerun()
            return

        # ----- Modo normal: mostrar tarjeta -----
        col_info, col_abrir, col_borrar = st.columns([4, 1, 1])

        with col_info:
            st.markdown(f"#### 🏠 {proyecto['nombre']}")

            # Contadores en tiempo real
            imagenes = listar_imagenes(proyecto)
            total = len(imagenes)
            opt = sum(
                1 for img in imagenes if existe_version_optimizada(img, proyecto)
            )
            cert = sum(
                1 for img in imagenes if existe_certificado(img, proyecto)
            )

            st.markdown(
                f"📷 {total} fotos · ✨ {opt} optimizadas · 🔐 {cert} certificadas"
            )

        with col_abrir:
            if st.button(
                "Abrir",
                key=f"abrir_{proyecto_id}",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.proyecto_actual = proyecto_id
                st.session_state.pagina = "galeria"
                st.rerun()

        with col_borrar:
            if st.button(
                "🗑️",
                key=f"borrar_{proyecto_id}",
                use_container_width=True,
            ):
                st.session_state.proyecto_a_borrar = proyecto_id
                st.rerun()


def eliminar_proyecto_completo(proyecto, usuario_id):
    """
    Elimina un proyecto completo:
      - Borra la entrada de la base de datos.
      - Borra la carpeta del proyecto en disco (con todas las fotos,
        optimizadas y certificados).

    Solo se ejecuta si el proyecto pertenece al usuario.
    """
    proyecto_id = proyecto["id"]

    #  1. Verificación de propiedad 
    proyecto_validado = obtener_proyecto(proyecto_id, usuario_id)
    if proyecto_validado is None:
        st.error("No tienes permiso para eliminar este proyecto.")
        return

    #  2. Borrar la carpeta del proyecto en disco 
    try:
        carpeta = carpeta_proyecto(proyecto_validado)
        if carpeta.exists():
            shutil.rmtree(carpeta)
    except Exception as error:
        st.warning(f"No se pudo borrar la carpeta en disco: {error}")
        # Continuamos: al menos quitamos la entrada de la BD

    #  3. Borrar la entrada de la BD 
    eliminar_proyecto(proyecto_id, usuario_id)

    st.success(f"✅ Proyecto **{proyecto_validado['nombre']}** eliminado.")