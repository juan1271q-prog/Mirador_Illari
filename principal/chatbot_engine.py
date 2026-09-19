import math
import re
import unicodedata
from collections import Counter
from html import unescape


def plain_text(value: str) -> str:
    texto = unescape(str(value or ""))
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


PALABRAS_VACIAS = {
    "a", "al", "algo", "como", "con", "cual", "cuando",
    "de", "del", "donde", "el", "ella", "en", "es",
    "esta", "este", "hay", "la", "las", "lo", "los",
    "me", "para", "por", "que", "se", "su", "un",
    "una", "y",
}

SINONIMOS = {
    "direccion": ["ubicacion", "lugar"],
    "donde": ["ubicacion"],
    "llegar": ["ruta", "indicaciones"],
    "llego": ["ruta", "indicaciones"],
    "camino": ["ruta", "indicaciones"],
    "horas": ["horario"],
    "abre": ["horario"],
    "cierran": ["horario"],
    "costo": ["precio", "tarifa"],
    "cuesta": ["precio", "tarifa"],
    "valor": ["precio", "tarifa"],
    "actividades": ["servicios"],
    "atracciones": ["servicios"],
    "reservar": ["reserva"],
    "estacionamiento": ["parqueadero"],
    "carro": ["vehiculo"],
    "niños": ["ninos"],
    "mascota": ["mascotas"],
}

SALUDOS = {
    "hola",
    "buenas",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
    "saludos",
}

DESPEDIDAS = {
    "adios",
    "hasta luego",
    "nos vemos",
    "gracias",
    "muchas gracias",
}

def normalizar_texto(texto: str) -> str:
    """
    Convierte el texto a minúsculas, elimina tildes,
    símbolos y espacios repetidos.
    """

    texto = str(texto or "").lower().strip()

    texto = unicodedata.normalize(
        "NFD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    texto = re.sub(
        r"[^a-z0-9ñ\s]",
        " ",
        texto,
    )

    return re.sub(
        r"\s+",
        " ",
        texto,
    ).strip()


def tokenizar(texto: str) -> list[str]:
    texto_normalizado = normalizar_texto(texto)

    tokens = [
        palabra
        for palabra in texto_normalizado.split()
        if (
            palabra not in PALABRAS_VACIAS
            and len(palabra) > 1
        )
    ]

    tokens_ampliados = list(tokens)

    for token in tokens:
        tokens_ampliados.extend(
            SINONIMOS.get(token, [])
        )

    return tokens_ampliados


def es_saludo(mensaje: str) -> bool:
    texto = normalizar_texto(mensaje)

    # Ordenar saludos por longitud para prefijos compuestos.
    saludos_prefijos = sorted(
        SALUDOS,
        key=lambda s: -len(s)
    )

    inofensivas = {
        "amigo",
        "amiga",
        "amigos",
        "amigas",
        "bien",
        "todo",
    }

    for saludo in saludos_prefijos:
        if texto == saludo or texto.startswith(saludo + " "):
            resto = texto[len(saludo):].strip()

            if not resto:
                return True

            tokens_resto = tokenizar(resto)

            if not tokens_resto:
                return True

            if set(tokens_resto) <= inofensivas:
                return True

            return False

    # Si no hay prefijo pero las tokens son únicamente saludos/inofensivas,
    # considerarlo saludo.
    tokens = set(tokenizar(mensaje))
    if tokens and tokens <= (SALUDOS | inofensivas):
        return True

    return False


def es_despedida(mensaje: str) -> bool:
    texto = normalizar_texto(mensaje)

    despedidas = {
        "adios",
        "hasta luego",
        "nos vemos",
        "gracias",
        "muchas gracias",
    }

    palabras_consulta = {
        "que",
        "donde",
        "cuando",
        "puedo",
        "puede",
        "puedes",
        "quiero",
        "horario",
        "horarios",
        "servicio",
        "servicios",
        "precio",
        "precios",
        "parqueadero",
        "perro",
        "mascota",
        "mascotas",
        "ubicacion",
        "ruta",
        "recomienda",
        "recomendar",
        "dime",
        "decir",
        "saber",
    }

    agradecimiento_extra = {
        "por",
        "muy",
        "amable",
        "ayudar",
        "ayudarme",
        "ayuda",
        "gracias",
        "muchas",
        "tu",
        "tus",
        "favor",
        "de",
        "la",
        "el",
        "bien",
    }

    for despedida in despedidas:
        if texto == despedida:
            return True

        if texto.startswith(despedida + " "):
            resto = texto[len(despedida):].strip()
            if not resto:
                return True

            tokens_resto = tokenizar(resto)
            if not tokens_resto:
                return True

            if set(tokens_resto) & palabras_consulta:
                return False

            if set(tokens_resto) <= agradecimiento_extra:
                return True

            return False

    return False


