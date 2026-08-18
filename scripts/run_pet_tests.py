from principal.views import procesar_mensaje_chatbot

tests = [
    'puedo llevar mi perro',
    'aceptan mascotas',
    'puedo ir con mi gato',
    'donde estan ubicados',
    'tienen piscina',
    'que servicios tienen'
]

for t in tests:
    r = procesar_mensaje_chatbot(t, None)
    local = 'True' if r.get('metodo') != 'gemini_flash' else 'False'
    gemini = 'True' if r.get('metodo') == 'gemini_flash' else 'False'
    print(f'Pregunta: {t} | tema: {r.get("tema")} | local: {local} | Gemini: {gemini}')
    print('->', (r.get('respuesta') or '')[:200].replace('\n',' '))
    print()
