import difflib
import hashlib
import json
import logging
import math
import re
import unicodedata
import urllib.request
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

from collections import Counter
from html import unescape

from django.core.cache import cache

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.utils.http import url_has_allowed_host_and_scheme

from .gemini_service import obtener_respuesta_gemini
from .chatbot_engine import (
    detectar_servicio,
    sugerencias_por_servicio,
    construir_respuesta_servicio,
    crear_contexto_chatbot,
    obtener_precio_servicio,
    obtener_capacidad_servicio,
    obtener_disponibilidad_servicio,
    obtener_reserva_servicio,
)
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.http import require_GET, require_POST
from .models import (
    CarruselInicio,
    ContenidoInicio,
    InformacionInstitucional,
    Contacto,
    ServicioTuristico,
    TIPO_SERVICIO_CHOICES,
    EventoNovedad,
    GaleriaMultimedia,
    PreguntaFrecuente,
    Valor,
)

logger = logging.getLogger(__name__)


def chatbot_rate_limit_exceeded(
    request,
    limit=15,
    window=60,
):
    """
    Limita la cantidad de consultas realizadas al chatbot.
    Máximo 15 solicitudes durante 60 segundos por IP.
    """
    ip = request.META.get(
        "REMOTE_ADDR",
        "unknown",
    )

    identificador = hashlib.sha256(
        ip.encode("utf-8")
    ).hexdigest()

    clave = f"chatbot_rate:{identificador}"

    if cache.add(
        clave,
        1,
        timeout=window,
    ):
        return False

    try:
        cantidad = cache.incr(clave)
    except ValueError:
        cache.set(
            clave,
            1,
            timeout=window,
        )
        return False

    return cantidad > limit


def dominio_google_maps_permitido(url):
    """
    Comprueba que la URL pertenezca realmente a Google Maps.
    """

    if not url:
        return False

    dominio = (
        urlparse(url)
        .netloc
        .lower()
        .split(":")[0]
    )

    dominios_permitidos = {
        "google.com",
        "www.google.com",
        "maps.google.com",
        "maps.app.goo.gl",
        "goo.gl",
    }

    return (
        dominio in dominios_permitidos
        or dominio.endswith(".google.com")
    )


def resolve_google_maps_url(url, allow_network=False):
    """
    Resuelve enlaces cortos de Google Maps solo cuando se solicita
    explícitamente. La vista pública evita esta llamada por defecto
    para no bloquear la carga de la página por una petición externa.
    """

    if not url:
        return url

    url = url.strip()

    parsed = urlparse(url)
    dominio = parsed.netloc.lower().split(":")[0]

    dominios_cortos = {
        "maps.app.goo.gl",
        "goo.gl",
    }

    if dominio not in dominios_cortos:
        return url

    if not allow_network:
        return url

    codigo_url = hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()

    clave_cache = f"google_maps_resuelto:{codigo_url}"

    url_guardada = cache.get(clave_cache)

    if url_guardada:
        return url_guardada

    try:
        solicitud = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/120 Safari/537.36"
                )
            },
        )

        with urllib.request.urlopen(
            solicitud,
            timeout=2,
        ) as respuesta:
            url_resuelta = respuesta.geturl()

        if not dominio_google_maps_permitido(
            url_resuelta
        ):
            cache.set(
                clave_cache,
                url,
                300,
            )
            return url

        cache.set(
            clave_cache,
            url_resuelta,
            60 * 60 * 24,
        )

        return url_resuelta

    except Exception:
        cache.set(
            clave_cache,
            url,
            300,
        )

        return url


