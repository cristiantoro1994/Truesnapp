# =====================================================================
# procesamiento/optimizar.py
# =====================================================================
# Pipeline de optimización de imágenes basado en OpenCV.
#
# Funciones individuales:
#   - leer_imagen:                 abre una imagen del disco
#   - guardar_imagen_cv:           guarda una imagen en disco con escritura atómica
#   - reducir_ruido:               reducción de ruido NLM (Non-Local Means)
#   - balancear_color:             balance de blancos automático (Gray World)
#   - ajustar_brillo_contraste:    CLAHE en canal L (espacio LAB)
#   - mejorar_nitidez:             unsharp masking
#
# Pipeline central:
#   - optimizar_imagen_opencv:     aplica todas las mejoras secuenciales
#   - optimizar_archivo:           lee, optimiza y guarda en una sola operación
#
# Funciones de Fase 6 (Paso 7):
#   - aplicar_marca_de_agua:       marca "TrueSnapp" en esquina inferior derecha
# =====================================================================

import cv2
import numpy as np
from pathlib import Path


# =====================================================================
# 1. LECTURA Y ESCRITURA DE IMÁGENES
# =====================================================================

def leer_imagen(ruta):
    """
    Lee una imagen desde disco soportando rutas con caracteres especiales
    (acentos, ñ, etc.) que cv2.imread no maneja bien en Windows.

    Devuelve la imagen como array de OpenCV (BGR), o None si falla.
    """
    try:
        ruta = Path(ruta)
        if not ruta.exists():
            return None

        # Lectura por bytes + decode para soportar acentos en la ruta
        with open(ruta, "rb") as f:
            datos = np.frombuffer(f.read(), dtype=np.uint8)

        imagen = cv2.imdecode(datos, cv2.IMREAD_COLOR)
        return imagen
    except Exception:
        return None


def guardar_imagen_cv(imagen, ruta):
    """
    Guarda una imagen en disco con escritura atómica.

    Escritura atómica:
      1. Escribe primero en un archivo temporal (.tmp.jpg).
      2. Solo cuando se ha escrito todo, renombra al nombre final.
    Esto evita que un fallo a mitad deje un archivo corrupto.

    IMPORTANTE: el archivo temporal lleva la extensión real al final
    (.tmp.jpg, .tmp.png) porque OpenCV identifica el formato por la
    extensión. Si fuera ".jpg.tmp", cv2.imencode fallaría.
    """
    if imagen is None:
        return False

    try:
        ruta = Path(ruta)

        # Aseguramos que la carpeta destino existe
        ruta.parent.mkdir(parents=True, exist_ok=True)

        # Construimos el nombre temporal: nombre.tmp.ext
        extension = ruta.suffix
        ruta_tmp = ruta.with_name(ruta.stem + ".tmp" + extension)

        # Codificamos la imagen al formato correspondiente
        exito, datos = cv2.imencode(extension, imagen)
        if not exito:
            return False

        # Escribimos los bytes al archivo temporal
        with open(ruta_tmp, "wb") as f:
            f.write(datos.tobytes())

        # Si el archivo final ya existe, lo borramos antes del rename
        # (Windows no permite overwrite con rename)
        if ruta.exists():
            ruta.unlink()

        # Renombrado atómico
        ruta_tmp.rename(ruta)

        return True
    except Exception:
        return False


# =====================================================================
# 2. ALGORITMOS DE OPTIMIZACIÓN (FASE 4)
# =====================================================================

def reducir_ruido(imagen):
    """
    Reducción de ruido con NLM (Non-Local Means).

    h=10 es un valor moderado: limpia el ruido sin eliminar
    detalles importantes (texturas, granos finos).
    """
    return cv2.fastNlMeansDenoisingColored(
        imagen,
        None,
        h=10,
        hColor=10,
        templateWindowSize=7,
        searchWindowSize=21,
    )


def balancear_color(imagen):
    """
    Balance de blancos automático (Gray World).

    Asume que la media de cada canal de color debería ser
    aproximadamente igual. Corrige dominantes de color (ej:
    amarillento de bombillas, azulado de día nublado).
    """
    resultado = imagen.astype(np.float32)

    # Media de cada canal (B, G, R)
    media_b = np.mean(resultado[:, :, 0])
    media_g = np.mean(resultado[:, :, 1])
    media_r = np.mean(resultado[:, :, 2])

    # Media global de la imagen
    media_global = (media_b + media_g + media_r) / 3.0

    # Aplicamos el factor de corrección a cada canal
    if media_b > 0:
        resultado[:, :, 0] *= media_global / media_b
    if media_g > 0:
        resultado[:, :, 1] *= media_global / media_g
    if media_r > 0:
        resultado[:, :, 2] *= media_global / media_r

    # Recortamos al rango válido [0, 255] y volvemos a uint8
    resultado = np.clip(resultado, 0, 255).astype(np.uint8)
    return resultado


