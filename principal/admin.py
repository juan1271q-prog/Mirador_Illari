from django import forms
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html, strip_tags
from html import unescape
from .forms import (
    ServicioTuristicoForm,
    ContactoAdminForm,
    EventoNovedadForm,
)
from .models import (
    CarruselInicio,
    ContenidoInicio,
    InformacionInstitucional,
    Contacto,
    ServicioTuristico,
    EventoNovedad,
    GaleriaMultimedia,
    PreguntaFrecuente,
    Valor,
    TIPO_AVISO_CHOICES,
)


class RegistroUnicoAdminMixin:
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False

        return super().has_add_permission(request)

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False


class AdministradorAuditoriaMixin:
    def save_model(self, request, obj, form, change):
        if not getattr(obj, 'id_usuario_id', None):
            obj.id_usuario = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )


class VistaPreviaImagenAdminMixin:
    """
    Agrega una vista previa ampliada de imágenes en Django Admin.
    Cada administrador debe indicar el nombre de su campo de imagen.
    """

    campo_imagen = None
    readonly_fields = ("vista_previa_imagen",)

    class Media:
        js = ("js/admin_image_preview.js",)

    @admin.display(description="Vista previa de la imagen")
    def vista_previa_imagen(self, obj):
        if not obj or not obj.pk:
            return (
                "Guarda primero el registro para visualizar "
                "la imagen completa."
            )

        imagen = getattr(
            obj,
            self.campo_imagen,
            None,
        )

        if not imagen:
            return "No existe una imagen registrada."

        return format_html(
            '<button type="button" '
            'class="image-preview-toggle image-preview-admin-button" '
            'data-image-url="{}" '
            'data-image-title="{}">'
            '<img src="{}" '
            'alt="Vista previa de {}" '
            'class="image-preview-admin-thumb">'
            '</button>',
            imagen.url,
            str(obj),
            imagen.url,
            str(obj),
        )


class ContenidoInicioAdminForm(forms.ModelForm):
    class Meta:
        model = ContenidoInicio
        fields = "__all__"
        labels = {
            "hero_titulo": "Título principal",
            "hero_subtitulo": "Texto debajo del título",
            "hero_boton_texto": "Texto del botón principal",
            "hero_boton_url": "Destino del botón",
            "atractivos_titulo": "Título de la sección",
            "atractivos_descripcion": "Descripción de la sección",
            "atractivo_1_activo": "¿Mostrar Paisajes?",
            "atractivo_1_titulo": "Título de la tarjeta",
            "atractivo_1_desc": "Descripción de la tarjeta",
            "atractivo_2_activo": "¿Mostrar Aventura?",
            "atractivo_2_titulo": "Título de la tarjeta",
            "atractivo_2_desc": "Descripción de la tarjeta",
            "atractivo_3_activo": "¿Mostrar Cultura local?",
            "atractivo_3_titulo": "Título de la tarjeta",
            "atractivo_3_desc": "Descripción de la tarjeta",
            "atractivo_4_activo": "¿Mostrar Atención?",
            "atractivo_4_titulo": "Título de la tarjeta",
            "atractivo_4_desc": "Descripción de la tarjeta",
        }
        help_texts = {
            "hero_titulo": "Es el texto grande que aparece sobre el carrusel.",
            "hero_subtitulo": (
                "Es la frase corta que aparece debajo del título principal."
            ),
            "hero_boton_texto": (
                "Texto visible dentro del botón del Hero. "
                "Ejemplo: Ver servicios."
            ),
            "hero_boton_url": (
                "Dirección a la que llevará el botón. "
                "No la cambies si no conoces la ruta."
            ),
            "atractivos_titulo": (
                "Título principal de la sección ubicada debajo del carrusel."
            ),
            "atractivos_descripcion": (
                "Texto introductorio que aparece debajo del título "
                "de Nuestros atractivos."
            ),
            "atractivo_1_activo": (
                "Desmarca esta opción para ocultar Paisajes de la página de Inicio."
            ),
            "atractivo_1_titulo": "Nombre visible de la tarjeta Paisajes.",
            "atractivo_1_desc": (
                "Texto corto que explica qué encontrará el visitante."
            ),
            "atractivo_2_activo": (
                "Desmarca esta opción para ocultar Aventura de la página de Inicio."
            ),
            "atractivo_2_titulo": "Nombre visible de la tarjeta Aventura.",
            "atractivo_2_desc": (
                "Descripción corta de las actividades de aventura."
            ),
            "atractivo_3_activo": (
                "Desmarca esta opción para ocultar Cultura local de la página de Inicio."
            ),
            "atractivo_3_titulo": (
                "Nombre visible de la tarjeta Cultura local."
            ),
            "atractivo_3_desc": (
                "Descripción corta relacionada con cultura y comunidad."
            ),
            "atractivo_4_activo": (
                "Desmarca esta opción para ocultar Atención de la página de Inicio."
            ),
            "atractivo_4_titulo": "Nombre visible de la tarjeta Atención.",
            "atractivo_4_desc": (
                "Descripción corta sobre atención e información al visitante."
            ),
        }


