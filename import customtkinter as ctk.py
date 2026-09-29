import customtkinter as ctk
import serial
import serial.tools.list_ports

# -----------------------------------------------------------------------------
# 1. AUTODETECCIÓN Y GESTIÓN DEL PUERTO COM
# -----------------------------------------------------------------------------
PUERTO_COM = 'COM3'
BAUDIOS = 9600
arduino = None
modo_simulador = False

def intentar_conexion():
    global arduino, modo_simulador
    puertos = [p.device for p in serial.tools.list_ports.comports()]
    puerto_destino = PUERTO_COM if PUERTO_COM in puertos else (puertos[0] if puertos else None)
    
    if puerto_destino:
        try:
            # Timeout muy bajo para evitar congelar la interfaz gráfica
            arduino = serial.Serial(puerto_destino, BAUDIOS, timeout=0.05)
            modo_simulador = False
            return f"[OK] Conectado en {puerto_destino}", "#27ae60"
        except Exception:
            arduino = None
            modo_simulador = True
            return "[MODO REPOSO] Arduino no detectado", "#e67e22"
    else:
        arduino = None
        modo_simulador = True
        return "[MODO REPOSO] Sin puertos COM activos", "#e67e22"

# -----------------------------------------------------------------------------
# 2. CONFIGURACIÓN DE LA VENTANA
# -----------------------------------------------------------------------------
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Smart City - Central Eólica & Telemetría")
app.geometry("560x760")
app.configure(fg_color="#121212")

monitoreo_activo = False
ultimo_voltaje = 0.0
ultimo_amperaje = 0.0
id_after = None

# -----------------------------------------------------------------------------
# 3. LÓGICA DE TELEMETRÍA Y PROCESAMIENTO
# -----------------------------------------------------------------------------
def obtener_datos():
    global ultimo_voltaje, ultimo_amperaje
    if arduino and arduino.is_open:
        try:
            linea = None
            # Vaciar búfer para procesar únicamente el último dato enviado
            while arduino.in_waiting > 0:
                linea = arduino.readline().decode('utf-8', errors='ignore').strip()
            
            if linea and "," in linea:
                partes = linea.split(",")
                ultimo_voltaje = float(partes[0])
                ultimo_amperaje = float(partes[1])
            return ultimo_voltaje, ultimo_amperaje
        except (ValueError, IndexError, Exception):
            return ultimo_voltaje, ultimo_amperaje
    else:
        # SIMULACIÓN ESTÁTICA: Sin Arduino, los valores se mantienen en 0
        return 0.0, 0.0