def redirect_back_or_home(request):
    """
    Redirecciona de forma segura a la URL referente o a la página de inicio.
    Valida que el referente pertenezca al mismo dominio antes de redirigir.
    """
    referencia = request.META.get("HTTP_REFERER")

    if referencia and url_has_allowed_host_and_scheme(
        referencia,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(referencia)

    return redirect("inicio")


def extract_map_search_query(url):
    """
    Extrae el nombre del lugar cuando el enlace no contiene coordenadas.
    """

    if not url:
        return None

    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    for parametro in ("query", "q"):
        valor = query_params.get(parametro)

        if valor:
            consulta = valor[0].strip()

            if not re.fullmatch(
                r"-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?",
                consulta,
            ):
                return consulta

    match = re.search(
        r"/(?:place|search)/([^/]+)",
        parsed.path,
    )

    if match:
        return unquote(match.group(1)).replace("+", " ")

    return None


def limpiar_direccion_para_mapa(valor):
    """Quita enlaces de Google Maps pegados al texto de la dirección."""
    if not valor:
        return ""

    texto = (valor or "").strip()
    texto = re.sub(
        r"https?://(?:maps\.app\.goo\.gl|goo\.gl|(?:www\.)?maps\.google\.[^\s]+|(?:www\.)?google\.[^\s]+)[^\s]*",
        "",
        texto,
        flags=re.IGNORECASE,
    )
    texto = re.sub(r"[,;]\s*$", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def build_map_embed(url, fallback_address=None):
    """
    Recibe un enlace normal copiado desde Google Maps y genera
    automáticamente el mapa incrustado.

    Si el enlace es corto o no se puede resolver sin acceder a internet,
    usa el texto de la dirección registrada como respaldo para que la
    página siga mostrando el mapa sin depender del acceso externo.
    """

    original_url = (url or "").strip()
    fallback_address = limpiar_direccion_para_mapa(fallback_address)

    if not original_url and not fallback_address:
        return None, None

    resolved_url = resolve_google_maps_url(original_url, allow_network=False)
    candidate_url = resolved_url if resolved_url and resolved_url != original_url else original_url

    if "/maps/embed" in candidate_url.lower():
        return candidate_url, original_url

    coordinates = extract_map_coordinates(candidate_url)

    if coordinates:
        latitude, longitude = coordinates
        location_query = quote_plus(f"loc:{latitude},{longitude}")
        embed_src = (
            "https://maps.google.com/maps"
            f"?q={location_query}"
            "&z=17"
            "&hl=es"
            "&output=embed"
        )
        return embed_src, original_url

    search_query = extract_map_search_query(candidate_url)

    if search_query:
        embed_src = (
            "https://maps.google.com/maps"
            f"?q={quote_plus(search_query)}"
            "&z=17"
            "&hl=es"
            "&output=embed"
        )
        return embed_src, original_url

    if fallback_address:
        embed_src = (
            "https://maps.google.com/maps"
            f"?q={quote_plus(fallback_address)}"
            "&z=17"
            "&hl=es"
            "&output=embed"
        )
        return embed_src, original_url

    return None, original_url


def extract_map_coordinates(url):
    """
    Obtiene las coordenadas exactas del marcador.
    Se priorizan !3d y !4d sobre las coordenadas de la vista.
    """

    if not url:
        return None

    # Coordenadas exactas del marcador.
    match = re.search(
        r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)",
        url,
    )

    if match:
        return match.group(1), match.group(2)

    # Parámetro q=-1.000,-77.000
    match = re.search(
        r"[?&](?:q|query)=(-?\d+(?:\.\d+)?),"
        r"(-?\d+(?:\.\d+)?)",
        url,
    )

    if match:
        return match.group(1), match.group(2)

    # Coordenadas visibles en /@latitud,longitud,zoom
    match = re.search(
        r"@(-?\d+(?:\.\d+)?),"
        r"(-?\d+(?:\.\d+)?),"
        r"\d+(?:\.\d+)?z",
        url,
    )

    if match:
        return match.group(1), match.group(2)

    return None



def get_informacion_activa():
    return InformacionInstitucional.objects.filter(activo=True).order_by('-id').first()


def get_contacto_activo():
    return Contacto.objects.filter(activo=True).order_by('-id').first()


def get_contenido_activo():
    return ContenidoInicio.objects.filter(activo_informacion=True).order_by('-id').first()


def serialize_pregunta(pregunta):
    return {
        "id": pregunta.id,
        "pregunta": plain_text(pregunta.pregunta),
    }


def inicio(request):
    """
    Muestra el contenido completo de la página de inicio.
    """

    informacion = get_informacion_activa()
    contenido = get_contenido_activo()
    contacto = get_contacto_activo()

    if contenido is None:
        contenido = {
            "activo_informacion": True,
            "hero_titulo": (
                "Bienvenidos al Centro Turístico Mirador Illari"
            ),
            "hero_subtitulo": (
                "Naturaleza, aventura y cultura local "
                "en un solo lugar."
            ),
            "hero_boton_texto": "Planifica tu visita",
            "hero_boton_url": "/contacto/",
            "atractivos_titulo": "Nuestros atractivos",
            "atractivos_descripcion": (
                "Explora los lugares y experiencias que "
                "hacen único al Mirador Illari."
            ),
            "atractivo_1_activo": True,
            "atractivo_1_titulo": "Paisajes",
            "atractivo_1_desc": (
                "Disfruta de paisajes naturales y una vista "
                "privilegiada de la zona."
            ),
            "atractivo_2_activo": True,
            "atractivo_2_titulo": "Aventura",
            "atractivo_2_desc": (
                "Vive actividades al aire libre en contacto "
                "con la naturaleza."
            ),
            "atractivo_3_activo": True,
            "atractivo_3_titulo": "Cultura local",
            "atractivo_3_desc": (
                "Conoce las costumbres, tradiciones y riqueza "
                "cultural de la comunidad."
            ),
            "atractivo_4_activo": True,
            "atractivo_4_titulo": "Atención",
            "atractivo_4_desc": (
                "Recibe una atención cercana y disfruta "
                "de una experiencia agradable."
            ),
        }

    carrusel = (
        CarruselInicio.objects
        .filter(activo=True)
        .exclude(imagen="")
        .order_by("orden", "id")
    )

    if isinstance(contenido, dict):
        hero_boton_url = contenido.get(
            "hero_boton_url",
            "/contacto/",
        )
    else:
        hero_boton_url = (
            contenido.hero_boton_url
            or "/contacto/"
        )

    if (
        not hero_boton_url.startswith("/")
        or hero_boton_url.startswith("//")
    ):
        hero_boton_url = "/contacto/"

    return render(
        request,
        "principal/inicio.html",
        {
            "informacion": informacion,
            "contenido": contenido,
            "contacto": contacto,
            "carrusel": carrusel,
            "hero_boton_url": hero_boton_url,
        },
    )

def nosotros(request):
    informacion = get_informacion_activa()

    valores = Valor.objects.filter(
        activo=True
    ).order_by('orden')

    return render(request, 'principal/nosotros.html', {
        'informacion': informacion,
        'valores': valores,
    })

def servicios(request):
    tipos_permitidos = [choice[0] for choice in TIPO_SERVICIO_CHOICES]

    servicios_lista = ServicioTuristico.objects.filter(
        activo=True
    ).order_by('nombre')
    buscar = request.GET.get('buscar', request.GET.get('q', '')).strip()
    tipo = request.GET.get('tipo', '').strip()

    if buscar:
        servicios_lista = servicios_lista.filter(
            Q(nombre__icontains=buscar) |
            Q(tipo__icontains=buscar) |
            Q(descripcion__icontains=buscar)
        )

    if tipo and tipo in tipos_permitidos:
        servicios_lista = servicios_lista.filter(
            tipo__iexact=tipo
        )
    else:
        tipo = ''

    tipos = (
        ServicioTuristico.objects
        .filter(activo=True, tipo__in=tipos_permitidos)
        .values_list('tipo', flat=True)
        .distinct()
        .order_by('tipo')
    )

    paginador = Paginator(servicios_lista.order_by('nombre'), 6)

    servicios = paginador.get_page(request.GET.get('page'))

    contexto = {
        'servicios': servicios,
        'buscar': buscar,
        'tipos': tipos,
        'tipo_seleccionado': tipo,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(
            request,
            'principal/parciales/servicios_resultados.html',
            contexto
        )

    return render(request, 'principal/servicios.html', contexto)

def detalle_servicio(request, servicio_id):
    servicio = get_object_or_404(
        ServicioTuristico,
        id=servicio_id,
        activo=True
    )

    return render(request, 'principal/detalle_servicio.html', {
        'servicio': servicio
    })

def eventos(request):
    tipo = request.GET.get('tipo', '').strip()
    tipo_normalizado = tipo.lower()
    buscar = request.GET.get('buscar', '').strip()

    eventos_lista = EventoNovedad.objects.filter(activo=True)

    if tipo_normalizado in ['evento', 'novedad']:
        eventos_lista = eventos_lista.filter(tipo__iexact=tipo_normalizado)
    else:
        tipo = ''
        tipo_normalizado = ''

    if buscar:
        eventos_lista = eventos_lista.filter(
            Q(titulo__icontains=buscar) |
            Q(contenido__icontains=buscar) |
            Q(tipo__icontains=buscar)
        )

    tipos = (
        EventoNovedad.objects
        .filter(activo=True)
        .exclude(tipo__isnull=True)
        .exclude(tipo='')
        .values_list('tipo', flat=True)
        .distinct()
        .order_by('tipo')
    )

    eventos_lista = eventos_lista.order_by('-fecha_evento', '-fecha_publicacion')

    paginador = Paginator(eventos_lista, 6)

    eventos = paginador.get_page(request.GET.get('page'))

    contexto = {
        'eventos': eventos,
        'tipos': tipos,
        'tipo_seleccionado': tipo_normalizado,
        'buscar': buscar,
        'hoy': timezone.localdate(),
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(
            request,
            'principal/parciales/eventos_resultados.html',
            contexto
        )

    return render(request, 'principal/eventos.html', contexto)


def detalle_evento(request, evento_id):
    evento = get_object_or_404(
        EventoNovedad,
        id=evento_id,
        activo=True
    )

    return render(request, 'principal/detalle_evento.html', {
        'evento': evento,
        'hoy': timezone.localdate(),
    })

def galeria(request):
    imagenes = GaleriaMultimedia.objects.filter(
        activo=True
    ).order_by('-fecha_subida')

    paginador = Paginator(imagenes, 9)

    numero_pagina = request.GET.get('page')

    pagina = paginador.get_page(numero_pagina)

    return render(request, 'principal/galeria.html', {
        'galeria': pagina
    })

def contacto(request):
    contacto = get_contacto_activo()

    map_embed_url, map_link = build_map_embed(
        getattr(contacto, "mapa_embed_url", None) if contacto else None,
        getattr(contacto, "direccion", None) if contacto else None,
    )

    return render(
        request,
        "principal/contacto.html",
        {
            "contacto": contacto,
            "map_embed_url": map_embed_url,
            "map_link": (
                map_link
                or (
                    contacto.mapa_embed_url
                    if contacto
                    else None
                )
            ),
        },
    )


@require_GET
def api_preguntas(request):
    preguntas = (
        PreguntaFrecuente.objects
        .filter(activo=True)
        .order_by("id")
    )

    return JsonResponse({
        "preguntas": [
            serialize_pregunta(pregunta)
            for pregunta in preguntas
        ]
    })


def plain_text(value):
    """
    Convierte el contenido HTML de CKEditor en texto normal.
    """

    texto = unescape(strip_tags(str(value or "")))

    return re.sub(
        r"\s+",
        " ",
        texto
    ).strip()


def normalize_text(text):
    """
    Convierte el texto a minúsculas, elimina tildes,
    signos y espacios repetidos.
    """

    text = plain_text(text).lower()

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = text.encode(
        "ascii",
        "ignore"
    ).decode("ascii")

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def obtener_faq_exacta(pregunta_id, mensaje):
    """Return the active FAQ only when its ID and question both match."""
    try:
        pregunta_id = int(pregunta_id)
    except (TypeError, ValueError):
        return None

    pregunta = PreguntaFrecuente.objects.filter(
        id=pregunta_id,
        activo=True,
    ).first()

    if not pregunta:
        return None

    if normalize_text(pregunta.pregunta) != normalize_text(mensaje):
        return None

    respuesta = plain_text(pregunta.respuesta)
    if not respuesta:
        return None

    return pregunta, respuesta


def obtener_faq_por_texto_exacto(mensaje):
    """Devuelve la FAQ activa cuyo texto exacto coincide con el mensaje."""
    mensaje_normalizado = normalize_text(mensaje)

    if not mensaje_normalizado:
        return None

    preguntas = PreguntaFrecuente.objects.filter(
        activo=True,
    ).order_by("id")

    for pregunta in preguntas:
        if normalize_text(pregunta.pregunta) != mensaje_normalizado:
            continue

        respuesta = plain_text(pregunta.respuesta)
        if not respuesta:
            continue

        return pregunta, respuesta

    return None


def buscar_faq_por_palabras(claves):
    """Busca una FAQ conservadora por palabras clave relevantes."""
    if not claves:
        return None

    preguntas = PreguntaFrecuente.objects.filter(
        activo=True,
    ).order_by("id")

    for pregunta in preguntas:
        texto = normalize_text(pregunta.pregunta or "")
        if not texto:
            continue

        if any(
            normalize_text(clave) in texto
            for clave in claves
            if normalize_text(clave)
        ):
            respuesta = plain_text(pregunta.respuesta)
            if respuesta:
                return pregunta, respuesta

    return None

# Palabras que no son importantes para reconocer el tema.
STOPWORDS_CHATBOT = {
    "a",
    "al",
    "algo",
    "como",
    "con",
    "cual",
    "cuales",
    "cuando",
    "de",
    "del",
    "donde",
    "el",
    "en",
    "es",
    "esta",
    "este",
    "la",
    "las",
    "lo",
    "los",
    "me",
    "mi",
    "para",
    "por",
    "puede",
    "puedes",
    "puedo",
    "que",
    "se",
    "si",
    "son",
    "su",
    "sus",
    "un",
    "una",
    "y",
    "ya",
}

# Permite reconocer palabras que tienen significados similares.
TOKEN_EQUIVALENCIAS = {
    "abre": "abrir",
    "abren": "abrir",
    "abierto": "abrir",
    "abierta": "abrir",
    "atiende": "atencion",
    "atienden": "atencion",
    "horarios": "horario",
    "horas": "hora",
    "alojarme": "alojamiento",
    "alojarse": "alojamiento",
    "alojamiento": "alojamiento",
    "hospedaje": "alojamiento",
    "hospedarme": "alojamiento",
    "hospedarse": "alojamiento",
    "dormir": "alojamiento",
    "quedarme": "alojamiento",
    "quedarse": "alojamiento",
    "quedo": "alojamiento",
    "alojar": "alojamiento",
    "glamping": "alojamiento",
    "glampin": "alojamiento",
    "glampign": "alojamiento",
    "comunicarme": "contacto",
    "contactarme": "contacto",
    "llamarme": "contacto",
    "ubicado": "ubicacion",
    "ubicada": "ubicacion",
    "queda": "ubicacion",
    "direccion": "ubicacion",
    "direcciones": "ubicacion",
    "servicio": "servicios",
    "ofrece": "servicios",
    "ofrecen": "servicios",
    "actividades": "servicios",
    "atractivos": "servicios",
    "hacer": "servicios",
    "precios": "precio",
    "costos": "precio",
    "costo": "precio",
    "cuesta": "precio",
    "cuestan": "precio",
    "tarifas": "precio",
    "tarifa": "precio",
    "cobra": "precio",
    "cobran": "precio",
    "valen": "precio",
    "vale": "precio",
    "eventos": "evento",
    "novedades": "evento",
    "mascotas": "mascota",
}


def _fuzzy_intent_token(token):
    """Aplica corrección difusa a tokens que coinciden con intenciones conocidas."""

    if not token:
        return token

    token = TOKEN_EQUIVALENCIAS.get(token, token)

    if token in STOPWORDS_CHATBOT:
        return token

    # Reglas de temas definidas más abajo.
    intent_keywords = set().union(*REGLAS_TEMAS.values())

    if token in intent_keywords:
        return token

    matches = difflib.get_close_matches(
        token,
        intent_keywords,
        n=1,
        cutoff=0.88,
    )

    if matches:
        return matches[0]

    return token


def chatbot_tokens(text):
    """
    Divide el mensaje en palabras importantes.
    """

    tokens = []

    for token in normalize_text(text).split():

        token = _fuzzy_intent_token(token)

        if (
            len(token) > 1
            and token not in STOPWORDS_CHATBOT
        ):
            tokens.append(token)

    return tokens


def text_tokens(text):
    return set(chatbot_tokens(text))


def is_greeting(text):
    """
    Verifica si el mensaje es un saludo.
    """
    texto = normalize_text(text)

    # Prefijos de saludo (ordenados por longitud para coincidir "buenas tardes" antes de "buenas").
    saludos_prefijos = [
        "buenas tardes",
        "buenos dias",
        "buenas noches",
        "buenas",
        "buenos",
        "hola",
        "saludos",
        "hey",
        "que tal",
    ]

    # Palabras inofensivas que pueden acompañar a un saludo pero no constituyen
    # una consulta significativa por sí mismas.
    inofensivas = {
        "amigo",
        "amiga",
        "amigos",
        "amigas",
        "bien",
        "todo",
        "buenos",
        "buenas",
    }

    for pref in saludos_prefijos:
        if texto == pref or texto.startswith(pref + " "):
            resto = texto[len(pref):].strip()

            # Si no queda texto después del prefijo, es solo saludo.
            if not resto:
                return True

            # Tokens importantes del resto (elimina stopwords).
            tokens_resto = set(chatbot_tokens(resto))

            # Si no quedan tokens importantes (ej. "hola, ¿cómo estás?"), es saludo.
            if not tokens_resto:
                return True

            # Si los tokens restantes son solo palabras inofensivas o saludos,
            # es un saludo compuesto como "hola buenas tardes".
            saludo_extra = {
                "hola",
                "buenos",
                "buenas",
                "dias",
                "tardes",
                "noches",
                "muy",
                "que",
                "tal",
                "bien",
                "gracias",
            }

            if tokens_resto <= (inofensivas | saludo_extra):
                return True

            # Hay tokens significativos después del saludo: NO es solo saludo.
            return False

    # Si no coincide con ningún prefijo, comprobar tokens globales: si solo
    # contienen palabras de saludo, es saludo; en caso contrario no.
    tokens = set(chatbot_tokens(text))
    saludos_tokens = {"hola", "buenos", "buenas", "saludos", "hey", "quetal", "que", "tal"}

    if tokens and tokens <= (saludos_tokens | inofensivas):
        return True

    return False


def is_farewell(text):
    """
    Reconoce agradecimientos y despedidas.
    """

    texto = normalize_text(text)

    despedidas = {
        "adios",
        "hasta luego",
        "nos vemos",
        "gracias",
        "muchas gracias",
    }

    # Palabras que indican una consulta real después de un saludo/agradecimiento.
    palabras_consulta = {
        "que",
        "qué",
        "donde",
        "dónde",
        "cuando",
        "cuándo",
        "puedo",
        "puede",
        "puede",
        "puedes",
        "quiero",
        "sabes",
        "sabes",
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
        "ubicación",
        "lugar",
        "ruta",
        "recomienda",
        "recomendar",
        "donde",
        "dónde",
        "a",
        "qué",
        "aquí",
        "cómo",
        "como",
        "puedo",
        "puede",
        "me",
        "mi",
        "nos",
        "para",
        "sabes",
        "dime",
        "decir",
        "saber",
        "sabes",
    }

    agradecimiento_extra = {
        "por",
        "muy",
        "amable",
        "ayudar",
        "ayudarme",
        "ayuda",
        "saludos",
        "gracias",
        "muchas",
        "tu",
        "tus",
        "favor",
        "de",
        "la",
        "el",
        "en",
        "bien",
        "gracias",
    }

    for despedida in despedidas:
        if texto == despedida:
            return True

        if texto.startswith(f"{despedida} "):
            resto = texto[len(despedida):].strip()
            if not resto:
                return True

            tokens_resto = set(chatbot_tokens(resto))
            if not tokens_resto:
                return True

            if tokens_resto & palabras_consulta:
                return False

            if tokens_resto <= agradecimiento_extra:
                return True

            return False

    return False


def farewell_response():
    return (
        "Gracias por comunicarte con el Centro Turístico "
        "Mirador Illari. Esperamos recibirte pronto."
    )


def generic_response_prompt(informacion=None):
    """
    Respuesta cuando el chatbot no reconoce la pregunta.
    """

    if (
        informacion
        and getattr(
            informacion,
            "chatbot_respuesta_predeterminada",
            None
        )
    ):
        return plain_text(
            informacion.chatbot_respuesta_predeterminada
        )

    return (
        "No encontré una respuesta relacionada con tu pregunta. "
        "Puedes consultar los horarios, la ubicación, los servicios, "
        "los precios, los eventos o los medios de contacto."
    )


def greeting_response(informacion=None):
    """
    Respuesta para los saludos.
    """

    if (
        informacion
        and getattr(
            informacion,
            "chatbot_intro",
            None
        )
    ):
        return plain_text(
            informacion.chatbot_intro
        )

    return (
        "¡Hola! Soy el chatbot del Mirador Illari. "
        "Puedes preguntarme por horarios, ubicación, "
        "servicios, precios, eventos o contacto."
    )

# Palabras utilizadas para reconocer cada tema.
REGLAS_TEMAS = {

    "horario": {
        "horario",
        "hora",
        "abrir",
        "apertura",
        "atencion",
        "cerrar",
        "cierra",
        "lunes",
        "martes",
        "miercoles",
        "jueves",
        "viernes",
        "sabado",
        "domingo",
        "abren",
        "abrenes",
        "atienden",
    },

    "ubicacion": {
        "ubicacion",
        "mapa",
        "llegar",
        "ruta",
        "sector",
        "parroquia",
        "tena",
        "yutzupino",
        "direccion",
        "donde",
        "queda",
        "quedan",
    },

    "contacto": {
        "contacto",
        "whatsapp",
        "telefono",
        "celular",
        "numero",
        "correo",
        "email",
        "llamar",
        "comunicar",
        "contactar",
        "mensaje",
    },

    "eventos": {
        "evento",
        "agenda",
        "fecha",
        "programacion",
        "festival",
        "novedad",
    },

    "precios": {
        "precio",
        "valor",
        "entrada",
        "adulto",
        "nino",
        "tercera",
    },

    "mascotas": {
        "mascota",
        "mascotas",
        "perro",
        "perros",
        "gato",
        "gatos",
        "animal",
        "animales",
    },

    "servicios": {
        "servicios",
        "atraccion",
        "atracciones",
        "hospedaje",
        "gastronomia",
        "piscina",
        "cabana",
        "cabanas",
        "actividad",
        "actividades",
        "atractivos",
        "parqueadero",
        "restaurante",
        "caballos",
        "cancha",
        "ofrecen",
        "ofrece",
        "hacer",
        "haceres",
    },
}


def detectar_tema_por_condiciones(mensaje):
    """Reconoce intenciones conservadoras, evitando falsos positivos por palabras generales."""
    if not mensaje:
        return None

    tokens = set(chatbot_tokens(mensaje))
    texto = normalize_text(mensaje)
    if not texto:
        return None

    animal_terms = (
        "mascota",
        "mascotas",
        "perro",
        "perros",
        "gato",
        "gatos",
        "animal",
        "animales",
    )

    frases_alimentos = (
        "alimento",
        "alimentos",
        "comida",
        "comidas",
        "llevar comida",
        "ingresar comida",
        "entrar con comida",
        "llevar alimentos",
        "dejan entrar alimentos",
        "puedo llevar comida",
        "puedo ingresar comida",
        "se puede llevar comida",
        "quiero llevar comida",
        "bebidas",
    )
    if any(frase in texto for frase in frases_alimentos):
        return "alimentos"

    frases_mascotas = (
        "aceptan mascotas",
        "permiten mascotas",
        "puedo llevar mi perro",
        "puedo llevar mi gato",
        "puedo ingresar con un perro",
        "puedo ingresar con un gato",
        "puedo entrar con mi perro",
        "puedo ir con mi perro",
        "puedo ir con mi gato",
        "puedo llevar mascota",
        "puedo llevar mascotas",
        "dejan entrar mascotas",
        "puedo llevar un perro",
        "puedo llevar un gato",
        "puedo llevar animales",
        "puedo entrar con un animal",
        "aceptan perros",
        "permiten perros",
        "aceptan gatos",
        "permiten gatos",
    )
    if any(frase in texto for frase in frases_mascotas) or (
        any(animal in texto for animal in animal_terms)
        and any(
            palabra in texto
            for palabra in (
                "llevar",
                "entrar",
                "aceptan",
                "permiten",
                "ir con",
                "ingresar con",
                "llevar mi",
            )
        )
    ):
        return "mascotas"

    frases_parqueadero = (
        "parqueadero",
        "parqueo",
        "estacionamiento",
        "estacionar",
        "dejar el carro",
        "dejar el auto",
        "dejar el vehiculo",
        "dejar el vehículo",
        "vehiculo",
        "vehículo",
    )
    if any(frase in texto for frase in frases_parqueadero):
        return "parqueadero"

    frases_pagos = (
        "metodo de pago",
        "metodos de pago",
        "forma de pago",
        "formas de pago",
        "como pagar",
        "como puedo pagar",
        "puedo pagar por transferencia",
        "aceptan efectivo",
        "aceptan tarjeta",
        "transferencia bancaria",
        "transferencias bancarias",
        "pago",
        "pagos",
        "pagar",
        "efectivo",
        "tarjeta",
        "transferencia",
        "transferencias",
    )
    if any(frase in texto for frase in frases_pagos):
        return "pagos"

    frases_reserva_general = (
        "hay que reservar",
        "necesito reservar",
        "se necesita reserva",
        "requiere reserva",
        "debo reservar",
        "tengo que reservar",
        "reservacion",
        "reservación",
    )
    if any(frase in texto for frase in frases_reserva_general):
        return "reserva_general"

    consultas_mejor_momento = (
        "mejor horario",
        "mejor hora",
        "hora recomendada",
        "momento recomendado",
        "cuando conviene ir",
        "cuando es mejor ir",
        "a que hora conviene ir",
        "a que hora se ve el atardecer",
        "para ver el atardecer",
        "ver el atardecer",
        "hora del atardecer",
        "mejor momento para visitar",
    )
    if any(frase in texto for frase in consultas_mejor_momento):
        return "mejor_momento"

    frases_contacto = (
        "como puedo comunicarme",
        "como puedo contactarlos",
        "como los contacto",
        "quiero contactarlos",
        "quiero comunicarme con ustedes",
        "como hablo con ustedes",
        "como puedo hablar con ustedes",
        "datos de contacto",
        "numero de contacto",
        "como contacto",
        "como me contacto",
        "como puedo contactarme",
        "como comunicarme",
        "como contactar",
        "whatsapp",
        "telefono",
        "celular",
        "correo",
    )
    if any(frase in texto for frase in frases_contacto) or tokens & REGLAS_TEMAS["contacto"]:
        return "contacto"

    frases_horario = (
        "horario de atencion",
        "horario de atención",
        "cuando abren",
        "a que hora abren",
        "cuando cierran",
        "que hora abren",
        "a que hora atienden",
        "horario",
        "hora",
    )
    if any(frase in texto for frase in frases_horario) or (
        tokens & REGLAS_TEMAS["horario"]
        or "cuando abre" in texto
        or "a que hora abre" in texto
    ):
        return "horario"

    frases_como_llegar = (
        "como llegar",
        "como llego",
        "como puedo llegar",
        "como se llega",
        "que ruta tomo",
        "indicaciones para llegar",
        "camino para llegar",
        "como llegar al lugar",
        "como llego al lugar",
    )
    if any(frase in texto for frase in frases_como_llegar):
        return "como_llegar"

    frases_mapa = (
        "mapa",
        "google maps",
        "muestreme el mapa",
        "muestrame el mapa",
        "quiero ver el mapa",
        "ver el mapa",
        "dame la ubicacion",
        "dame la ubicación",
        "ubicacion en google maps",
        "ubicación en google maps",
    )
    if any(frase in texto for frase in frases_mapa):
        return "mapa"

    frases_alojamiento = (
        "alojamiento",
        "hospedaje",
        "hospedar",
        "alojarme",
        "alojarse",
        "hospedarme",
        "hospedarse",
        "donde dormir",
        "donde puedo dormir",
        "puedo dormir",
        "puedo quedarme",
        "me puedo quedar",
        "quiero quedarme",
        "me puedo quedar ahi",
        "puedo quedarme ahi",
        "donde puedo quedarme",
        "lugar para quedarse",
        "lugar para dormir",
        "lugar para pasar la noche",
        "pasar la noche",
        "puedo pasar la noche",
        "quedarse a dormir",
        "quedarme a dormir",
        "donde quedarse",
        "tienen alojamiento",
        "hay alojamiento",
        "tienen hospedaje",
        "hay hospedaje",
        "puedo alojarme",
        "puedo hospedarme",
        "glamping",
        "glampin",
        "glampign",
    )
    if any(frase in texto for frase in frases_alojamiento):
        return "alojamiento"

    frases_ubicacion = (
        "donde queda",
        "donde esta",
        "donde estan",
        "donde se encuentra",
        "donde estan ubicados",
        "donde quedan",
        "direccion",
        "ubicacion",
        "ubicación",
        "donde queda el lugar",
        "donde queda mirador",
    )
    if any(frase in texto for frase in frases_ubicacion) or tokens & REGLAS_TEMAS["ubicacion"]:
        return "ubicacion"

    frases_camping = (
        "camping",
        "acampar",
        "puedo acampar",
        "llevar mi carpa",
        "poner mi carpa",
        "espacio para carpa",
        "zona de camping",
        "tienen camping",
        "hay camping",
    )
    if any(frase in texto for frase in frases_camping):
        return "camping"

    frases_eventos = (
        "que eventos",
        "eventos",
        "novedades",
        "programacion",
        "festival",
    )
    if any(frase in texto for frase in frases_eventos) or tokens & REGLAS_TEMAS["eventos"]:
        return "eventos"

    frases_precios = (
        "cuanto cuesta",
        "cuanto cobran",
        "cuanto vale",
        "cuanto cuestan",
        "cuanto valen",
        "precio",
        "precios",
        "costo",
        "costos",
        "valor",
        "tarifa",
        "tarifas",
        "cuanto sale",
    )
    if any(frase in texto for frase in frases_precios) or tokens & REGLAS_TEMAS["precios"]:
        return "precios"

    frases_servicios = (
        "que ofrecen",
        "que puedo hacer",
        "que actividades tienen",
        "que actividades",
        "actividades tienen",
        "que servicios tienen",
        "que servicios ofrecen",
        "que cosas ofrecen",
        "servicios",
        "atractivos",
        "ofrecen",
        "ofrece",
    )
    if any(frase in texto for frase in frases_servicios) or tokens & REGLAS_TEMAS["servicios"]:
        return "servicios"

    return None


def inferir_tema(texto):
    """
    Intenta obtener el tema de una pregunta frecuente.
    """

    tema = detectar_tema_por_condiciones(texto)

    return tema or "general"


def buscar_servicio(mensaje, servicios):
    """
    Busca si el usuario escribió el nombre de un servicio.
    """

    mensaje_normalizado = normalize_text(mensaje)

    mejor_servicio = None
    mejor_puntuacion = 0

    tokens_mensaje = set(
        chatbot_tokens(mensaje)
    )

    for servicio in servicios:

        nombre_normalizado = normalize_text(
            servicio.nombre
        )

        if (
            nombre_normalizado
            and nombre_normalizado in mensaje_normalizado
        ):
            return servicio

        tokens_servicio = set(
            chatbot_tokens(servicio.nombre)
        )

        coincidencias = len(
            tokens_mensaje & tokens_servicio
        )

        if coincidencias > mejor_puntuacion:
            mejor_puntuacion = coincidencias
            mejor_servicio = servicio

    if mejor_puntuacion > 0:
        return mejor_servicio

    return None


def formatear_servicio(servicio):
    """
    Construye la respuesta de un servicio turístico.
    """

    partes = [
        f"Servicio: {servicio.nombre}."
    ]

    descripcion = plain_text(
        servicio.descripcion
    )

    if descripcion:
        partes.append(descripcion)

    precios = []

    if servicio.precio_adulto is not None:
        precios.append(
            f"Adulto: ${servicio.precio_adulto}"
        )

    if servicio.precio_niño is not None:
        precios.append(
            f"Niño: ${servicio.precio_niño}"
        )

    if servicio.precio_tercera_edad is not None:
        precios.append(
            f"Tercera edad: ${servicio.precio_tercera_edad}"
        )

    if precios:
        partes.append(
            "Precios: " + ", ".join(precios) + "."
        )

    elif servicio.precio_texto:
        partes.append(
            f"Precio: {plain_text(servicio.precio_texto)}."
        )

    elif servicio.precio_desde is not None:
        partes.append(
            f"Precio desde: ${servicio.precio_desde}."
        )

    if servicio.capacidad is not None:
        partes.append(
            f"Capacidad: hasta {servicio.capacidad} personas."
        )

    if servicio.disponibilidad:
        partes.append(
            f"Disponibilidad: "
            f"{plain_text(servicio.disponibilidad)}."
        )

    if servicio.requiere_reserva:
        partes.append(
            "Este servicio requiere reserva previa."
        )

    return " ".join(partes)


def respuesta_por_condicion(
    tema,
    mensaje,
    informacion=None
):
    """Genera la respuesta directa según el tema reconocido usando datos reales del proyecto."""
    contacto = get_contacto_activo()

    if tema == "horario":
        horario = plain_text(getattr(contacto, "horarios_atencion", "") or "")
        if horario:
            return (
                "El Centro Turístico Mirador Illari atiende "
                f"{horario.rstrip('.')}"
                "."
            )
        return "El horario de atención todavía no se encuentra registrado."

    elif tema == "ubicacion":
        faq_ubicacion = buscar_faq_por_palabras(("donde esta", "donde está", "ubicado", "ubicados", "donde queda"))
        if faq_ubicacion:
            return faq_ubicacion[1]

        direccion = plain_text(getattr(contacto, "direccion", "") or "")
        direccion = limpiar_direccion_para_mapa(direccion)
        if direccion:
            direccion_limpia = direccion.strip()
            if normalize_text(direccion_limpia).startswith("en "):
                return (
                    "El Centro Turístico Mirador Illari está ubicado "
                    f"{direccion_limpia.rstrip('.')}."
                )
            return (
                "El Centro Turístico Mirador Illari está ubicado en "
                f"{direccion_limpia.rstrip('.')}."
            )
        return "La ubicación todavía no se encuentra registrada. Puedes revisarla en la sección Contacto."

    elif tema == "como_llegar":
        faq_llegar = buscar_faq_por_palabras(("como llegar", "como llego", "ruta", "indicaciones para llegar"))
        if faq_llegar:
            return faq_llegar[1]
        return (
            "Puedes llegar en vehículo hasta el parqueadero del Centro Turístico Mirador Illari "
            "y después caminar aproximadamente cinco minutos."
        )

    elif tema == "mapa":
        direccion = plain_text(getattr(contacto, "direccion", "") or "")
        if direccion:
            return (
                "Puedes ver la ubicación del Centro Turístico Mirador Illari en Google Maps "
                f"o consultar la dirección: {direccion.rstrip('.')}."
            )
        return "Puedes consultar la ubicación del Centro Turístico Mirador Illari en Google Maps."

    elif tema == "alojamiento":
        servicios = list(
            ServicioTuristico.objects.filter(
                activo=True,
                tipo="Hospedaje",
            ).order_by("id")
        )
        if not servicios:
            servicios = list(
                ServicioTuristico.objects.filter(
                    activo=True,
                ).order_by("id")
            )
        for servicio in servicios:
            nombre = normalize_text(servicio.nombre or "")
            if "glamping" in nombre or "hospedaje" in nombre or "alojamiento" in nombre:
                return construir_respuesta_servicio(servicio, mensaje)
        if servicios:
            return construir_respuesta_servicio(servicios[0], mensaje)
        return "No tengo registrado actualmente un servicio de alojamiento."

    elif tema == "camping":
        camping = ServicioTuristico.objects.filter(
            activo=True,
        ).order_by("id")
        nombre_relacionado = None
        for servicio in camping:
            nombre = normalize_text(servicio.nombre or "")
            if "camping" in nombre or "carpa" in nombre:
                nombre_relacionado = servicio
                break
        if nombre_relacionado:
            return construir_respuesta_servicio(nombre_relacionado, mensaje)
        return "No tengo registrado actualmente un servicio de camping."

    elif tema == "alimentos":
        faq = buscar_faq_por_palabras(("alimento", "alimentos", "comida", "ingresar comida", "llevar comida", "bebidas"))
        if faq:
            return faq[1]
        return None

    elif tema == "mascotas":
        faq = buscar_faq_por_palabras(("mascota", "mascotas", "perro", "gato", "animal", "animales"))
        if faq:
            return faq[1]
        return None

    elif tema == "parqueadero":
        faq = buscar_faq_por_palabras(("parqueadero", "parqueo", "estacionamiento", "estacionar", "dejar el carro", "dejar el auto", "vehiculo", "vehículo"))
        if faq:
            return faq[1]
        return None

    elif tema == "pagos":
        faq = buscar_faq_por_palabras(("metodo de pago", "metodos de pago", "forma de pago", "formas de pago", "efectivo", "transferencia", "tarjeta"))
        if faq:
            return faq[1]
        return None

    elif tema == "reserva_general":
        faq = buscar_faq_por_palabras(("necesito reservar", "hay que reservar", "requiere reserva", "reservacion", "reservación"))
        if faq:
            return faq[1]
        return None

    elif tema == "mejor_momento":
        faq = buscar_faq_por_palabras(("mejor horario", "mejor hora", "atardecer", "mejor momento para visitar"))
        if faq:
            return faq[1]
        return None

    elif tema == "contacto":
        datos = []
        whatsapp = plain_text(getattr(contacto, "whatsapp", "") or "")
        telefono = plain_text(getattr(contacto, "telefono", "") or "")
        correo = plain_text(getattr(contacto, "correo", "") or "")
        if whatsapp:
            datos.append(f"WhatsApp: {whatsapp}")
        if telefono:
            datos.append(f"Teléfono: {telefono}")
        if correo:
            datos.append(f"Correo: {correo}")
        if datos:
            return " | ".join(datos)
        return "Los medios de contacto todavía no se encuentran registrados."

    elif tema in {"servicios", "precios"}:
        servicios = list(ServicioTuristico.objects.filter(activo=True).order_by("nombre"))
        if not servicios:
            return "Actualmente no existen servicios turísticos activos registrados."

        servicio_encontrado = buscar_servicio(mensaje, servicios)
        if servicio_encontrado:
            return formatear_servicio(servicio_encontrado)

        if "que puedes hacer" in normalize_text(mensaje) or "que puedo hacer" in normalize_text(mensaje):
            nombres = ", ".join(servicio.nombre for servicio in servicios[:6])
            return (
                "En Mirador Illari puedes disfrutar de "
                f"{nombres}. Si quieres, te puedo ayudar con horarios, precios o reservas."
            )

        nombres = ", ".join(servicio.nombre for servicio in servicios[:6])
        if tema == "precios":
            return (
                "Los precios dependen del servicio seleccionado. Puedes preguntar por uno de estos servicios: "
                f"{nombres}."
            )
        return "Los servicios turísticos disponibles son: " + nombres + "."

    elif tema == "eventos":
        eventos = list(EventoNovedad.objects.filter(activo=True).order_by("fecha_evento", "-fecha_publicacion")[:5])
        if not eventos:
            return "Actualmente no existen eventos o novedades activos registrados."
        detalles = []
        for evento in eventos:
            if evento.fecha_evento:
                detalles.append(f"{evento.titulo} ({evento.fecha_evento.strftime('%d/%m/%Y')})")
            else:
                detalles.append(evento.titulo)
        return "Eventos y novedades disponibles: " + "; ".join(detalles) + "."

    respuesta_local = generic_response_prompt(informacion)
    respuesta_gemini = obtener_respuesta_gemini(mensaje)
    if respuesta_gemini:
        return {
            "respuesta": respuesta_gemini,
            "tema": "gemini",
            "confianza": 50,
            "metodo": "gemini_flash",
            "reconocido": True,
        }
    return {
        "respuesta": respuesta_local,
        "tema": "desconocido",
        "confianza": 0,
        "metodo": "TF-IDF + similitud del coseno",
        "reconocido": False,
    }


def debe_adjuntar_mapa(resultado, mensaje=None, pregunta=None):
    """Indica si la respuesta requiere aportar un mapa de ubicación."""
    if not isinstance(resultado, dict):
        return False

    tema = resultado.get("tema")
    if tema in {"ubicacion", "mapa"}:
        return True

    if tema != "faq_admin":
        return False

    texto = mensaje or ""
    if pregunta and getattr(pregunta, "pregunta", None):
        texto = texto or pregunta.pregunta

    if not texto:
        return False

    tema_texto = detectar_tema_por_condiciones(texto)
    return tema_texto in {"ubicacion", "mapa"}


def crear_vectores_tfidf(
    documentos_tokens,
    consulta_tokens
):
    """
    Crea los vectores TF-IDF sin utilizar API
    ni librerías externas.
    """

    todos_los_tokens = (
        documentos_tokens
        + [consulta_tokens]
    )

    vocabulario = sorted({
        token
        for tokens in todos_los_tokens
        for token in tokens
    })

    if not vocabulario:
        return [], []

    numero_documentos = len(
        documentos_tokens
    )

    frecuencia_documentos = {

        termino: sum(
            1
            for tokens in documentos_tokens
            if termino in set(tokens)
        )

        for termino in vocabulario
    }

    idf = {

        termino: (
            math.log(
                (1 + numero_documentos)
                /
                (
                    1
                    + frecuencia_documentos[termino]
                )
            )
            + 1
        )

        for termino in vocabulario
    }

    def crear_vector(tokens):

        contador = Counter(tokens)

        total = max(
            len(tokens),
            1
        )

        return [

            (
                contador[termino]
                /
                total
            )
            *
            idf[termino]

            for termino in vocabulario
        ]

    vectores_documentos = [

        crear_vector(tokens)

        for tokens in documentos_tokens
    ]

    vector_consulta = crear_vector(
        consulta_tokens
    )

    return (
        vectores_documentos,
        vector_consulta
    )


def similitud_coseno(
    vector_a,
    vector_b
):
    """
    Calcula la similitud entre dos vectores.
    """

    producto = sum(
        a * b
        for a, b in zip(
            vector_a,
            vector_b
        )
    )

    norma_a = math.sqrt(
        sum(
            valor * valor
            for valor in vector_a
        )
    )

    norma_b = math.sqrt(
        sum(
            valor * valor
            for valor in vector_b
        )
    )

    if norma_a == 0 or norma_b == 0:
        return 0.0

    return producto / (
        norma_a * norma_b
    )


def buscar_respuesta_tfidf(
    mensaje,
    preguntas
):
    """
    Busca la pregunta frecuente más parecida.
    """

    registros = list(preguntas)

    if not registros:
        return None, 0.0

    consulta_tokens = chatbot_tokens(
        mensaje
    )

    documentos_tokens = [

        chatbot_tokens(
            pregunta.pregunta
        )

        for pregunta in registros
    ]

    (
        vectores_documentos,
        vector_consulta
    ) = crear_vectores_tfidf(
        documentos_tokens,
        consulta_tokens
    )

    mejor_indice = None
    mejor_similitud = 0.0

    for indice, vector_documento in enumerate(
        vectores_documentos
    ):

        similitud = similitud_coseno(
            vector_consulta,
            vector_documento
        )

        terminos_comunes = set(
            chatbot_tokens(mensaje)
        ) & set(
            chatbot_tokens(registros[indice].pregunta)
        )

        if not terminos_comunes:
            continue

        if similitud > mejor_similitud:
            mejor_indice = indice
            mejor_similitud = similitud

    if mejor_indice is None:
        return None, 0.0

    return (
        registros[mejor_indice],
        mejor_similitud
    )


def procesar_mensaje_chatbot(
    mensaje,
    informacion=None
):
    """
    Orden del chatbot:

    1. Pregunta del usuario.
    2. Condiciones if y elif.
    3. Si no reconoce el tema, aplica TF-IDF.
    4. Calcula la similitud del coseno.
    5. Devuelve una respuesta o pregunta desconocida.
    """

    mensaje = plain_text(mensaje)

    if not mensaje:
        return {
            "respuesta": (
                "Escribe tu pregunta o selecciona "
                "una opción disponible."
            ),
            "tema": "desconocido",
            "confianza": 0,
            "metodo": "validación",
            "reconocido": False,
        }

    preguntas = PreguntaFrecuente.objects.filter(
        activo=True
    )

    mensaje_normalizado = normalize_text(
        mensaje
    )

    # COINCIDENCIA EXACTA O PARCIAL NORMALIZADA
    local_found = False

    faq_texto = obtener_faq_por_texto_exacto(mensaje)
    if faq_texto:
        pregunta, respuesta = faq_texto
        logger.info("Chatbot local encontrado: True (coincidencia exacta por texto)")
        return {
            "respuesta": respuesta,
            "tema": inferir_tema(pregunta.pregunta),
            "confianza": 100,
            "metodo": "faq_admin_exacta_texto",
            "reconocido": True,
        }

    for pregunta in preguntas:

        pregunta_normalizada = normalize_text(
            pregunta.pregunta
        )

        if pregunta_normalizada == mensaje_normalizado:
            respuesta_pregunta = plain_text(pregunta.respuesta)
            if respuesta_pregunta:
                logger.info("Chatbot local encontrado: True (coincidencia exacta)")
                return {
                    "respuesta": respuesta_pregunta,
                    "tema": inferir_tema(
                        pregunta.pregunta
                    ),
                    "confianza": 100,
                    "metodo": "coincidencia exacta",
                    "reconocido": True,
                }

    # PRIMERA PARTE: CONDICIONES IF Y ELIF
    tema = detectar_tema_por_condiciones(
        mensaje
    )

    if tema:
        respuesta_cond = respuesta_por_condicion(
            tema,
            mensaje,
            informacion
        )
        if respuesta_cond:
            logger.info("Chatbot local encontrado: True (condicion '%s')", tema)
            return {
                "respuesta": respuesta_cond,
                "tema": tema,
                "confianza": 100,
                "metodo": "condiciones if/elif",
                "reconocido": True,
            }
        # Si la condición no generó una respuesta útil, continuar.

    # SALUDO
    if is_greeting(mensaje):
        # is_greeting ahora devuelve True solo para saludos "puros".
        logger.info("Chatbot local encontrado: True (saludo)")
        return {
            "respuesta": greeting_response(
                informacion
            ),
            "tema": "saludo",
            "confianza": 100,
            "metodo": "condiciones if/elif",
            "reconocido": True,
        }

    # DESPEDIDA O AGRADECIMIENTO
    if is_farewell(mensaje):
        logger.info("Chatbot local encontrado: True (despedida)")
        return {
            "respuesta": farewell_response(),
            "tema": "despedida",
            "confianza": 100,
            "metodo": "condiciones if/elif",
            "reconocido": True,
        }

    # SEGUNDA PARTE: TF-IDF Y SIMILITUD DEL COSENO
    mejor_pregunta, similitud = buscar_respuesta_tfidf(
        mensaje,
        preguntas
    )

    # Umbral conservador para evitar responder una FAQ no relacionada.
    umbral = 0.55

    if (
        mejor_pregunta
        and similitud >= umbral
    ):

        # Solo devolver si la FAQ tiene una respuesta almacenada válida.
        respuesta_mejor = plain_text(
            mejor_pregunta.respuesta
        )

        if respuesta_mejor:
            confianza = round(
                similitud * 100
            )

            logger.info("Chatbot local encontrado: True (TF-IDF, confianza=%s)", confianza)

            return {
                "respuesta": respuesta_mejor,
                "tema": inferir_tema(
                    mejor_pregunta.pregunta
                ),
                "confianza": min(
                    99,
                    max(
                        1,
                        confianza
                    )
                ),
                "metodo": (
                    "TF-IDF + similitud del coseno"
                ),
                "reconocido": True,
            }

    # PREGUNTA DESCONOCIDA: forzar fallback a Gemini antes de responder genérico
    respuesta_local = generic_response_prompt(
        informacion
    )

    # Debug: indicar si encontramos alguna respuesta local útil hasta aquí
    logger.info("Chatbot local encontrado: False (se invocará Gemini si es posible)")

    respuesta_gemini = None

    try:
        respuesta_gemini = obtener_respuesta_gemini(
            mensaje
        )
    except Exception:
        logger.exception(
            "Error al consultar Gemini durante la respuesta del chatbot."
        )

    if respuesta_gemini:
        return {
            "respuesta": respuesta_gemini,
            "tema": "gemini",
            "confianza": 50,
            "metodo": "gemini_flash",
            "reconocido": True,
        }

    return {
        "respuesta": respuesta_local,
        "tema": "desconocido",
        "confianza": 0,
        "metodo": (
            "TF-IDF + similitud del coseno"
        ),
        "reconocido": False,
    }


@require_POST
def api_chatbot(request):
    """
    Recibe una pregunta desde la página web y devuelve
    una respuesta generada por el motor local.
    """

    if len(request.body) > 4096:
        return JsonResponse(
            {
                "reconocido": False,
                "respuesta": (
                    "La solicitud es demasiado extensa."
                ),
                "confianza": 0,
            },
            status=413,
        )

    try:
        datos = json.loads(
            request.body.decode("utf-8")
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {
                "reconocido": False,
                "respuesta": (
                    "No se pudo interpretar la solicitud."
                ),
                "confianza": 0,
            },
            status=400,
        )

    mensaje = datos.get("mensaje", "")

    if not isinstance(mensaje, str):
        return JsonResponse(
            {
                "reconocido": False,
                "respuesta": (
                    "El mensaje debe contener texto."
                ),
                "confianza": 0,
            },
            status=400,
        )

    mensaje = mensaje.strip()

    if not mensaje:
        return JsonResponse(
            {
                "reconocido": False,
                "respuesta": (
                    "Escribe una pregunta para poder ayudarte."
                ),
                "confianza": 0,
            },
            status=400,
        )

    if len(mensaje) > 180:
        return JsonResponse(
            {
                "reconocido": False,
                "respuesta": (
                    "La pregunta es demasiado extensa. "
                    "Escríbela de forma más breve."
                ),
                "confianza": 0,
            },
            status=400,
        )

    if chatbot_rate_limit_exceeded(request):
        return JsonResponse(
            {
                "reconocido": False,
                "respuesta": (
                    "Has realizado muchas consultas. "
                    "Intenta nuevamente en un momento."
                ),
                "confianza": 0,
            },
            status=429,
        )

    try:
        faq_exacta = obtener_faq_exacta(
            datos.get("pregunta_id"),
            mensaje,
        ) if datos.get("pregunta_id") is not None else None
        faq_pregunta = None

        if faq_exacta:
            pregunta, respuesta = faq_exacta
            faq_pregunta = pregunta
            resultado = {
                "reconocido": True,
                "respuesta": respuesta,
                "tema": "faq_admin",
                "confianza": 100,
                "metodo": "faq_admin_exacta",
                "sugerencias": [],
            }
            logger.info(
                "FAQ exacta seleccionada: id=%s metodo=faq_admin_exacta confianza=100",
                pregunta.id,
            )
        else:
            faq_texto = obtener_faq_por_texto_exacto(mensaje)
            if faq_texto:
                pregunta, respuesta = faq_texto
                faq_pregunta = pregunta
                resultado = {
                    "reconocido": True,
                    "respuesta": respuesta,
                    "tema": "faq_admin",
                    "confianza": 100,
                    "metodo": "faq_admin_exacta_texto",
                    "sugerencias": [],
                }
                logger.info(
                    "FAQ exacta por texto seleccionada: id=%s metodo=faq_admin_exacta_texto confianza=100",
                    pregunta.id,
                )
            else:
                resultado = None

        servicio_detectado = None
        if resultado is None:
            contexto = request.session.get("chatbot_contexto", {})
            mensaje_normalizado = normalize_text(mensaje)
            contexto_ambiguo = bool(contexto) and any(
                frase in mensaje_normalizado for frase in (
                    "cuanto cuesta",
                    "precio",
                    "cuanto vale",
                    "cuantas personas",
                    "cuántas personas",
                    "hay que reservar",
                    "requiere reserva",
                    "disponibilidad",
                    "esta disponible",
                    "que incluye",
                    "qué incluye",
                    "quiero hospedarme",
                    "quiero alojarme",
                    "quiero reservar",
                )
            )

            tema_detectado = detectar_tema_por_condiciones(mensaje)
            if contexto_ambiguo and tema_detectado in {"precios", "reserva_general", "servicios", "alojamiento"}:
                servicio_contexto = detectar_servicio(mensaje, contexto)
                if servicio_contexto is not None:
                    servicio_detectado = servicio_contexto
                    respuesta_servicio = construir_respuesta_servicio(servicio_detectado, mensaje)
                    if respuesta_servicio:
                        resultado = {
                            "reconocido": True,
                            "respuesta": respuesta_servicio,
                            "tema": tema_detectado,
                            "confianza": 100,
                            "sugerencias": sugerencias_por_servicio(servicio_detectado),
                        }

            if resultado is None:
                tema_detectado = detectar_tema_por_condiciones(mensaje)
                if tema_detectado:
                    respuesta_tema = respuesta_por_condicion(tema_detectado, mensaje, get_informacion_activa())
                    if respuesta_tema:
                        resultado = {
                            "reconocido": True,
                            "respuesta": respuesta_tema,
                            "tema": tema_detectado,
                            "confianza": 100,
                            "sugerencias": [],
                        }

            if resultado is None:
                servicio_detectado = detectar_servicio(mensaje, contexto)
                nombre_explicito = (
                    servicio_detectado is not None and (
                        normalize_text(servicio_detectado.nombre) in mensaje_normalizado
                        or normalize_text(servicio_detectado.nombre).split()[0] in mensaje_normalizado.split()
                    )
                )
                solicitud_servicio = any(
                    frase in mensaje_normalizado for frase in (
                        "quiero hospedarme",
                        "quiero alojarme",
                        "quiero reservar",
                        "quiero quedarme",
                        "me puedo quedar",
                    )
                )
                if servicio_detectado is not None and not (
                    nombre_explicito or contexto_ambiguo or solicitud_servicio
                ):
                    servicio_detectado = None

        if resultado is None:
            if servicio_detectado is not None:
                respuesta_servicio = construir_respuesta_servicio(servicio_detectado, mensaje)
                if respuesta_servicio:
                    resultado = {
                        "reconocido": True,
                        "respuesta": respuesta_servicio,
                        "tema": "servicio",
                        "confianza": 100,
                        "sugerencias": sugerencias_por_servicio(servicio_detectado),
                    }
                else:
                    resultado = procesar_mensaje_chatbot(mensaje, get_informacion_activa())
            else:
                resultado = procesar_mensaje_chatbot(mensaje, get_informacion_activa())

        if isinstance(resultado, str):
            resultado = {
                "reconocido": True,
                "respuesta": resultado,
                "tema": "respuesta_local",
                "confianza": 100,
                "sugerencias": [],
            }

        if not isinstance(resultado, dict):
            raise TypeError(
                "El motor del chatbot no devolvió un resultado válido."
            )

        resultado.setdefault(
            "respuesta",
            "No pude generar una respuesta.",
        )
        resultado.setdefault("reconocido", True)
        resultado.setdefault("confianza", 0)
        resultado.setdefault(
            "sugerencias",
            [
                "Horarios de atención",
                "Ubicación",
                "Servicios turísticos",
                "Eventos y novedades",
            ],
        )

        if servicio_detectado is not None:
            request.session["chatbot_contexto"] = crear_contexto_chatbot(
                servicio_detectado,
                tema=resultado.get("tema", "servicio"),
                intencion="consulta_servicio"
            )
        elif resultado and resultado.get("tema") in {"alojamiento", "camping", "servicio"}:
            servicio_detectado = detectar_servicio(mensaje, request.session.get("chatbot_contexto", {}))
            if servicio_detectado is not None:
                request.session["chatbot_contexto"] = crear_contexto_chatbot(
                    servicio_detectado,
                    tema=resultado.get("tema", "servicio"),
                    intencion="consulta_servicio"
                )

        historial = request.session.get("historial_chatbot", [])
        historial.append({
            "usuario": mensaje,
            "chatbot": resultado["respuesta"],
            "tema": resultado.get("tema", "desconocido"),
            "confianza": resultado.get("confianza", 0),
        })
        request.session["historial_chatbot"] = historial[-10:]

        resultado.setdefault("sugerencias", [])

        if debe_adjuntar_mapa(resultado, mensaje, faq_pregunta):
            contacto = get_contacto_activo()
            if contacto:
                mapa_embed_url, mapa_link = build_map_embed(
                    contacto.mapa_embed_url,
                    contacto.direccion,
                )
                direccion = plain_text(contacto.direccion)
                if not mapa_embed_url and direccion:
                    mapa_embed_url = (
                        "https://maps.google.com/maps"
                        f"?q={quote_plus(direccion)}"
                        "&z=17"
                        "&hl=es"
                        "&output=embed"
                    )
                resultado["mapa"] = {
                    "embed_url": mapa_embed_url or "",
                    "link": mapa_link or contacto.mapa_embed_url or "",
                    "titulo": "Ubicación del Centro Turístico Mirador Illari",
                }

        request.session.modified = True
        return JsonResponse(resultado)

    except Exception:
        logger.exception("Error al procesar el mensaje del chatbot.")
        return JsonResponse(
            {
                "reconocido": False,
                "respuesta": "Ocurrió un error interno al procesar la pregunta.",
                "confianza": 0,
            },
            status=500,
        )


@require_POST
def limpiar_chatbot(request):
    request.session["historial_chatbot"] = []
    request.session["chatbot_contexto"] = {
        "ultimo_servicio": None,
        "ultimo_tema": None,
        "ultima_intencion": None,
    }
    request.session.modified = True
    return JsonResponse({"ok": True, "mensaje": "Sesión del chatbot reiniciada."})


def chatbot(request):
    """
    Función alternativa para el formulario
    del chatbot sin JavaScript.
    """

    if request.method == "POST":

        if "limpiar" in request.POST:

            request.session[
                "chat_historial"
            ] = []

            return redirect_back_or_home(request)

        mensaje = request.POST.get(
            "mensaje",
            ""
        ).strip()

        opcion = request.POST.get(
            "opcion",
            ""
        ).strip()

        if opcion:
            mensaje = opcion

        if mensaje:

            resultado = procesar_mensaje_chatbot(
                mensaje,
                get_informacion_activa()
            )

            texto_respuesta = (
                f"{resultado['respuesta']}\n\n"
                f"Tema: {resultado['tema']} | "
                f"Confianza: "
                f"{resultado['confianza']}%"
            )

            historial = request.session.get(
                "chat_historial",
                []
            )

            historial.append({
                "tipo": "usuario",
                "texto": mensaje
            })

            historial.append({
                "tipo": "bot",
                "texto": texto_respuesta
            })

            request.session[
                "chat_historial"
            ] = historial[-10:]

    return redirect_back_or_home(request)


def error_404(request, exception):
    return render(
        request,
        'principal/404.html',
        status=404
    )