class InformacionInstitucionalAdminForm(forms.ModelForm):
    class Meta:
        model = InformacionInstitucional
        fields = "__all__"
        labels = {
            "nosotros_eyebrow": "Etiqueta superior",
            "titulo": "Título principal de Nosotros",
            "eslogan": "Frase debajo del título",
            "descripcion": "Presentación general",
            "historia": "Historia",
            "logo": "Logo institucional",
            "proposito_titulo": "Título de la sección Propósito",
            "proposito": "Propósito",
            "mision": "Misión",
            "vision": "Visión",
            "valores_titulo": "Título de la sección Valores",
            "chatbot_titulo": "Nombre del asistente",
            "chatbot_intro": "Mensaje de bienvenida",
            "chatbot_placeholder": "Texto del campo para escribir",
            "chatbot_enviar_texto": "Texto del botón Enviar",
            "chatbot_opciones_etiqueta": "Texto de opciones rápidas",
            "chatbot_respuesta_predeterminada": "Respuesta predeterminada",
            "servicios_titulo": "Título de servicios",
            "eventos_titulo": "Título de eventos y novedades",
            "galeria_titulo": "Título de la galería",
            "contacto_titulo": "Título de contacto",
        }
        help_texts = {
            "nosotros_eyebrow": (
                "Texto pequeño que aparece encima del título principal. "
                "Ejemplo: Quiénes somos."
            ),
            "titulo": "Es el título grande de la portada de Nosotros.",
            "eslogan": "Frase corta ubicada debajo del título principal.",
            "descripcion": (
                "Texto de presentación ubicado en la sección Historia."
            ),
            "historia": (
                "Cuenta brevemente el origen y trayectoria del establecimiento."
            ),
            "logo": (
                "Imagen que identifica visualmente al centro turístico."
            ),
            "proposito": (
                "Explica la razón de ser y el propósito del lugar."
            ),
            "mision": "Describe lo que se busca ofrecer actualmente.",
            "vision": (
                "Describe hacia dónde se quiere proyectar el establecimiento."
            ),
            "valores_titulo": (
                "Título que aparece antes de las tarjetas de Valores."
            ),
            "chatbot_titulo": (
                "Nombre visible del asistente virtual."
            ),
            "chatbot_intro": (
                "Este mensaje aparece cuando se inicia una nueva conversación."
            ),
            "chatbot_placeholder": (
                "Texto que aparece dentro del campo donde el visitante escribe su consulta."
            ),
            "chatbot_enviar_texto": (
                "Texto que se muestra en el botón de envío del chatbot."
            ),
            "chatbot_opciones_etiqueta": (
                "Etiqueta que introducen las opciones rápidas del asistente."
            ),
            "chatbot_respuesta_predeterminada": (
                "Respuesta que se muestra cuando el chatbot no tiene una respuesta específica."
            ),
            "servicios_titulo": (
                "Encabezado de la sección de servicios turísticos en la web."
            ),
            "eventos_titulo": (
                "Encabezado de la sección de eventos y novedades."
            ),
            "galeria_titulo": (
                "Encabezado de la sección de galería multimedia."
            ),
            "contacto_titulo": (
                "Encabezado de la sección de contacto."
            ),
        }


