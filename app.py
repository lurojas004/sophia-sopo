"""
Sophia - Chatbot Turistico de Sopó, Cundinamarca
Aplicacion desarrollada con Streamlit y la API de Groq
Modelo principal: openai/gpt-oss-120b (respaldo: openai/gpt-oss-20b)
Groq retiró llama-3.3-70b-versatile el 16 de agosto de 2026.

Version 2 (segundo avance):
- Fichas visuales para todas las categorias: hospedajes, restaurantes,
  cafeterias, eventos, festivales, sitios turisticos y emprendimientos.
- Instrucciones del modelo ajustadas para responder solo con informacion validada.
- Contexto selectivo: solo se envia al modelo la informacion relevante a la
  pregunta, para no superar los limites de la API gratuita de Groq.
- Registro de consultas ampliado (CSV) con lugares detectados, modelo y tiempo.
"""

import streamlit as st
import json
import csv
import os
import base64
import html
import time
import uuid
import unicodedata
from datetime import datetime, timezone, timedelta
from groq import Groq


# Configuracion de la pagina

st.set_page_config(
    page_title="Sophia - Asistente Turistico de Sopó",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colores y estilos

CUSTOM_CSS = """
<style>
    :root {
        --azul-principal: #0B3D91;
        --azul-secundario: #1E5FBF;
        --azul-claro: #E8F1FC;
        --blanco: #FFFFFF;
        --gris-texto: #2B2B2B;
    }

    .stApp {
        background-color: var(--blanco);
    }

    .sophia-header {
        background: linear-gradient(90deg, var(--azul-principal) 0%, var(--azul-secundario) 100%);
        padding: 28px 32px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 2px 8px rgba(11, 61, 145, 0.15);
    }

    .sophia-header h1 {
        color: var(--blanco);
        margin: 0;
        font-size: 32px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }

    .sophia-header p {
        color: var(--azul-claro);
        margin: 6px 0 0 0;
        font-size: 15px;
    }

    .sophia-header-inner {
        display: flex;
        align-items: center;
        gap: 20px;
    }

    .sophia-escudo {
        height: 64px;
        width: auto;
        background-color: var(--blanco);
        border-radius: 10px;
        padding: 6px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
    }

    section[data-testid="stSidebar"] {
        background-color: var(--azul-claro);
        border-right: 2px solid var(--azul-secundario);
    }

    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label {
        color: var(--azul-principal) !important;
    }

    /* Texto de los botones de la barra lateral en blanco (si no, queda azul sobre azul) */
    section[data-testid="stSidebar"] .stButton > button p,
    section[data-testid="stSidebar"] .stDownloadButton > button p {
        color: var(--blanco) !important;
    }

    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
        background-color: var(--azul-claro);
        border-radius: 12px;
        border: 1px solid var(--azul-secundario);
    }

    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {
        background-color: var(--blanco);
        border-radius: 12px;
        border: 1px solid #D0D0D0;
    }

    .stButton > button, .stDownloadButton > button {
        background-color: var(--azul-principal);
        color: var(--blanco);
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 8px 18px;
    }

    .stButton > button:hover, .stDownloadButton > button:hover {
        background-color: var(--azul-secundario);
        color: var(--blanco);
    }

    .stChatInput textarea {
        border: 1.5px solid var(--azul-secundario) !important;
        border-radius: 10px !important;
    }

    .sophia-footer {
        text-align: center;
        color: #6B6B6B;
        font-size: 12px;
        margin-top: 40px;
        padding-top: 16px;
        border-top: 1px solid var(--azul-claro);
    }

    /* Contenedor de fichas (varias fichas una al lado de otra) */
    .fichas-contenedor {
        display: flex;
        flex-wrap: wrap;
        gap: 14px;
        margin: 10px 0 16px 0;
    }

    .ficha-lugar {
        background-color: var(--blanco);
        border: 1px solid var(--azul-claro);
        border-radius: 14px;
        overflow: hidden;
        width: 340px;
        max-width: 100%;
        box-shadow: 0 2px 10px rgba(11, 61, 145, 0.10);
    }

    .ficha-lugar img {
        width: 100%;
        height: 170px;
        object-fit: cover;
        display: block;
    }

    .ficha-lugar-contenido {
        padding: 14px 16px 16px 16px;
    }

    .ficha-lugar-categoria {
        color: var(--azul-secundario);
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin: 0 0 4px 0;
    }

    .ficha-lugar-titulo {
        color: var(--azul-principal);
        font-size: 17px;
        font-weight: 700;
        margin: 0 0 4px 0;
    }

    .ficha-lugar-direccion {
        color: var(--gris-texto);
        font-size: 13px;
        margin: 0 0 10px 0;
    }

    .ficha-lugar-badges {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 10px;
    }

    .ficha-lugar-badge {
        background-color: var(--azul-claro);
        color: var(--azul-principal);
        font-size: 11px;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 20px;
    }

    .ficha-lugar-descripcion {
        color: var(--gris-texto);
        font-size: 13.5px;
        line-height: 1.5;
        margin: 0 0 10px 0;
    }

    .ficha-lugar-dato {
        color: var(--gris-texto);
        font-size: 12.5px;
        margin: 0 0 4px 0;
    }

    .ficha-lugar-dato b {
        color: var(--azul-principal);
    }

    .ficha-lugar-contacto {
        color: var(--azul-secundario);
        font-size: 13px;
        font-weight: 600;
        border-top: 1px solid var(--azul-claro);
        padding-top: 8px;
        margin: 8px 0 0 0;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# Archivos

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Se cargan las dos bases. Si un lugar aparece en ambas, se usa la version
# del archivo que esta mas abajo en la lista (la mas reciente).
JSON_FILES = [
    "base_datos_turistica_sopo.json",
]

LOG_PATH = os.path.join(BASE_DIR, "registro_consultas.csv")
LOG_COLUMNAS = [
    "fecha_hora",
    "id_sesion",
    "pregunta",
    "respuesta",
    "lugares_detectados",
    "categorias_consultadas",
    "modelo",
    "tiempo_respuesta_s",
    "estado",
]

MODELOS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]

# Limite aproximado de caracteres de contexto enviado al modelo por consulta
MAX_CONTEXTO = 10000

# Nombres visibles de cada categoria
NOMBRES_CATEGORIA = {
    "hoteles": "Hospedaje",
    "restaurantes": "Gastronomía",
    "eventos": "Evento",
    "festivales": "Festival",
    "sitios_turisticos": "Sitio turístico",
    "emprendimientos": "Emprendimiento",
}

# Otros nombres que puede tener una categoria en la base anterior
ALIAS_CATEGORIA = {
    "hospedajes": "hoteles",
    "hospedaje": "hoteles",
    "hoteles": "hoteles",
    "restaurantes": "restaurantes",
    "gastronomia": "restaurantes",
    "cafeterias": "restaurantes",
    "eventos": "eventos",
    "festivales": "festivales",
    "sitios_turisticos": "sitios_turisticos",
    "sitios": "sitios_turisticos",
    "atractivos": "sitios_turisticos",
    "emprendimientos": "emprendimientos",
}

# Palabras de la pregunta que indican que el usuario quiere una categoria
PALABRAS_CATEGORIA = {
    "hoteles": ["hotel", "hosped", "alojam", "dormir", "quedarme", "quedarnos",
                "cabana", "habitacion", "noche", "posada", "glamping",
                "mascota", "perro", "gato", "pet friendly"],
    "restaurantes": ["restaurante", "comer", "almorz", "almuerzo", "cenar", "cena",
                     "comida", "plato", "hamburguesa", "pizza", "sushi", "parrilla",
                     "carne", "desayun", "brunch", "cafe", "cafeteria", "postre",
                     "onces", "dulce", "tinto", "gastronom", "pasteleria"],
    "eventos": ["evento", "programacion", "concierto", "muestra", "esta semana",
                "hoy", "manana", "fin de semana", "maraton", "agenda"],
    "festivales": ["festival", "fiesta", "feria"],
    "sitios_turisticos": ["sitio", "visitar", "conocer", "turistic", "que hacer",
                          "lugares", "plan", "caminata", "sender", "naturaleza",
                          "santuario", "iglesia", "parapente", "aventura", "mirador",
                          "pionono", "parque"],
    "emprendimientos": ["emprend", "artesan", "recuerdo", "souvenir", "producto local",
                        "impresion 3d", "impresiones 3d"],
}

# Palabras que no sirven para identificar un lugar por su nombre
PALABRAS_COMUNES = {
    "hotel", "restaurante", "cafe", "sopo", "del", "las", "los", "para", "con",
    "casa", "gran", "real", "parque", "festival", "cocina", "salon", "onces",
    "pasteleria", "hospedaje", "principal", "municipio", "tour", "sitio",
    "centro", "plaza", "senor",
}

# Campos internos que no se envian al modelo
CAMPOS_INTERNOS = {"imagen", "fuente", "estado_validacion"}


# Utilidades de texto

def normalizar(texto):
    """Minusculas y sin tildes, para comparar textos."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", str(texto).lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


def tokens(texto):
    limpio = "".join(c if c.isalnum() else " " for c in normalizar(texto))
    return limpio.split()


def ahora_colombia():
    return datetime.now(timezone(timedelta(hours=-5)))


def fecha_legible(momento):
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    return f"{dias[momento.weekday()]} {momento.day} de {meses[momento.month - 1]} de {momento.year}"


# Base de datos

@st.cache_data
def cargar_bases(rutas):
    """
    Carga todos los archivos JSON disponibles y los organiza en:
    - lugares: lista de diccionarios, cada uno con su categoria (_categoria)
    - general: informacion que no es un lugar (historia, como llegar, etc.)
    - archivos: nombres de los archivos que se cargaron
    """
    lugares_por_nombre = {}
    general = {}
    archivos = []

    for ruta in rutas:
        if not os.path.exists(ruta):
            continue
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        archivos.append(os.path.basename(ruta))

        if not isinstance(datos, dict):
            continue

        for clave, valor in datos.items():
            categoria = ALIAS_CATEGORIA.get(normalizar(clave))
            elementos = None
            if isinstance(valor, list):
                elementos = valor
            elif isinstance(valor, dict) and valor and all(isinstance(v, dict) for v in valor.values()):
                elementos = list(valor.values())

            es_lista_de_lugares = (
                elementos is not None
                and any(isinstance(e, dict) and e.get("nombre") for e in elementos)
            )

            if categoria and es_lista_de_lugares:
                for elemento in elementos:
                    if isinstance(elemento, dict) and elemento.get("nombre"):
                        lugar = dict(elemento)
                        lugar["_categoria"] = categoria
                        lugares_por_nombre[normalizar(lugar["nombre"])] = lugar
            else:
                general[clave] = valor

    return {
        "lugares": list(lugares_por_nombre.values()),
        "general": general,
        "archivos": archivos,
    }


def construir_indice_nombres(lugares):
    """
    Prepara la deteccion de lugares por nombre. Un lugar se detecta si:
    - la pregunta contiene su nombre completo o un alias, o
    - la pregunta contiene todas las palabras importantes de su nombre, o
    - la pregunta contiene una palabra de su nombre que no aparece en ningun
      otro lugar (por ejemplo "pionono", "vesta" o "camelia").
    """
    frecuencia = {}
    nombres_por_lugar = []
    for lugar in lugares:
        nombres = [lugar.get("nombre", "")] + list(lugar.get("alias") or [])
        palabras = set()
        for nombre in nombres:
            palabras.update(t for t in tokens(nombre) if len(t) >= 4 and t not in PALABRAS_COMUNES)
        for palabra in palabras:
            frecuencia[palabra] = frecuencia.get(palabra, 0) + 1
        nombres_por_lugar.append((lugar, nombres, palabras))

    indice = []
    for lugar, nombres, palabras in nombres_por_lugar:
        unicas = {p for p in palabras if frecuencia[p] == 1}
        indice.append({
            "lugar": lugar,
            "nombres": [normalizar(n) for n in nombres if n],
            "palabras": palabras,
            "unicas": unicas,
        })
    return indice


def detectar_lugares(texto, indice, maximo=3):
    """
    Devuelve los lugares mencionados en el texto (maximo 3), en el orden
    en que aparecen mencionados.
    """
    if not texto:
        return []
    texto_norm = normalizar(texto)
    lista_tokens = tokens(texto)
    palabras_texto = set(lista_tokens)
    encontrados = []
    for entrada in indice:
        posicion = None
        for n in entrada["nombres"]:
            if n and n in texto_norm:
                pos = texto_norm.index(n)
                posicion = pos if posicion is None else min(posicion, pos)
        if posicion is None and entrada["palabras"] and entrada["palabras"] <= palabras_texto:
            posicion = min(texto_norm.find(p) for p in entrada["palabras"])
        if posicion is None and entrada["unicas"] & palabras_texto:
            posicion = min(texto_norm.find(p) for p in entrada["unicas"] & palabras_texto)
        if posicion is not None:
            encontrados.append((posicion, entrada["lugar"]))
    encontrados.sort(key=lambda x: x[0])
    return [lugar for _, lugar in encontrados[:maximo]]


def detectar_categorias(texto):
    texto_norm = normalizar(texto)
    return [cat for cat, palabras in PALABRAS_CATEGORIA.items()
            if any(p in texto_norm for p in palabras)]


def limpiar_lugar(lugar):
    """Quita campos internos y vacios antes de enviar el lugar al modelo."""
    limpio = {}
    for clave, valor in lugar.items():
        if clave in CAMPOS_INTERNOS or clave.startswith("_"):
            continue
        if valor in (None, "", [], {}):
            continue
        limpio[clave] = valor
    limpio["categoria"] = NOMBRES_CATEGORIA.get(lugar.get("_categoria"), lugar.get("categoria", ""))
    return limpio


def resumir_lugar(lugar):
    """Version corta de un lugar, para cuando se pide una categoria completa."""
    def corto(valor, limite=90):
        valor = valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False)
        return valor if len(valor) <= limite else valor[:limite] + "..."

    resumen = {"nombre": lugar["nombre"]}
    tipo = lugar.get("tipo_cocina") or lugar.get("tipo")
    if tipo:
        resumen["tipo"] = corto(tipo, 70)
    for campo in ["direccion", "lugar", "telefono", "horario", "fechas",
                  "periodicidad", "precio_referencia", "inscripciones_estado"]:
        if lugar.get(campo) not in (None, "", [], {}):
            resumen[campo] = corto(lugar[campo])
    if lugar.get("_categoria") in ("hoteles", "sitios_turisticos") and lugar.get("politicas"):
        resumen["politicas"] = [corto(p, 60) for p in lugar["politicas"][:4]]
    destacados = lugar.get("platos_destacados") or lugar.get("actividades") or lugar.get("servicios")
    if destacados:
        resumen["destacados"] = [corto(d, 50) for d in destacados[:3]]
    # Lo relacionado con mascotas siempre se incluye, porque es una pregunta frecuente
    mascotas = [x for x in (lugar.get("servicios") or []) + (lugar.get("politicas") or [])
                if any(p in normalizar(x) for p in ["mascota", "pet"])]
    if mascotas:
        resumen["mascotas"] = [corto(m, 70) for m in mascotas[:2]]
    return resumen


