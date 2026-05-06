# Gestión de proyectos en la base de datos.
# Todas las operaciones CRUD se realizan contra la tabla "proyectos"
# de SQLite, y SIEMPRE se filtra por usuario_id para garantizar el
# aislamiento entre cuentas.
# Estructura de un proyecto en la BD:
#   - id: TEXT (8 caracteres aleatorios, los mismos que las carpetas)
#   - usuario_id: INTEGER (a quién pertenece el proyecto)
#   - nombre: TEXT (nombre legible para el usuario)
#   - fecha_creacion: TIMESTAMP (cuándo se creó)


import uuid

from utils.base_datos import (
    ejecutar_consulta,
    ejecutar_modificacion,
)


# 1. Crear un proyecto nuevo


def crear_proyecto(usuario_id, nombre):
    """
    Crea un proyecto nuevo en la base de datos.

    Genera un ID único de 8 caracteres (los mismos que ya usábamos
    para las carpetas en disco) y lo asocia al usuario indicado.

    Parámetros:
      usuario_id: id numérico del usuario propietario.
      nombre: nombre legible del proyecto.

    Devuelve:
      (True, datos_proyecto) si se creó correctamente.
      (False, mensaje_error) si hubo problemas.

    datos_proyecto es un diccionario con: id, nombre, fecha_creacion.
    """
    # ----- Validaciones -----
    nombre = nombre.strip() if nombre else ""
    if not nombre:
        return False, "El nombre del proyecto no puede estar vacío."

    if usuario_id is None:
        return False, "Usuario no identificado. Vuelve a iniciar sesión."

    #  Generamos el ID único 
    proyecto_id = uuid.uuid4().hex[:8]

    #  Insertamos en la BD 
    try:
        ejecutar_modificacion(
            """
            INSERT INTO proyectos (id, usuario_id, nombre)
            VALUES (?, ?, ?)
            """,
            (proyecto_id, usuario_id, nombre),
        )

        return True, {
            "id": proyecto_id,
            "nombre": nombre,
            "usuario_id": usuario_id,
        }
    except Exception as error:
        return False, f"No se pudo crear el proyecto: {error}"


# 2. Listar los proyectos de un usuario

def listar_proyectos_usuario(usuario_id):
    """
    Devuelve la lista de proyectos del usuario indicado.

    Solo devuelve proyectos cuyo usuario_id coincide. Esto es la
    base del aislamiento: ningún usuario puede ver proyectos de otro.

    Devuelve:
      Lista de diccionarios con: id, nombre, fecha_creacion.
      Lista vacía si el usuario no tiene proyectos.
    """
    if usuario_id is None:
        return []

    filas = ejecutar_consulta(
        """
        SELECT id, nombre, fecha_creacion
        FROM proyectos
        WHERE usuario_id = ?
        ORDER BY fecha_creacion DESC
        """,
        (usuario_id,),
    )

    # Convertimos cada fila a un diccionario
    return [
        {
            "id": fila["id"],
            "nombre": fila["nombre"],
            "fecha_creacion": fila["fecha_creacion"],
        }
        for fila in filas
    ]


# 3. Obtener un proyecto concreto (con verificación de propiedad)


def obtener_proyecto(proyecto_id, usuario_id):
    """
    Devuelve los datos de un proyecto SI pertenece al usuario.

    IMPORTANTE: comprobamos siempre que el proyecto pertenece al
    usuario que lo solicita. Si un usuario manipulara la URL o el
    estado para acceder a un proyecto ajeno, esta función devolvería
    None y la app mostraría "proyecto no encontrado".

    Devuelve:
      Diccionario con datos del proyecto si existe Y pertenece al
      usuario. None en caso contrario.
    """
    if usuario_id is None or not proyecto_id:
        return None

    filas = ejecutar_consulta(
        """
        SELECT id, nombre, fecha_creacion
        FROM proyectos
        WHERE id = ? AND usuario_id = ?
        """,
        (proyecto_id, usuario_id),
    )

    if not filas:
        return None

    fila = filas[0]
    return {
        "id": fila["id"],
        "nombre": fila["nombre"],
        "fecha_creacion": fila["fecha_creacion"],
        "usuario_id": usuario_id,
    }


# 4. Eliminar un proyecto (con verificación de propiedad)


def eliminar_proyecto(proyecto_id, usuario_id):
    """
    Borra un proyecto de la base de datos SI pertenece al usuario.

    Solo elimina la entrada de la tabla "proyectos". Las fotos en
    disco no se borran aquí (se gestionan desde el dashboard al
    eliminar la carpeta).

    Devuelve:
      True si se eliminó, False si no existía o no pertenecía al usuario.
    """
    if usuario_id is None or not proyecto_id:
        return False

    filas_afectadas = ejecutar_modificacion(
        """
        DELETE FROM proyectos
        WHERE id = ? AND usuario_id = ?
        """,
        (proyecto_id, usuario_id),
    )

    return filas_afectadas > 0


# 5. Verificar propiedad (utilidad para otras pantallas)


def usuario_es_dueno(proyecto_id, usuario_id):
    """
    Comprueba si un proyecto pertenece a un usuario.

    Útil para pantallas que reciben un proyecto_id (galería, certificado)
    y necesitan validar el acceso antes de mostrar nada.

    Devuelve True si el proyecto pertenece al usuario, False si no.
    """
    return obtener_proyecto(proyecto_id, usuario_id) is not None