class ContactoAdminFormLocal(ContactoAdminForm):
    class Meta(ContactoAdminForm.Meta):
        labels = {
            "direccion": "Dirección",
            "mapa_embed_url": "Mapa de Google",
            "whatsapp": "WhatsApp",
            "telefono": "Teléfono",
            "correo": "Correo electrónico",
            "horarios_atencion": "Horarios de atención",
            "facebook_url": "Facebook",
            "instagram_url": "Instagram",
            "tiktok_url": "TikTok",
            "youtube_url": "YouTube",
            "activo": "¿Mostrar en la página pública?",
        }
        help_texts = {
            "direccion": "Dirección física del centro turístico para visitantes.",
            "mapa_embed_url": (
                "Enlace oficial de Google Maps que muestra la ubicación del centro."
            ),
            "whatsapp": (
                "Número que utilizarán los visitantes para comunicarse por WhatsApp."
            ),
            "telefono": "Número fijo del centro turístico, si existe.",
            "correo": "Correo electrónico público del centro turístico.",
            "horarios_atencion": (
                "Horario que se mostrará a los visitantes en la página pública."
            ),
            "facebook_url": "Pegue el enlace completo del perfil oficial de Facebook.",
            "instagram_url": "Pegue el enlace completo del perfil oficial de Instagram.",
            "tiktok_url": "Pegue el enlace completo del perfil oficial de TikTok.",
            "youtube_url": "Pegue el enlace completo del perfil oficial de YouTube.",
            "activo": "Active esta información para utilizarla en la página pública de Contacto.",
        }


class ServicioTuristicoAdminForm(ServicioTuristicoForm):
    class Meta(ServicioTuristicoForm.Meta):
        labels = {
            "nombre": "Nombre del servicio",
            "tipo": "Tipo de servicio",
            "descripcion": "Descripción",
            "imagen_principal": "Imagen principal",
            "precio_texto": "Texto de precio",
            "precio_desde": "Precio desde",
            "precio_adulto": "Precio adulto",
            "precio_niño": "Precio niño",
            "precio_tercera_edad": "Precio tercera edad",
            "disponibilidad": "Disponibilidad",
            "capacidad": "Capacidad",
            "requiere_reserva": "¿Requiere reserva?",
            "incluye": "¿Qué incluye?",
            "activo": "¿Mostrar este servicio?",
        }
        help_texts = {
            "precio_texto": "Texto libre para mostrar información especial de precios.",
            "precio_desde": "Precio referencial desde el cual inicia el servicio.",
            "precio_adulto": "Precio correspondiente a visitantes adultos.",
            "precio_niño": "Precio correspondiente a niños.",
            "precio_tercera_edad": "Precio correspondiente a adultos mayores.",
            "disponibilidad": "Indique disponibilidad, fechas o horarios del servicio.",
            "capacidad": "Número máximo de personas permitidas, si aplica.",
            "requiere_reserva": "Marque esta opción si el visitante debe reservar antes de utilizar el servicio.",
            "incluye": "Describa lo que incluye el servicio para el visitante.",
            "activo": "Active este servicio para mostrarlo en la página pública.",
        }


