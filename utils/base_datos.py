# Gestión de la base de datos SQLite para TrueSnapp.
# Estructura:
#   - Tabla usuarios:  cuentas registradas con contraseñas cifradas.
#   - Tabla proyectos: proyectos asociados a cada usuario.
#
# La base de datos se guarda en: datos/truesnapp.db
# (El archivo está excluido del control de versiones via .gitignore.)
#
# Este módulo expone funciones de bajo nivel para conectarse a la BD.
# Las consultas concretas (registrar usuario, listar proyectos, etc.)
# se construyen en módulos especializados:
#   - utils/usuarios.py    
#   - utils/proyectos.py   


import sqlite3
from pathlib import Path


# Constantes


# Carpeta donde guardamos la base de datos (la misma que las imágenes)
CARPETA_DATOS = Path("datos")

# Ruta completa del archivo de la base de datos
RUTA_BASE_DATOS = CARPETA_DATOS / "truesnapp.db"


# 1. Inicialización: crear la base de datos y las tablas


def inicializar_base_datos():
    """
    Crea la base de datos y las tablas si no existen.

    Se llama UNA vez al arrancar la app (desde app.py).
    Es una operación idempotente: si las tablas ya existen, no hace nada.

    Tablas que crea:
      - usuarios
      - proyectos
    """
    # Aseguramos que la carpeta datos/ existe
    CARPETA_DATOS.mkdir(parents=True, exist_ok=True)

    # Abrimos conexión y creamos las tablas
    with obtener_conexion() as conn:
        cursor = conn.cursor()

        # ----- Tabla usuarios -----
        # email es UNIQUE: no puede haber dos usuarios con el mismo email
        # contrasena_hash guarda el hash bcrypt (NO la contraseña real)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                contrasena_hash TEXT NOT NULL,
                nombre TEXT NOT NULL,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ----- Tabla proyectos -----
        # id es TEXT (los 8 caracteres aleatorios que ya generamos en
        # la Fase 3 con uuid.uuid4().hex[:8])
        # usuario_id es la clave foránea: indica a quién pertenece
        # ON DELETE CASCADE: si se borra un usuario, sus proyectos
        # también se borran automáticamente (pero NO usamos ON DELETE
        # USER por ahora; lo dejamos como referencia simple)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proyectos (
                id TEXT PRIMARY KEY,
                usuario_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        """)

        # ----- Índice para búsquedas rápidas -----
        # Cuando listemos los proyectos de un usuario, buscaremos por
        # usuario_id. Un índice acelera mucho esa búsqueda en el futuro.
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_proyectos_usuario
            ON proyectos (usuario_id)
        """)

        # Confirmamos los cambios en la base de datos
        conn.commit()

# 2. Obtener una conexión a la base de datos


def obtener_conexion():
    """
    Abre una nueva conexión a la base de datos.

    Importante: usar siempre con "with" para que se cierre automáticamente:

        with obtener_conexion() as conn:
            cursor = conn.cursor()
            ...

    Devuelve:
      Objeto Connection de sqlite3.
    """
    # Creamos la carpeta si aún no existe (defensa en profundidad)
    CARPETA_DATOS.mkdir(parents=True, exist_ok=True)

    # Abrimos la conexión
    # check_same_thread=False permite usar la conexión desde varios
    # threads (Streamlit la necesita para los reruns)
    conn = sqlite3.connect(
        str(RUTA_BASE_DATOS),
        check_same_thread=False,
    )

    # Configuramos para que las filas se devuelvan como diccionarios
    # En lugar de:  fila[0], fila[1], ...
    # Podremos usar: fila["email"], fila["nombre"], ...
    conn.row_factory = sqlite3.Row

    # Activamos las claves foráneas (en SQLite están desactivadas por
    # defecto por compatibilidad con versiones antiguas)
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# 3. Funciones auxiliares para consultas comunes

def ejecutar_consulta(sql, parametros=None):
    """
    Ejecuta una consulta SELECT y devuelve TODAS las filas.

    IMPORTANTE: usar siempre parámetros para evitar inyección SQL.

    Ejemplo correcto:
      ejecutar_consulta(
          "SELECT * FROM usuarios WHERE email = ?",
          (email,)
      )

    Ejemplo INCORRECTO (vulnerable):
      ejecutar_consulta(f"SELECT * FROM usuarios WHERE email = '{email}'")
    """
    if parametros is None:
        parametros = ()

    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, parametros)
        return cursor.fetchall()


def ejecutar_modificacion(sql, parametros=None):
    """
    Ejecuta una consulta INSERT, UPDATE o DELETE.

    Devuelve el id de la fila insertada (útil para INSERT) o
    el número de filas afectadas (para UPDATE/DELETE).
    """
    if parametros is None:
        parametros = ()

    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, parametros)
        conn.commit()

        # Para INSERT: devolvemos el id del registro creado
        if sql.strip().upper().startswith("INSERT"):
            return cursor.lastrowid
        # Para UPDATE/DELETE: devolvemos cuántas filas se afectaron
        return cursor.rowcount