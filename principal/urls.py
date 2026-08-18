from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('nosotros/', views.nosotros, name='nosotros'),

    path('servicios/', views.servicios, name='servicios'),
    path(
        'servicios/<int:servicio_id>/',
        views.detalle_servicio,
        name='detalle_servicio'
    ),

    path('eventos/', views.eventos, name='eventos'),
    path(
        'eventos/<int:evento_id>/',
        views.detalle_evento,
        name='detalle_evento'
    ),

    path('galeria/', views.galeria, name='galeria'),
    path('contacto/', views.contacto, name='contacto'),
    path('chatbot/', views.chatbot, name='chatbot'),

    path('api/chatbot/', views.api_chatbot, name='api_chatbot'),
    path('api/preguntas/', views.api_preguntas, name='api_preguntas'),
]