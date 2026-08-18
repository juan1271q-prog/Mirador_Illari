import logging
import os
import re
from html import unescape

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from google import genai
except ImportError:  # pragma: no cover
    genai = None


def _plain_text(value: str) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _get_gemini_api_key() -> str | None:
    return (
        os.getenv("GEMINI_API_KEY")
        or getattr(settings, "GEMINI_API_KEY", None)
    )


def _get_gemini_model_name() -> str:
    return (
        os.getenv("GEMINI_MODEL_NAME")
        or getattr(settings, "GEMINI_MODEL_NAME", "gemini-3.6-flash")
    )


def _get_gemini_client():
    if genai is None:
        return None

    api_key = _get_gemini_api_key()
    if not api_key:
        # Make the absence of the API key visible in the Django terminal for diagnosis.
        logger.error("GEMINI_API_KEY no configurada: Gemini deshabilitado. Agrega GEMINI_API_KEY en .env")
        return None

    http_options = None
    api_endpoint = getattr(settings, "GEMINI_API_ENDPOINT", None)
    if api_endpoint:
        http_options = genai.types.HttpOptions(base_url=api_endpoint)

    try:
        return genai.Client(
            api_key=api_key,
            http_options=http_options,
        )
    except Exception as e:
        # Log only error type and message to terminal for diagnosis.
        try:
            msg = str(e)
            # Never log the raw API key
            if api_key and api_key in msg:
                msg = msg.replace(api_key, "[REDACTED]")
        except Exception:
            msg = "(error al formatear el mensaje de la excepción)"
        logger.error("Gemini client error: %s: %s", type(e).__name__, msg)
        return None


def _extract_response_text(response) -> str | None:
    if response is None:
        return None
    # Prefer the full text field when available.
    # Collect possible text sources.
    text_val = None
    try:
        if hasattr(response, "text") and response.text:
            text_val = str(response.text).strip()
    except Exception:
        text_val = None

    # Assemble from candidates[0].content.parts first (most complete), then response.parts
    parts_text = None
    try:
        texto_parts = []
        if hasattr(response, "candidates"):
            try:
                candidates = getattr(response, "candidates")
                if candidates:
                    first = candidates[0]
                    content = getattr(first, "content", None)
                    if content and hasattr(content, "parts"):
                        for part in getattr(content, "parts"):
                            try:
                                if hasattr(part, "text") and part.text:
                                    texto_parts.append(str(part.text).strip())
                            except Exception:
                                continue
            except Exception:
                pass

        # If still empty, try top-level response.parts
        if not texto_parts:
            parts = getattr(response, "parts", None)
            if parts:
                for part in parts:
                    try:
                        if hasattr(part, "text") and part.text:
                            texto_parts.append(str(part.text).strip())
                    except Exception:
                        continue

        if texto_parts:
            parts_text = " ".join(texto_parts).strip()
    except Exception:
        parts_text = None

    # If both exist, prefer the more complete (longer) text to avoid truncation.
    try:
        if text_val and parts_text:
            # Use parts_text when it is meaningfully longer than text_val.
            if len(parts_text) > len(text_val) + 5:
                return parts_text
            return text_val
        if text_val:
            return text_val
        if parts_text:
            return parts_text
    except Exception:
        pass

    # Last fallback: try candidates fields like output/text
    try:
        if hasattr(response, "candidates"):
            candidates = getattr(response, "candidates")
            if candidates:
                first = candidates[0]
                for attr in ("output", "content", "text"):
                    val = getattr(first, attr, None)
                    if val:
                        return str(val).strip()
    except Exception:
        pass

    return None


