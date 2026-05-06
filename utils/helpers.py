# Funciones auxiliares reutilizables en toda la app.
#
# Contiene:
#   1. Inicialización del estado de sesión
#   2. Cambiar de pantalla
#   3. Router (decide qué pantalla mostrar)
#   4. Funciones para gestión de archivos de imágenes
#   5. Funciones para gestión de versiones optimizadas 
#   6. Limpieza de archivos temporales 


import streamlit as st
import re                 # Expresiones regulares (limpieza de nombres)
import unicodedata        # Para quitar acentos
from pathlib import Path  # Para trabajar con rutas de archivos
import uuid               # Para generar identificadores únicos


# 1. Inicialización del estado de sesión

def inicializar_estado():
    """
    Crea las variables básicas de st.session_state si no existen.
    Se llama UNA sola vez al inicio de app.py.

    Variables que prepara:
      - pagina: nombre de la pantalla actual
      - usuario_logueado: True/False según si el usuario entró
      - email_usuario: email del usuario logueado
      - proyecto_actual: ID del proyecto que el usuario está viendo
      - foto_a_borrar: foto que está esperando confirmación de borrado
      - proyecto_a_borrar: proyecto que está esperando confirmación
    """

    # Pantalla actual. Empezamos en "login".
    if "pagina" not in st.session_state:
        st.session_state.pagina = "login"

    # Estado del usuario
    if "usuario_logueado" not in st.session_state:
        st.session_state.usuario_logueado = False

    # Datos del usuario actual (Fase 6)
    if "usuario_id" not in st.session_state:
        st.session_state.usuario_id = None
    if "usuario_email" not in st.session_state:
        st.session_state.usuario_email = None
    if "usuario_nombre" not in st.session_state:
        st.session_state.usuario_nombre = None    

    if "email_usuario" not in st.session_state:
        st.session_state.email_usuario = ""

    # Proyecto que el usuario está viendo (None = ninguno)
    if "proyecto_actual" not in st.session_state:
        st.session_state.proyecto_actual = None

    # Confirmaciones pendientes (Fase 3)
    if "foto_a_borrar" not in st.session_state:
        st.session_state.foto_a_borrar = None

    if "proyecto_a_borrar" not in st.session_state:
        st.session_state.proyecto_a_borrar = None

# Foto seleccionada para ver su certificado (Fase 5)
    if "foto_certificado" not in st.session_state:
        st.session_state.foto_certificado = None

# 2. Cambiar de pantalla

def cambiar_pagina(nombre_pagina):
    """
    Cambia la pantalla activa de la app.

    Parámetros:
      nombre_pagina: texto con el nombre de la pantalla a mostrar.
                     Valores válidos: "login", "dashboard", "galeria",
                     "certificado", "descargas", "nuevo_proyecto".

    Uso desde otro archivo:
      from utils.helpers import cambiar_pagina
      cambiar_pagina("dashboard")
    """
    st.session_state.pagina = nombre_pagina
    st.rerun()


# 3. Router: decide qué pantalla mostrar

def mostrar_pagina_actual():
    """
    Lee st.session_state.pagina y muestra la pantalla correspondiente.
    Esta función se llama desde app.py.

    Funciona como un "portero": recibe el nombre de la pantalla y
    llama a la función mostrar() del archivo correcto.
    """

    # Importamos las pantallas aquí dentro (no arriba) para evitar
    # importaciones circulares.
    from paginas import (
        login,
        dashboard,
        galeria,
        certificado,
        descargas,
        nuevo_proyecto,
        registro,
    )

    # Protección de acceso: si el usuario NO está logueado,
    # solo puede ver la pantalla de login.
    if not st.session_state.usuario_logueado:
        if st.session_state.pagina == "registro":
            registro.mostrar()
        else:
         login.mostrar()
        return

    # Si está logueado, mostramos la pantalla seleccionada
    pagina = st.session_state.pagina

    if pagina == "login":
        login.mostrar()
    elif pagina == "dashboard":
        dashboard.mostrar()
    elif pagina == "galeria":
        galeria.mostrar()
    elif pagina == "certificado":
        certificado.mostrar()
    elif pagina == "descargas":
        descargas.mostrar()
    elif pagina == "nuevo_proyecto":
        nuevo_proyecto.mostrar()
    elif pagina == "registro":
        registro.mostrar()    
    else:
        # Si llega un nombre desconocido, volvemos al dashboard
        st.warning(f"Pantalla desconocida: '{pagina}'. Volviendo al dashboard.")
        st.session_state.pagina = "dashboard"
        dashboard.mostrar()