def calcular_idf(
    documentos: list[list[str]],
) -> dict[str, float]:

    total_documentos = len(documentos)

    vocabulario = {
        token
        for documento in documentos
        for token in documento
    }

    valores_idf = {}

    for palabra in vocabulario:
        documentos_con_palabra = sum(
            1
            for documento in documentos
            if palabra in documento
        )

        valores_idf[palabra] = (
            math.log(
                (total_documentos + 1)
                / (documentos_con_palabra + 1)
            )
            + 1
        )

    return valores_idf


def crear_vector(
    tokens: list[str],
    valores_idf: dict[str, float],
) -> dict[str, float]:

    frecuencias = Counter(tokens)
    total_tokens = len(tokens) or 1

    return {
        palabra: (
            frecuencia / total_tokens
        ) * valores_idf.get(palabra, 0)
        for palabra, frecuencia in frecuencias.items()
    }


def similitud_coseno(
    vector_a: dict[str, float],
    vector_b: dict[str, float],
) -> float:

    palabras_comunes = (
        set(vector_a)
        & set(vector_b)
    )

    producto = sum(
        vector_a[palabra]
        * vector_b[palabra]
        for palabra in palabras_comunes
    )

    magnitud_a = math.sqrt(
        sum(
            valor ** 2
            for valor in vector_a.values()
        )
    )

    magnitud_b = math.sqrt(
        sum(
            valor ** 2
            for valor in vector_b.values()
        )
    )

    if magnitud_a == 0 or magnitud_b == 0:
        return 0.0

    return producto / (
        magnitud_a * magnitud_b
    )


def buscar_mejor_respuesta(
    mensaje: str,
    preguntas_frecuentes: list[dict],
) -> dict | None:
    """
    Compara el mensaje con las preguntas registradas
    en PostgreSQL mediante TF-IDF y similitud coseno.
    """

    if not preguntas_frecuentes:
        return None

    tokens_mensaje = tokenizar(mensaje)

    if not tokens_mensaje:
        return None

    documentos = [
        tokenizar(registro["pregunta"])
        for registro in preguntas_frecuentes
    ]

    documentos_completos = [
        tokens_mensaje,
        *documentos,
    ]

    valores_idf = calcular_idf(
        documentos_completos
    )

    vector_mensaje = crear_vector(
        tokens_mensaje,
        valores_idf,
    )

    mejor_resultado = None
    mejor_confianza = 0.0

    mensaje_normalizado = normalizar_texto(
        mensaje
    )

    for registro, tokens_pregunta in zip(
        preguntas_frecuentes,
        documentos,
    ):
        vector_pregunta = crear_vector(
            tokens_pregunta,
            valores_idf,
        )

        confianza = similitud_coseno(
            vector_mensaje,
            vector_pregunta,
        )

        pregunta_normalizada = normalizar_texto(
            registro["pregunta"]
        )

        # Bonificación cuando existe una coincidencia
        # textual directa.
        if (
            mensaje_normalizado in pregunta_normalizada
            or pregunta_normalizada in mensaje_normalizado
        ):
            confianza += 0.20

        confianza = min(
            confianza,
            1.0,
        )

        if confianza > mejor_confianza:
            mejor_confianza = confianza
            mejor_resultado = {
                "pregunta": registro["pregunta"],
                "respuesta": registro["respuesta"],
                "confianza": mejor_confianza,
            }

    if mejor_confianza < 0.22:
        return None

    return mejor_resultado


def _servicio_contextual_referencia(contexto: dict | None):
    if not contexto:
        return None

    valor = contexto.get("ultimo_servicio")

    if not valor:
        return None

    from .models import ServicioTuristico

    try:
        servicio_id = int(valor)
    except (TypeError, ValueError):
        servicio_id = None

    consulta = ServicioTuristico.objects.filter(activo=True)

    if servicio_id is not None:
        servicio = consulta.filter(id=servicio_id).first()
        if servicio:
            return servicio

    if isinstance(valor, str):
        normalizado = normalizar_texto(valor)
        for servicio in consulta.order_by("nombre"):
            if normalizar_texto(servicio.nombre) == normalizado:
                return servicio
            if normalizado in normalizar_texto(servicio.nombre):
                return servicio

    return None


def obtener_precio_servicio(servicio):
    if servicio is None:
        return None

    if servicio.precio_adulto is not None:
        return f"${servicio.precio_adulto}"

    if servicio.precio_niño is not None:
        return f"${servicio.precio_niño}"

    if servicio.precio_tercera_edad is not None:
        return f"${servicio.precio_tercera_edad}"

    if servicio.precio_desde is not None:
        return f"${servicio.precio_desde}"

    if servicio.precio_texto:
        return servicio.precio_texto.strip()

    return None


