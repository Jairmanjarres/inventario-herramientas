import streamlit as st
import requests
import base64
from datetime import datetime
from PIL import Image  # <--- Agregamos esto para asegurar que el logo cargue bien

# 1. Cargar la imagen del logo de forma segura
try:
    img_logo = Image.open("logo.png")
except:  # <--- ¡CORREGIDO AQUÍ! Ya no tiene el paréntesis que causaba el error
    img_logo = "💻"

# 2. Configurar la pestaña del navegador
st.set_page_config(
    page_title="Inventario Erco",
    page_icon=img_logo,
    layout="centered"
)

# 3. Mostrar el logo GRANDE en la pantalla de la app
try:
    st.image("logo.png", width=180)
except Exception as e:
    st.warning("No se pudo mostrar la imagen del logo en pantalla.")
# 💻 CONFIGURACIÓN DIRECTA CON TUS ENLACES DE GOOGLE
API_URL = "https://script.google.com/macros/s/AKfycbx3vMau5fmFIhQSXS0Aa1MP42PnP6GCeaJ_zCiPIPvaMvv2pu5jzmcZrld8-Mn3mHkeZA/exec"
FOLDER_ID = "automatizado"

st.set_page_config(page_title="Inventario Pro", page_icon="🔧", layout="centered")

# Función puente de comunicación API
def ejecutar_api(payload):
    try:
        r = requests.post(API_URL, json=payload, timeout=30)
        return r.json()
    except:
        return {"status": "error", "message": "Fallo de comunicación con la base de datos."}

# Validación inicial de variables de entorno
if "TU_" in API_URL or "TU_" in FOLDER_ID:
    st.error("⚠️ Configuración pendiente: ingresa tu API_URL y tu FOLDER_ID en el archivo app.py.")
    st.stop()

# Cargar base de datos de accesos
res_users = ejecutar_api({"action": "get_users"})
usuarios_db = res_users.get("data", {}) if res_users.get("status") == "success" else {}

if "usuario_autenticado" not in st.session_state:
    st.session_state.usuario_autenticado = None

# --- MÓDULO DE LOGIN Y AUTOGESTIÓN DE PIN ---
if st.session_state.usuario_autenticado is None:
    st.title("🔐 Control de Acceso")
    if not usuarios_db:
        st.error("Error al sincronizar usuarios. Revisa la pestaña 'Usuarios' de tu Google Sheet.")
        st.stop()
        
    usuario_sel = st.selectbox("Identifícate seleccionando tu nombre:", list(usuarios_db.keys()))
    pin_actual = usuarios_db.get(usuario_sel, "")
    
    # Caso: Usuario nuevo sin contraseña establecida
    if str(pin_actual).strip() == "":
        st.info(f"✨ ¡Hola {usuario_sel}! Es tu primer ingreso. Crea tu clave de seguridad.")
        nuevo_pin = st.text_input("Crea tu PIN de acceso (4 números):", type="password", max_chars=4)
        confirmar_pin = st.text_input("Confirma tu PIN de acceso:", type="password", max_chars=4)
        
        if st.button("Registrar Contraseña y Acceder", use_container_width=True):
            if len(nuevo_pin) != 4 or not nuevo_pin.isdigit():
                st.error("El PIN debe contener exactamente 4 caracteres numéricos.")
            elif nuevo_pin != confirmar_pin:
                st.error("Las contraseñas ingresadas no coinciden.")
            else:
                res = ejecutar_api({"action": "save_pin", "usuario": usuario_sel, "pin": nuevo_pin})
                if res.get("status") == "success":
                    st.success("¡Contraseña guardada con éxito!")
                    st.session_state.usuario_autenticado = usuario_sel
                    st.rerun()
                else:
                    st.error("Error de escritura en el servidor.")
    else:
        # Caso: Usuario recurrente con contraseña activa
        pin_ingresado = st.text_input("Ingresa tu PIN de seguridad (4 dígitos):", type="password", max_chars=4)
        if st.button("Iniciar Sesión", use_container_width=True):
            if str(pin_ingresado) == str(pin_actual):
                st.session_state.usuario_autenticado = usuario_sel
                st.rerun()
            else:
                st.error("❌ PIN de acceso incorrecto.")