def construir_contexto(base, pregunta, lugares_detectados, categorias):
    """
    Arma el contexto que recibe el modelo en cada consulta:
    1. Un indice corto con todos los lugares registrados (siempre).
    2. La ficha completa de los lugares mencionados en la pregunta.
    3. Un resumen de las categorias por las que pregunta el usuario.
    4. Informacion general del municipio, si existe en la base.
    """
    if not base or not base["lugares"]:
        return "No hay informacion turistica cargada."

    partes = []

    indice_txt = []
    for categoria, nombre_visible in NOMBRES_CATEGORIA.items():
        nombres = [l["nombre"] for l in base["lugares"] if l["_categoria"] == categoria]
        if nombres:
            indice_txt.append(f"- {nombre_visible}: " + "; ".join(nombres))
    partes.append("INDICE DE LUGARES REGISTRADOS:\n" + "\n".join(indice_txt))

    if lugares_detectados:
        detalle = [limpiar_lugar(l) for l in lugares_detectados]
        partes.append("DETALLE DE LOS LUGARES MENCIONADOS:\n" +
                      json.dumps(detalle, ensure_ascii=False, separators=(",", ":")))

    nombres_ya_incluidos = {l["nombre"] for l in lugares_detectados}
    for categoria in categorias:
        resumenes = [resumir_lugar(l) for l in base["lugares"]
                     if l["_categoria"] == categoria and l["nombre"] not in nombres_ya_incluidos]
        if resumenes:
            partes.append(f"RESUMEN DE {NOMBRES_CATEGORIA[categoria].upper()}:\n" +
                          json.dumps(resumenes, ensure_ascii=False, separators=(",", ":")))

    palabras_generales = ["historia", "cultura", "llegar", "como llego", "transporte", "ruta",
                          "informacion", "alcaldia", "pregunta", "turismo"]
    pide_general = any(p in normalizar(pregunta) for p in palabras_generales)
    if base["general"] and (pide_general or not (lugares_detectados or categorias)):
        general_txt = json.dumps(base["general"], ensure_ascii=False, separators=(",", ":"))
        partes.append("INFORMACION GENERAL DEL MUNICIPIO:\n" + general_txt[:2500])

    contexto = "\n\n".join(partes)
    return contexto[:MAX_CONTEXTO]