# 4. FUNCIONES PARA GESTIÓN DE ARCHIVOS DE IMÁGENES

# Estas funciones manejan la lectura, escritura y borrado de fotos
# en el disco. Las fotos se guardan en: datos/imagenes/[id_proyecto]/



# Carpeta raíz donde se guardan TODAS las imágenes de la app
CARPETA_RAIZ_IMAGENES = Path("datos/imagenes")

# Extensiones de imagen permitidas en TrueSnapp
EXTENSIONES_PERMITIDAS = ["jpg", "jpeg", "png"]


def carpeta_proyecto(proyecto):
    """
    Devuelve la ruta de la carpeta de un proyecto.
    No crea la carpeta, solo calcula su ruta.

    Usa el ID único del proyecto en lugar del nombre.
    Esto evita que dos proyectos con el mismo nombre compartan
    carpeta y se mezclen las fotos.

    Parámetros:
      proyecto: diccionario con al menos las claves 'id' y 'nombre'.

    Ejemplo:
      proyecto = {"id": "a1b2c3d4", "nombre": "Casa Playa"}
      carpeta_proyecto(proyecto) → datos/imagenes/a1b2c3d4
    """
    return CARPETA_RAIZ_IMAGENES / proyecto["id"]


def crear_carpeta_proyecto(proyecto):
    """
    Crea físicamente la carpeta de un proyecto en el disco.
    Si ya existe, no hace nada (no lanza error).
    """
    ruta = carpeta_proyecto(proyecto)
    # parents=True: crea las carpetas padre si no existen
    # exist_ok=True: no protesta si ya existe
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def limpiar_nombre_archivo(nombre):
    """
    Limpia un nombre de archivo eliminando caracteres problemáticos.

    Reemplaza:
      - Caracteres prohibidos en Windows (: ? * < > | / \\) por guion bajo.
      - Espacios y otros caracteres raros por guion bajo.
      - Acentos por su versión sin acento (á → a, ñ → n).

    Ejemplo:
      "WhatsApp Image 2026-05-02 at 16.14.56.jpeg"
      → "WhatsApp_Image_2026-05-02_at_16.14.56.jpeg"
    """
    # Separamos el nombre y la extensión
    ruta = Path(nombre)
    nombre_base = ruta.stem
    extension = ruta.suffix.lower()

    # 1. Quitamos acentos (á → a, ñ → n, etc.)
    nombre_base = unicodedata.normalize("NFKD", nombre_base)
    nombre_base = nombre_base.encode("ASCII", "ignore").decode("ASCII")

    # 2. Reemplazamos cualquier carácter que NO sea letra, número,
    # guion o punto, por un guion bajo
    nombre_base = re.sub(r"[^a-zA-Z0-9._-]", "_", nombre_base)

    # 3. Eliminamos guiones bajos consecutivos (_ _ _ → _)
    nombre_base = re.sub(r"_+", "_", nombre_base)

    # 4. Eliminamos guiones bajos al inicio o al final
    nombre_base = nombre_base.strip("_")

    # Si por algún motivo quedó vacío, le ponemos un nombre por defecto
    if not nombre_base:
        nombre_base = "imagen"

    return f"{nombre_base}{extension}"


def guardar_imagen(archivo_subido, proyecto):
    """
    Guarda una imagen subida por el usuario en la carpeta del proyecto.

    Limpia el nombre del archivo para evitar problemas con caracteres
    no permitidos en Windows o problemáticos para OpenCV.

    Parámetros:
      archivo_subido: el archivo que devuelve st.file_uploader
      proyecto: diccionario con los datos del proyecto

    Devuelve la ruta donde se guardó la imagen.
    """
    # Aseguramos que la carpeta del proyecto existe
    carpeta = crear_carpeta_proyecto(proyecto)

    # Limpiamos el nombre del archivo (quita espacios, dos puntos, etc.)
    nombre_limpio = limpiar_nombre_archivo(archivo_subido.name)

    # Generamos un nombre único para evitar sobreescribir fotos
    id_unico = uuid.uuid4().hex[:8]  # 8 caracteres aleatorios
    nombre_archivo = f"{id_unico}_{nombre_limpio}"

    # Ruta completa donde guardaremos la imagen
    ruta_completa = carpeta / nombre_archivo

    # Escribimos el contenido del archivo subido al disco
    with open(ruta_completa, "wb") as f:
        f.write(archivo_subido.getbuffer())

    return ruta_completa


