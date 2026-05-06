# Gestión de usuarios de TrueSnapp:
#   - Cifrado profesional de contraseñas (bcrypt)
#   - Registro de nuevos usuarios
#   - Autenticación (login)
#   - Validación de email y contraseña
#
# IMPORTANTE: las contraseñas NUNCA se guardan en texto plano.
# Siempre se cifran con bcrypt antes de tocar la base de datos.


import re
import bcrypt

from utils.base_datos import (
    ejecutar_consulta,
    ejecutar_modificacion,
)


# Constantes

# Longitud mínima de contraseña (estándar de buena práctica)
LONGITUD_MINIMA_CONTRASENA = 8

# Patrón para validar emails (formato básico user@dominio.tld)
PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# 1. Cifrado de contraseñas con bcrypt

def cifrar_contrasena(contrasena):
    """
    Convierte una contraseña en texto plano a un hash bcrypt seguro.

    El hash NO se puede revertir: ni siquiera nosotros podemos saber
    cuál era la contraseña original.

    bcrypt añade automáticamente un "salt" aleatorio a cada contraseña,
    así que dos usuarios con la misma contraseña tendrán hashes
    completamente distintos.

    Devuelve un string con el hash (formato: $2b$12$XXXX...).
    """
    # bcrypt trabaja con bytes, no con strings
    contrasena_bytes = contrasena.encode("utf-8")

    # Generamos un salt nuevo y aleatorio
    # rounds=12 es el estándar profesional (más alto = más seguro
    # pero más lento; 12 es buen equilibrio)
    salt = bcrypt.gensalt(rounds=12)

    # Ciframos la contraseña con el salt
    hash_bytes = bcrypt.hashpw(contrasena_bytes, salt)

    # Devolvemos como string para guardar en la BD
    return hash_bytes.decode("utf-8")


def verificar_contrasena(contrasena, hash_guardado):
    """
    Comprueba si una contraseña coincide con un hash guardado.

    Útil para el login: el usuario escribe su contraseña, la
    comparamos con el hash que guardamos al registrarse.

    Devuelve True si coincide, False si no (o si hay error).
    """
    try:
        # Convertimos ambos a bytes
        contrasena_bytes = contrasena.encode("utf-8")
        hash_bytes = hash_guardado.encode("utf-8")

        # bcrypt.checkpw hace la comparación de forma segura
        return bcrypt.checkpw(contrasena_bytes, hash_bytes)
    except Exception:
        # Si hay cualquier error (hash corrupto, etc.), denegamos acceso
        return False


# 2. Validación de datos


def validar_email(email):
    """
    Comprueba que el email tenga formato válido.
    Devuelve (True, "") si es válido, o (False, mensaje_error) si no.
    """
    if not email:
        return False, "El email no puede estar vacío."

    email = email.strip().lower()

    if not PATRON_EMAIL.match(email):
        return False, "El email no tiene un formato válido."

    return True, ""


def validar_contrasena(contrasena):
    """
    Comprueba que la contraseña cumpla los requisitos mínimos.
    Devuelve (True, "") si es válida, o (False, mensaje_error) si no.
    """
    if not contrasena:
        return False, "La contraseña no puede estar vacía."

    if len(contrasena) < LONGITUD_MINIMA_CONTRASENA:
        return False, (
            f"La contraseña debe tener al menos "
            f"{LONGITUD_MINIMA_CONTRASENA} caracteres."
        )

    return True, ""


# 3. Registro de usuarios


def existe_email(email):
    """
    Comprueba si un email ya está registrado en la base de datos.
    Devuelve True si ya existe, False si no.
    """
    email = email.strip().lower()

    filas = ejecutar_consulta(
        "SELECT id FROM usuarios WHERE email = ?",
        (email,),
    )

    return len(filas) > 0


def registrar_usuario(email, contrasena, nombre):
    """
    Crea un nuevo usuario en la base de datos.

    Pasos:
      1. Valida email y contraseña.
      2. Comprueba que el email no esté ya registrado.
      3. Cifra la contraseña con bcrypt.
      4. Inserta el usuario en la base de datos.

    Parámetros:
      email: email del usuario.
      contrasena: contraseña en texto plano (se ciframos al guardar).
      nombre: nombre para saludar (ej: "Cristian").

    Devuelve:
      (True, mensaje_exito) si se registró correctamente.
      (False, mensaje_error) si hubo algún problema.
    """
    # ----- Validar email -----
    email = email.strip().lower()
    valido_email, error_email = validar_email(email)
    if not valido_email:
        return False, error_email

    # ----- Validar contraseña -----
    valido_pass, error_pass = validar_contrasena(contrasena)
    if not valido_pass:
        return False, error_pass

    # ----- Validar nombre -----
    nombre = nombre.strip() if nombre else ""
    if not nombre:
        return False, "El nombre no puede estar vacío."

    # ----- Verificar que el email no exista -----
    if existe_email(email):
        return False, "Ya existe una cuenta con este email."

    # ----- Cifrar contraseña y guardar -----
    try:
        hash_contrasena = cifrar_contrasena(contrasena)

        ejecutar_modificacion(
            """
            INSERT INTO usuarios (email, contrasena_hash, nombre)
            VALUES (?, ?, ?)
            """,
            (email, hash_contrasena, nombre),
        )

        return True, "Cuenta creada correctamente."
    except Exception as error:
        return False, f"No se pudo crear la cuenta: {error}"


# 4. Autenticación (login)


def autenticar_usuario(email, contrasena):
    """
    Verifica las credenciales de un usuario.

    Pasos:
      1. Busca el usuario por email.
      2. Compara la contraseña con el hash guardado.
      3. Si coincide, devuelve los datos del usuario.

    IMPORTANTE: nunca revelamos si el email existe o no.
    Si las credenciales son incorrectas, mostramos un mensaje
    genérico para no dar pistas a posibles atacantes.

    Devuelve:
      (True, datos_usuario) si las credenciales son correctas.
      (False, mensaje_error) si no.

    datos_usuario es un diccionario con: id, email, nombre.
    """
    email = email.strip().lower()

    if not email or not contrasena:
        return False, "Introduce email y contraseña."

    # Buscar el usuario por email
    filas = ejecutar_consulta(
        "SELECT id, email, nombre, contrasena_hash FROM usuarios WHERE email = ?",
        (email,),
    )

    # Si no existe, devolvemos error genérico 
    if not filas:
        return False, "Email o contraseña incorrectos."

    usuario = filas[0]

    # Verificar la contraseña
    if not verificar_contrasena(contrasena, usuario["contrasena_hash"]):
        return False, "Email o contraseña incorrectos."

    # Credenciales correctas: devolvemos los datos básicos
    datos_usuario = {
        "id": usuario["id"],
        "email": usuario["email"],
        "nombre": usuario["nombre"],
    }

    return True, datos_usuario