# Fichas visuales

def imagen_a_base64(ruta):
    if not ruta or not os.path.exists(ruta):
        return None, None
    extension = os.path.splitext(ruta)[1].lower()
    mime = "image/png" if extension == ".png" else "image/jpeg"
    with open(ruta, "rb") as archivo_imagen:
        return base64.b64encode(archivo_imagen.read()).decode(), mime


def texto_corto(texto, limite=230):
    texto = texto or ""
    if len(texto) <= limite:
        return texto
    return texto[:limite].rsplit(" ", 1)[0] + "..."


def html_ficha(lugar, base_dir):
    """Construye el HTML de la ficha visual de un lugar de cualquier categoria."""
    e = html.escape

    imagen_html = ""
    if lugar.get("imagen"):
        imagen_b64, mime = imagen_a_base64(os.path.join(base_dir, lugar["imagen"]))
        if imagen_b64:
            imagen_html = f'<img src="data:{mime};base64,{imagen_b64}" alt="{e(lugar["nombre"])}" />'

    categoria = NOMBRES_CATEGORIA.get(lugar.get("_categoria"), "")
    tipo = lugar.get("tipo") or lugar.get("tipo_cocina") or ""
    etiqueta = f"{categoria} | {tipo}" if tipo else categoria

    ubicacion = lugar.get("direccion") or lugar.get("lugar") or ""
    if not ubicacion and lugar.get("lugares"):
        ubicacion = ", ".join(lugar["lugares"][:3])

    etiquetas = (lugar.get("servicios") or lugar.get("actividades")
                 or lugar.get("oferta") or lugar.get("productos") or [])
    badges = "".join(f'<span class="ficha-lugar-badge">{e(str(s))}</span>' for s in etiquetas[:6])

    datos = []
    if lugar.get("fechas"):
        datos.append(("Fechas", lugar["fechas"]))
    if lugar.get("periodicidad"):
        datos.append(("Se realiza", lugar["periodicidad"]))
    if lugar.get("ultima_edicion"):
        datos.append(("Última edición", lugar["ultima_edicion"]))
    if lugar.get("horario") and isinstance(lugar["horario"], str):
        datos.append(("Horario", lugar["horario"]))
    if lugar.get("precio_referencia"):
        datos.append(("Precios", lugar["precio_referencia"]))
    if lugar.get("inscripciones_estado") == "cerradas":
        datos.append(("Inscripciones", "Cerradas. Puedes asistir como espectador."))
    datos_html = "".join(f'<p class="ficha-lugar-dato"><b>{e(t)}:</b> {e(str(v))}</p>' for t, v in datos)

    contacto = lugar.get("telefono") or lugar.get("correo") or ""
    contacto_html = f'<p class="ficha-lugar-contacto">{e(contacto)}</p>' if contacto else ""

    return f"""
    <div class="ficha-lugar">
        {imagen_html}
        <div class="ficha-lugar-contenido">
            <p class="ficha-lugar-categoria">{e(etiqueta)}</p>
            <p class="ficha-lugar-titulo">{e(lugar["nombre"])}</p>
            <p class="ficha-lugar-direccion">{e(ubicacion)}</p>
            <div class="ficha-lugar-badges">{badges}</div>
            <p class="ficha-lugar-descripcion">{e(texto_corto(lugar.get("descripcion", "")))}</p>
            {datos_html}
            {contacto_html}
        </div>
    </div>
    """


