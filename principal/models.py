import os
import re

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django_ckeditor_5.fields import CKEditor5Field
from django.utils.html import strip_tags
from html import unescape
from PIL import Image


def validate_image_file(
    image,
    *,
    min_short_side=600,
    min_long_side=1000,
    allowed_extensions=None
):
    """Valida formato, peso y dimensiones de las imágenes públicas."""

    if not image:
        return

    extension = os.path.splitext(
        getattr(image, "name", "")
    )[1].lower()

    allowed_extensions = allowed_extensions or {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }

    if extension not in allowed_extensions:
        raise ValidationError(
            "Formato no permitido. Utilice JPG, JPEG, PNG o WEBP."
        )

    limite = 5 * 1024 * 1024

    if getattr(image, "size", 0) > limite:
        raise ValidationError(
            "La imagen no debe superar los 5 MB."
        )

    try:
        with Image.open(image) as img:
            width, height = img.size
    except Exception as exc:
        raise ValidationError(
            "La imagen no es válida."
        ) from exc
    finally:
        if hasattr(image, "seek"):
            image.seek(0)

    lado_menor = min(width, height)
    lado_mayor = max(width, height)

    if (
        lado_menor < min_short_side
        or lado_mayor < min_long_side
    ):
        raise ValidationError(
            f"La imagen debe tener como mínimo "
            f"{min_short_side} px en su lado menor y "
            f"{min_long_side} px en su lado mayor."
        )


def validate_public_image(image):
    """Valida imágenes para servicios, eventos y galería."""
    validate_image_file(
        image,
        allowed_extensions={'.jpg', '.jpeg', '.png', '.webp'},
    )


def validate_carrusel_image(image):
    """Valida que la imagen del carrusel tenga un formato y tamaño aceptado."""
    validate_image_file(
        image,
        allowed_extensions={'.jpg', '.jpeg', '.png', '.webp'},
    )


def validate_logo_image(image):
    """Valida que el logo institucional sea una imagen válida, con formato permitido y peso máximo de 2 MB."""
    if not image:
        return

    extension = os.path.splitext(
        getattr(image, "name", "")
    )[1].lower()

    formatos_permitidos = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }

    if extension not in formatos_permitidos:
        raise ValidationError(
            "El logo debe estar en formato JPG, JPEG, PNG o WEBP."
        )

    limite = 2 * 1024 * 1024

    if getattr(image, "size", 0) > limite:
        raise ValidationError(
            "El logo no debe superar los 2 MB."
        )

    try:
        with Image.open(image) as img:
            img.verify()
    except Exception as exc:
        raise ValidationError(
            "El archivo seleccionado no es una imagen válida."
        ) from exc
    finally:
        if hasattr(image, "seek"):
            image.seek(0)


def validate_phone_number(value):
    """Valida que el número de teléfono o WhatsApp contenga solo dígitos y opcionalmente + al inicio."""
    if not value:
        return

    value = value.strip()

    # Permite: + opcional al inicio, dígitos, espacios y guiones
    if not re.fullmatch(r"\+?\d[\d\s-]*", value):
        raise ValidationError(
            "Ingrese un número de teléfono válido."
        )

    # Contar solo los dígitos (eliminar +, espacios y guiones)
    digits = re.sub(r"\D", "", value)

    # Validar que haya entre 7 y 15 dígitos
    if not 7 <= len(digits) <= 15:
        raise ValidationError(
            "El número debe contener entre 7 y 15 dígitos."
        )


class CarruselInicio(models.Model):
    id_usuario = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name="Administrador", blank=True, null=True)
    imagen = models.ImageField(
        upload_to='carrusel/',
        verbose_name='Imagen de Fondo',
        help_text=(
            'Tamaño recomendado: 1000 × 1250 px. '
            'Utilice imágenes verticales con el elemento principal centrado. '
            'Formatos permitidos: JPG, JPEG, PNG y WEBP.'
        ),
    )
    orden = models.PositiveIntegerField(default=0, verbose_name='Orden de aparición')
    activo = models.BooleanField(default=True, verbose_name='¿Mostrar esta foto en el Carrusel?')

    class Meta:
        verbose_name = "Imagen de Carrusel"
        verbose_name_plural = "1. Carrusel de Inicio (Solo Fotos)"
        ordering = ['orden']

    def clean(self):
        super().clean()
        if self.imagen:
            validate_carrusel_image(self.imagen)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Foto de Portada #{self.id} - Orden: {self.orden}"