def obtener_capacidad_servicio(servicio):
    if servicio is None:
        return None

    if servicio.capacidad is not None:
        return str(servicio.capacidad)

    return None


def obtener_disponibilidad_servicio(servicio):
    if servicio is None:
        return None

    texto = plain_text(getattr(servicio, "disponibilidad", "") or "")
    if texto:
        return texto

    return None


def obtener_reserva_servicio(servicio):
    if servicio is None:
        return None

    return bool(getattr(servicio, "requiere_reserva", False))


def obtener_incluye_servicio(servicio):
    if servicio is None:
        return None

    texto = plain_text(getattr(servicio, "incluye", "") or "")
    if texto:
        return texto

    return None


def crear_contexto_chatbot(servicio=None, tema=None, intencion=None):
    contexto = {
        "ultimo_servicio": None,
        "ultimo_tema": tema,
        "ultima_intencion": intencion,
    }

    if servicio is not None:
        contexto["ultimo_servicio"] = getattr(servicio, "id", None)
        contexto["ultimo_servicio_nombre"] = getattr(servicio, "nombre", "")

    return contexto


def detectar_servicio(mensaje: str, contexto: dict | None = None):
    """Detecta el servicio activo más probable, usando contexto y sinónimos del alojamiento."""
    if not mensaje:
        return None

    from .models import ServicioTuristico

    texto = normalizar_texto(mensaje)
    if not texto:
        return None

    servicios = list(
        ServicioTuristico.objects.filter(activo=True).order_by("nombre")
    )

    if not servicios:
        return None

    contexto_servicio = _servicio_contextual_referencia(contexto)
    frases_contextuales = (
        "ese",
        "esa",
        "eso",
        "ese servicio",
        "esa opcion",
        "cuanto cuesta",
        "y el precio",
        "cuantas personas",
        "cuántas personas",
        "hay que reservar",
        "requiere reserva",
        "esta disponible",
        "qué incluye",
        "que incluye",
        "cuanto vale",
        "precio",
        "capacidad",
        "disponibilidad",
    )
    if contexto_servicio and any(frase in texto for frase in frases_contextuales):
        return contexto_servicio

    nombres = [normalizar_texto(servicio.nombre) for servicio in servicios]
    for servicio in servicios:
        nombre_norm = normalizar_texto(servicio.nombre)
        if nombre_norm and nombre_norm in texto:
            return servicio
        if texto in nombre_norm:
            return servicio

    # Sinónimos y expresiones comunes para alojamiento, especialmente glamping.
    hosting_aliases = (
        "alojamiento",
        "hospedaje",
        "hospedarme",
        "hospedarse",
        "quedarme a dormir",
        "quedarse a dormir",
        "dormir ahi",
        "pasar la noche",
        "alojamiento en la naturaleza",
        "glamping",
        "hospedarse",
        "alojarme",
        "alojarse",
        "lugar para dormir",
        "lugar para quedarse",
    )
    if any(alias in texto for alias in hosting_aliases):
        hoteles = [
            servicio for servicio in servicios
            if servicio.tipo == "Hospedaje"
            or "glamping" in normalizar_texto(servicio.nombre)
            or "hospedaje" in normalizar_texto(servicio.nombre)
            or "alojamiento" in normalizar_texto(servicio.nombre)
        ]
        if hoteles:
            return hoteles[0]

    campings = [
        servicio for servicio in servicios
        if "camping" in normalizar_texto(servicio.nombre)
    ]
    if "camping" in texto and not "glamping" in texto and campings:
        return campings[0]

    mejor_servicio = None
    mejor_puntuacion = 0
    for servicio in servicios:
        tokens_servicio = set(tokenizar(servicio.nombre))
        tokens_mensaje = set(tokenizar(mensaje))
        coincidencias = len(tokens_servicio & tokens_mensaje)
        if coincidencias > mejor_puntuacion:
            mejor_puntuacion = coincidencias
            mejor_servicio = servicio

    return mejor_servicio if mejor_puntuacion > 0 else None