def texto_para_mostrar(texto):
    """
    Streamlit interpreta el texto entre dos signos $ como formula matematica,
    lo que daña los precios (por ejemplo "$12.000 y $15.000"). Se escapan.
    """
    return (texto or "").replace("\\$", "$").replace("$", "\\$")


def mostrar_fichas(lugares, base_dir):
    if not lugares:
        return
    fichas = "".join(html_ficha(l, base_dir) for l in lugares)
    # Se quitan saltos de linea y sangrias: si no, Streamlit interpreta
    # parte del HTML como bloque de codigo y lo muestra como texto.
    fichas = "".join(linea.strip() for linea in fichas.splitlines())
    st.markdown(f'<div class="fichas-contenedor">{fichas}</div>', unsafe_allow_html=True)


# Registro de consultas en CSV

def preparar_registro():
    """Si existe un registro con el formato anterior, lo guarda aparte."""
    if not os.path.exists(LOG_PATH):
        return
    with open(LOG_PATH, "r", encoding="utf-8") as archivo_csv:
        encabezado = archivo_csv.readline().strip().split(",")
    if encabezado != LOG_COLUMNAS:
        nuevo_nombre = os.path.join(BASE_DIR, "registro_consultas_version1.csv")
        if not os.path.exists(nuevo_nombre):
            os.rename(LOG_PATH, nuevo_nombre)


