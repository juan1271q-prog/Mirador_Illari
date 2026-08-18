from django.db import migrations


def create_default_valores(apps, schema_editor):
    Valor = apps.get_model('principal', 'Valor')
    default_valores = [
        {
            'titulo': 'Compromiso con la comunidad',
            'descripcion': 'Fomentamos el desarrollo local y la cultura comunitaria en cada experiencia.',
            'icono_emoji': '🤝',
            'orden': 1,
            'activo': True,
        },
        {
            'titulo': 'Sostenibilidad',
            'descripcion': 'Cuidamos el entorno natural con prácticas turísticas responsables.',
            'icono_emoji': '🌿',
            'orden': 2,
            'activo': True,
        },
        {
            'titulo': 'Hospitalidad',
            'descripcion': 'Atendemos a nuestros visitantes con calidez, respeto y profesionalismo.',
            'icono_emoji': '🏡',
            'orden': 3,
            'activo': True,
        },
        {
            'titulo': 'Autenticidad',
            'descripcion': 'Ofrecemos una experiencia verdadera de la Amazonía ecuatoriana.',
            'icono_emoji': '🌎',
            'orden': 4,
            'activo': True,
        },
    ]
    for valor_data in default_valores:
        Valor.objects.update_or_create(
            titulo=valor_data['titulo'],
            defaults=valor_data,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('principal', '0017_atractivoinicio'),
    ]

    operations = [
        migrations.RunPython(create_default_valores, migrations.RunPython.noop),
    ]