def construir_respuesta_servicio(servicio: object, mensaje: str | None = None):
    if servicio is None:
        return None

    texto = normalizar_texto(mensaje or "")
    if ("que es glamping" in texto) or ("glamping" in texto and "que es" in texto):
        base = (
            "El glamping es una forma de hospedaje en la naturaleza que combina la experiencia "
            "de acampar con mayor comodidad."
        )
        detalle = plain_text(getattr(servicio, "descripcion", "") or "")
        if detalle:
            base = f"{base} {detalle}"
        return base

    if any(frase in texto for frase in ("cuanto cuesta", "cuánto cuesta", "precio", "cuanto vale", "y el precio")):
        precio = obtener_precio_servicio(servicio)
        if precio:
            return f"El precio de {servicio.nombre} es {precio}."
        return "No tengo registrado ese dato actualmente. ¿Quieres saber otra cosa de este servicio?"

    if any(frase in texto for frase in ("cuantas personas", "cuántas personas", "capacidad", "personas entran")):
        capacidad = obtener_capacidad_servicio(servicio)
        if capacidad:
            return f"La capacidad de {servicio.nombre} es de {capacidad} personas."
        return "No tengo registrado ese dato actualmente. ¿Quieres saber otra cosa de este servicio?"

    if any(frase in texto for frase in ("hay que reservar", "requiere reserva", "reserva", "reservar")):
        reserva = obtener_reserva_servicio(servicio)
        if reserva is not None:
            return (
                "Sí, requiere reserva previa."
                if reserva else
                "No requiere reserva previa."
            )
        return "No tengo registrado ese dato actualmente. ¿Quieres saber otra cosa de este servicio?"

    if "disponible" in texto or "disponibilidad" in texto or "hay disponibilidad" in texto:
        disponibilidad = obtener_disponibilidad_servicio(servicio)
        if disponibilidad:
            return f"La disponibilidad de {servicio.nombre} es: {disponibilidad}."
        return "No tengo registrado ese dato actualmente. ¿Quieres saber otra cosa de este servicio?"

    if "incluye" in texto or "que incluye" in texto or "qué incluye" in texto:
        incluye = obtener_incluye_servicio(servicio)
        if incluye:
            return f"{servicio.nombre} incluye: {incluye}."
        return "No tengo registrado ese dato actualmente. ¿Quieres saber otra cosa de este servicio?"

    descripcion = plain_text(getattr(servicio, "descripcion", "") or "")
    if descripcion:
        return f"{servicio.nombre}: {descripcion}"
    return f"Estoy revisando la información disponible de {servicio.nombre}."


def sugerencias_por_servicio(servicio):
    sugerencias = [
        "💲 Ver precio",
        "👥 Ver capacidad",
        "📅 ¿Requiere reserva?",
        "📍 Cómo llegar",
    ]
    if servicio is None:
        return sugerencias
    if getattr(servicio, "tipo", "") == "Hospedaje":
        sugerencias = [
            "💲 Ver precio",
            "👥 Ver capacidad",
            "📅 ¿Requiere reserva?",
            "🏡 ¿Qué incluye?",
        ]
    return sugerencias


def procesar_mensaje(
    mensaje: str,
    preguntas_frecuentes: list[dict],
) -> dict:
    """
    Motor principal del agente conversacional.
    Funciona completamente de manera local.
    """

    mensaje = str(mensaje or "").strip()

    if not mensaje:
        return {
            "reconocido": False,
            "respuesta": (
                "Escribe una pregunta para poder ayudarte."
            ),
            "tema": "mensaje_vacio",
            "confianza": 0,
            "sugerencias": [],
        }

    if len(mensaje) > 180:
        return {
            "reconocido": False,
            "respuesta": (
                "La pregunta es demasiado extensa. "
                "Escríbela de forma más breve."
            ),
            "tema": "mensaje_extenso",
            "confianza": 0,
            "sugerencias": [],
        }

    # Primero busca información turística aunque
    # el mensaje también contenga un saludo.
    resultado = buscar_mejor_respuesta(
        mensaje,
        preguntas_frecuentes,
    )

    if resultado:
        return {
            "reconocido": True,
            "respuesta": resultado["respuesta"],
            "tema": resultado["pregunta"],
            "confianza": round(
                resultado["confianza"] * 100,
                2,
            ),
            "sugerencias": [
                "Horarios",
                "Ubicación",
                "Servicios",
                "Eventos",
            ],
        }

    if es_saludo(mensaje):
        return {
            "reconocido": True,
            "respuesta": (
                "Hola. Soy el asistente virtual del "
                "Centro Turístico Mirador Illari. "
                "Puedes preguntarme sobre horarios, "
                "ubicación, servicios, eventos o precios."
            ),
            "tema": "saludo",
            "confianza": 100,
            "sugerencias": [
                "Horarios",
                "Ubicación",
                "Servicios",
                "Eventos",
            ],
        }

    if es_despedida(mensaje):
        return {
            "reconocido": True,
            "respuesta": (
                "Gracias por comunicarte con Mirador Illari. "
                "Esperamos recibirte pronto."
            ),
            "tema": "despedida",
            "confianza": 100,
            "sugerencias": [],
        }

    return {
        "reconocido": False,
        "respuesta": (
            "No pude comprender completamente tu pregunta. "
            "Puedes consultar sobre horarios, ubicación, "
            "servicios, precios, eventos, reservas, mascotas "
            "o parqueadero."
        ),
        "tema": "desconocido",
        "confianza": 0,
        "sugerencias": [
            "Horarios",
            "Ubicación",
            "Servicios",
            "Contacto",
        ],
    }