@admin.register(ContenidoInicio)
class ContenidoInicioAdmin(
    RegistroUnicoAdminMixin,
    AdministradorAuditoriaMixin,
    admin.ModelAdmin,
):
    form = ContenidoInicioAdminForm
    save_on_top = True
    readonly_fields = (
        "vista_previa_atractivo_1",
        "vista_previa_atractivo_2",
        "vista_previa_atractivo_3",
        "vista_previa_atractivo_4",
    )
    list_display = ("hero_titulo",)
    list_editable = ()
    fieldsets = (
        ("Portada principal - Carrusel", {
            "fields": (
                "hero_titulo",
                "hero_subtitulo",
                "hero_boton_texto",
                "hero_boton_url",
            ),
            "description": (
                "Estos textos aparecen encima de las fotografías "
                "del carrusel principal."
            ),
        }),
        ("Sección Nuestros atractivos", {
            "fields": (
                "atractivos_titulo",
                "atractivos_descripcion",
            ),
            "description": (
                "Configura el título y texto introductorio que aparecen "
                "antes de los atractivos destacados."
            ),
        }),
        ("Atractivo 1 - Paisajes", {
            "fields": (
                "atractivo_1_activo",
                "atractivo_1_titulo",
                "atractivo_1_desc",
                "atractivo_1_imagen",
                "vista_previa_atractivo_1",
            ),
            "description": (
                "Configure el título, descripción e imagen del primer atractivo."
            ),
        }),
        ("Atractivo 2 - Aventura", {
            "fields": (
                "atractivo_2_activo",
                "atractivo_2_titulo",
                "atractivo_2_desc",
                "atractivo_2_imagen",
                "vista_previa_atractivo_2",
            ),
            "description": (
                "Configure el título, descripción e imagen del segundo atractivo."
            ),
        }),
        ("Atractivo 3 - Cultura local", {
            "fields": (
                "atractivo_3_activo",
                "atractivo_3_titulo",
                "atractivo_3_desc",
                "atractivo_3_imagen",
                "vista_previa_atractivo_3",
            ),
            "description": (
                "Configure el título, descripción e imagen del tercer atractivo."
            ),
        }),
        ("Atractivo 4 - Atención", {
            "fields": (
                "atractivo_4_activo",
                "atractivo_4_titulo",
                "atractivo_4_desc",
                "atractivo_4_imagen",
                "vista_previa_atractivo_4",
            ),
            "description": (
                "Configure el título, descripción e imagen del cuarto atractivo."
            ),
        }),
    )

    class Media:
        js = ("js/admin_image_preview.js",)

    def _vista_previa_atractivo(self, obj, campo):
        if not obj or not obj.pk:
            return "Guarda primero para visualizar la imagen."

        imagen = getattr(obj, campo, None)

        if not imagen:
            return "Todavía no se ha cargado una imagen."

        return format_html(
            '<img src="{}" '
            'style="width:230px; height:150px; object-fit:cover; '
            'border-radius:12px; border:1px solid #ddd;" />',
            imagen.url,
        )

    @admin.display(description="Vista previa de Paisajes")
    def vista_previa_atractivo_1(self, obj):
        return self._vista_previa_atractivo(obj, "atractivo_1_imagen")

    @admin.display(description="Vista previa de Aventura")
    def vista_previa_atractivo_2(self, obj):
        return self._vista_previa_atractivo(obj, "atractivo_2_imagen")

    @admin.display(description="Vista previa de Cultura local")
    def vista_previa_atractivo_3(self, obj):
        return self._vista_previa_atractivo(obj, "atractivo_3_imagen")

    @admin.display(description="Vista previa de Atención")
    def vista_previa_atractivo_4(self, obj):
        return self._vista_previa_atractivo(obj, "atractivo_4_imagen")


