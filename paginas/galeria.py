# =====================================================================
# paginas/galeria.py
# =====================================================================
# Galería de imágenes de un proyecto.
#
# El usuario puede:
#   - Ver todas las fotos del proyecto en una rejilla
#   - Subir nuevas fotos (desde móvil o escritorio)
#   - Optimizar fotos con OpenCV + IA Real-ESRGAN (Fase 4)
#   - Marca de agua "TrueSnapp" automática (Fase 6)
#   - Comparar original/optimizada con slider deslizante
#   - Re-optimizar (borra solo la versión optimizada y reprocesa)
#   - Certificar fotos en blockchain (Fase 5)
#   - Ver el certificado de las fotos ya certificadas
#   - Eliminar fotos con doble confirmación
# =====================================================================

import streamlit as st
from streamlit_image_comparison import image_comparison

from utils.helpers import (
    guardar_imagen,
    listar_imagenes,
    eliminar_imagen,
    ruta_imagen_optimizada,
    existe_version_optimizada,
    limpiar_archivos_temporales,
    ruta_certificado,
    existe_certificado,
    guardar_comprobante,
)

from procesamiento.optimizar import (
    leer_imagen,
    guardar_imagen_cv,
    reducir_ruido,
    balancear_color,
    ajustar_brillo_contraste,
    mejorar_nitidez,
    aplicar_marca_de_agua,
)

from procesamiento.optimizar_ia import (
    hay_clave_replicate,
    optimizar_con_ia,
)

from blockchain.certificar import calcular_hash
from blockchain.registrar_blockchain import (
    registrar_hash_en_blockchain,
    opentimestamps_disponible,
)


def mostrar():
    """Muestra la galería de imágenes del proyecto seleccionado."""

    if st.button("← Volver", key="volver_galeria"):
        st.session_state.foto_a_borrar = None
        st.session_state.pagina = "dashboard"
        st.rerun()

    proyecto = obtener_proyecto_actual()

    if proyecto is None:
        st.warning("No se encontró el proyecto. Volviendo al dashboard...")
        st.session_state.pagina = "dashboard"
        st.rerun()
        return

    limpiar_archivos_temporales(proyecto)

    st.markdown(f"## 🏠 {proyecto['nombre']}")

    st.markdown("### 📤 Subir fotos")

    archivos_subidos = st.file_uploader(
        label="Arrastra tus fotos aquí o pulsa para seleccionarlas",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"uploader_{proyecto['id']}",
    )

    if archivos_subidos:
        procesar_archivos_subidos(archivos_subidos, proyecto)

    st.markdown("---")

    imagenes = listar_imagenes(proyecto)
    total = len(imagenes)

    st.markdown(f"### 📷 Galería ({total} fotos)")

    if total == 0:
        st.info(
            "Aún no has subido ninguna foto a este proyecto. "
            "Usa el botón de arriba para añadir las primeras."
        )
    else:
        mostrar_rejilla_imagenes(imagenes, proyecto)


def obtener_proyecto_actual():
    """Devuelve el proyecto seleccionado, verificando propiedad."""
    from utils.proyectos import obtener_proyecto

    proyecto_id = st.session_state.get("proyecto_actual")
    usuario_id = st.session_state.get("usuario_id")

    if proyecto_id is None or usuario_id is None:
        return None

    return obtener_proyecto(proyecto_id, usuario_id)


def procesar_archivos_subidos(archivos_subidos, proyecto):
    """Guarda en el disco las fotos nuevas (sin duplicar)."""
    clave_estado = f"archivos_procesados_{proyecto['id']}"

    if clave_estado not in st.session_state:
        st.session_state[clave_estado] = set()

    procesados = st.session_state[clave_estado]
    cantidad_guardada = 0

    for archivo in archivos_subidos:
        if archivo.file_id in procesados:
            continue

        try:
            guardar_imagen(archivo, proyecto)
            procesados.add(archivo.file_id)
            cantidad_guardada += 1
        except Exception as error:
            st.error(f"Error al guardar **{archivo.name}**: {error}")

    if cantidad_guardada > 0:
        st.success(f"✅ {cantidad_guardada} foto(s) guardada(s) correctamente.")
        st.session_state.foto_a_borrar = None
        st.rerun()


def mostrar_rejilla_imagenes(imagenes, proyecto):
    """Muestra las imágenes en una rejilla de 3 columnas."""
    columnas_por_fila = 3

    for i in range(0, len(imagenes), columnas_por_fila):
        cols = st.columns(columnas_por_fila)

        for j in range(columnas_por_fila):
            indice = i + j
            if indice < len(imagenes):
                ruta_imagen = imagenes[indice]
                with cols[j]:
                    mostrar_miniatura_completa(ruta_imagen, proyecto)


