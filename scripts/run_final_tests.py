from principal.views import procesar_mensaje_chatbot

tests = [
    'hola buenas tardes',
    'hola buenas tardes donde estan ubicados',
    'hola muy buena tardes me puede ayuda con la ubicion',
    'que servisios tienen',
    'a que orario abren',
    'tienen parqueadero',
    'tienen piscina',
    'puedo llevar mi perro',
    'que me recomiendas para ir con mi familia',
]

for t in tests:
    r = procesar_mensaje_chatbot(t, None)
    local = 'True' if r.get('metodo') != 'gemini_flash' else 'False'
    gemini = 'True' if r.get('metodo') == 'gemini_flash' else 'False'
    print(f'Pregunta: {t} | tema: {r.get("tema")} | local: {local} | Gemini: {gemini}')
    print('->', (r.get('respuesta') or '')[:180].replace('\n', ' '))
    print()