class ContenidoInicio(models.Model):
    id_usuario = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name="Administrador", blank=True, null=True)
    activo_informacion = models.BooleanField(default=True, verbose_name="¿Mostrar estos textos en la Web?")
    
    # Textos del Banner Superior
    hero_titulo = models.CharField(max_length=200, blank=True, verbose_name="Título del Banner")
    hero_subtitulo = models.CharField(max_length=250, blank=True, verbose_name="Subtítulo del Banner")
    hero_boton_texto = models.CharField(max_length=100, blank=True, default="Planifica tu visita", verbose_name="Texto del botón del banner")
    hero_boton_url = models.CharField(max_length=500, blank=True, default="/contacto/", verbose_name="Enlace del botón del banner")
    
    # Sección de atractivos
    atractivos_titulo = models.CharField(max_length=100, blank=True, default="Nuestros atractivos", verbose_name="Título de sección de atractivos")
    atractivos_descripcion = CKEditor5Field('Descripción de sección de atractivos', config_name='default', blank=True, default="Explora los lugares y experiencias que hacen único al Mirador Illari.")
    
    # Textos de las 4 Tarjetas de Atractivos Inferiores
    atractivo_1_activo = models.BooleanField(default=True, verbose_name="Mostrar tarjeta Paisajes")
    atractivo_1_titulo = models.CharField(max_length=100, blank=True, verbose_name="Título Tarjeta 1")
    atractivo_1_desc = CKEditor5Field('Descripción Tarjeta 1', config_name='default', blank=True)
    atractivo_1_imagen = models.ImageField(
        upload_to="inicio/atractivos/",
        blank=True,
        null=True,
        verbose_name="Imagen de Paisajes",
    )
    
    atractivo_2_activo = models.BooleanField(default=True, verbose_name="Mostrar tarjeta Aventura")
    atractivo_2_titulo = models.CharField(max_length=100, blank=True, verbose_name="Título Tarjeta 2")
    atractivo_2_desc = CKEditor5Field('Descripción Tarjeta 2', config_name='default', blank=True)
    atractivo_2_imagen = models.ImageField(
        upload_to="inicio/atractivos/",
        blank=True,
        null=True,
        verbose_name="Imagen de Aventura",
    )
    
    atractivo_3_activo = models.BooleanField(default=True, verbose_name="Mostrar tarjeta Cultura local")
    atractivo_3_titulo = models.CharField(max_length=100, blank=True, verbose_name="Título Tarjeta 3")
    atractivo_3_desc = CKEditor5Field('Descripción Tarjeta 3', config_name='default', blank=True)
    atractivo_3_imagen = models.ImageField(
        upload_to="inicio/atractivos/",
        blank=True,
        null=True,
        verbose_name="Imagen de Cultura local",
    )
    
    atractivo_4_activo = models.BooleanField(default=True, verbose_name="Mostrar tarjeta Atención")
    atractivo_4_titulo = models.CharField(max_length=100, blank=True, verbose_name="Título Tarjeta 4")
    atractivo_4_desc = CKEditor5Field('Descripción Tarjeta 4', config_name='default', blank=True)
    atractivo_4_imagen = models.ImageField(
        upload_to="inicio/atractivos/",
        blank=True,
        null=True,
        verbose_name="Imagen de Atención",
    )

    class Meta:
        verbose_name = "Texto de Inicio"
        verbose_name_plural = "2. Textos de Página de Inicio"

    def __str__(self):
        return "Configuración Única de Textos de la Portada"


class InformacionInstitucional(models.Model):
    id_usuario = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name="Administrador", blank=True, null=True)
    titulo = models.CharField(max_length=150, verbose_name="Título Institucional")
    eslogan = models.CharField(max_length=250, blank=True, null=True, verbose_name="Eslogan")
    descripcion = CKEditor5Field('Descripción General', config_name='default')
    nosotros_eyebrow = models.CharField(max_length=100, blank=True, default="Quiénes somos", verbose_name="Etiqueta de sección Nosotros")
    proposito_titulo = models.CharField(max_length=100, blank=True, default="Nuestro propósito", verbose_name="Título de propósito")
    valores_titulo = models.CharField(max_length=100, blank=True, default="Nuestros Valores", verbose_name="Título de valores")
    servicios_titulo = models.CharField(max_length=100, blank=True, default="Servicios Turísticos", verbose_name="Título de servicios")
    eventos_titulo = models.CharField(max_length=100, blank=True, default="Eventos y Novedades", verbose_name="Título de eventos")
    galeria_titulo = models.CharField(max_length=100, blank=True, default="Galería Multimedia", verbose_name="Título de galería")
    contacto_titulo = models.CharField(max_length=100, blank=True, default="Contacto", verbose_name="Título de contacto")
    chatbot_titulo = models.CharField(max_length=150, blank=True, default="Chatbot Mirador Illari", verbose_name="Título del Chatbot")
    chatbot_intro = CKEditor5Field('Texto de bienvenida del chatbot', config_name='default', blank=True, default="Hola, soy Jeyson, tu guía virtual del Mirador Illari. ¿En qué puedo ayudarte?")
    chatbot_placeholder = models.CharField(max_length=150, blank=True, default="Escribe tu mensaje...", verbose_name="Texto del placeholder de entrada")
    chatbot_enviar_texto = models.CharField(max_length=50, blank=True, default="Enviar", verbose_name="Texto del botón Enviar")
    chatbot_opciones_etiqueta = models.CharField(max_length=150, blank=True, default="Opciones rápidas", verbose_name="Etiqueta de opciones rápidas")
    chatbot_respuesta_predeterminada = CKEditor5Field('Respuesta predeterminada del chatbot', config_name='default', blank=True, default="Gracias por tu mensaje. Para más información puedes revisar las opciones rápidas o contactarnos por WhatsApp.")
    proposito = CKEditor5Field('Propósito Institucional', config_name='default', blank=True, null=True)
    historia = CKEditor5Field('Historia', config_name='default', blank=True, null=True)
    mision = CKEditor5Field('Misión', config_name='default')
    vision = CKEditor5Field('Visión', config_name='default')
    logo = models.ImageField(
        upload_to='institucional/',
        blank=True,
        null=True,
        verbose_name="Logo Institucional",
    )
    activo = models.BooleanField(default=True, verbose_name="¿Mostrar en la Web pública?")

    class Meta:
        verbose_name = "Información Institucional"
        verbose_name_plural = "3. Información Institucional"

    def clean(self):
        super().clean()
        if self.logo:
            validate_logo_image(self.logo)

    def __str__(self):
        return self.titulo