def mostrar_miniatura_completa(ruta_imagen, proyecto):
    """Muestra una miniatura de la imagen + botones de acción."""
    id_foto = str(ruta_imagen)

    foto_pendiente = st.session_state.get("foto_a_borrar", None)

    if foto_pendiente == id_foto:
        st.image(str(ruta_imagen), use_container_width=True)
        st.warning("¿Seguro? Pulsa otra vez para borrar.")
        if st.button("🗑️ Confirmar borrado", key=f"confirmar_{id_foto}"):
            eliminar_foto_completa(ruta_imagen, proyecto)
        return

    optimizada = existe_version_optimizada(ruta_imagen, proyecto)

    if optimizada:
        ruta_optimizada = ruta_imagen_optimizada(ruta_imagen, proyecto)

        image_comparison(
            img1=str(ruta_imagen),
            img2=str(ruta_optimizada),
            label1="Original",
            label2="✨ Optimizada",
            width=300,
            starting_position=50,
            show_labels=True,
            make_responsive=True,
            in_memory=True,
        )
    else:
        st.image(str(ruta_imagen), use_container_width=True)

    nombre_limpio = quitar_id_del_nombre(ruta_imagen.name)
    st.markdown(
        f"<p style='font-size: 0.75rem; color: #A0A6AC; "
        f"text-align: center; margin: 0.4rem 0 0.3rem 0;'>"
        f"{nombre_limpio}</p>",
        unsafe_allow_html=True,
    )

    if optimizada:
        st.markdown(
            "<p style='text-align: center; color: #27AE60; "
            "font-size: 0.85rem; font-weight: 600; margin: 0.3rem 0;'>"
            "✅ Optimizada</p>",
            unsafe_allow_html=True,
        )

        certificada = existe_certificado(ruta_imagen, proyecto)

        if certificada:
            if st.button(
                "🔐 Ver certificado",
                key=f"vercertificado_{id_foto}",
                use_container_width=True,
            ):
                st.session_state.foto_certificado = id_foto
                st.session_state.pagina = "certificado"
                st.rerun()
        else:
            if st.button("🔐 Certificar", key=f"certificar_{id_foto}"):
                certificar_foto(ruta_imagen, proyecto)

        if st.button("🔄 Re-optimizar", key=f"reoptimizar_{id_foto}"):
            reoptimizar_foto(ruta_imagen, proyecto)
    else:
        if st.button("✨ Optimizar", key=f"optimizar_{id_foto}"):
            optimizar_foto(ruta_imagen, proyecto)

    if st.button("🗑️ Borrar", key=f"borrar_{id_foto}"):
        st.session_state.foto_a_borrar = id_foto
        st.rerun()


def optimizar_foto(ruta_imagen, proyecto):
    """
    Pipeline híbrido completo:
      Capa 1: OpenCV (siempre)
      Capa 2: Real-ESRGAN (si hay clave Replicate)
      Capa 3: Marca de agua TrueSnapp (siempre, al final)
    """
    import time

    ruta_destino = ruta_imagen_optimizada(ruta_imagen, proyecto)
    ruta_intermedia = ruta_imagen_optimizada(ruta_imagen, proyecto)

    usar_ia = hay_clave_replicate()

    contenedor_mensaje = st.empty()
    barra_progreso = st.progress(0)

    try:
        contenedor_mensaje.info("🧹 Limpiando ruido de la imagen...")
        barra_progreso.progress(10)

        imagen = leer_imagen(ruta_imagen)
        if imagen is None:
            contenedor_mensaje.error("No se pudo leer la imagen. Inténtalo de nuevo.")
            return

        imagen = reducir_ruido(imagen)
        barra_progreso.progress(20 if usar_ia else 30)
        time.sleep(0.2)

        contenedor_mensaje.info("🎨 Equilibrando los colores...")
        imagen = balancear_color(imagen)
        barra_progreso.progress(35 if usar_ia else 45)
        time.sleep(0.2)

        contenedor_mensaje.info("💡 Mejorando la iluminación...")
        imagen = ajustar_brillo_contraste(imagen)
        barra_progreso.progress(45 if usar_ia else 65)
        time.sleep(0.2)

        contenedor_mensaje.info("🔪 Realzando los detalles...")
        imagen = mejorar_nitidez(imagen)
        barra_progreso.progress(55 if usar_ia else 80)
        time.sleep(0.2)

        if usar_ia:
            guardar_imagen_cv(imagen, ruta_intermedia)

            contenedor_mensaje.info("🤖 Aplicando IA profesional (Real-ESRGAN)...")
            barra_progreso.progress(70)

            imagen_ia = optimizar_con_ia(ruta_intermedia)

            if imagen_ia is not None:
                imagen = imagen_ia
                contenedor_mensaje.success("✨ ¡IA aplicada correctamente!")
            else:
                contenedor_mensaje.warning(
                    "⚠️ La IA no estuvo disponible. "
                    "Se usará el resultado de la optimización clásica."
                )

            barra_progreso.progress(85)
            time.sleep(0.4)

        # ----- Marca de agua "TrueSnapp" (Fase 6 - Paso 7) -----
        contenedor_mensaje.info("🏷️ Aplicando marca de agua TrueSnapp...")
        imagen = aplicar_marca_de_agua(imagen)
        barra_progreso.progress(95)
        time.sleep(0.2)

        contenedor_mensaje.info("💾 Guardando la versión optimizada...")
        guardar_imagen_cv(imagen, ruta_destino)
        barra_progreso.progress(100)
        time.sleep(0.3)

        contenedor_mensaje.success("✅ ¡Foto optimizada correctamente!")
        time.sleep(0.6)
        st.rerun()

    except Exception as error:
        contenedor_mensaje.error(f"Error al optimizar: {error}")
        barra_progreso.empty()