def registrar_consulta(fila):
    existe = os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as archivo_csv:
        escritor = csv.writer(archivo_csv)
        if not existe:
            escritor.writerow(LOG_COLUMNAS)
        escritor.writerow([fila.get(c, "") for c in LOG_COLUMNAS])


def contar_consultas():
    if not os.path.exists(LOG_PATH):
        return 0
    with open(LOG_PATH, "r", encoding="utf-8") as archivo_csv:
        return max(sum(1 for _ in csv.reader(archivo_csv)) - 1, 0)


# Conexion con la API de Groq

def obtener_cliente_groq():
    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        try:
            api_key = st.secrets["GROQ_API_KEY"]
        except Exception:
            api_key = None

    if not api_key:
        st.error(
            "No se encontro la llave GROQ_API_KEY. "
            "Configurala como variable de entorno o en el archivo .streamlit/secrets.toml"
        )
        st.stop()

    return Groq(api_key=api_key)


SYSTEM_PROMPT_BASE = """Eres Sophia, la asistente virtual turística oficial del municipio de Sopó, Cundinamarca, Colombia.

Fecha de hoy: {fecha}.

Ayudas a turistas y visitantes con información clara, amable y precisa sobre hospedajes, restaurantes y cafeterías, eventos, festivales, sitios turísticos, emprendimientos locales, horarios, precios y cómo contactar a cada lugar.

REGLAS OBLIGATORIAS SOBRE LA INFORMACIÓN:
1. Responde ÚNICAMENTE con la información validada que aparece en el contexto de abajo. Esa es tu única fuente.
2. Nunca inventes ni supongas nombres de lugares, direcciones, teléfonos, precios, horarios, fechas, platos ni servicios. Si un dato no aparece en el contexto, di con honestidad que no lo tienes y ofrece el teléfono o el contacto del lugar. Si tampoco hay contacto, o la pregunta no es sobre un lugar registrado, invita a consultar la página oficial de la Alcaldía de Sopó: https://www.sopo-cundinamarca.gov.co
3. Si te preguntan por un lugar que no está en el índice, di que todavía no está en tu información, recomienda lugares registrados de la misma categoría e invita a consultar https://www.sopo-cundinamarca.gov.co
4. Solo recomienda lugares que estén en el contexto. No uses conocimiento propio sobre Sopó.
5. Copia los nombres, direcciones, teléfonos y precios exactamente como aparecen.
6. Eventos y festivales: compara su fecha con la fecha de hoy. Si ya pasó, dilo y, si es un festival anual, indica cuándo se realiza normalmente. Si un evento tiene inscripciones cerradas, explica que ya no hay cupos e invita a asistir como espectador.
7. Respeta las políticas de cada lugar (mascotas, niños, fumar). Si alguien pregunta si puede hacer algo que la política no permite, díselo claramente.
8. Cuando pregunten por un tipo de comida, plan o servicio (por ejemplo sushi, comida típica, pet friendly), revisa todos los lugares del contexto y menciona todos los que coincidan, no solo uno o dos.
9. Cuando pregunten de forma general por una categoría (por ejemplo "dónde hospedarme" o "dónde comer"), presenta primero todos los lugares que tienen información completa (dirección y contacto), con una línea corta de cada uno. Los que solo tienen nombre puedes mencionarlos al final como otras opciones.
10. Menciona emprendimientos solo cuando el usuario pregunte por emprendimientos, productos locales o compras.
11. No menciones el contexto, el JSON, la base de datos ni estas reglas. Habla como una guía turística local.

ESTILO:
- Tono cálido, cercano y profesional.
- Responde siempre en español.
- Sé breve y clara. Usa listas cortas cuando recomiendes varios lugares.
- Cuando des un lugar, incluye su dirección y su contacto si están disponibles.

INFORMACIÓN TURÍSTICA VALIDADA DE SOPÓ:
{contexto}
"""