class CarruselInicioAdminForm(forms.ModelForm):
    class Meta:
        model = CarruselInicio
        fields = '__all__'
        labels = {
            "imagen": "Fotografía del carrusel",
            "orden": "Orden de aparición",
            "activo": "¿Mostrar esta imagen?",
        }
        help_texts = {
            "imagen": "Seleccione la fotografía que aparecerá en el carrusel de la página de Inicio.",
            "orden": "Use números para definir el orden. Un número menor aparecerá primero.",
            "activo": "Desmarque esta opción para ocultar temporalmente la imagen del carrusel.",
        }

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen:
            from .models import validate_carrusel_image
            validate_carrusel_image(imagen)
        return imagen


@admin.register(CarruselInicio)
class CarruselInicioAdmin(AdministradorAuditoriaMixin, admin.ModelAdmin):
    form = CarruselInicioAdminForm
    list_display = ("orden", "miniatura_carrusel", "activo")
    list_display_links = ("miniatura_carrusel",)
    list_editable = ("orden", "activo")
    ordering = ("orden",)
    readonly_fields = ("imagen_preview",)
    fieldsets = (
        (
            "Imagen del carrusel",
            {
                "fields": ("imagen", "orden", "activo", "imagen_preview"),
                "description": (
                    "Seleccione la fotografía, defina el orden en el que aparecerá y "
                    "controle si debe mostrarse en la portada de Inicio."
                ),
            },
        ),
    )

    class Media:
        js = ("js/admin_image_preview.js",)

    def changelist_view(self, request, extra_context=None):
        messages.info(
            request,
            "Haz clic en una imagen para modificarla. Puedes cambiar el orden y la visibilidad desde esta lista.",
        )
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description="Imagen")
    def miniatura_carrusel(self, obj):
        if not obj or not obj.imagen:
            return "Sin imagen"

        return format_html(
            '<img src="{0}" alt="{1}" style="max-width:100px; max-height:90px; width:auto; height:auto; object-fit:cover; border-radius:8px; display:block;" />',
            obj.imagen.url,
            obj,
        )

    def imagen_preview(self, obj):
        if obj.imagen:
            return format_html(
                '<a href="{0}" class="image-preview-toggle" data-image-url="{0}" title="Ver imagen en modal">'
                '<img src="{0}" style="max-width:200px; height:auto; border-radius: 10px;" />'
                '</a>',
                obj.imagen.url,
            )
        return "-"
    imagen_preview.short_description = "Vista previa de la imagen"
    imagen_preview.help_text = "Aquí se muestra una vista previa de la fotografía guardada."


@admin.register(InformacionInstitucional)
class InformacionInstitucionalAdmin(
    RegistroUnicoAdminMixin,
    AdministradorAuditoriaMixin,
    admin.ModelAdmin,
):
    form = InformacionInstitucionalAdminForm
    save_on_top = True
    list_display = ("titulo", "eslogan", "activo")
    list_editable = ("activo",)
    fieldsets = (
        ("Portada de Nosotros", {
            "fields": ("nosotros_eyebrow", "titulo", "eslogan", "logo"),
            "description": (
                "Configure los textos principales que aparecen en la portada de la "
                "página Nosotros."
            ),
        }),
        ("Historia y presentación", {
            "fields": ("descripcion", "historia"),
            "description": (
                "Información que presenta el Centro Turístico Mirador Illari y su historia."
            ),
        }),
        ("Nuestra esencia", {
            "fields": (
                "proposito_titulo",
                "proposito",
                "mision",
                "vision",
            ),
            "description": (
                "Contenido institucional que explica el propósito, misión y visión del centro turístico."
            ),
        }),
        ("Valores institucionales", {
            "fields": ("valores_titulo",),
            "description": (
                "Configure el título que aparece antes de los valores institucionales. "
                "Los valores individuales se gestionan desde su propio módulo."
            ),
        }),
        ("Chatbot Illari", {
            "fields": (
                "chatbot_titulo",
                "chatbot_intro",
                "chatbot_placeholder",
                "chatbot_enviar_texto",
                "chatbot_opciones_etiqueta",
                "chatbot_respuesta_predeterminada",
            ),
            "description": (
                "Textos básicos que se muestran en el asistente virtual Illari."
            ),
        }),
        ("Textos adicionales del sitio", {
            "fields": (
                "servicios_titulo",
                "eventos_titulo",
                "galeria_titulo",
                "contacto_titulo",
            ),
            "description": (
                "Textos utilizados como títulos o encabezados en otras secciones públicas."
            ),
        }),
        ("Estado", {
            "fields": ("activo",),
            "description": (
                "Active esta información para utilizarla en las páginas públicas del sitio."
            ),
        }),
    )


