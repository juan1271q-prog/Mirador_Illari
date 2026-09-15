from django import forms
from django.contrib import admin
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
            '<span>Ver imagen completa</span>'
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
            "activo_informacion": "¿Mostrar el contenido de Inicio?",
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
            "activo_informacion": (
                "Activa o desactiva los textos administrables de la "
                "página Inicio."
            ),
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
                "Desmarca esta opción si no quieres mostrar Paisajes."
            ),
            "atractivo_1_titulo": "Nombre visible de la tarjeta Paisajes.",
            "atractivo_1_desc": (
                "Texto corto que explica qué encontrará el visitante."
            ),
            "atractivo_2_activo": (
                "Desmarca esta opción si no quieres mostrar Aventura."
            ),
            "atractivo_2_titulo": "Nombre visible de la tarjeta Aventura.",
            "atractivo_2_desc": (
                "Descripción corta de las actividades de aventura."
            ),
            "atractivo_3_activo": (
                "Desmarca esta opción si no quieres mostrar Cultura local."
            ),
            "atractivo_3_titulo": (
                "Nombre visible de la tarjeta Cultura local."
            ),
            "atractivo_3_desc": (
                "Descripción corta relacionada con cultura y comunidad."
            ),
            "atractivo_4_activo": (
                "Desmarca esta opción si no quieres mostrar Atención."
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
            "proposito_titulo": "Título de la sección Propósito",
            "proposito": "Propósito",
            "mision": "Misión",
            "vision": "Visión",
            "valores_titulo": "Título de la sección Valores",
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
    list_display = ("hero_titulo", "activo_informacion")
    list_editable = ("activo_informacion",)
    fieldsets = (
        ("1. Estado de la página Inicio", {
            "fields": ("activo_informacion",),
            "description": (
                "Desde aquí puedes activar o desactivar el contenido "
                "administrable de la página principal."
            ),
        }),
        ("2. Portada principal - Carrusel", {
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
        ("3. Sección Nuestros atractivos", {
            "fields": (
                "atractivos_titulo",
                "atractivos_descripcion",
            ),
            "description": (
                "Configura el título y texto introductorio que aparecen "
                "antes de las cuatro tarjetas."
            ),
        }),
        ("4. Atractivo 1 - Paisajes", {
            "fields": (
                "atractivo_1_activo",
                "atractivo_1_titulo",
                "atractivo_1_desc",
                "atractivo_1_imagen",
                "vista_previa_atractivo_1",
            ),
            "description": (
                "Configura el texto y la fotografía "
                "de la tarjeta Paisajes que aparece en Inicio."
            ),
        }),
        ("5. Atractivo 2 - Aventura", {
            "fields": (
                "atractivo_2_activo",
                "atractivo_2_titulo",
                "atractivo_2_desc",
                "atractivo_2_imagen",
                "vista_previa_atractivo_2",
            ),
            "description": (
                "Configura el texto y la fotografía "
                "de la tarjeta Aventura."
            ),
        }),
        ("6. Atractivo 3 - Cultura local", {
            "fields": (
                "atractivo_3_activo",
                "atractivo_3_titulo",
                "atractivo_3_desc",
                "atractivo_3_imagen",
                "vista_previa_atractivo_3",
            ),
        }),
        ("7. Atractivo 4 - Atención", {
            "fields": (
                "atractivo_4_activo",
                "atractivo_4_titulo",
                "atractivo_4_desc",
                "atractivo_4_imagen",
                "vista_previa_atractivo_4",
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

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen:
            from .models import validate_carrusel_image
            validate_carrusel_image(imagen)
        return imagen


@admin.register(CarruselInicio)
class CarruselInicioAdmin(AdministradorAuditoriaMixin, admin.ModelAdmin):
    form = CarruselInicioAdminForm
    list_display = ("orden", "imagen_preview", "activo")
    list_display_links = ("imagen_preview",)
    list_editable = ("orden", "activo")
    ordering = ("orden",)
    readonly_fields = ("imagen_preview",)

    class Media:
        js = ("js/admin_image_preview.js",)

    def imagen_preview(self, obj):
        if obj.imagen:
            return format_html(
                '<a href="{0}" class="image-preview-toggle" data-image-url="{0}" title="Ver imagen en modal">'
                '<img src="{0}" style="max-width:200px; height:auto; border-radius: 10px;" />'
                '</a>',
                obj.imagen.url,
            )
        return "-"
    imagen_preview.short_description = "Imagen"


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
        ("1. Portada de Nosotros", {
            "fields": ("nosotros_eyebrow", "titulo", "eslogan", "logo"),
            "description": (
                "Estos textos y el logo aparecen en la parte superior "
                "de la página Nosotros."
            ),
        }),
        ("2. Historia y presentación", {
            "fields": ("descripcion", "historia"),
            "description": (
                "Información que explica quiénes somos y la historia del lugar."
            ),
        }),
        ("3. Nuestra esencia", {
            "fields": (
                "proposito_titulo",
                "proposito",
                "mision",
                "vision",
            ),
            "description": "Configura Propósito, Misión y Visión.",
        }),
        ("4. Valores", {
            "fields": ("valores_titulo",),
            "description": (
                "Los valores individuales se administran desde "
                "4. Valores Institucionales."
            ),
        }),
        ("5. Configuración y otros textos", {
            "fields": (
                "activo",
                "servicios_titulo",
                "eventos_titulo",
                "galeria_titulo",
                "contacto_titulo",
                "chatbot_titulo",
                "chatbot_intro",
                "chatbot_placeholder",
                "chatbot_enviar_texto",
                "chatbot_opciones_etiqueta",
                "chatbot_respuesta_predeterminada",
            ),
        }),
    )


@admin.register(Contacto)
class ContactoAdmin(
    RegistroUnicoAdminMixin,
    AdministradorAuditoriaMixin,
    admin.ModelAdmin,
):
    form = ContactoAdminForm
    list_display = ("direccion", "whatsapp", "correo", "activo")
    list_editable = ("activo",)
    fieldsets = (
        ("Datos de contacto", {
            'fields': ('direccion', 'horarios_atencion', 'whatsapp', 'telefono', 'correo', 'mapa_embed_url')
        }),
        ("Redes sociales", {
            'fields': ('facebook_url', 'instagram_url', 'tiktok_url', 'youtube_url')
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

    form = ServicioTuristicoForm
    list_display = (
        "nombre",
        "tipo",
        "precio_adulto",
        "precio_niño",
        "precio_tercera_edad",
        "activo",
    )
    list_filter = ("tipo", "activo", "requiere_reserva")
    search_fields = ("nombre", "tipo", "descripcion")
    list_editable = ("activo",)
    fieldsets = (
        ("Información General", {
            'fields': (
                'nombre', 'tipo', 'descripcion', 'imagen_principal', 'vista_previa_imagen', 'activo'
            )
        }),
        ("Precios y disponibilidad", {
            'fields': (
                'precio_texto', 'precio_desde', 'precio_adulto',
                'precio_niño', 'precio_tercera_edad', 'disponibilidad',
                'requiere_reserva',
            )
        }),
        ("Detalles opcionales", {
            'fields': ('capacidad', 'incluye'),
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
            "imagen": "Imagen principal",
            "precio_texto": "Información de precio",
            "activo": "¿Mostrar esta publicación?",
        }
        help_texts = {
            "titulo": "Nombre que verá el visitante en la tarjeta.",
            "contenido": "Resumen de la actividad o novedad.",
            "tipo": "Indica si el contenido se mostrará como Evento o Novedad.",
            "fecha_evento": "Fecha asociada al evento. Es obligatoria para los eventos.",
            "imagen": "Fotografía principal que aparecerá en la página.",
            "precio_texto": "Información visible sobre el precio o acceso.",
            "activo": "Desmarca esta opción si no deseas mostrar la publicación.",
        }


@admin.register(EventoNovedad)
class EventoNovedadAdmin(
    VistaPreviaImagenAdminMixin,
    AdministradorAuditoriaMixin,
    admin.ModelAdmin,
):
    campo_imagen = "imagen"

    class Media:
        js = ("js/admin_image_preview.js",)

    form = EventoNovedadAdminForm
    save_on_top = True
    list_display = ("titulo", "tipo", "fecha_evento", "activo")
    list_editable = ("activo",)
    list_filter = (EventoNovedadTipoFilter,)
    search_fields = ("titulo", "contenido", "tipo")
    fieldsets = (
        ("1. Información principal", {
            "fields": ("titulo", "contenido"),
            "description": "Texto que verá el visitante en la publicación.",
        }),
        ("2. Publicación", {
            "fields": (
                "tipo",
                "fecha_evento",
                "imagen",
                "vista_previa_imagen",
            ),
            "description": "Define si es evento o novedad y su contenido visual.",
        }),
        ("3. Visibilidad y precio", {
            "fields": ("precio_texto", "activo"),
        }),
    )


@admin.register(GaleriaMultimedia)
class GaleriaMultimediaAdmin(
    VistaPreviaImagenAdminMixin,
    AdministradorAuditoriaMixin,
    admin.ModelAdmin,
):
    campo_imagen = "imagen"

    class Media:
        js = ("js/admin_image_preview.js",)

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

    fieldsets = (
        (
            "Información de la imagen",
            {
                "fields": (
                    "titulo",
                    "descripcion",
                    "imagen",
                    "vista_previa_imagen",
                    "activo",
                ),
            },
        ),
    )


@admin.register(PreguntaFrecuente)
class PreguntaFrecuenteAdmin(
    AdministradorAuditoriaMixin,
    admin.ModelAdmin
):
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

    search_fields = (
        "pregunta",
        "respuesta",
    )

    @admin.display(
        description="Pregunta del Usuario",
        ordering="pregunta"
    )
    def pregunta_limpia(self, obj):
        return unescape(
            strip_tags(str(obj.pregunta or ""))
        )


@admin.register(Valor)
class ValorAdmin(AdministradorAuditoriaMixin, admin.ModelAdmin):
    list_display = ("titulo", "orden", "icono_emoji", "activo")
    list_editable = ("orden", "activo")
    list_display_links = ("titulo",)
    ordering = ("orden",)
