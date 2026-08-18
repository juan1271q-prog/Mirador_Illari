import json
from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse
from PIL import Image

from .models import (
    CarruselInicio,
    Contacto,
    EventoNovedad,
    InformacionInstitucional,
    PreguntaFrecuente,
    ServicioTuristico,
    validate_logo_image,
    validate_public_image,
)
from .views import build_map_embed


class ChatbotSeguridadTests(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client(
            enforce_csrf_checks=True
        )

        self.url = reverse('api_chatbot')

    def obtener_token_csrf(self):
        self.client.get(reverse('inicio'))

        return self.client.cookies[
            'csrftoken'
        ].value

    def test_api_rechaza_get(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(
            respuesta.status_code,
            405,
        )

    def test_api_acepta_post_con_csrf(self):
        token = self.obtener_token_csrf()

        respuesta = self.client.post(
            self.url,
            data=json.dumps({
                'mensaje': 'Hola',
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

    def test_mensaje_demasiado_largo(self):
        token = self.obtener_token_csrf()

        respuesta = self.client.post(
            self.url,
            data=json.dumps({
                'mensaje': 'a' * 181,
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

    def test_api_aplica_limite_de_consultas(self):
        token = self.obtener_token_csrf()

        for _ in range(15):
            respuesta = self.client.post(
                self.url,
                data=json.dumps({
                    'mensaje': 'Hola',
                }),
                content_type='application/json',
                HTTP_X_CSRFTOKEN=token,
            )

            self.assertEqual(
                respuesta.status_code,
                200,
            )

        respuesta = self.client.post(
            self.url,
            data=json.dumps({
                'mensaje': 'Hola',
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(
            respuesta.status_code,
            429,
        )

        self.assertEqual(
            respuesta.json()['reconocido'],
            False,
        )

    def test_api_preguntas_no_expone_respuestas(self):
        PreguntaFrecuente.objects.create(
            pregunta='¿Aceptan mascotas?',
            respuesta='Sí, bajo responsabilidad del propietario.',
            activo=True,
        )

        respuesta = self.client.get(
            reverse('api_preguntas')
        )

        registro = respuesta.json()[
            'preguntas'
        ][0]

        self.assertIn(
            'pregunta',
            registro,
        )

        self.assertNotIn(
            'respuesta',
            registro,
        )

    def test_mensaje_vacio_rechaza(self):
        token = self.obtener_token_csrf()

        respuesta = self.client.post(
            self.url,
            data=json.dumps({
                'mensaje': '',
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


class ServicioTuristicoValidationTests(SimpleTestCase):

    def _create_valid_image(self, fmt='PNG'):
        image = Image.new('RGB', (1200, 900), color='blue')
        buffer = BytesIO()
        image.save(buffer, format=fmt)
        buffer.seek(0)
        return SimpleUploadedFile(
            f'servicio.{fmt.lower()}',
            buffer.getvalue(),
            content_type='image/png' if fmt == 'PNG' else 'image/jpeg',
        )

    def _build_servicio(self, **kwargs):
        data = {
            'nombre': 'Servicio de prueba',
            'tipo': 'Hospedaje',
            'descripcion': 'Descripción de prueba',
            'imagen_principal': self._create_valid_image(),
            'capacidad': 10,
        }
        data.update(kwargs)
        return ServicioTuristico(**data)

    def test_precio_desde_negativo_falla(self):
        servicio = self._build_servicio(precio_desde=-1)

        with self.assertRaises(ValidationError):
            servicio.full_clean()

    def test_precio_adulto_negativo_falla(self):
        servicio = self._build_servicio(precio_adulto=-5)

        with self.assertRaises(ValidationError):
            servicio.full_clean()

    def test_precio_nino_negativo_falla(self):
        servicio = self._build_servicio(precio_niño=-3)

        with self.assertRaises(ValidationError):
            servicio.full_clean()

    def test_precio_tercera_edad_negativo_falla(self):
        servicio = self._build_servicio(precio_tercera_edad=-2)

        with self.assertRaises(ValidationError):
            servicio.full_clean()

    def test_capacidad_cero_falla(self):
        servicio = self._build_servicio(capacidad=0)

        with self.assertRaises(ValidationError):
            servicio.full_clean()

    def test_capacidad_negativa_falla(self):
        servicio = self._build_servicio(capacidad=-1)

        with self.assertRaises(ValidationError):
            servicio.full_clean()

    def test_capacidad_positiva_valida(self):
        servicio = self._build_servicio(capacidad=15)

        servicio.full_clean()


class EventoNovedadValidationTests(SimpleTestCase):

    def _create_valid_image(self, fmt='PNG'):
        image = Image.new('RGB', (1200, 900), color='green')
        buffer = BytesIO()
        image.save(buffer, format=fmt)
        buffer.seek(0)
        return SimpleUploadedFile(
            f'evento.{fmt.lower()}',
            buffer.getvalue(),
            content_type='image/png' if fmt == 'PNG' else 'image/jpeg',
        )

    def _build_evento(self, **kwargs):
        data = {
            'titulo': 'Evento de prueba',
            'contenido': 'Contenido de prueba',
            'tipo': 'Evento',
            'imagen': self._create_valid_image(),
            'fecha_evento': date(2026, 8, 15),
        }
        data.update(kwargs)
        return EventoNovedad(**data)

    def test_evento_sin_fecha_falla(self):
        evento = self._build_evento(fecha_evento=None)

        with self.assertRaises(ValidationError):
            evento.full_clean()

    def test_evento_con_fecha_valida(self):
        evento = self._build_evento()

        evento.full_clean()

    def test_novedad_sin_fecha_valida(self):
        novedad = self._build_evento(tipo='Novedad', fecha_evento=None)

        novedad.full_clean()


class ContactoValidationTests(SimpleTestCase):

    def _build_contacto(self, **kwargs):
        data = {
            'direccion': 'Av. Principal 123',
            'whatsapp': '0991234567',
            'telefono': '022345678',
            'correo': 'info@ejemplo.com',
            'horarios_atencion': 'Lun - Dom 08:00 - 18:00',
        }
        data.update(kwargs)
        return Contacto(**data)

    def test_whatsapp_valido(self):
        contacto = self._build_contacto()

        contacto.full_clean()

    def test_whatsapp_con_letras_falla(self):
        contacto = self._build_contacto(whatsapp='099abc123')

        with self.assertRaises(ValidationError):
            contacto.full_clean()

    def test_whatsapp_demasiado_corto_falla(self):
        contacto = self._build_contacto(whatsapp='12345')

        with self.assertRaises(ValidationError):
            contacto.full_clean()

    def test_whatsapp_internacional_con_mas_valido(self):
        contacto = self._build_contacto(whatsapp='+593987654321')

        contacto.full_clean()

    def test_telefono_vacio_permitido(self):
        contacto = self._build_contacto(telefono='')

        contacto.full_clean()

    def test_telefono_con_letras_falla(self):
        contacto = self._build_contacto(telefono='abc123')

        with self.assertRaises(ValidationError):
            contacto.full_clean()


class InformacionInstitucionalLogoValidationTests(SimpleTestCase):

    def _create_logo(self, *, filename='logo.png', content=b'valid', content_type='image/png'):
        return SimpleUploadedFile(filename, content, content_type=content_type)

    def _create_valid_logo(self, fmt='PNG'):
        image = Image.new('RGB', (800, 600), color='red')
        buffer = BytesIO()
        image.save(buffer, format=fmt)
        buffer.seek(0)
        return SimpleUploadedFile(
            f'logo.{fmt.lower()}',
            buffer.getvalue(),
            content_type='image/png' if fmt == 'PNG' else 'image/jpeg',
        )

    def _build_informacion(self, **kwargs):
        data = {
            'titulo': 'Mirador Illari',
            'descripcion': 'Descripción institucional',
            'mision': 'Misión institucional',
            'vision': 'Visión institucional',
        }
        data.update(kwargs)
        return InformacionInstitucional(**data)

    def test_logo_formato_permitido_valida(self):
        logo = self._create_valid_logo(fmt='PNG')
        info = self._build_informacion(logo=logo)

        info.full_clean()

    def test_logo_formato_no_permitido_falla(self):
        info = self._build_informacion(logo=self._create_logo(filename='logo.gif', content=b'not-image', content_type='image/gif'))

        with self.assertRaises(ValidationError):
            info.full_clean()

    def test_logo_supera_2mb_falla(self):
        logo = self._create_logo(filename='logo.png', content=b'x' * (2 * 1024 * 1024 + 1), content_type='image/png')
        info = self._build_informacion(logo=logo)

        with self.assertRaises(ValidationError):
            info.full_clean()

    def test_logo_que_no_es_imagen_real_falla(self):
        info = self._build_informacion(logo=self._create_logo(filename='logo.png', content=b'not-a-real-image', content_type='image/png'))

        with self.assertRaises(ValidationError):
            info.full_clean()


class CarruselInicioImageValidationTests(SimpleTestCase):

    def _create_image(self, width, height, fmt='PNG'):
        image = Image.new('RGB', (width, height), color='red')
        buffer = BytesIO()
        image.save(buffer, format=fmt)
        buffer.seek(0)
        return SimpleUploadedFile(
            f'test-image.{fmt.lower()}',
            buffer.getvalue(),
            content_type='image/png' if fmt == 'PNG' else 'image/jpeg',
        )

    def test_formato_permitido_valida(self):
        instance = CarruselInicio(imagen=self._create_image(1000, 1250, fmt='JPEG'))
        instance.full_clean()

    def test_imagen_demasiado_pequena_no_valida(self):
        instance = CarruselInicio(imagen=self._create_image(200, 200, fmt='PNG'))

        with self.assertRaises(ValidationError):
            instance.full_clean()

    def test_archivo_no_valido_no_valida(self):
        invalid_file = SimpleUploadedFile(
            'test-image.gif',
            b'abc',
            content_type='image/gif',
        )

        with self.assertRaises(ValidationError):
            validate_public_image(invalid_file)

    def test_imagen_muy_grande_no_valida(self):
        oversized_file = SimpleUploadedFile(
            'test-image.jpg',
            b'x' * (6 * 1024 * 1024),
            content_type='image/jpeg',
        )

        with self.assertRaises(ValidationError):
            validate_public_image(oversized_file)


class ChatbotFuncionamientoTests(TestCase):

    def _create_valid_image(self, filename, color):
        image = Image.new('RGB', (1200, 900), color=color)
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return SimpleUploadedFile(
            filename,
            buffer.getvalue(),
            content_type='image/png',
        )

    def setUp(self):
        cache.clear()
        self.url = reverse(
            "api_chatbot"
        )

        PreguntaFrecuente.objects.create(
            pregunta=(
                "¿Cuál es el mejor horario "
                "para visitar?"
            ),
            respuesta=(
                "El mejor horario es de "
                "16:30 a 18:30."
            ),
            activo=True,
        )

        PreguntaFrecuente.objects.create(
            pregunta="¿Aceptan mascotas?",
            respuesta=(
                "Sí, se permite el ingreso "
                "de mascotas."
            ),
            activo=True,
        )

        EventoNovedad.objects.create(
            titulo="Festival amazónico",
            contenido="Evento cultural.",
            tipo="Evento",
            imagen=self._create_valid_image('evento-prueba.png', 'green'),
            fecha_evento=date(2026, 8, 15),
            activo=True,
        )

        ServicioTuristico.objects.create(
            nombre="Glamping",
            tipo="Hospedaje",
            descripcion=(
                "Alojamiento en contacto "
                "con la naturaleza."
            ),
            imagen_principal=self._create_valid_image('servicio-prueba.png', 'blue'),
            activo=True,
        )

    def consultar(self, mensaje):
        return self.client.post(
            self.url,
            data=json.dumps({
                "mensaje": mensaje,
            }),
            content_type="application/json",
        )

    def test_responde_servicios(self):
        respuesta = self.consultar(
            "Hola, ¿qué servicios ofrecen?"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            respuesta.json()["tema"],
            "servicios",
        )

    def test_responde_eventos(self):
        respuesta = self.consultar(
            "¿Existen eventos?"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertIn(
            "Festival amazónico",
            respuesta.json()["respuesta"],
        )

    def test_responde_mejor_horario(self):
        respuesta = self.consultar(
            "¿Cuál es el mejor horario?"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertIn(
            "16:30",
            respuesta.json()["respuesta"],
        )

    def test_responde_mascotas(self):
        respuesta = self.consultar(
            "¿Puedo ir con mi mascota?"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertIn(
            "mascotas",
            respuesta.json()["respuesta"].lower(),
        )

    def test_responde_despedida(self):
        respuesta = self.consultar(
            "Muchas gracias"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            respuesta.json()["tema"],
            "despedida",
        )

    def test_reconoce_sinonimos_de_intenciones_comunes(self):
        consultas = {
            "¿Hay dónde dormir?": "alojamiento",
            "¿Me puedo quedar ahí?": "alojamiento",
            "¿Tienen alojamiento?": "alojamiento",
            "Quiero pasar la noche": "alojamiento",
            "¿Puedo alojarme?": "alojamiento",
            "¿Cuánto cuesta?": "precios",
            "¿Cuánto cobran?": "precios",
            "¿Dónde queda?": "ubicacion",
            "¿Cómo llego?": "como_llegar",
            "¿Qué puedo hacer ahí?": "servicios",
            "¿Qué actividades tienen?": "servicios",
            "¿A qué hora abren?": "horario",
            "¿Cómo puedo comunicarme?": "contacto",
        }

        for mensaje, tema_esperado in consultas.items():
            with self.subTest(mensaje=mensaje):
                respuesta = self.consultar(mensaje)

                self.assertEqual(
                    respuesta.status_code,
                    200,
                )
                self.assertEqual(
                    respuesta.json()["tema"],
                    tema_esperado,
                    mensaje,
                )


class PaginasPublicasTest(TestCase):

    def test_inicio_carga(self):
        respuesta = self.client.get(reverse('inicio'))
        self.assertEqual(respuesta.status_code, 200)

    def test_nosotros_carga(self):
        respuesta = self.client.get(reverse('nosotros'))
        self.assertEqual(respuesta.status_code, 200)

    def test_servicios_carga(self):
        respuesta = self.client.get(reverse('servicios'))
        self.assertEqual(respuesta.status_code, 200)

    def test_eventos_carga(self):
        respuesta = self.client.get(reverse('eventos'))
        self.assertEqual(respuesta.status_code, 200)

    def test_galeria_carga(self):
        respuesta = self.client.get(reverse('galeria'))
        self.assertEqual(respuesta.status_code, 200)

    def test_contacto_carga(self):
        respuesta = self.client.get(reverse('contacto'))
        self.assertEqual(respuesta.status_code, 200)

    def test_build_map_embed_no_hace_peticion_externa_para_url_corta(self):
        url = "https://maps.app.goo.gl/abc123"

        with patch("principal.views.urllib.request.urlopen") as mock_urlopen:
            embed_src, map_link = build_map_embed(url)

        self.assertIsNone(embed_src)
        self.assertEqual(map_link, url)
        mock_urlopen.assert_not_called()

    def test_contacto_muestra_mapa_con_direccion_si_el_link_es_corto(self):
        Contacto.objects.create(
            direccion="Puerto Napo, Tena – Napo",
            mapa_embed_url="https://maps.app.goo.gl/abc123",
            whatsapp="0991234567",
            correo="info@ejemplo.com",
            horarios_atencion="Lun - Dom 8:00 - 18:00",
            activo=True,
        )

        respuesta = self.client.get(reverse('contacto'))

        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content.decode('utf-8')
        self.assertIn('maps.google.com/maps', contenido)
        self.assertNotIn('Ver en Google Maps', contenido)

        respuesta = self.client.get(reverse('contacto'))

        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content.decode('utf-8')
        self.assertIn('maps.google.com/maps', contenido)
        self.assertNotIn('Ver en Google Maps', contenido)

    def test_detalle_servicio_carga(self):
        from .models import ServicioTuristico
        from django.core.files.uploadedfile import SimpleUploadedFile
        from io import BytesIO
        from PIL import Image

        # Crear una imagen en memoria para el test
        imagen = BytesIO()
        img = Image.new('RGB', (1200, 750), color='red')
        img.save(imagen, format='JPEG')
        imagen.seek(0)

        archivo_imagen = SimpleUploadedFile(
            "test_servicio.jpg",
            imagen.getvalue(),
            content_type="image/jpeg"
        )

        servicio = ServicioTuristico.objects.create(
            nombre="Servicio Test",
            tipo="Atracciones",
            descripcion="Descripción de prueba",
            imagen_principal=archivo_imagen,
            activo=True,
        )

        respuesta = self.client.get(reverse('detalle_servicio', args=[servicio.id]))
        self.assertEqual(respuesta.status_code, 200)

    def test_detalle_evento_carga(self):
        from .models import EventoNovedad
        from django.core.files.uploadedfile import SimpleUploadedFile
        from datetime import date
        from io import BytesIO
        from PIL import Image

        # Crear una imagen en memoria para el test
        imagen = BytesIO()
        img = Image.new('RGB', (1200, 750), color='red')
        img.save(imagen, format='JPEG')
        imagen.seek(0)

        archivo_imagen = SimpleUploadedFile(
            "test_evento.jpg",
            imagen.getvalue(),
            content_type="image/jpeg"
        )

        evento = EventoNovedad.objects.create(
            titulo="Evento Test",
            contenido="Contenido de prueba",
            tipo="Evento",
            imagen=archivo_imagen,
            fecha_evento=date.today(),
            activo=True,
        )

        respuesta = self.client.get(reverse('detalle_evento', args=[evento.id]))
        self.assertEqual(respuesta.status_code, 200)