@admin.register(Contacto)
class ContactoAdmin(
    RegistroUnicoAdminMixin,
    AdministradorAuditoriaMixin,
    admin.ModelAdmin,
):
    form = ContactoAdminFormLocal
    list_display = ("direccion", "whatsapp", "correo", "activo")
    list_editable = ("activo",)
    fieldsets = (
        ("Datos de contacto", {
            "fields": ("direccion", "telefono", "whatsapp", "correo"),
            "description": (
                "Información principal que verá el visitante para comunicarse con el "
                "Centro Turístico Mirador Illari."
            ),
        }),
        ("Horarios de atención", {
            "fields": ("horarios_atencion",),
            "description": (
                "Configure los horarios que se mostrarán públicamente a los visitantes."
            ),
        }),
        ("Ubicación y mapa", {
            "fields": ("mapa_embed_url",),
            "description": (
                "Configure la información utilizada para mostrar la ubicación del centro turístico."
            ),
        }),
        ("Redes sociales", {
            "fields": ("facebook_url", "instagram_url", "tiktok_url", "youtube_url"),
            "description": (
                "Enlaces oficiales que se mostrarán en la página de Contacto."
            ),
        }),
        ("Estado", {
            "fields": ("activo",),
            "description": "Active esta información para utilizarla en la página pública de Contacto."
        }),
    )


@admin.register(ServicioTuristico)
class ServicioTuristicoAdmin(
    VistaPreviaImagenAdminMixin,
    AdministradorAuditoriaMixin,
    admin.ModelAdmin,
):
    campo_imagen = "imagen_principal"

    class Media:
        js = ("js/admin_image_preview.js",)

    form = ServicioTuristicoAdminForm
    list_display = (
        "nombre",
        "tipo",
        "disponibilidad",
        "requiere_reserva",
        "activo",
    )
    list_filter = ("tipo", "activo", "requiere_reserva")
    search_fields = ("nombre", "tipo", "descripcion")
    list_editable = ("activo",)
    fieldsets = (
        ("Información general", {
            "fields": (
                "nombre",
                "tipo",
                "descripcion",
                "imagen_principal",
                "vista_previa_imagen",
                "activo",
            ),
            "description": (
                "Datos principales que identifican este servicio en la página pública."
            ),
        }),
        ("Precios", {
            "fields": (
                "precio_texto",
                "precio_desde",
                "precio_adulto",
                "precio_niño",
                "precio_tercera_edad",
            ),
            "description": (
                "Configure únicamente los precios que correspondan a este servicio."
            ),
        }),
        ("Disponibilidad y reserva", {
            "fields": ("disponibilidad", "capacidad", "requiere_reserva"),
            "description": (
                "Indique cuándo está disponible el servicio, su capacidad y si requiere reserva."
            ),
        }),
        ("Información adicional", {
            "fields": ("incluye",),
            "description": (
                "Detalle lo que incluye el servicio y cualquier información complementaria."
            ),
        }),
    )


class EventoNovedadTipoFilter(SimpleListFilter):
    title = 'Tipo'
    parameter_name = 'tipo'

    def lookups(self, request, model_admin):
        return [(tipo, tipo) for tipo, _ in TIPO_AVISO_CHOICES]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(tipo__iexact=self.value())
        return queryset


