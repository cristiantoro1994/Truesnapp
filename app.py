# Este es el punto de entrada de la app. Para ejecutarla:
#     streamlit run app.py
#
# Este archivo orquesta TODA la app en 4 pasos sencillos:
#   1. Configurar la página (título, icono, layout)
#   2. Aplicar los estilos visuales de TrueSnapp
#   3. Inicializar el estado de sesión
#   4. Mostrar la pantalla correspondiente (router)


import streamlit as st

# Importamos las funciones que creamos en otros archivos
from utils.estilos import aplicar_estilos
from utils.helpers import inicializar_estado, mostrar_pagina_actual
from utils.base_datos import inicializar_base_datos

# 1. Configuración general de la página

# Esta función SIEMPRE debe ir antes que cualquier otra de Streamlit.
st.set_page_config(
    page_title="TrueSnapp",            # Título en la pestaña del navegador
    page_icon="📸",                     # Icono de la pestaña
    layout="centered",                  # Diseño centrado (ideal móvil)
    initial_sidebar_state="collapsed",  # Sin barra lateral
)


# 2. Aplicar los estilos visuales de TrueSnapp

# Inyecta el CSS personalizado: colores, botones grandes, tarjetas, etc.
aplicar_estilos()


# 3. Inicializar el estado de sesión

# Inicializa la base de datos SQLite si aún no existe (Fase 6)
inicializar_base_datos()

# Crea las variables básicas (página actual, usuario, etc.) si no existen.
inicializar_estado()


# 4. Mostrar la pantalla correspondiente (router)

# Decide qué pantalla mostrar según st.session_state.pagina:
#   - login → paginas/login.py
#   - dashboard → paginas/dashboard.py
#   - galeria → paginas/galeria.py
#   - certificado → paginas/certificado.py
#   - descargas → paginas/descargas.py
mostrar_pagina_actual()