def ajustar_brillo_contraste(imagen):
    """
    Ajuste de brillo y contraste con CLAHE en el canal L.

    CLAHE (Contrast Limited Adaptive Histogram Equalization) trabaja
    en el espacio LAB para no alterar los colores, y aplica el ajuste
    por zonas locales en lugar de globalmente. Resultados naturales
    sin "saturación falsa".
    """
    # Convertimos BGR -> LAB
    lab = cv2.cvtColor(imagen, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # CLAHE solo en el canal de luminosidad (L)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_mejorado = clahe.apply(l)

    # Recombinamos y volvemos a BGR
    lab_mejorado = cv2.merge([l_mejorado, a, b])
    resultado = cv2.cvtColor(lab_mejorado, cv2.COLOR_LAB2BGR)
    return resultado


def mejorar_nitidez(imagen):
    """
    Mejora de nitidez con unsharp masking.

    Es la técnica clásica usada en Photoshop, Lightroom, etc.:
      1. Crea una versión borrosa de la imagen.
      2. La resta de la original (resaltando los bordes).
      3. Suma el resultado a la original.
    """
    # Versión borrosa (blur gaussiano)
    borrosa = cv2.GaussianBlur(imagen, (0, 0), sigmaX=2.0)

    # Combinación: original * 1.5 - borrosa * 0.5
    resultado = cv2.addWeighted(imagen, 1.5, borrosa, -0.5, 0)
    return resultado


# =====================================================================
# 3. PIPELINE CENTRAL
# =====================================================================

def optimizar_imagen_opencv(imagen):
    """
    Aplica el pipeline completo de OpenCV en orden:
      1. Reducción de ruido (limpieza primero, antes de realzar)
      2. Balance de color (corrección de dominantes)
      3. Brillo/contraste (CLAHE)
      4. Nitidez (último: realza los detalles ya corregidos)
    """
    if imagen is None:
        return None

    imagen = reducir_ruido(imagen)
    imagen = balancear_color(imagen)
    imagen = ajustar_brillo_contraste(imagen)
    imagen = mejorar_nitidez(imagen)
    return imagen


def optimizar_archivo(ruta_origen, ruta_destino):
    """
    Lee, optimiza y guarda en una sola llamada.
    Útil para automatizar fuera del flujo de la galería.
    """
    imagen = leer_imagen(ruta_origen)
    if imagen is None:
        return False

    optimizada = optimizar_imagen_opencv(imagen)
    if optimizada is None:
        return False

    return guardar_imagen_cv(optimizada, ruta_destino)


# =====================================================================
# 4. MARCA DE AGUA "TrueSnapp" (FASE 6 - PASO 7)
# =====================================================================
# Aplica una marca de agua con el nombre de la app en la esquina
# inferior derecha de la imagen optimizada.
#
# Implementación: OpenCV nativo (cv2.putText).
# - No depende de fuentes del sistema (en Windows con Python 3.14
#   las fuentes TrueType pueden fallar al cargarse).
# - Más rápido que PIL.
# - Funciona en cualquier sistema operativo, incluido Streamlit Cloud.
#
# Decisiones de diseño:
#   - Solo se aplica a la versión optimizada (no a la original).
#   - El tamaño es proporcional al ancho de la imagen para que se
#     vea bien tanto en fotos pequeñas como grandes.
#   - Texto blanco con sombra negra para legibilidad en cualquier fondo.
# =====================================================================

TEXTO_MARCA = "TrueSnapp"

# Proporción del texto respecto al ancho de la imagen
# Para imágenes de 1000px de ancho → escala ~1.8 (legible)
# Para imágenes de 4000px de ancho → escala ~7.2 (legible)
PROPORCION_TEXTO = 0.0018

# Margen desde los bordes (2.5% del ancho)
PROPORCION_MARGEN = 0.025


def aplicar_marca_de_agua(imagen_cv):
    """
    Aplica la marca de agua "TrueSnapp" a una imagen.

    Recibe la imagen en formato OpenCV (BGR) y devuelve la imagen
    con la marca aplicada en formato OpenCV.

    Estrategia:
      1. Calcula tamaño de fuente proporcional al ancho.
      2. Calcula posición en la esquina inferior derecha.
      3. Dibuja la sombra (texto negro desplazado).
      4. Dibuja el texto principal blanco encima.

    Devuelve:
      - Imagen OpenCV con la marca aplicada (numpy array, BGR).
      - La imagen original sin cambios si hay error.
    """
    if imagen_cv is None:
        return imagen_cv

    try:
        # Trabajamos sobre una copia para no modificar el original
        imagen = imagen_cv.copy()
        alto, ancho = imagen.shape[:2]

        # ----- 1. Configurar fuente y tamaño -----
        # Fuente nativa de OpenCV (siempre disponible)
        fuente = cv2.FONT_HERSHEY_SIMPLEX

        # Tamaño proporcional al ancho de la imagen
        escala = max(ancho * PROPORCION_TEXTO, 0.8)

        # Grosor proporcional a la escala
        grosor = max(int(escala * 1.5), 2)

        # ----- 2. Medir el texto -----
        (ancho_texto, alto_texto), _ = cv2.getTextSize(
            TEXTO_MARCA,
            fuente,
            escala,
            grosor,
        )

        # ----- 3. Calcular posición (esquina inferior derecha) -----
        margen = int(ancho * PROPORCION_MARGEN)
        x = ancho - ancho_texto - margen
        y = alto - margen  # En OpenCV, y es la línea base del texto

        # ----- 4. Dibujar la sombra (negro, desplazada) -----
        # Hace que el texto se vea bien en cualquier fondo
        desplazamiento = max(int(escala), 1)
        cv2.putText(
            imagen,
            TEXTO_MARCA,
            (x + desplazamiento, y + desplazamiento),
            fuente,
            escala,
            (0, 0, 0),  # Negro en BGR
            grosor + 1,
            cv2.LINE_AA,
        )

        # ----- 5. Dibujar el texto principal (blanco) -----
        cv2.putText(
            imagen,
            TEXTO_MARCA,
            (x, y),
            fuente,
            escala,
            (255, 255, 255),  # Blanco en BGR
            grosor,
            cv2.LINE_AA,
        )

        return imagen

    except Exception as error:
        print(f"[Marca de agua] Error: {error}")
        return imagen_cv