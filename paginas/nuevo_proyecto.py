# Pantalla para crear un proyecto nuevo.
# El proyecto se asocia automáticamente al usuario que está logueado
# en ese momento, leyendo el usuario_id de la sesión.


import streamlit as st

from utils.proyectos import crear_proyecto


def mostrar():
    """Muestra el formulario para crear un proyecto nuevo."""

    if st.button("← Volver al dashboard", key="volver_nuevo_proyecto"):
        st.session_state.pagina = "dashboard"
        st.rerun()

    st.markdown("# ➕ Nuevo proyecto")
    st.markdown(
        "Crea un proyecto para organizar las fotos de un alojamiento. "
        "Por ejemplo: *Casa de la Playa*, *Apartamento Centro*, etc."
    )

    st.markdown("---")

    nombre = st.text_input(
        "Nombre del proyecto",
        key="nuevo_proyecto_nombre",
        placeholder="Ej: Casa Playa, Apartamento Centro...",
    )

    st.markdown("")

    if st.button(
        "Crear proyecto",
        use_container_width=True,
        type="primary",
        key="boton_crear_proyecto",
    ):
        procesar_creacion(nombre)


def procesar_creacion(nombre):
    """Valida y crea el proyecto en la base de datos."""

    usuario_id = st.session_state.get("usuario_id")
    if usuario_id is None:
        st.error("Debes iniciar sesión.")
        return

    exito, resultado = crear_proyecto(usuario_id, nombre)

    if not exito:
        st.error(f"❌ {resultado}")
        return

    # resultado es un diccionario con id, nombre, usuario_id
    st.success(f"✅ Proyecto **{resultado['nombre']}** creado correctamente.")

    import time
    time.sleep(0.8)

    # Volvemos al dashboard
    st.session_state.pagina = "dashboard"
    st.rerun()