def listar_imagenes(proyecto):
    """
    Devuelve una lista con las rutas de todas las imágenes
    de un proyecto, ordenadas por fecha (más recientes primero).

    Ignora los archivos temporales (con .tmp. en el nombre) que
    pudieran haber quedado de procesos de optimización interrumpidos.

    Parámetros:
      proyecto: diccionario con los datos del proyecto.
    """
    carpeta = carpeta_proyecto(proyecto)

    # Si la carpeta no existe, devolvemos lista vacía
    if not carpeta.exists():
        return []

    # Usamos un conjunto (set) para evitar duplicados automáticamente
    imagenes_unicas = set()

    # Recorremos TODOS los archivos de la carpeta y filtramos
    for archivo in carpeta.iterdir():
        # Solo nos interesan archivos (no subcarpetas)
        if not archivo.is_file():
            continue

        # Ignoramos archivos temporales de optimización (foto.tmp.jpg)
        if ".tmp." in archivo.name:
            continue

        # Sacamos la extensión sin el punto y en minúsculas
        # Ejemplo: "foto.JPG" → extension = "jpg"
        extension = archivo.suffix.lower().lstrip(".")

        # Si la extensión está en nuestra lista permitida, la añadimos
        if extension in EXTENSIONES_PERMITIDAS:
            imagenes_unicas.add(archivo)

    # Convertimos el conjunto a lista y ordenamos por fecha
    imagenes = list(imagenes_unicas)
    imagenes.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    return imagenes


def eliminar_imagen(ruta_imagen):
    """
    Elimina una imagen del disco.
    Recibe la ruta completa de la imagen a borrar.
    """
    ruta = Path(ruta_imagen)
    if ruta.exists():
        ruta.unlink()  # unlink() es como "borrar archivo"
        return True
    return False


# 5. FUNCIONES PARA GESTIÓN DE VERSIONES OPTIMIZADAS 

# A partir de la Fase 4, cada foto puede tener DOS versiones:
#   - Original  → datos/imagenes/[id_proyecto]/[archivo]
#   - Optimizada → datos/imagenes/[id_proyecto]/optimizadas/[archivo]
#
# La versión optimizada lleva EL MISMO NOMBRE que la original,
# así sabemos siempre qué optimizada corresponde a cada original.


def carpeta_optimizadas(proyecto):
    """
    Devuelve la ruta de la subcarpeta de imágenes optimizadas
    de un proyecto.

    Ejemplo:
      proyecto = {"id": "a1b2c3d4", ...}
      → datos/imagenes/a1b2c3d4/optimizadas
    """
    return carpeta_proyecto(proyecto) / "optimizadas"


def ruta_imagen_optimizada(ruta_original, proyecto):
    """
    Calcula dónde se debe guardar (o leer) la versión optimizada
    de una imagen original.

    Mantiene el mismo nombre de archivo, solo cambia la carpeta.

    Ejemplo:
      ruta_original = datos/imagenes/a1b2c3d4/foto1.jpg
      → datos/imagenes/a1b2c3d4/optimizadas/foto1.jpg
    """
    # Aseguramos que la subcarpeta existe 
    carpeta_dest = carpeta_optimizadas(proyecto)
    carpeta_dest.mkdir(parents=True, exist_ok=True)

    # Devolvemos la ruta con el mismo nombre del archivo original
    return carpeta_dest / Path(ruta_original).name


def existe_version_optimizada(ruta_original, proyecto):
    """
    Comprueba si una imagen ya tiene su versión optimizada en disco.

    Devuelve True si existe, False si no.
    Útil para no procesar dos veces la misma foto.
    """
    return ruta_imagen_optimizada(ruta_original, proyecto).exists()


# 6. LIMPIEZA DE ARCHIVOS TEMPORALES 

# La función guardar_imagen_cv() del módulo procesamiento/optimizar.py
# usa escritura atómica: primero escribe a un archivo .tmp.[ext] y
# luego lo renombra al nombre final. Si algo falla a mitad (caída de
# luz, proceso interrumpido), puede quedar un archivo huérfano.
# Esta función los detecta y los borra automáticamente.


