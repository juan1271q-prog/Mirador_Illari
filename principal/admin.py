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


@admin.register(ContenidoInicio)
class ContenidoInicioAdmin(
    RegistroUnicoAdminMixin,
    AdministradorAuditoriaMixin,
    admin.ModelAdmin,
):
    list_display = ("hero_titulo", "hero_subtitulo", "activo_informacion")
    list_editable = ("activo_informacion",)
    fieldsets = (
        ("Sección de inicio", {
            'fields': (
                'activo_informacion', 'hero_titulo', 'hero_subtitulo',
                'hero_boton_texto', 'hero_boton_url',
                'atractivos_titulo', 'atractivos_descripcion',
            )
        }),
        ("Tarjetas de atractivos", {
            'fields': (
                'atractivo_1_activo', 'atractivo_1_titulo', 'atractivo_1_desc',
                'atractivo_2_activo', 'atractivo_2_titulo', 'atractivo_2_desc',
                'atractivo_3_activo', 'atractivo_3_titulo', 'atractivo_3_desc',
                'atractivo_4_activo', 'atractivo_4_titulo', 'atractivo_4_desc',
            )
        }),
    )


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
    list_display = ("titulo", "eslogan", "activo")
    list_editable = ("activo",)
    fieldsets = (
        ("Información general", {
            'fields': (
                'titulo', 'eslogan', 'descripcion', 'logo', 'activo'
            )
        }),
        ("Títulos de páginas", {
            'fields': (
                'nosotros_eyebrow', 'proposito_titulo', 'valores_titulo',
                'servicios_titulo', 'eventos_titulo', 'galeria_titulo', 'contacto_titulo',
            )
        }),
        ("Chatbot", {
            'fields': (
                'chatbot_titulo', 'chatbot_intro', 'chatbot_placeholder',
                'chatbot_enviar_texto', 'chatbot_opciones_etiqueta', 'chatbot_respuesta_predeterminada',
            )
        }),
        ("Contenido adicional", {
            'fields': ('proposito', 'historia', 'mision', 'vision')
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


@admin.register(EventoNovedad)
class EventoNovedadAdmin(
    VistaPreviaImagenAdminMixin,
    AdministradorAuditoriaMixin,
    admin.ModelAdmin,
):
    campo_imagen = "imagen"

    class Media:
        js = ("js/admin_image_preview.js",)

    form = EventoNovedadForm
    list_display = ("titulo", "tipo", "fecha_evento", "activo")
    list_editable = ("activo",)
    list_filter = (EventoNovedadTipoFilter,)
    search_fields = ("titulo", "contenido", "tipo")
    fieldsets = (
        ("Información General", {
            'fields': ('titulo', 'tipo', 'contenido', 'imagen', 'vista_previa_imagen')
        }),
        ("Información adicional", {
            'fields': ('precio_texto', 'fecha_evento', 'activo')
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