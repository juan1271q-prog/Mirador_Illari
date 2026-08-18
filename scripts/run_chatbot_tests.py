from principal.views import procesar_mensaje_chatbot

tests = [
    ('hola','saludo'),
    ('hola muy buenas tardes me puede ayudar con la ubicación?','ubicacion'),
    ('hola muy buena tardes me puede ayuda con la ubicion??','ubicacion_or_gemini'),
    ('hola que servicios tienen','servicios'),
    ('buenas tardes que puedo hacer si voy con niños','niños'),
    ('hola quiero ir con mi familia que me recomienda','familia_gemini'),
    ('hola tienen piscina','piscina')
]

for texto, label in tests:
    print('\n---')
    print('Input:', texto)
    r = procesar_mensaje_chatbot(texto, None)
    print('Returned tema:', r.get('tema'))
    print('Returned metodo:', r.get('metodo'))
    print('Returned reconocido:', r.get('reconocido'))
    print('Response (short):', (r.get('respuesta') or '')[:300].replace('\n',' '))
