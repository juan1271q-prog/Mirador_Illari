import json
from datetime import date
from decimal import Decimal
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

    def _create_valid_image(self):
        image = Image.new('RGB', (1200, 900), color='green')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return SimpleUploadedFile(
            'servicio.png',
            buffer.getvalue(),
            content_type='image/png',
        )

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
        pregunta = PreguntaFrecuente.objects.create(
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

        self.assertEqual(registro['id'], pregunta.id)

        self.assertNotIn(
            'respuesta',
            registro,
        )

    def test_id_faq_devuelve_respuesta_exacta(self):
        pregunta = PreguntaFrecuente.objects.create(
            pregunta='¿Cuál es el horario de atención?',
            respuesta='RESPUESTA HORARIO TEST',
            activo=True,
        )
        token = self.obtener_token_csrf()

        respuesta = self.client.post(
            self.url,
            data=json.dumps({
                'mensaje': pregunta.pregunta,
                'pregunta_id': pregunta.id,
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos['respuesta'], 'RESPUESTA HORARIO TEST')
        self.assertEqual(datos['metodo'], 'faq_admin_exacta')
        self.assertEqual(datos['confianza'], 100)

    def test_faq_exacta_de_ubicacion_adjunta_mapa(self):
        Contacto.objects.create(
            direccion='Parroquia Puerto Napo, cantón Tena, provincia de Napo, Ecuador',
            mapa_embed_url='https://maps.app.goo.gl/X1ngzxzPrM7uRkXK6',
            whatsapp='0991234567',
            correo='info@ejemplo.com',
            horarios_atencion='Lun - Dom 08:00 - 18:00',
            activo=True,
        )
        pregunta = PreguntaFrecuente.objects.create(
            pregunta='¿Dónde está ubicado el Centro Turístico Mirador Illari?',
            respuesta='El Centro Turístico Mirador Illari está ubicado en la parroquia Puerto Napo, cantón Tena, provincia de Napo, Ecuador.',
            activo=True,
        )
        token = self.obtener_token_csrf()

        respuesta = self.client.post(
            self.url,
            data=json.dumps({
                'mensaje': pregunta.pregunta,
                'pregunta_id': pregunta.id,
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos['respuesta'], pregunta.respuesta)
        self.assertIn('mapa', datos)
        self.assertTrue(datos['mapa'].get('embed_url') or datos['mapa'].get('link'))

    def test_ubicacion_manual_adjunta_mapa(self):
        Contacto.objects.create(
            direccion='Parroquia Puerto Napo, cantón Tena, provincia de Napo, Ecuador',
            mapa_embed_url='https://maps.app.goo.gl/X1ngzxzPrM7uRkXK6',
            whatsapp='0991234567',
            correo='info@ejemplo.com',
            horarios_atencion='Lun - Dom 08:00 - 18:00',
            activo=True,
        )
        token = self.obtener_token_csrf()

        for mensaje in [
            '¿Dónde están ubicados?',
        ]:
            with self.subTest(mensaje=mensaje):
                respuesta = self.client.post(
                    self.url,
                    data=json.dumps({'mensaje': mensaje}),
                    content_type='application/json',
                    HTTP_X_CSRFTOKEN=token,
                )
                self.assertEqual(respuesta.status_code, 200)
                datos = respuesta.json()
                self.assertIn('mapa', datos)
                self.assertTrue(datos['mapa'].get('embed_url') or datos['mapa'].get('link'))

    def test_consultas_no_ubicacion_no_devuelven_mapa(self):
        Contacto.objects.create(
            direccion='Parroquia Puerto Napo, cantón Tena, provincia de Napo, Ecuador',
            mapa_embed_url='https://maps.app.goo.gl/X1ngzxzPrM7uRkXK6',
            whatsapp='0991234567',
            correo='info@ejemplo.com',
            horarios_atencion='Lun - Dom 08:00 - 18:00',
            activo=True,
        )
        token = self.obtener_token_csrf()

        for mensaje in [
            '¿Cuánto cuesta la entrada?',
            '¿Qué servicios tienen?',
        ]:
            with self.subTest(mensaje=mensaje):
                respuesta = self.client.post(
                    self.url,
                    data=json.dumps({'mensaje': mensaje}),
                    content_type='application/json',
                    HTTP_X_CSRFTOKEN=token,
                )
                self.assertEqual(respuesta.status_code, 200)
                self.assertNotIn('mapa', respuesta.json())

    def test_faq_explicita_gana_al_contexto_de_glamping(self):
        PreguntaFrecuente.objects.create(
            pregunta='¿Cuál es el horario de atención?',
            respuesta='RESPUESTA HORARIO TEST',
            activo=True,
        )
        servicio = ServicioTuristico.objects.create(
            nombre='Glamping Mirador',
            tipo='Hospedaje',
            descripcion='Alojamiento en la naturaleza.',
            precio_adulto=Decimal('120.00'),
            capacidad=2,
            imagen_principal=self._create_valid_image(),
            activo=True,
        )
        self.client.session['chatbot_contexto'] = {
            'ultimo_servicio': servicio.id,
        }
        self.client.session.save()
        token = self.obtener_token_csrf()

        respuesta = self.client.post(
            self.url,
            data=json.dumps({
                'mensaje': '¿Cuál es el horario de atención?',
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.json()['respuesta'],
            'RESPUESTA HORARIO TEST',
        )

    def test_diez_faq_devuelven_su_respuesta_por_id(self):
        preguntas = [
            PreguntaFrecuente.objects.create(
                pregunta=f'Pregunta frecuente {indice}?',
                respuesta=f'Respuesta exacta {indice}',
                activo=True,
            )
            for indice in range(1, 11)
        ]
        token = self.obtener_token_csrf()

        for pregunta in preguntas:
            respuesta = self.client.post(
                self.url,
                data=json.dumps({
                    'mensaje': pregunta.pregunta,
                    'pregunta_id': pregunta.id,
                }),
                content_type='application/json',
                HTTP_X_CSRFTOKEN=token,
            )

            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(
                respuesta.json()['respuesta'],
                pregunta.respuesta,
            )

    @patch('principal.views.obtener_respuesta_gemini', return_value=None)
    def test_baja_similitud_no_elige_faq_no_relacionada(self, obtener_gemini):
        PreguntaFrecuente.objects.create(
            pregunta='¿Cuál es el horario de atención?',
            respuesta='RESPUESTA HORARIO TEST',
            activo=True,
        )
        token = self.obtener_token_csrf()

        respuesta = self.client.post(
            self.url,
            data=json.dumps({
                'mensaje': '¿Qué colores tiene el atardecer?',
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotEqual(
            respuesta.json()['respuesta'],
            'RESPUESTA HORARIO TEST',
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


class ChatbotContextMemoryTests(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.url = reverse('api_chatbot')
        self.client.get(reverse('inicio'))
        self.csrf = self.client.cookies['csrftoken'].value

    def _create_valid_image(self, fmt='PNG'):
        image = Image.new('RGB', (1200, 900), color='green')
        buffer = BytesIO()
        image.save(buffer, format=fmt)
        buffer.seek(0)
        return SimpleUploadedFile(
            f'servicio.{fmt.lower()}',
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

    def test_contexto_recuerda_servicio_y_precio(self):
        servicio = ServicioTuristico.objects.create(
            nombre='Glamping Mirador',
            tipo='Hospedaje',
            descripcion='Un alojamiento en la naturaleza.',
            precio_desde=Decimal('120.00'),
            precio_adulto=Decimal('120.00'),
            capacidad=2,
            requiere_reserva=True,
            disponibilidad='Disponible todo el año',
            imagen_principal=self._create_valid_image(),
            activo=True,
        )

        respuesta1 = self.client.post(
            self.url,
            data=json.dumps({'mensaje': 'Quiero hospedarme'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(respuesta1.status_code, 200)
        self.assertIn('alojamiento', respuesta1.json()['respuesta'].lower())

        contexto = self.client.session.get('chatbot_contexto', {})
        self.assertTrue(contexto)

        respuesta2 = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Cuánto cuesta?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(respuesta2.status_code, 200)
        respuesta2_json = respuesta2.json()
        self.assertIn(str(servicio.precio_adulto), respuesta2_json['respuesta'])

        respuesta3 = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Cuántas personas entran?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(respuesta3.status_code, 200)
        self.assertIn('2', respuesta3.json()['respuesta'])

        respuesta4 = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Hay que reservar?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(respuesta4.status_code, 200)
        self.assertIn('reserv', respuesta4.json()['respuesta'].lower())

    def test_glamping_explica_sin_inventar_datos(self):
        ServicioTuristico.objects.create(
            nombre='Glamping Mirador',
            tipo='Hospedaje',
            descripcion='Alojamiento tranquilo en la naturaleza.',
            precio_desde=Decimal('150.00'),
            capacidad=2,
            imagen_principal=self._create_valid_image(),
            activo=True,
        )

        respuesta = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Qué es glamping?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(respuesta.status_code, 200)
        texto = respuesta.json()['respuesta']
        self.assertIn('glamping', texto.lower())
        self.assertIn('hospedaje', texto.lower())
        self.assertIn('naturaleza', texto.lower())

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


class ChatbotPrecisionRegressionTests(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.url = reverse('api_chatbot')
        self.client.get(reverse('inicio'))
        self.csrf = self.client.cookies['csrftoken'].value

    def _create_valid_image(self, fmt='PNG', color='blue', filename='servicio.png'):
        image = Image.new('RGB', (1200, 900), color=color)
        buffer = BytesIO()
        image.save(buffer, format=fmt)
        buffer.seek(0)
        return SimpleUploadedFile(
            filename,
            buffer.getvalue(),
            content_type='image/png' if fmt == 'PNG' else 'image/jpeg',
        )

    def test_faq_exacta_por_texto_gana_a_servicio(self):
        PreguntaFrecuente.objects.create(
            pregunta='¿Cuál es el costo de la entrada?',
            respuesta='RESPUESTA FAQ ENTRADA',
            activo=True,
        )
        ServicioTuristico.objects.create(
            nombre='Entrada al Mirador',
            tipo='Atracciones',
            descripcion='RESPUESTA SERVICIO',
            imagen_principal=self._create_valid_image(filename='entrada.png', color='green'),
            activo=True,
        )

        respuesta = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Cuál es el costo de la entrada?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['respuesta'], 'RESPUESTA FAQ ENTRADA')

    def test_puedo_llevar_comida_no_va_a_mascotas(self):
        PreguntaFrecuente.objects.create(
            pregunta='¿Se puede ingresar con alimentos?',
            respuesta='RESPUESTA FAQ ALIMENTOS',
            activo=True,
        )

        respuesta = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Puedo llevar comida?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['respuesta'], 'RESPUESTA FAQ ALIMENTOS')

    def test_puedo_llevar_mi_perro_va_a_faq_mascotas(self):
        PreguntaFrecuente.objects.create(
            pregunta='¿Se puede ingresar con mascotas?',
            respuesta='RESPUESTA FAQ MASCOTAS',
            activo=True,
        )

        respuesta = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Puedo llevar mi perro?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['respuesta'], 'RESPUESTA FAQ MASCOTAS')

    def test_parqueadero_responde_faq_por_sinonimos(self):
        PreguntaFrecuente.objects.create(
            pregunta='¿Existe parqueadero?',
            respuesta='RESPUESTA FAQ PARQUEADERO',
            activo=True,
        )

        for mensaje in [
            '¿Tienen parqueadero?',
            '¿Hay estacionamiento?',
            '¿Dónde puedo dejar el carro?',
        ]:
            with self.subTest(mensaje=mensaje):
                respuesta = self.client.post(
                    self.url,
                    data=json.dumps({'mensaje': mensaje}),
                    content_type='application/json',
                    HTTP_X_CSRFTOKEN=self.csrf,
                )
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.json()['respuesta'], 'RESPUESTA FAQ PARQUEADERO')

    def test_pagos_usan_faq_y_no_precio(self):
        PreguntaFrecuente.objects.create(
            pregunta='¿Qué métodos de pago aceptan?',
            respuesta='RESPUESTA FAQ PAGOS',
            activo=True,
        )

        for mensaje in [
            '¿Cómo puedo pagar?',
            '¿Puedo pagar por transferencia?',
            '¿Aceptan efectivo?',
        ]:
            with self.subTest(mensaje=mensaje):
                respuesta = self.client.post(
                    self.url,
                    data=json.dumps({'mensaje': mensaje}),
                    content_type='application/json',
                    HTTP_X_CSRFTOKEN=self.csrf,
                )
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.json()['respuesta'], 'RESPUESTA FAQ PAGOS')

    def test_reserva_general_usa_faq_sin_contexto_y_servicio_con_contexto(self):
        faq = PreguntaFrecuente.objects.create(
            pregunta='¿Necesito reservar?',
            respuesta='RESPUESTA FAQ RESERVA',
            activo=True,
        )
        ServicioTuristico.objects.create(
            nombre='Glamping Illari',
            tipo='Hospedaje',
            descripcion='Alojamiento en la naturaleza.',
            precio_adulto=Decimal('120.00'),
            capacidad=2,
            requiere_reserva=True,
            imagen_principal=self._create_valid_image(filename='glamping.png', color='orange'),
            activo=True,
        )

        respuesta_sin_contexto = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Hay que reservar?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(respuesta_sin_contexto.status_code, 200)
        self.assertEqual(respuesta_sin_contexto.json()['respuesta'], faq.respuesta)

        self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Tienen glamping?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )

        respuesta_con_contexto = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Hay que reservar?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(respuesta_con_contexto.status_code, 200)
        self.assertIn('reserva', respuesta_con_contexto.json()['respuesta'].lower())

    def test_mejor_momento_usa_faq_y_no_horario_general(self):
        PreguntaFrecuente.objects.create(
            pregunta='¿Cuál es el mejor horario para visitar?',
            respuesta='RESPUESTA FAQ MEJOR MOMENTO',
            activo=True,
        )

        for mensaje in [
            '¿A qué hora conviene ir?',
            '¿Cuál es la mejor hora para ir?',
            '¿A qué hora se ve el atardecer?',
        ]:
            with self.subTest(mensaje=mensaje):
                respuesta = self.client.post(
                    self.url,
                    data=json.dumps({'mensaje': mensaje}),
                    content_type='application/json',
                    HTTP_X_CSRFTOKEN=self.csrf,
                )
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.json()['respuesta'], 'RESPUESTA FAQ MEJOR MOMENTO')

    def test_contacto_y_camping_y_hospedaje_seguiran_reglas_reales(self):
        Contacto.objects.create(
            direccion='Parroquia Puerto Napo, Tena',
            mapa_embed_url='https://maps.google.com/?q=Parroquia+Puerto+Napo',
            whatsapp='0991234567',
            correo='info@ejemplo.com',
            horarios_atencion='Lun - Dom 08:00 - 18:00',
            activo=True,
        )
        ServicioTuristico.objects.create(
            nombre='Glamping Illari',
            tipo='Hospedaje',
            descripcion='Alojamiento real tipo glamping.',
            precio_adulto=Decimal('180.00'),
            capacidad=2,
            imagen_principal=self._create_valid_image(filename='glamping2.png', color='purple'),
            activo=True,
        )

        contacto = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Cómo puedo contactarlos?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(contacto.status_code, 200)
        self.assertIn('0991234567', contacto.json()['respuesta'])

        camping = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Tienen camping?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(camping.status_code, 200)
        self.assertNotIn('sí', camping.json()['respuesta'].lower())

        hospedaje = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Tienen glamping?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(hospedaje.status_code, 200)
        self.assertIn('glamping', hospedaje.json()['respuesta'].lower())

    def test_mapas_se_adjuntan_solo_para_ubicacion_y_mapa(self):
        Contacto.objects.create(
            direccion='Parroquia Puerto Napo, Tena',
            mapa_embed_url='https://maps.google.com/?q=Parroquia+Puerto+Napo',
            whatsapp='0991234567',
            correo='info@ejemplo.com',
            horarios_atencion='Lun - Dom 08:00 - 18:00',
            activo=True,
        )
        PreguntaFrecuente.objects.create(
            pregunta='¿Cómo llego?',
            respuesta='RESPUESTA FAQ COMO LLEGAR',
            activo=True,
        )

        llegar_exacto = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Cómo llego?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(llegar_exacto.status_code, 200)
        self.assertEqual(llegar_exacto.json()['respuesta'], 'RESPUESTA FAQ COMO LLEGAR')
        self.assertNotIn('mapa', llegar_exacto.json())

        llegar_equivalente = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Cómo puedo llegar?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(llegar_equivalente.status_code, 200)
        self.assertEqual(llegar_equivalente.json()['respuesta'], 'RESPUESTA FAQ COMO LLEGAR')
        self.assertNotIn('mapa', llegar_equivalente.json())

        ubicacion = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Dónde están ubicados?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(ubicacion.status_code, 200)
        self.assertIn('mapa', ubicacion.json())

        mapa = self.client.post(
            self.url,
            data=json.dumps({'mensaje': 'Muéstrame el mapa'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(mapa.status_code, 200)
        self.assertIn('mapa', mapa.json())

        costo = self.client.post(
            self.url,
            data=json.dumps({'mensaje': '¿Cuál es el costo de la entrada?'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(costo.status_code, 200)
        self.assertNotIn('mapa', costo.json())


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