class Contacto(models.Model):
    id_usuario = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name="Administrador", blank=True, null=True)
    direccion = models.CharField(max_length=250, verbose_name="Dirección Física")
    mapa_embed_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="Enlace de Google Maps",
        help_text="Pega cualquier enlace de Google Maps o Google Maps App. Se convertirá automáticamente en un mapa incrustado.",
    )
    whatsapp = models.CharField(max_length=20, verbose_name="Número de WhatsApp")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono Fijo")
    correo = models.EmailField(verbose_name="Correo Electrónico")
    horarios_atencion = models.CharField(max_length=200, verbose_name="Horarios de Atención")
    facebook_url = models.URLField(blank=True, null=True, verbose_name="Facebook URL")
    instagram_url = models.URLField(blank=True, null=True, verbose_name="Instagram URL")
    tiktok_url = models.URLField(blank=True, null=True, verbose_name="TikTok URL")
    youtube_url = models.URLField(blank=True, null=True, verbose_name="YouTube URL")
    activo = models.BooleanField(default=True, verbose_name="¿Mostrar en la Web pública?")

    class Meta:
        verbose_name = "Contacto"
        verbose_name_plural = "8. Contacto"

    def clean(self):
        super().clean()

        errores = {}

        # Validar WhatsApp (obligatorio)
        if self.whatsapp:
            try:
                validate_phone_number(self.whatsapp)
            except ValidationError as e:
                errores["whatsapp"] = e.message

        # Validar Teléfono (opcional, pero si tiene valor debe ser válido)
        if self.telefono:
            try:
                validate_phone_number(self.telefono)
            except ValidationError as e:
                errores["telefono"] = e.message

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Contacto {self.id or ''}"


TIPO_SERVICIO_CHOICES = [
    ("Atracciones", "Atracciones"),
    ("Hospedaje", "Hospedaje"),
    ("Gastronomía", "Gastronomía"),
    ("Servicios Generales", "Servicios Generales"),
]


class ServicioTuristico(models.Model):
    id_usuario = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name="Administrador", blank=True, null=True)
    nombre = models.CharField(max_length=150, verbose_name="Nombre del Servicio")
    tipo = models.CharField(
        max_length=100,
        choices=TIPO_SERVICIO_CHOICES,
        verbose_name="Tipo (Atracciones, Hospedaje, Gastronomía, Servicios Generales)",
    )
    descripcion = CKEditor5Field('Descripción', config_name='default')
    precio_desde = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Precio Desde",
        help_text="Valor aproximado cuando el precio varía según temporada o paquete.",
    )
    precio_texto = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Texto de precio",
        help_text="Texto opcional que describa el precio, por ejemplo 'Consultar precio' o 'Desde 120.00'.",
    )
    precio_adulto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Precio Adulto",
    )
    precio_niño = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Precio Niño")
    precio_tercera_edad = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Precio Tercera Edad")
    disponibilidad = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Disponibilidad",
        help_text="Información opcional sobre fechas, horarios o disponibilidad del servicio.",
    )
    requiere_reserva = models.BooleanField(
        default=False,
        verbose_name="Requiere reserva",
        help_text="Marca si el servicio necesita reserva previa.",
    )
    capacidad = models.PositiveIntegerField(blank=True, null=True, verbose_name="Capacidad Máxima")
    incluye = CKEditor5Field('Incluye', config_name='default', blank=True, null=True)
    imagen_principal = models.ImageField(
        upload_to='servicios/',
        validators=[validate_public_image],
        verbose_name="Imagen principal",
    )
    activo = models.BooleanField(default=True, verbose_name="¿Servicio Activo / Visible?")

    class Meta:
        verbose_name = "Servicio Turístico"
        verbose_name_plural = "5. Servicios Turísticos"

    def clean(self):
        super().clean()

        errores = {}

        campos_precio = {
            "precio_desde": self.precio_desde,
            "precio_adulto": self.precio_adulto,
            "precio_niño": self.precio_niño,
            "precio_tercera_edad": self.precio_tercera_edad,
        }

        for campo, valor in campos_precio.items():
            if valor is not None and valor < 0:
                errores[campo] = (
                    "El precio no puede ser un valor negativo."
                )

        if self.capacidad is not None and self.capacidad <= 0:
            errores["capacidad"] = (
                "La capacidad debe ser mayor a 0."
            )

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


