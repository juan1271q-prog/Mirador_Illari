from urllib.parse import urlparse

from django import forms

from .models import (
    Contacto,
    ServicioTuristico,
    EventoNovedad,
    validate_phone_number,
)


class ContactoAdminForm(forms.ModelForm):
    mapa_embed_url = forms.URLField(
        required=False,
        label="Enlace de ubicación de Google Maps",
        help_text=(
            "Abre Google Maps, busca el establecimiento, pulsa "
            "'Compartir', selecciona 'Copiar enlace' y pégalo aquí. "
            "No copies código HTML ni iframe."
        ),
        widget=forms.URLInput(
            attrs={
                "placeholder": "Ejemplo: https://maps.app.goo.gl/...",
                "style": "width: 100%;",
            }
        ),
    )

    class Meta:
        model = Contacto
        fields = "__all__"

    def clean_mapa_embed_url(self):
        url = (self.cleaned_data.get("mapa_embed_url") or "").strip()

        if not url:
            return url

        dominio = urlparse(url).netloc.lower().split(":")[0]

        dominios_permitidos = {
            "google.com",
            "www.google.com",
            "maps.google.com",
            "maps.app.goo.gl",
            "goo.gl",
        }

        es_subdominio_google = dominio.endswith(".google.com")

        if dominio not in dominios_permitidos and not es_subdominio_google:
            raise forms.ValidationError(
                "Pega únicamente un enlace copiado desde Google Maps."
            )

        return url

    def clean_whatsapp(self):
        whatsapp = self.cleaned_data.get("whatsapp")

        if not whatsapp:
            return whatsapp

        try:
            validate_phone_number(whatsapp)
        except forms.ValidationError as e:
            raise forms.ValidationError(e.message)

        return whatsapp

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono")

        if not telefono:
            return telefono

        try:
            validate_phone_number(telefono)
        except forms.ValidationError as e:
            raise forms.ValidationError(e.message)

        return telefono

class ServicioTuristicoForm(forms.ModelForm):

    class Meta:
        model = ServicioTuristico
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        campos_precio = (
            "precio_desde",
            "precio_adulto",
            "precio_niño",
            "precio_tercera_edad",
        )

        for campo in campos_precio:
            valor = cleaned_data.get(campo)

            if valor is not None and valor < 0:
                self.add_error(
                    campo,
                    "El precio no puede ser negativo.",
                )

        capacidad = cleaned_data.get("capacidad")
        if capacidad is not None and capacidad <= 0:
            self.add_error(
                "capacidad",
                "La capacidad debe ser mayor a 0.",
            )

        return cleaned_data


class EventoNovedadForm(forms.ModelForm):

    class Meta:
        model = EventoNovedad
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        tipo = cleaned_data.get("tipo")
        fecha_evento = cleaned_data.get("fecha_evento")

        if tipo == "Evento" and not fecha_evento:
            self.add_error(
                "fecha_evento",
                "Debes ingresar la fecha del evento.",
            )

        return cleaned_data