class EventoNovedadAdminForm(forms.ModelForm):
    class Meta:
        model = EventoNovedad
        fields = "__all__"
        labels = {
            "titulo": "Título",
            "contenido": "Descripción",
            "tipo": "Tipo de publicación",
            "fecha_evento": "Fecha del evento",
            "fecha_publicacion": "Fecha de publicación",
            "imagen": "Imagen principal",
            "precio_texto": "Información de precio",
            "activo": "¿Mostrar esta publicación?",
        }
        help_texts = {
            "titulo": "Nombre que verá el visitante en la tarjeta.",
            "contenido": "Escriba la información que verá el visitante.",
            "tipo": "Seleccione si corresponde a un evento o a una novedad.",
            "fecha_evento": "Fecha en la que se realizará el evento.",
            "fecha_publicacion": "Fecha en la que se publicó este contenido.",
            "imagen": "Fotografía principal que aparecerá en la página.",
            "precio_texto": "Deje vacío si no corresponde informar un precio o acceso.",
            "activo": "Desmarque esta opción para ocultar temporalmente la publicación.",
        }


@admin.register(EventoNovedad)
class EventoNovedadAdmin(
    VistaPreviaImagenAdminMixin,
    AdministradorAuditoriaMixin,
    admin.ModelAdmin,
):
    campo_imagen = "imagen"
    readonly_fields = (
        "vista_previa_imagen",
        "fecha_publicacion",
    )

    class Media:
        js = ("js/admin_image_preview.js",)

    form = EventoNovedadAdminForm
    save_on_top = True
    list_display = ("titulo", "tipo", "fecha_evento", "activo")
    list_editable = ("activo",)
    list_filter = (EventoNovedadTipoFilter,)
    search_fields = ("titulo", "contenido", "tipo")
    fieldsets = (
        ("Información principal", {
            "fields": ("titulo", "tipo", "contenido", "imagen", "vista_previa_imagen"),
            "description": (
                "Configure el título, tipo, contenido e imagen que verá el visitante."
            ),
        }),
        ("Publicación", {
            "fields": ("fecha_evento", "fecha_publicacion"),
            "description": (
                "La fecha del evento puede modificarse. La fecha de publicación se registra automáticamente cuando se crea el contenido."
            ),
        }),
        ("Precio o acceso", {
            "fields": ("precio_texto",),
            "description": (
                "Configure el precio únicamente si este evento o actividad lo requiere."
            ),
        }),
        ("Visibilidad", {
            "fields": ("activo",),
            "description": "Active este contenido para mostrarlo en la página pública.",
        }),
    )


class GaleriaMultimediaAdminForm(forms.ModelForm):
    class Meta:
        model = GaleriaMultimedia
        fields = "__all__"
        labels = {
            "titulo": "Título de la imagen",
            "descripcion": "Descripción corta",
            "imagen": "Fotografía",
            "fecha_subida": "Fecha de carga",
            "activo": "¿Mostrar esta imagen en la galería?",
        }
        help_texts = {
            "titulo": "Nombre o descripción corta que identificará la fotografía.",
            "descripcion": "Texto breve opcional para contextualizar la imagen.",
            "imagen": "Seleccione la fotografía que desea mostrar en la galería.",
            "fecha_subida": "Fecha en la que la imagen fue agregada al sistema.",
            "activo": "Desmarque esta opción para ocultar temporalmente la imagen de la galería.",
        }