def actualizar_monitoreo():
    global id_after
    if not monitoreo_activo:
        return

    voltaje, corriente = obtener_datos()
    potencia_mw = voltaje * corriente  # P = V * I (mW)
    
    # Actualizar valores numéricos
    lbl_voltaje.configure(text=f"{voltaje:.2f} V")
    lbl_corriente.configure(text=f"{corriente:.1f} mA")
    lbl_potencia.configure(text=f"Potencia Estimada: {potencia_mw:.1f} mW")
    
    # Determinar cuántos LEDs se activan (umbrales cada 0.8V)
    leds_encendidos = int(voltaje // 0.8)
    leds_encendidos = min(max(leds_encendidos, 0), 5)
    
    # Actualizar leds virtuales en pantalla
    colores_activos = ["#2ecc71", "#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"]
    for i in range(5):
        if i < leds_encendidos:
            canvas_leds[i].configure(fg_color=colores_activos[i])
        else:
            canvas_leds[i].configure(fg_color="#2b2b36")
            
    lbl_conteo_leds.configure(text=f"LEDs Activos en Red: {leds_encendidos} / 5")

    id_after = app.after(250, actualizar_monitoreo)

def alternar_monitoreo():
    global monitoreo_activo, id_after
    if not monitoreo_activo:
        # Intentar reintentar la conexión serie al presionar el botón
        msg, color = intentar_conexion()
        lbl_estado.configure(text=msg, text_color=color)
        
        monitoreo_activo = True
        btn_iniciar.configure(text="Detener Monitoreo", fg_color="#c0392b")
        actualizar_monitoreo()
    else:
        monitoreo_activo = False
        if id_after:
            app.after_cancel(id_after)
            id_after = None
        btn_iniciar.configure(text="Conectar y Monitorear en Vivo", fg_color="#27ae60")

def al_cerrar():
    global monitoreo_activo, id_after
    monitoreo_activo = False
    if id_after:
        app.after_cancel(id_after)
    if arduino and arduino.is_open:
        try:
            arduino.close()
        except Exception:
            pass
    app.destroy()

app.protocol("WM_DELETE_WINDOW", al_cerrar)

# -----------------------------------------------------------------------------
# 4. CONSTRUCCIÓN DE LA INTERFAZ GÁFICA
# -----------------------------------------------------------------------------
# Encabezado
lbl_titulo = ctk.CTkLabel(app, text="RED ELÉCTRICA EÓLICA", font=("Roboto", 22, "bold"), text_color="#ffffff")
lbl_titulo.pack(pady=(20, 5))

# Indicador de estado de conexión al hardware
msg_inicio, color_inicio = intentar_conexion()
lbl_estado = ctk.CTkLabel(app, text=msg_inicio, font=("Roboto", 12, "bold"), text_color=color_inicio)
lbl_estado.pack(pady=(0, 10))

# Tarjeta Doble: Voltaje y Corriente
frame_medidores = ctk.CTkFrame(app, fg_color="transparent")
frame_medidores.pack(pady=10, padx=20, fill="x")

# Panel Voltaje
box_v = ctk.CTkFrame(frame_medidores, corner_radius=15, fg_color="#1e1e24")
box_v.pack(side="left", expand=True, fill="both", padx=5)
ctk.CTkLabel(box_v, text="TENSIÓN (VOLTIOS)", font=("Roboto", 11, "bold"), text_color="#a0a0a0").pack(pady=(15, 0))
lbl_voltaje = ctk.CTkLabel(box_v, text="0.00 V", font=("Roboto", 38, "bold"), text_color="#00d2d3")
lbl_voltaje.pack(pady=10)

# Panel Corriente
box_i = ctk.CTkFrame(frame_medidores, corner_radius=15, fg_color="#1e1e24")
box_i.pack(side="right", expand=True, fill="both", padx=5)
ctk.CTkLabel(box_i, text="CORRIENTE (mA)", font=("Roboto", 11, "bold"), text_color="#a0a0a0").pack(pady=(15, 0))
lbl_corriente = ctk.CTkLabel(box_i, text="0.0 mA", font=("Roboto", 38, "bold"), text_color="#ff9f43")
lbl_corriente.pack(pady=10)

# Potencia
lbl_potencia = ctk.CTkLabel(app, text="Potencia Estimada: 0.0 mW", font=("Roboto", 14, "bold"), text_color="#1dd1a1")
lbl_potencia.pack(pady=5)

# Panel de LEDs Virtuales
frame_leds = ctk.CTkFrame(app, corner_radius=15, fg_color="#1e1e24")
frame_leds.pack(pady=15, padx=20, fill="x")

lbl_conteo_leds = ctk.CTkLabel(frame_leds, text="LEDs Activos en Red: 0 / 5", font=("Roboto", 13, "bold"), text_color="#ffffff")
lbl_conteo_leds.pack(pady=(12, 10))

frame_iluminacion = ctk.CTkFrame(frame_leds, fg_color="transparent")
frame_iluminacion.pack(pady=(0, 15))

canvas_leds = []
for i in range(5):
    led_box = ctk.CTkFrame(frame_iluminacion, width=45, height=45, corner_radius=22, fg_color="#2b2b36")
    led_box.pack(side="left", padx=8)
    led_box.pack_propagate(False)
    canvas_leds.append(led_box)

# Botón de Control
btn_iniciar = ctk.CTkButton(
    app, 
    text="Conectar y Monitorear en Vivo", 
    font=("Roboto", 14, "bold"), 
    fg_color="#27ae60", 
    hover_color="#2ecc71", 
    height=45,
    command=alternar_monitoreo
)
btn_iniciar.pack(pady=20)

app.mainloop()