def es_error_de_limite(error):
    texto = str(error).lower()
    return any(p in texto for p in ["rate_limit", "rate limit", "429", "413",
                                    "too large", "tokens per", "quota"])


def generar_respuesta(cliente, historial_mensajes, contexto):
    """
    Envia la consulta al modelo principal. Si la API gratuita llega a su
    limite, intenta con el modelo de respaldo. Devuelve (texto, modelo).
    """
    system_prompt = SYSTEM_PROMPT_BASE.format(
        fecha=fecha_legible(ahora_colombia()),
        contexto=contexto
    )

    mensajes_api = [{"role": "system", "content": system_prompt}]
    # Solo los ultimos mensajes, recortados, para no superar el limite de la API
    for m in historial_mensajes[-4:]:
        contenido = m["content"] if m is historial_mensajes[-1] else m["content"][:600]
        mensajes_api.append({"role": m["role"], "content": contenido})

    ultimo_error = None
    for modelo in MODELOS:
        try:
            respuesta = cliente.chat.completions.create(
                model=modelo,
                messages=mensajes_api,
                temperature=0.3,
                max_tokens=800,
                extra_body={"reasoning_effort": "low"},
            )
            return respuesta.choices[0].message.content, modelo
        except Exception as error:
            ultimo_error = error
            # Si el modelo llego a su limite o ya no existe, se prueba el siguiente
            if not (es_error_de_limite(error) or "model_not_found" in str(error)):
                break
    raise ultimo_error