TIPO_AVISO_CHOICES = [
    ("Evento", "Evento"),
    ("Novedad", "Novedad"),
]


class EventoNovedad(models.Model):
    id_usuario = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name="Administrador", blank=True, null=True)
    titulo = models.CharField(max_length=200, verbose_name="Título del Evento")
    contenido = CKEditor5Field('Contenido / Detalle', config_name='default')
    tipo = models.CharField(max_length=100, choices=TIPO_AVISO_CHOICES, verbose_name="Tipo de Aviso")
    imagen = models.ImageField(
        upload_to='eventos/',
        validators=[validate_public_image],
        verbose_name="Imagen publicitaria",
    )
    fecha_publicacion = models.DateField(auto_now_add=True, verbose_name="Fecha de Publicación")
    fecha_evento = models.DateField(blank=True, null=True, verbose_name="Fecha del Evento")
    precio_texto = models.CharField(
        "Precio",
        max_length=100,
        blank=True,
        help_text="Ejemplo: Incluido con la entrada, Desde $45, Gratuito, Consultar disponibilidad.",
    )
    activo = models.BooleanField(default=True, verbose_name="¿Publicación Activa?")

    class Meta:
        verbose_name = "Evento o Novedad"
        verbose_name_plural = "6. Eventos y Novedades"

    def clean(self):
        super().clean()

        if self.tipo == "Evento" and not self.fecha_evento:
            raise ValidationError({
                "fecha_evento": (
                    "Debes ingresar la fecha del evento."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo


class GaleriaMultimedia(models.Model):
    id_usuario = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name="Administrador", blank=True, null=True)
    titulo = models.CharField(max_length=150, blank=True, null=True, verbose_name="Título")
    descripcion = CKEditor5Field('Descripción Corta', config_name='default', blank=True, null=True)
    imagen = models.ImageField(
        upload_to='galeria/',
        validators=[validate_public_image],
        verbose_name="Archivo de imagen",
    )
    fecha_subida = models.DateField(auto_now_add=True, verbose_name="Fecha de Subida")
    activo = models.BooleanField(default=True, verbose_name="¿Visible en Galería?")

    class Meta:
        verbose_name = "Elemento de Galería"
        verbose_name_plural = "7. Galería Multimedia"

    def __str__(self):
        return self.titulo if self.titulo else f"Imagen {self.id}"


class PreguntaFrecuente(models.Model):
    id_usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        verbose_name="Administrador",
        blank=True,
        null=True
    )

    pregunta = CKEditor5Field(
        "Pregunta del Usuario",
        config_name="default"
    )

    respuesta = CKEditor5Field(
        "Respuesta del Chatbot",
        config_name="default"
    )

    activo = models.BooleanField(
        default=True,
        verbose_name="¿Activa en la Base del Chatbot?"
    )

    class Meta:
        verbose_name = "Pregunta Frecuente"
        verbose_name_plural = "9. Preguntas Frecuentes"

    def __str__(self):
        texto = unescape(
            strip_tags(str(self.pregunta or ""))
        )
        return texto[:100]


class Valor(models.Model):
    id_usuario = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name="Administrador", blank=True, null=True)
    titulo = models.CharField(max_length=100, verbose_name="Nombre del Valor")
    descripcion = CKEditor5Field('Descripción del Valor', config_name='default')
    icono_emoji = models.CharField(max_length=10, blank=True, null=True, verbose_name="Ícono (Emoji)")
    orden = models.PositiveIntegerField(default=0, verbose_name="Orden de aparición")
    activo = models.BooleanField(default=True, verbose_name="¿Mostrar este valor?")

    class Meta:
        verbose_name = "Valor Institucional"
        verbose_name_plural = "4. Valores Institucionales"
        ordering = ['orden']

    def __str__(self):
        return self.titulo
