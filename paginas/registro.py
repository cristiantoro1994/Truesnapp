# Pantalla de registro de nuevos usuarios.
# El usuario introduce nombre, email y contraseña, y se valida todo
# antes de crear la cuenta. Si todo va bien, se redirige al login
# con un mensaje de éxito.


import streamlit as st

from utils.usuarios import registrar_usuario


def mostrar():
    """Muestra el formulario de registro de usuarios."""

    # ----- Cabecera -----
    st.markdown("# 🆕 Crear cuenta")
    st.markdown(
        "Regístrate para empezar a usar **TrueSnapp**. "
        "Tus datos se guardan de forma segura y solo tú podrás verlos."
    )

    st.markdown("---")

    # ----- Formulario -----
    nombre = st.text_input(
        "Nombre",
        key="reg_nombre",
        placeholder="Cómo te llamas (ej: Cristian)",
    )

    email = st.text_input(
        "Email",
        key="reg_email",
        placeholder="tucorreo@ejemplo.com",
    )

    contrasena = st.text_input(
        "Contraseña",
        key="reg_contrasena",
        type="password",
        placeholder="Mínimo 8 caracteres",
    )

    contrasena_repetida = st.text_input(
        "Repite la contraseña",
        key="reg_contrasena_repetida",
        type="password",
        placeholder="Vuelve a escribir tu contraseña",
    )

    st.markdown("")

    #  Botón de crear cuenta 
    if st.button("Crear cuenta", use_container_width=True, type="primary"):
        procesar_registro(nombre, email, contrasena, contrasena_repetida)

    st.markdown("---")

    #  Enlace para volver al login 
    if st.button(
        "← Ya tengo cuenta, volver al login",
        use_container_width=True,
        key="volver_a_login",
    ):
        st.session_state.pagina = "login"
        st.rerun()


def procesar_registro(nombre, email, contrasena, contrasena_repetida):
    """
    Valida los datos y crea la cuenta si todo está correcto.
    """
    # Comprobaciones rápidas antes de llamar al módulo
    if contrasena != contrasena_repetida:
        st.error("Las contraseñas no coinciden.")
        return

    # Llamamos al módulo de usuarios para que haga el registro
    exito, mensaje = registrar_usuario(email, contrasena, nombre)

    if exito:
        # Mensaje grande y visible
        st.success(
            f"### ✅ ¡Cuenta creada correctamente!\n\n"
            f"Bienvenido a TrueSnapp. En unos segundos te llevamos al login..."
        )
        # Globos celebrativos para refuerzo visual
        st.balloons()
        # Pausa de 3 segundos para que el usuario lea el mensaje
        import time
        time.sleep(3)
        st.session_state.pagina = "login"
        st.rerun()
    else:
        st.error(f"❌ {mensaje}")