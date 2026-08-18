import math
import re
import unicodedata
from collections import Counter

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