def limpiar_archivos_temporales(proyecto):
    """
    Borra cualquier archivo temporal que pudiera haber quedado de
    procesos de optimización interrumpidos.

    Detecta archivos cuyo nombre contiene ".tmp." (por ejemplo:
    foto.tmp.jpg, paisaje.tmp.png), que es el patrón que usa
    guardar_imagen_cv() para escritura atómica.

    Se ejecuta automáticamente al listar las imágenes de un proyecto,
    como medida de higiene del sistema de archivos.
    """
    def es_temporal(archivo):
        """Decide si un archivo es un temporal huérfano de optimización."""
        # El patrón es: [nombre].tmp.[extension]
        # Ejemplo: foto.tmp.jpg → True
        # Ejemplo: foto.jpg     → False
        return ".tmp." in archivo.name

    # Limpiamos en la carpeta del proyecto
    carpeta_p = carpeta_proyecto(proyecto)
    if carpeta_p.exists():
        for archivo in carpeta_p.iterdir():
            if archivo.is_file() and es_temporal(archivo):
                try:
                    archivo.unlink()
                except OSError:
                    # Si no se puede borrar (permisos, etc.), seguimos
                    pass

    # Limpiamos también en la subcarpeta de optimizadas
    carpeta_opt = carpeta_optimizadas(proyecto)
    if carpeta_opt.exists():
        for archivo in carpeta_opt.iterdir():
            if archivo.is_file() and es_temporal(archivo):
                try:
                    archivo.unlink()
                except OSError:
                    pass

              
# 7. FUNCIONES PARA GESTIÓN DE CERTIFICADOS BLOCKCHAIN 

# Cuando el usuario certifica una foto optimizada, se genera un
# comprobante .ots de OpenTimestamps que se guarda en disco.
# Estructura:
#   datos/imagenes/[id_proyecto]/certificados/[nombre_foto].ots
# El comprobante .ots lleva el mismo nombre que la foto optimizada,
# pero con extensión .ots. Así sabemos qué certificado pertenece a
# qué foto.


def carpeta_certificados(proyecto):
    """
    Devuelve la ruta de la subcarpeta de certificados blockchain
    de un proyecto.

    Ejemplo:
      proyecto = {"id": "a1b2c3d4", ...}
      → datos/imagenes/a1b2c3d4/certificados
    """
    return carpeta_proyecto(proyecto) / "certificados"


def ruta_certificado(ruta_imagen, proyecto):
    """
    Calcula dónde se debe guardar (o leer) el comprobante .ots
    de una imagen.

    Mantiene el mismo nombre de la imagen, solo cambia la extensión
    a .ots y la carpeta a certificados/.

    Ejemplo:
      ruta_imagen = datos/imagenes/a1b2c3d4/optimizadas/foto.jpg
      → datos/imagenes/a1b2c3d4/certificados/foto.ots
    """
    # Aseguramos que la subcarpeta existe (la creamos si no)
    carpeta_dest = carpeta_certificados(proyecto)
    carpeta_dest.mkdir(parents=True, exist_ok=True)

    # Cambiamos la extensión del archivo a .ots
    nombre_ots = Path(ruta_imagen).stem + ".ots"
    return carpeta_dest / nombre_ots


def existe_certificado(ruta_imagen, proyecto):
    """
    Comprueba si una foto ya tiene un certificado blockchain.

    Devuelve True si existe el archivo .ots, False si no.
    """
    return ruta_certificado(ruta_imagen, proyecto).exists()


def guardar_comprobante(comprobante_bytes, ruta_imagen, proyecto):
    """
    Guarda en disco el comprobante .ots devuelto por OpenTimestamps.

    Parámetros:
      comprobante_bytes: contenido del archivo .ots como bytes.
      ruta_imagen: ruta de la imagen optimizada que se certificó.
      proyecto: diccionario con los datos del proyecto.

    Devuelve True si se guardó bien, False si falló.
    """
    if comprobante_bytes is None:
        return False

    try:
        ruta_dest = ruta_certificado(ruta_imagen, proyecto)
        ruta_dest.write_bytes(comprobante_bytes)
        return True
    except OSError:
        return False
    
   
# 8. CIERRE DE SESIÓN 


def cerrar_sesion():
    """
    Cierra la sesión del usuario actual.

    Limpia todas las variables relacionadas con el usuario y los
    proyectos en memoria, y vuelve a la pantalla de login.

    Es importante limpiar TODO para que el siguiente usuario que
    inicie sesión no vea por error datos del usuario anterior.
    """
    import streamlit as st

    # Vaciamos los datos del usuario
    st.session_state.usuario_logueado = False
    st.session_state.usuario_id = None
    st.session_state.usuario_email = None
    st.session_state.usuario_nombre = None

    # Limpiamos cualquier referencia a proyectos del usuario anterior
    st.session_state.proyecto_actual = None
    st.session_state.proyecto_a_borrar = None
    st.session_state.foto_a_borrar = None
    st.session_state.foto_certificado = None

    # Volvemos al login
    st.session_state.pagina = "login"