@admin.register(GaleriaMultimedia)
class GaleriaMultimediaAdmin(
    VistaPreviaImagenAdminMixin,
    AdministradorAuditoriaMixin,
    admin.ModelAdmin,
):
    campo_imagen = "imagen"

    class Media:
        js = ("js/admin_image_preview.js",)

    form = GaleriaMultimediaAdminForm
    list_display = (
        "titulo",
        "fecha_subida",
        "activo",
    )

    list_display_links = (
        "titulo",
    )

    list_editable = (
        "activo",
    )

    readonly_fields = ("fecha_subida", "vista_previa_imagen")

    search_fields = (
        "titulo",
    )

    fieldsets = (
        (
            "Imagen de galería",
            {
                "fields": (
                    "titulo",
                    "descripcion",
                    "imagen",
                    "vista_previa_imagen",
                ),
                "description": (
                    "Agregue la fotografía y la información que se mostrará en la galería pública del sitio."
                ),
            },
        ),
        (
            "Información de publicación",
            {
                "fields": (
                    "fecha_subida",
                    "activo",
                ),
                "description": (
                    "Revise la fecha de carga y controle si esta imagen debe mostrarse públicamente."
                ),
            },
        ),
    )


class PreguntaFrecuenteAdminForm(forms.ModelForm):
    class Meta:
        model = PreguntaFrecuente
        fields = "__all__"
        labels = {
            "pregunta": "Pregunta del visitante",
            "respuesta": "Respuesta del chatbot",
            "activo": "¿Usar esta pregunta en el chatbot?",
        }
        help_texts = {
            "pregunta": (
                "Escriba la pregunta tal como podría formularla un visitante."
            ),
            "respuesta": (
                "Esta es la respuesta que mostrará el chatbot cuando identifique esta pregunta."
            ),
            "activo": (
                "Desmarque esta opción para dejar de utilizar temporalmente esta pregunta."
            ),
        }


@admin.register(PreguntaFrecuente)
class PreguntaFrecuenteAdmin(
    AdministradorAuditoriaMixin,
    admin.ModelAdmin
):
    form = PreguntaFrecuenteAdminForm
    list_display = (
        "pregunta_limpia",
        "activo",
    )

    list_display_links = (
        "pregunta_limpia",
    )

    list_editable = (
        "activo",
    )

    list_filter = ("activo",)

    search_fields = (
        "pregunta",
        "respuesta",
    )

    fieldsets = (
        (
            "Pregunta y respuesta",
            {
                "fields": ("pregunta", "respuesta"),
                "description": (
                    "Escriba la pregunta que puede realizar el visitante y la respuesta exacta "
                    "que deberá mostrar el chatbot."
                ),
            },
        ),
        (
            "Estado",
            {
                "fields": ("activo",),
                "description": (
                    "Active esta pregunta para que pueda utilizarse en el chatbot."
                ),
            },
        ),
    )

    @admin.display(
        description="Pregunta del Usuario",
        ordering="pregunta"
    )
    def pregunta_limpia(self, obj):
        return unescape(
            strip_tags(str(obj.pregunta or ""))
        )


class ValorAdminForm(forms.ModelForm):
    class Meta:
        model = Valor
        fields = "__all__"
        labels = {
            "titulo": "Nombre del valor",
            "descripcion": "Descripción",
            "icono_emoji": "Icono",
            "orden": "Orden de aparición",
            "activo": "¿Mostrar este valor?",
        }
        help_texts = {
            "titulo": "Nombre del valor institucional que verá el visitante.",
            "descripcion": "Explique brevemente qué representa este valor.",
            "icono_emoji": "Icono que acompañará al valor en la página pública.",
            "orden": "Use números para definir el orden. Un número menor aparecerá primero.",
            "activo": "Desmarque esta opción para ocultar temporalmente este valor.",
        }


@admin.register(Valor)
class ValorAdmin(AdministradorAuditoriaMixin, admin.ModelAdmin):
    form = ValorAdminForm
    list_display = ("titulo", "orden", "icono_emoji", "activo")
    list_editable = ("orden", "activo")
    list_display_links = ("titulo",)
    ordering = ("orden",)
    fieldsets = (
        (
            "Valor institucional",
            {
                "fields": ("titulo", "descripcion", "icono_emoji", "orden", "activo"),
                "description": (
                    "Configure la información que se mostrará en la sección de valores institucionales."
                ),
            },
        ),
    )
