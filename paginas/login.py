# =====================================================================
# paginas/login.py
# =====================================================================
# Pantalla de inicio de sesión de TrueSnapp.
#
# Validamos las credenciales contra la base de datos:
#   - Solo usuarios registrados pueden entrar.
#   - La contraseña se compara contra el hash bcrypt guardado.
#   - Los datos del usuario quedan en st.session_state para que
#     todas las demás pantallas sepan QUIÉN es el usuario actual.
# =====================================================================

import streamlit as st

from utils.usuarios import autenticar_usuario


def mostrar():
    """Muestra el formulario de inicio de sesión."""

    # ----- Cabecera con bienvenida -----
    st.markdown("# 👋 Bienvenido a TrueSnapp")
    st.markdown(
        "Inicia sesión para acceder a tus proyectos de fotografía."
    )

    st.markdown("---")

    # ----- Formulario de login -----
    email = st.text_input(
        "Email",
        key="login_email",
        placeholder="tucorreo@ejemplo.com",
    )

    contrasena = st.text_input(
        "Contraseña",
        key="login_contrasena",
        type="password",
        placeholder="Tu contraseña",
    )

    st.markdown("")

    # ----- Botón de iniciar sesión -----
    if st.button(
        "Iniciar sesión",
        use_container_width=True,
        type="primary",
        key="boton_iniciar_sesion",
    ):
        procesar_login(email, contrasena)

    st.markdown("---")

    # ----- Enlace para crear cuenta nueva -----
    st.markdown(
        "<p style='text-align: center; color: #7F8C8D; "
        "font-size: 0.9rem; margin: 0.6rem 0 0.3rem 0;'>"
        "¿Aún no tienes cuenta?</p>",
        unsafe_allow_html=True,
    )

    if st.button(
        "🆕 Crear cuenta nueva",
        use_container_width=True,
        key="boton_ir_a_registro",
    ):
        st.session_state.pagina = "registro"
        st.rerun()


def procesar_login(email, contrasena):
    """
    Procesa el intento de login validando contra la base de datos.

    Llama a autenticar_usuario(), que:
      1. Busca el usuario por email en la BD.
      2. Compara la contraseña con el hash bcrypt guardado.
      3. Si todo OK, devuelve los datos del usuario.

    Si hay éxito, guardamos los datos en session_state y vamos al dashboard.
    Si hay error, mostramos un mensaje genérico (sin revelar si el email
    existe o no, por seguridad).
    """
    # Validaciones rápidas antes de tocar la BD
    if not email or not contrasena:
        st.error("Introduce email y contraseña.")
        return

    # Llamamos al módulo de usuarios para autenticar contra la BD
    exito, resultado = autenticar_usuario(email, contrasena)

    if not exito:
        # resultado es un mensaje de error
        st.error(f"❌ {resultado}")
        return

    # ----- Login correcto: guardamos los datos del usuario -----
    # resultado es un diccionario con id, email, nombre
    st.session_state.usuario_logueado = True
    st.session_state.usuario_id = resultado["id"]
    st.session_state.usuario_email = resultado["email"]
    st.session_state.usuario_nombre = resultado["nombre"]

    # Limpiamos cualquier estado heredado de sesiones anteriores
    st.session_state.pagina = "dashboard"

    st.rerun()