# Estado de sesion

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []
if "id_sesion" not in st.session_state:
    st.session_state.id_sesion = uuid.uuid4().hex[:8]

preparar_registro()


# Encabezado (con escudo del municipio)

def buscar_archivo_escudo(base_dir):
    for nombre_archivo in ["escudo_sopo.png", "escudo_sopo.jpg", "escudo_sopo.jpeg"]:
        ruta = os.path.join(base_dir, nombre_archivo)
        if os.path.exists(ruta):
            return ruta
    return None


escudo_b64, escudo_mime = imagen_a_base64(buscar_archivo_escudo(BASE_DIR))
escudo_html = f'<img src="data:{escudo_mime};base64,{escudo_b64}" class="sophia-escudo" />' if escudo_b64 else ""

st.markdown(
    f"""
    <div class="sophia-header">
        <div class="sophia-header-inner">
            {escudo_html}
            <div>
                <h1>Sophia</h1>
                <p>Asistente turístico virtual del municipio de Sopó, Cundinamarca</p>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# Base de datos e indice

base_datos = cargar_bases(tuple(os.path.join(BASE_DIR, f) for f in JSON_FILES))
indice_nombres = construir_indice_nombres(base_datos["lugares"])
lugares_por_nombre = {l["nombre"]: l for l in base_datos["lugares"]}


# Barra lateral

with st.sidebar:
    st.markdown("### Acerca de Sophia")
    st.write(
        "Sophia es un proyecto desarrollado con el incentivo FOES, "
        "en articulación con la Secretaría de Turismo de la Alcaldía de Sopó. "
        "Su objetivo es orientar a los visitantes con información confiable "
        "sobre el municipio."
    )

    st.markdown("### Cómo usar el chat")
    st.write(
        "Escribe tu pregunta en el cuadro de texto inferior, por ejemplo:\n\n"
        "- ¿Dónde puedo hospedarme?\n"
        "- ¿Qué restaurantes de comida típica hay?\n"
        "- ¿Dónde puedo tomar un café?\n"
        "- ¿Qué eventos hay esta semana?\n"
        "- ¿Qué festivales se hacen en Sopó?\n"
        "- ¿Qué sitios turísticos puedo visitar?"
    )

    st.markdown("---")

    if st.button("Limpiar conversación"):
        st.session_state.mensajes = []
        st.rerun()

    if base_datos["lugares"]:
        st.success(f"Información turística cargada: {len(base_datos['lugares'])} lugares.")
        conteo = {}
        for l in base_datos["lugares"]:
            nombre_cat = NOMBRES_CATEGORIA.get(l["_categoria"], "Otros")
            conteo[nombre_cat] = conteo.get(nombre_cat, 0) + 1
        st.caption(" | ".join(f"{k}: {v}" for k, v in conteo.items()))
    else:
        st.warning("No se encontró la base de datos turística en la carpeta del proyecto.")

    st.markdown("### Registro de consultas")
    st.write(f"Consultas registradas: {contar_consultas()}")
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "rb") as archivo_log:
            st.download_button(
                "Descargar registro (CSV)",
                data=archivo_log.read(),
                file_name="registro_consultas.csv",
                mime="text/csv",
            )


# Cliente Groq

cliente_groq = obtener_cliente_groq()


# Historial de conversacion

for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.markdown(texto_para_mostrar(mensaje["content"]))
        fichas = [lugares_por_nombre[n] for n in mensaje.get("fichas", []) if n in lugares_por_nombre]
        mostrar_fichas(fichas, BASE_DIR)


# Entrada del usuario

pregunta_usuario = st.chat_input("Escribe tu pregunta sobre Sopó aquí...")

if pregunta_usuario:
    st.session_state.mensajes.append({"role": "user", "content": pregunta_usuario})
    with st.chat_message("user"):
        st.markdown(texto_para_mostrar(pregunta_usuario))

    # Lugares y categorias de la pregunta. Si no menciona ninguno, se revisa
    # la pregunta anterior para entender preguntas como "¿y el horario?".
    lugares_detectados = detectar_lugares(pregunta_usuario, indice_nombres)
    lugares_contexto = list(lugares_detectados)
    if not lugares_contexto:
        preguntas_previas = [m["content"] for m in st.session_state.mensajes[:-1] if m["role"] == "user"]
        if preguntas_previas:
            lugares_contexto = detectar_lugares(preguntas_previas[-1], indice_nombres)
    categorias = detectar_categorias(pregunta_usuario)

    # Si pregunta por eventos o festivales en general, se muestran sus fichas
    if not lugares_detectados:
        for categoria in ["eventos", "festivales"]:
            if categoria in categorias:
                lugares_detectados += [l for l in base_datos["lugares"]
                                       if l["_categoria"] == categoria][:3]
        lugares_detectados = lugares_detectados[:3]

    contexto = construir_contexto(base_datos, pregunta_usuario, lugares_contexto, categorias)

    with st.chat_message("assistant"):
        marcador_espera = st.empty()
        marcador_espera.markdown("Sophia está escribiendo...")
        inicio = time.time()
        modelo_usado = ""
        estado = "ok"
        try:
            respuesta_texto, modelo_usado = generar_respuesta(
                cliente_groq,
                st.session_state.mensajes,
                contexto
            )
        except Exception as error:
            estado = "error"
            if es_error_de_limite(error):
                respuesta_texto = (
                    "En este momento hay muchas consultas y alcancé el límite del servicio. "
                    "Por favor intenta de nuevo en un minuto."
                )
            else:
                respuesta_texto = (
                    "Ocurrió un error al conectar con el servicio de Sophia. "
                    "Por favor intenta de nuevo en unos segundos."
                )
            st.error(f"Detalle técnico: {error}")
        duracion = round(time.time() - inicio, 2)

        marcador_espera.markdown(texto_para_mostrar(respuesta_texto))

        # Si la pregunta no nombraba un lugar (por ejemplo "donde como sushi"),
        # se muestran las fichas de los lugares que Sophia recomendo.
        if not lugares_detectados and estado == "ok":
            lugares_detectados = detectar_lugares(respuesta_texto, indice_nombres, maximo=8)

        mostrar_fichas(lugares_detectados, BASE_DIR)

    st.session_state.mensajes.append({
        "role": "assistant",
        "content": respuesta_texto,
        "fichas": [l["nombre"] for l in lugares_detectados],
    })

    registrar_consulta({
        "fecha_hora": ahora_colombia().strftime("%Y-%m-%d %H:%M:%S"),
        "id_sesion": st.session_state.id_sesion,
        "pregunta": pregunta_usuario,
        "respuesta": respuesta_texto,
        "lugares_detectados": "; ".join(l["nombre"] for l in lugares_detectados),
        "categorias_consultadas": "; ".join(NOMBRES_CATEGORIA[c] for c in categorias),
        "modelo": modelo_usado,
        "tiempo_respuesta_s": duracion,
        "estado": estado,
    })


# Pie de pagina

st.markdown(
    """
    <div class="sophia-footer">
        Sophia - Proyecto de innovación turística de Sopó, Cundinamarca | Incentivo FOES
    </div>
    """,
    unsafe_allow_html=True
)
