from django.conf import settings
from .models import InformacionInstitucional, Contacto


def sitio_context(request):
    info_site = InformacionInstitucional.objects.filter(
        activo=True
    ).order_by("-id").first()

    contact_site = Contacto.objects.filter(
        activo=True
    ).order_by("-id").first()

    # Construir una URL segura para el logo si el archivo existe en el storage
    info_site_logo_url = None
    if info_site and getattr(info_site, 'logo', None):
        try:
            logo_field = info_site.logo
            # Algunos storages lanzan si el archivo no existe; comprobamos existencia cuando es posible
            if getattr(logo_field, 'name', None):
                storage = getattr(logo_field, 'storage', None)
                exists = True
                try:
                    if storage and hasattr(storage, 'exists'):
                        exists = storage.exists(logo_field.name)
                except Exception:
                    exists = False

                if exists:
                    # Acceder a .url en un try/except para evitar errores si falta el fichero
                    try:
                        info_site_logo_url = logo_field.url
                    except Exception:
                        info_site_logo_url = None
        except Exception:
            info_site_logo_url = None

    return {
        'info_site': info_site,
        'contact_site': contact_site,
        'info_site_logo_url': info_site_logo_url,
    }