else:
    # --- ENTORNO OPERATIVO DENTRO DE LA APP ---
    usuario_actual = st.session_state.usuario_autenticado
    
    with st.sidebar:
        st.write(f"### Lider: **{usuario_actual}** 👷‍♂️")
        if st.button("Cerrar Sesión"):
            st.session_state.usuario_autenticado = None
            st.rerun()
            
    st.title("🔧 Gestión Integral de Inventario")
    tab1, tab2 = st.tabs(["📝 Registrar Herramienta", "📊 Ver e Intervenir Inventario"])
    
    # PESTAÑA 1: ALTAS
    with tab1:
        st.subheader("Captura de nuevo elemento")
        nombre_herramienta = st.text_input("Nombre de la herramienta:")
        estado = st.selectbox("Estado físico inicial:", ["Buena", "Media", "Mal estado"])
        foto_capturada = st.camera_input("Fotografía obligatoria del estado del equipo")
        
        if st.button("Registrar en Base de Datos", use_container_width=True):
            if not nombre_herramienta:
                st.warning("Debes asignar un nombre descriptivo a la herramienta.")
            elif foto_capturada is None:
                st.warning("El registro exige una captura fotográfica en tiempo real.")
            else:
                with st.spinner("Subiendo archivos multimedia y guardando datos..."):
                    bytes_data = foto_capturada.getvalue()
                    img_b64 = base64.b64encode(bytes_data).decode("utf-8")
                    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    payload = {
                        "action": "save_tool",
                        "usuario": usuario_actual,
                        "herramienta": nombre_herramienta,
                        "estado": estado,
                        "image_base64": img_b64,
                        "fecha": fecha_actual,
                        "folder_id": FOLDER_ID
                    }
                    
                    res = ejecutar_api(payload)
                    if res.get("status") == "success":
                        st.success(f"¡{nombre_herramienta} agregada al inventario correctamente!")
                        st.rerun()
                    else:
                        st.error(f"Error detallado: {res}")

    # PESTAÑA 2: VISUALIZACIÓN, EDICIÓN Y ELIMINACIÓN
    with tab2:
        st.subheader("Panel General de Herramientas")
        res_inv = ejecutar_api({"action": "get_inventory"})
        inventario = res_inv.get("data", []) if res_inv.get("status") == "success" else []
        
        if not inventario:
            st.info("No hay registros en el inventario actual.")
        else:
            for reg in reversed(inventario):
                t_id = reg['id']
                t_user = reg['usuario']
                t_name = reg['herramienta']
                t_status = reg['estado']
                t_url = reg['foto_url']
                t_date = reg['fecha']
                
                with st.container():
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        if t_url:
                            st.image(t_url, width=150)
                        else:
                            st.write("📷 Sin imagen")
                    with col2:
                        st.markdown(f"### {t_name}")
                        st.markdown(f"**Encargado:** {t_user} | **Fecha:** {t_date}")
                        
                        if t_status == "Buena":
                            st.success(f"Estado: {t_status}")
                        elif t_status == "Media":
                            st.warning(f"Estado: {t_status}")
                        else:
                            st.error(f"Estado: {t_status}")
                        
                        # SEGURIDAD: Solo el dueño del registro puede editarlo o borrarlo
                        if t_user == usuario_actual:
                            with st.expander("⚙️ Modificar / Eliminar"):
                                nuevo_nom = st.text_input("Editar nombre:", value=t_name, key=f"edit_name_{t_id}")
                                nuevo_est = st.selectbox("Editar estado:", ["Buena", "Media", "Mal estado"], 
                                                         index=["Buena", "Media", "Mal estado"].index(t_status), 
                                                         key=f"edit_est_{t_id}")
                                
                                c1, c2 = st.columns(2)
                                if c1.button("💾 Guardar", key=f"btn_save_{t_id}", use_container_width=True):
                                    with st.spinner("Actualizando..."):
                                        res_mod = ejecutar_api({"action": "edit_tool", "id": t_id, "herramienta": nuevo_nom, "estado": nuevo_est})
                                        if res_mod.get("status") == "success":
                                            st.success("¡Cambios aplicados!")
                                            st.rerun()
                                            
                                if c2.button("🗑️ Borrar", key=f"btn_del_{t_id}", use_container_width=True):
                                    with st.spinner("Eliminando..."):
                                        res_del = ejecutar_api({"action": "delete_tool", "id": t_id})
                                        if res_del.get("status") == "success":
                                            st.error("Registro eliminado.")
                                            st.rerun()
                st.markdown("---")