def _build_public_context(mensaje: str) -> str:
    from django.utils.html import strip_tags

    from .models import (
        Contacto,
        EventoNovedad,
        InformacionInstitucional,
        PreguntaFrecuente,
        ServicioTuristico,
    )

    informacion = (
        InformacionInstitucional.objects
        .filter(activo=True)
        .order_by("-id")
        .first()
    )

    contacto = (
        Contacto.objects
        .filter(activo=True)
        .order_by("-id")
        .first()
    )

    servicios = list(
        ServicioTuristico.objects
        .filter(activo=True)
        .order_by("nombre")[:5]
    )

    preguntas = list(
        PreguntaFrecuente.objects
        .filter(activo=True)
        .order_by("id")[:5]
    )

    eventos = list(
        EventoNovedad.objects
        .filter(activo=True)
        .order_by("-fecha_evento", "-fecha_publicacion")[:3]
    )

    context_lines = [
        "Eres un asistente para el Centro Turístico Mirador Illari.",
        "Responde en español usando solo la información pública disponible de Mirador Illari.",
        (
            "No inventes precios, horarios, servicios, promociones ni datos que no existan. "
            "Si no tienes suficiente información, di que no puedes responder con seguridad y sugiere contactar al sitio."
        ),
        "No compartas ni uses contraseñas ni credenciales internas.",
        "Mantén la respuesta breve, clara y honesta.",
        "Información pública conocida:"
    ]

    if informacion:
        if informacion.chatbot_intro:
            context_lines.append(
                "Texto de bienvenida: "
                + _plain_text(informacion.chatbot_intro)
            )
        if informacion.chatbot_respuesta_predeterminada:
            context_lines.append(
                "Respuesta predeterminada del chatbot: "
                + _plain_text(informacion.chatbot_respuesta_predeterminada)
            )

    if contacto:
        if contacto.direccion:
            context_lines.append(
                "Dirección: "
                + _plain_text(contacto.direccion)
            )
        if contacto.horarios_atencion:
            context_lines.append(
                "Horario de atención: "
                + _plain_text(contacto.horarios_atencion)
            )
        if contacto.whatsapp:
            context_lines.append(
                "WhatsApp: "
                + _plain_text(contacto.whatsapp)
            )
        if contacto.telefono:
            context_lines.append(
                "Teléfono: "
                + _plain_text(contacto.telefono)
            )
        if contacto.correo:
            context_lines.append(
                "Correo: "
                + _plain_text(contacto.correo)
            )

    if servicios:
        context_lines.append("Servicios turísticos activos:")
        for servicio in servicios:
            line = f"- {servicio.nombre}."
            descripcion = _plain_text(servicio.descripcion)
            if descripcion:
                line += f" {descripcion}"
            if servicio.precio_texto:
                line += f" Precio: {_plain_text(servicio.precio_texto)}."
            elif servicio.precio_adulto is not None or servicio.precio_niño is not None or servicio.precio_tercera_edad is not None:
                precios = []
                if servicio.precio_adulto is not None:
                    precios.append(f"adulto ${servicio.precio_adulto}")
                if servicio.precio_niño is not None:
                    precios.append(f"niño ${servicio.precio_niño}")
                if servicio.precio_tercera_edad is not None:
                    precios.append(f"tercera edad ${servicio.precio_tercera_edad}")
                if precios:
                    line += " Precios: " + ", ".join(precios) + "."
            context_lines.append(line)

    if eventos:
        context_lines.append("Eventos y novedades activas:")
        for evento in eventos:
            title = _plain_text(evento.titulo)
            details = []
            if evento.fecha_evento:
                details.append(evento.fecha_evento.strftime("%d/%m/%Y"))
            if evento.tipo:
                details.append(_plain_text(evento.tipo))
            if details:
                context_lines.append(f"- {title} ({', '.join(details)}).")
            else:
                context_lines.append(f"- {title}.")

    if preguntas:
        context_lines.append("Preguntas frecuentes conocidas:")
        for pregunta in preguntas:
            pregunta_text = _plain_text(pregunta.pregunta)
            respuesta_text = _plain_text(pregunta.respuesta)
            if pregunta_text and respuesta_text:
                context_lines.append(
                    f"- Pregunta: {pregunta_text} Respuesta: {respuesta_text}."
                )

    context_lines.append(f"Pregunta del usuario: {mensaje}")
    context_lines.append("Contesta únicamente con la mejor respuesta posible en español.")

    return "\n".join(context_lines)


def obtener_respuesta_gemini(mensaje: str) -> str | None:
    if not mensaje:
        return None

    if genai is None:
        logger.debug("Gemini no está disponible porque falta el paquete SDK.")
        return None

    client = _get_gemini_client()

    if client is None:
        logger.debug("Gemini no está disponible porque falta la clave o el cliente no se pudo crear.")
        return None

    prompt_text = _build_public_context(mensaje)

    try:
        # Build a clearer, stricter system instruction to improve answer quality.
        system_instruction = (
            "Eres el asistente virtual del Centro Turístico Mirador Illari.\n\n"
            "Responde las preguntas de los visitantes utilizando exclusivamente la información pública proporcionada por el sistema.\n\n"
            "Tu respuesta debe ser clara, natural y útil.\n\n"
            "Cuando el visitante pida una recomendación, utiliza los servicios, actividades, horarios, eventos u otra información disponible para darle una recomendación concreta.\n\n"
            "No respondas solamente con frases generales como: 'Puedes disfrutar en familia' o 'Puedes visitar el centro turístico'.\n\n"
            "Explica brevemente qué podría hacer el visitante según la información disponible.\n\n"
            "Responde normalmente entre 2 y 4 oraciones.\n\n"
            "No dejes frases incompletas.\n\n"
            "No inventes precios, horarios, promociones, servicios, eventos, reservas, teléfonos o direcciones.\n\n"
            "Si no tienes información suficiente para responder algo específico, dilo claramente y recomienda revisar las opciones disponibles o comunicarse con el establecimiento.\n\n"
            "No menciones Gemini, inteligencia artificial, API, base de datos ni detalles técnicos."
        )

        chat = client.chats.create(
            model=_get_gemini_model_name(),
            config=genai.types.GenerateContentConfig(
                temperature=0.2,
                topP=0.85,
                topK=40,
                maxOutputTokens=600,
                systemInstruction=system_instruction,
            ),
        )

        # Log the size of the context sent to Gemini (characters) for diagnosis.
        try:
            logger.info("Contexto Gemini: %d caracteres", len(prompt_text))
        except Exception:
            logger.info("Contexto Gemini: (error calculando longitud)")

        response = chat.send_message(prompt_text)
        texto = _extract_response_text(response)

        # Log the size of the response received (characters)
        try:
            logger.info("Respuesta Gemini: %d caracteres", len(texto) if texto else 0)
        except Exception:
            logger.info("Respuesta Gemini: (error calculando longitud)")

        if texto:
            return _plain_text(texto)

    except Exception as e:
        # Log minimal error info to terminal only (type + message), never secrets.
        try:
            msg = str(e)
            api_key = _get_gemini_api_key()
            if api_key and api_key in msg:
                msg = msg.replace(api_key, "[REDACTED]")
        except Exception:
            msg = "(error al formatear el mensaje de la excepción)"
        logger.error("Gemini generation error: %s: %s", type(e).__name__, msg)

    return None