def certificar_foto(ruta_imagen, proyecto):
    """Certifica una foto optimizada en blockchain."""
    import time

    ruta_optimizada = ruta_imagen_optimizada(ruta_imagen, proyecto)

    contenedor_mensaje = st.empty()
    barra_progreso = st.progress(0)

    try:
        contenedor_mensaje.info("🔍 Verificando conexión con la red...")
        barra_progreso.progress(10)

        if not opentimestamps_disponible():
            contenedor_mensaje.error(
                "⚠️ No se pudo conectar con la red blockchain. "
                "Asegúrate de que OpenTimestamps está instalado."
            )
            barra_progreso.empty()
            return

        time.sleep(0.3)

        contenedor_mensaje.info("🧬 Calculando huella digital de la foto...")
        barra_progreso.progress(30)

        hash_foto = calcular_hash(ruta_optimizada)

        if hash_foto is None:
            contenedor_mensaje.error("❌ No se pudo leer la imagen optimizada.")
            barra_progreso.empty()
            return

        time.sleep(0.3)

        contenedor_mensaje.info(
            "🪙 Registrando en la blockchain de Bitcoin... "
            "(esto puede tardar 5-30 segundos)"
        )
        barra_progreso.progress(60)

        comprobante = registrar_hash_en_blockchain(hash_foto)

        if comprobante is None:
            contenedor_mensaje.warning(
                "⚠️ No se pudo registrar en blockchain en este momento. "
                "Inténtalo de nuevo en unos minutos."
            )
            barra_progreso.empty()
            return

        barra_progreso.progress(85)

        contenedor_mensaje.info("💾 Guardando el certificado...")

        exito = guardar_comprobante(comprobante, ruta_imagen, proyecto)

        if not exito:
            contenedor_mensaje.error("❌ No se pudo guardar el certificado en disco.")
            barra_progreso.empty()
            return

        barra_progreso.progress(100)
        time.sleep(0.4)

        contenedor_mensaje.success("✅ ¡Foto certificada en blockchain correctamente!")
        time.sleep(0.8)
        st.rerun()

    except Exception as error:
        contenedor_mensaje.error(f"Error al certificar: {error}")
        barra_progreso.empty()


def reoptimizar_foto(ruta_imagen, proyecto):
    """Borra la versión optimizada y vuelve a procesarla."""
    ruta_optimizada = ruta_imagen_optimizada(ruta_imagen, proyecto)
    if ruta_optimizada.exists():
        eliminar_imagen(ruta_optimizada)

    optimizar_foto(ruta_imagen, proyecto)


def eliminar_foto_completa(ruta_imagen, proyecto):
    """Elimina una foto y todos sus archivos relacionados."""
    eliminar_imagen(ruta_imagen)

    ruta_optimizada = ruta_imagen_optimizada(ruta_imagen, proyecto)
    if ruta_optimizada.exists():
        eliminar_imagen(ruta_optimizada)

    ruta_cert = ruta_certificado(ruta_imagen, proyecto)
    if ruta_cert.exists():
        eliminar_imagen(ruta_cert)

    st.session_state.foto_a_borrar = None
    st.rerun()


def quitar_id_del_nombre(nombre_archivo):
    """Quita el ID único del inicio del nombre del archivo."""
    if "_" in nombre_archivo:
        partes = nombre_archivo.split("_", 1)
        if len(partes) == 2:
            return partes[1]
    return nombre_archivo