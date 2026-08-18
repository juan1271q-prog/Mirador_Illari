"use strict";

/* =========================================================
   FUNCIONES GENERALES
   ========================================================= */

/**
 * Obtiene una cookie del navegador.
 * Se utiliza para enviar el token CSRF a Django.
 */
function obtenerCookie(nombre) {
    const cookies = document.cookie
        ? document.cookie.split(";")
        : [];

    for (const cookie of cookies) {
        const contenido = cookie.trim();

        if (
            contenido.startsWith(
                `${encodeURIComponent(nombre)}=`
            )
        ) {
            return decodeURIComponent(
                contenido.substring(
                    contenido.indexOf("=") + 1
                )
            );
        }
    }

    return "";
}

function textoPlano(valor) {
    return String(valor || "")
        .replace(/<[^>]*>/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

function obtenerTokenCsrf() {
    const tokenCookie = obtenerCookie("csrftoken");

    if (tokenCookie) {
        return tokenCookie;
    }

    const meta = document.querySelector(
        'meta[name="csrf-token"]'
    );

    return meta ? meta.content : "";
}

async function consultarChatbotLocal(mensaje) {
    const cajaChatbot = document.getElementById(
        "chatbotBox"
    );

    if (!cajaChatbot) {
        throw new Error(
            "No se encontró la caja del chatbot."
        );
    }

    const url = cajaChatbot.dataset.chatbotUrl;

    if (!url) {
        throw new Error(
            "No se configuró la dirección del chatbot."
        );
    }

    const respuestaHttp = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": obtenerTokenCsrf(),
            "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({
            mensaje: mensaje,
        }),
    });

    const contenido = await respuestaHttp.text();

    let datos;

    try {
        datos = JSON.parse(contenido);
    } catch (error) {
        throw new Error(
            `El servidor devolvió una respuesta no válida. ` +
            `Estado HTTP: ${respuestaHttp.status}`
        );
    }

    if (!respuestaHttp.ok) {
        throw new Error(
            datos.respuesta ||
            `Error HTTP ${respuestaHttp.status}`
        );
    }

    if (
        !datos.respuesta ||
        typeof datos.respuesta !== "string"
    ) {
        throw new Error(
            "La respuesta del chatbot está incompleta."
        );
    }

    return datos;
}


/* =========================================================
   FILTROS Y PAGINACIÓN EN EVENTOS (AJAX)
   ========================================================= */

function iniciarEventosAjax() {
    const filtros = document.getElementById("filtrosEventos");
    const resultados = document.getElementById("resultadosEventos");
    const cargando = document.getElementById("cargandoEventos");

    if (!filtros || !resultados) {
        return;
    }

    let controlador = null;
    let tipoActual = new URLSearchParams(window.location.search).get("tipo") || "";

    async function cargarEventos(parametros = null, actualizarUrl = true) {
        const datos = parametros ? new URLSearchParams(parametros) : new URLSearchParams();

        if (!parametros && tipoActual) {
            datos.set("tipo", tipoActual);
        }

        const url = `${window.location.pathname}?${datos.toString()}`;

        if (controlador) controlador.abort();

        controlador = new AbortController();

        if (cargando) cargando.hidden = false;
        resultados.classList.add("cargando");

        try {
            const respuesta = await fetch(url, {
                method: "GET",
                headers: { "X-Requested-With": "XMLHttpRequest" },
                signal: controlador.signal
            });

            if (!respuesta.ok) throw new Error("No fue posible cargar los eventos.");

            const html = await respuesta.text();

            resultados.innerHTML = html;

            if (actualizarUrl) {
                window.history.replaceState({}, "", url);
            }

        } catch (error) {
            if (error.name !== "AbortError") console.error(error);
        } finally {
            if (cargando) cargando.hidden = true;
            resultados.classList.remove("cargando");
        }
    }

    filtros.addEventListener("click", function (evento) {
        const boton = evento.target.closest(".filtro-evento");

        if (!boton) return;

        if (boton.tagName.toLowerCase() === 'a') {
            evento.preventDefault();
        }

        filtros.querySelectorAll(".filtro-evento").forEach(function (elemento) {
            elemento.classList.remove("activo");
        });

        boton.classList.add("activo");

        tipoActual = boton.dataset.tipo || "";

        const parametros = new URLSearchParams();
        if (tipoActual) parametros.set("tipo", tipoActual);

        cargarEventos(parametros);
    });

    resultados.addEventListener("click", function (evento) {
        const enlace = evento.target.closest(".paginacion a");

        if (!enlace) return;

        evento.preventDefault();

        const url = new URL(enlace.href, window.location.origin);

        cargarEventos(url.searchParams);
    });
}


/**
 * Devuelve la hora actual en formato corto.
 */
function obtenerHoraActual() {
    return new Date().toLocaleTimeString("es-EC", {
        hour: "2-digit",
        minute: "2-digit"
    });
}

function iniciarCarrusel() {
    const track = document.getElementById("heroTrack");

    if (!track) {
        return;
    }

    const slides = Array.from(
        track.querySelectorAll(".hero-slide")
    );

    if (slides.length === 0) {
        return;
    }

    const botonAnterior =
        document.getElementById("heroPrev");

    const botonSiguiente =
        document.getElementById("heroNext");

    const contenedorPuntos =
        document.getElementById("heroDots");

    const imagenRespaldo =
        track.dataset.fallbackImage || "";

    let indiceActual = 0;
    let cantidadVisible = obtenerCantidadVisible();
    let intervalo = null;

    slides.forEach(function (slide) {
        const imagen = slide.querySelector(
            ".hero-slide-media"
        );

        if (!imagen || !imagenRespaldo) {
            return;
        }

        function cargarRespaldo() {
            if (
                imagen.dataset.respaldoAplicado === "true"
            ) {
                return;
            }

            imagen.dataset.respaldoAplicado = "true";
            imagen.src = imagenRespaldo;
        }

        imagen.addEventListener(
            "error",
            cargarRespaldo
        );

        if (
            imagen.complete &&
            imagen.naturalWidth === 0
        ) {
            cargarRespaldo();
        }
    });

    function obtenerCantidadVisible() {
        const ancho = window.innerWidth;

        if (ancho >= 992) {
            return 3;
        }

        if (ancho >= 768) {
            return 2;
        }

        return 1;
    }

    function corregirIndice(indice) {
        return (
            indice + slides.length
        ) % slides.length;
    }

    function actualizarDiapositivas() {
        slides.forEach(function (slide) {
            slide.classList.remove(
                "position-left",
                "position-center",
                "position-right",
                "hidden"
            );

            slide.setAttribute(
                "aria-hidden",
                "true"
            );
        });

        const indicesVisibles = [];

        if (
            slides.length >= 3 &&
            cantidadVisible === 3
        ) {
            indicesVisibles.push(
                corregirIndice(indiceActual - 1)
            );

            indicesVisibles.push(
                indiceActual
            );

            indicesVisibles.push(
                corregirIndice(indiceActual + 1)
            );

        } else if (
            slides.length >= 2 &&
            cantidadVisible >= 2
        ) {
            indicesVisibles.push(
                indiceActual
            );

            indicesVisibles.push(
                corregirIndice(indiceActual + 1)
            );

        } else {
            indicesVisibles.push(
                indiceActual
            );
        }

        indicesVisibles.forEach(
            function (indice, posicion) {
                const slide = slides[indice];

                if (!slide) {
                    return;
                }

                slide.setAttribute(
                    "aria-hidden",
                    "false"
                );

                if (indicesVisibles.length === 3) {
                    if (posicion === 0) {
                        slide.classList.add(
                            "position-left"
                        );
                    } else if (posicion === 1) {
                        slide.classList.add(
                            "position-center"
                        );
                    } else {
                        slide.classList.add(
                            "position-right"
                        );
                    }

                } else if (
                    indicesVisibles.length === 2
                ) {
                    if (posicion === 0) {
                        slide.classList.add(
                            "position-center"
                        );
                    } else {
                        slide.classList.add(
                            "position-right"
                        );
                    }

                } else {
                    slide.classList.add(
                        "position-center"
                    );
                }
            }
        );

        slides.forEach(
            function (slide, indice) {
                if (
                    !indicesVisibles.includes(indice)
                ) {
                    slide.classList.add("hidden");
                }
            }
        );
    }

    function crearPuntos() {
        if (
            !contenedorPuntos ||
            slides.length < 2
        ) {
            return;
        }

        if (
            contenedorPuntos.children.length === 0
        ) {
            slides.forEach(
                function (_, indice) {
                    const punto =
                        document.createElement("button");

                    punto.type = "button";
                    punto.className = "hero-dot";

                    punto.setAttribute(
                        "aria-label",
                        `Mostrar imagen ${indice + 1}`
                    );

                    punto.addEventListener(
                        "click",
                        function () {
                            indiceActual = indice;
                            mostrarCarrusel();
                            reiniciarIntervalo();
                        }
                    );

                    contenedorPuntos.appendChild(
                        punto
                    );
                }
            );
        }

        Array.from(
            contenedorPuntos.children
        ).forEach(
            function (punto, indice) {
                punto.classList.toggle(
                    "active",
                    indice === indiceActual
                );
            }
        );
    }

    function mostrarCarrusel() {
        cantidadVisible =
            obtenerCantidadVisible();

        actualizarDiapositivas();
        crearPuntos();
    }

    function mostrarSiguiente() {
        indiceActual = corregirIndice(
            indiceActual + 1
        );

        mostrarCarrusel();
    }

    function mostrarAnterior() {
        indiceActual = corregirIndice(
            indiceActual - 1
        );

        mostrarCarrusel();
    }

    function iniciarIntervalo() {
        detenerIntervalo();

        if (slides.length < 2) {
            return;
        }

        intervalo = window.setInterval(
            mostrarSiguiente,
            4200
        );
    }

    function detenerIntervalo() {
        if (intervalo) {
            window.clearInterval(intervalo);
            intervalo = null;
        }
    }

    function reiniciarIntervalo() {
        detenerIntervalo();
        iniciarIntervalo();
    }

    if (botonAnterior) {
        botonAnterior.addEventListener(
            "click",
            function () {
                mostrarAnterior();
                reiniciarIntervalo();
            }
        );
    }

    if (botonSiguiente) {
        botonSiguiente.addEventListener(
            "click",
            function () {
                mostrarSiguiente();
                reiniciarIntervalo();
            }
        );
    }

    const seccionHero =
        document.querySelector(".hero");

    if (seccionHero) {
        seccionHero.addEventListener(
            "mouseenter",
            detenerIntervalo
        );

        seccionHero.addEventListener(
            "mouseleave",
            iniciarIntervalo
        );
    }

    window.addEventListener(
        "resize",
        function () {
            const nuevaCantidad =
                obtenerCantidadVisible();

            if (
                nuevaCantidad !== cantidadVisible
            ) {
                cantidadVisible = nuevaCantidad;
                mostrarCarrusel();
            }
        }
    );

    mostrarCarrusel();
    iniciarIntervalo();
}


/* =========================================================
   ANIMACIONES AL DESPLAZARSE
   ========================================================= */

function iniciarAnimaciones() {
    const selectores = [
        ".reveal-on-scroll",
        ".seccion",
        ".card",
        ".atractivo",
        ".servicio-card",
        ".evento-card",
        ".galeria-item",
        ".contacto-item",
        ".nosotros-tarjeta",
        ".nosotros-valor-card"
    ];

    const elementos = new Set();

    selectores.forEach(function (selector) {
        document
            .querySelectorAll(selector)
            .forEach(function (elemento) {
                elementos.add(elemento);
            });
    });

    document
        .querySelectorAll(".reveal-on-load")
        .forEach(function (elemento) {
            elemento.classList.add("visible");
        });

    if (!("IntersectionObserver" in window)) {
        elementos.forEach(function (elemento) {
            elemento.classList.add("visible");
        });

        return;
    }

    const observador = new IntersectionObserver(
        function (entradas, observer) {
            entradas.forEach(function (entrada) {
                if (entrada.isIntersecting) {
                    entrada.target.classList.add("visible");
                    observer.unobserve(entrada.target);
                }
            });
        },
        {
            threshold: 0.12
        }
    );

    elementos.forEach(function (elemento) {
        if (
            !elemento.classList.contains("reveal-on-load")
        ) {
            elemento.classList.add("reveal-on-scroll");
            observador.observe(elemento);
        }
    });
}


/* =========================================================
   LOGO DEL ENCABEZADO
   ========================================================= */

function iniciarLogo() {
    const logo = document.getElementById("brandLogo");

    if (!logo) {
        return;
    }

    logo.style.cursor = "pointer";

    logo.addEventListener("click", function () {
        window.location.href = "/";
    });
}

function iniciarMenuMovil() {
    const toggle = document.getElementById("menuToggle");
    const menu = document.getElementById("mainMenu");

    if (!toggle || !menu) {
        return;
    }

    toggle.addEventListener("click", function () {
        const abierto = menu.classList.toggle("abierto");
        toggle.setAttribute("aria-expanded", String(abierto));
        toggle.classList.toggle("activo", abierto);
    });

    menu.querySelectorAll("a").forEach(function (enlace) {
        enlace.addEventListener("click", function () {
            menu.classList.remove("abierto");
            toggle.setAttribute("aria-expanded", "false");
            toggle.classList.remove("activo");
        });
    });
}


/* =========================================================
   CHATBOT MIRADOR ILLARI
   ========================================================= */

function iniciarChatbot() {
    const widget = document.querySelector(".chatbot-widget");

    if (!widget) {
        return;
    }

    const tituloWidget =
        widget.dataset.chatbotTitle || "Chatbot Mirador Illari";

    const introWidget =
        widget.dataset.chatbotIntro ||
        "Hola 👋 Soy el chatbot del Mirador Illari. ¿En qué puedo ayudarte?";

    const placeholderWidget =
        widget.dataset.chatbotPlaceholder ||
        "Escribe tu mensaje...";

    const textoEnviar =
        widget.dataset.chatbotSendLabel || "Enviar";

    const etiquetaOpciones =
        widget.dataset.chatbotOptionsLabel ||
        "Opciones rápidas";

    const botonAbrir =
        document.getElementById("chatbotBtn");

    const caja =
        document.getElementById("chatbotBox");

    const botonCerrar =
        document.getElementById("cerrarChat");

    const botonMinimizar =
        document.getElementById("minimizarChat");

    const cuerpo =
        document.getElementById("chatbotBody");

    const contenedorMensajes =
        document.getElementById("chatbotMessages");

    const entrada =
        document.getElementById("chatInput");

    const botonEnviar =
        document.getElementById("sendBtn");

    function ajustarChatbotTeclado() {
        if (!window.visualViewport) {
            document.documentElement.style.setProperty(
                "--chatbot-keyboard-offset",
                "0px"
            );
            return;
        }

        const offset = Math.max(
            0,
            window.innerHeight - window.visualViewport.height
        );

        document.documentElement.style.setProperty(
            "--chatbot-keyboard-offset",
            `${offset}px`
        );
    }

    const opcionesRapidas =
        document.getElementById("quickChips");

    const botonMostrarOpciones =
        document.getElementById("quickChipsToggle");

    const horaInicial =
        document.getElementById("initialTime");

    if (
        !botonAbrir ||
        !caja ||
        !contenedorMensajes ||
        !entrada ||
        !botonEnviar
    ) {
        return;
    }

    const urlPreguntas =
        widget.dataset.preguntasApiUrl ||
        "/api/preguntas/";

    const contenidoOriginalBoton =
        botonEnviar.innerHTML;

    const cabeceraTitulo =
        document.querySelector(".chatbot-title strong");

    const cabeceraSubtitulo =
        document.querySelector(".chatbot-title span");

    const inputMensaje =
        document.getElementById("chatInput");

    if (cabeceraTitulo) {
        cabeceraTitulo.textContent = tituloWidget;
    }

    if (cabeceraSubtitulo) {
        cabeceraSubtitulo.textContent = etiquetaOpciones;
    }

    if (inputMensaje) {
        inputMensaje.placeholder = placeholderWidget;
        inputMensaje.setAttribute("aria-label", placeholderWidget);
    }

    botonEnviar.title = textoEnviar;
    botonEnviar.setAttribute("aria-label", textoEnviar);

    let enviando = false;

    if (horaInicial) {
        horaInicial.textContent = obtenerHoraActual();
    }

    function desplazarAlFinal(forzar = false) {
        window.setTimeout(function () {
            const cercaDelFinal =
                cuerpo &&
                (cuerpo.scrollHeight - cuerpo.scrollTop - cuerpo.clientHeight) < 180;

            if (!forzar && !cercaDelFinal) {
                return;
            }

            if (cuerpo) {
                cuerpo.scrollTop = cuerpo.scrollHeight;
            }

            contenedorMensajes.scrollTop =
                contenedorMensajes.scrollHeight;
        }, 40);
    }

    let scrollFijoEnFoco = 0;

    function bloquearScrollFondo() {
        scrollFijoEnFoco =
            window.scrollY ||
            document.documentElement.scrollTop ||
            0;

        document.body.classList.add("chatbot-open");
        document.body.style.position = "fixed";
        document.body.style.top = `${-scrollFijoEnFoco}px`;
        document.body.style.left = "0";
        document.body.style.width = "100%";
        document.body.style.overflow = "hidden";
    }

    function restaurarScrollFondo() {
        document.body.classList.remove("chatbot-open");
        document.body.style.position = "";
        document.body.style.top = "";
        document.body.style.left = "";
        document.body.style.width = "";
        document.body.style.overflow = "";

        window.scrollTo({
            top: scrollFijoEnFoco,
            left: 0,
            behavior: "auto"
        });
    }

    function enfocarEntradaConScrollSeguro() {
        if (!entrada) {
            return;
        }

        if ("focus" in HTMLInputElement.prototype) {
            try {
                entrada.focus({ preventScroll: true });
            } catch (error) {
                entrada.focus();
            }
        } else {
            entrada.focus();
        }
    }

    function abrirChatbot() {
        bloquearScrollFondo();
        caja.classList.add("activo");
        caja.classList.remove("minimized");
        widget.classList.add("chat-open");

        caja.setAttribute("aria-hidden", "false");
        botonAbrir.setAttribute("aria-expanded", "true");
        botonAbrir.setAttribute(
            "aria-label",
            "Cerrar asistente virtual"
        );

        window.setTimeout(function () {
            const esCelular = window.matchMedia(
                "(max-width: 600px)"
            ).matches;
            if (!esCelular) {
                enfocarEntradaConScrollSeguro();
            }
            desplazarAlFinal();
        }, 150);
    }

    function cerrarChatbot() {
        caja.classList.remove("activo");
        caja.classList.remove("minimized");
        widget.classList.remove("chat-open");
        restaurarScrollFondo();

        caja.setAttribute("aria-hidden", "true");
        botonAbrir.setAttribute("aria-expanded", "false");
        botonAbrir.setAttribute(
            "aria-label",
            "Abrir asistente virtual"
        );

        botonAbrir.focus();
    }

    function minimizarChatbot() {
        caja.classList.toggle("minimized");
    }

    function ocultarOpcionesRapidas() {
        if (!opcionesRapidas) {
            return;
        }

        opcionesRapidas.classList.add("oculto");
        opcionesRapidas.classList.remove("expandido");

        if (botonMostrarOpciones) {
            botonMostrarOpciones.hidden = false;
        }
    }

    function mostrarOpcionesRapidas() {
        if (!opcionesRapidas) {
            return;
        }

        opcionesRapidas.classList.remove("oculto");
        opcionesRapidas.classList.add("expandido");

        if (botonMostrarOpciones) {
            botonMostrarOpciones.hidden = true;
        }

        desplazarAlFinal(true);
    }

    function crearMensaje(texto, tipo, datos = null) {
        const mensaje = document.createElement("div");

        mensaje.className = `message ${tipo}`;

        if (tipo === "bot") {
            const avatar = document.createElement("img");
            const logoChatbot =
                document.querySelector(".chatbot-logo");

            avatar.className = "avatar";
            avatar.alt = "Logo de Mirador Illari";

            if (logoChatbot) {
                avatar.src = logoChatbot.src;
            }

            mensaje.appendChild(avatar);
        }

        const burbuja = document.createElement("div");
        burbuja.className = "bubble";

        const contenido = document.createElement("div");
        contenido.className = "bubble-text";
        contenido.textContent = String(texto || "");

        const hora = document.createElement("div");
        hora.className = "bubble-time";
        hora.textContent = obtenerHoraActual();

        burbuja.appendChild(contenido);

        const datosMapa =
            datos &&
            datos.mapa &&
            typeof datos.mapa === "object"
                ? datos.mapa
                : null;

        if (
            tipo === "bot" &&
            datosMapa &&
            (
                datosMapa.embed_url ||
                datosMapa.link
            )
        ) {
            const tarjetaMapa = document.createElement("div");

            tarjetaMapa.className = "chatbot-mapa-card";

            if (datosMapa.embed_url) {
                const iframe = document.createElement("iframe");

                iframe.className = "chatbot-mapa-iframe";

                iframe.src = datosMapa.embed_url;

                iframe.title = datosMapa.titulo || "Ubicación del Centro Turístico Mirador Illari";

                iframe.loading = "lazy";
                iframe.allowFullscreen = true;
                iframe.referrerPolicy = "no-referrer-when-downgrade";

                tarjetaMapa.appendChild(iframe);
            }

            if (datosMapa.link) {
                const enlaceMapa = document.createElement("a");

                enlaceMapa.className = "chatbot-mapa-enlace";

                enlaceMapa.href = datosMapa.link;

                enlaceMapa.target = "_blank";
                enlaceMapa.rel = "noopener noreferrer";

                enlaceMapa.textContent = "📍 Abrir ubicación en Google Maps";

                tarjetaMapa.appendChild(enlaceMapa);
            }

            burbuja.appendChild(tarjetaMapa);
        }

        burbuja.appendChild(hora);
        mensaje.appendChild(burbuja);

        contenedorMensajes.appendChild(mensaje);

        desplazarAlFinal();

        return mensaje;
    }

    function crearIndicadorEscritura() {
        const mensaje = document.createElement("div");

        mensaje.className = "message bot loader";

        const burbuja = document.createElement("div");
        burbuja.className = "bubble";
        burbuja.textContent = "Escribiendo...";

        mensaje.appendChild(burbuja);
        contenedorMensajes.appendChild(mensaje);

        desplazarAlFinal();

        return mensaje;
    }

    function cambiarEstadoEnvio(estado) {
        enviando = estado;
        botonEnviar.disabled = estado;
        entrada.disabled = estado;

        botonEnviar.innerHTML = estado
            ? "..."
            : contenidoOriginalBoton;
    }

    async function enviarConsulta(texto) {
        const mensaje = String(texto || "").trim();

        if (!mensaje || enviando) {
            return;
        }

        ocultarOpcionesRapidas();
        crearMensaje(mensaje, "user");

        const indicador = crearIndicadorEscritura();

        cambiarEstadoEnvio(true);

        try {
            const resultado = await consultarChatbotLocal(
                mensaje
            );

            indicador.remove();
            crearMensaje(
                resultado.respuesta,
                "bot",
                resultado
            );
        } catch (error) {
            console.error(
                "Error al consultar el chatbot:",
                error
            );

            indicador.remove();

            const mensajeError =
                error instanceof TypeError
                    ? (
                        "No fue posible comunicarse con el servidor. " +
                        "Comprueba que Django esté ejecutándose."
                    )
                    : (
                        error.message ||
                        "No pude procesar la pregunta."
                    );

            crearMensaje(
                mensajeError,
                "bot"
            );
        } finally {
            cambiarEstadoEnvio(false);
            if (window.matchMedia("(max-width: 600px)").matches) {
                window.setTimeout(function () {
                    enfocarEntradaConScrollSeguro();
                }, 50);
            } else {
                enfocarEntradaConScrollSeguro();
            }
        }
    }

    async function enviarMensajeEntrada() {
        const texto = entrada.value.trim();

        if (!texto) {
            entrada.focus();
            return;
        }

        entrada.value = "";
        await enviarConsulta(texto);
    }

    function asignarEventosOpciones() {
        if (!opcionesRapidas) {
            return;
        }

        opcionesRapidas
            .querySelectorAll(".quick-chip")
            .forEach(function (boton) {
                boton.addEventListener(
                    "click",
                    function () {
                        enviarConsulta(
                            boton.textContent.trim()
                        );
                    }
                );
            });
    }

    async function cargarPreguntasFrecuentes() {
        if (!opcionesRapidas) {
            return;
        }

        try {
            const respuesta = await fetch(
                urlPreguntas,
                {
                    method: "GET",
                    credentials: "same-origin",
                    headers: {
                        Accept: "application/json",
                        "X-Requested-With":
                            "XMLHttpRequest"
                    }
                }
            );

            if (!respuesta.ok) {
                throw new Error(
                    "No fue posible cargar las preguntas."
                );
            }

            const datos = await respuesta.json();

            if (
                !Array.isArray(datos.preguntas) ||
                datos.preguntas.length === 0
            ) {
                asignarEventosOpciones();
                return;
            }

            opcionesRapidas.innerHTML = "";

            datos.preguntas
                .slice(0, 5)
                .forEach(function (registro) {
                    const preguntaTexto = textoPlano(
                        registro.pregunta
                    );

                    const boton =
                        document.createElement("button");

                    boton.type = "button";
                    boton.className = "quick-chip";
                    boton.textContent = preguntaTexto;

                    boton.addEventListener(
                        "click",
                        function () {
                            enviarConsulta(
                                preguntaTexto
                            );
                        }
                    );

                    opcionesRapidas.appendChild(
                        boton
                    );
                });
        } catch (error) {
            asignarEventosOpciones();
        }
    }

    botonAbrir.addEventListener(
        "click",
        abrirChatbot
    );

    if (botonCerrar) {
        botonCerrar.addEventListener(
            "click",
            cerrarChatbot
        );
    }

    if (botonMinimizar) {
        botonMinimizar.addEventListener(
            "click",
            minimizarChatbot
        );
    }

    if (botonMostrarOpciones) {
        botonMostrarOpciones.addEventListener(
            "click",
            mostrarOpcionesRapidas
        );
    }

    botonEnviar.addEventListener(
        "click",
        function (evento) {
            evento.preventDefault();
            enviarMensajeEntrada();
        }
    );

    entrada.addEventListener(
        "focusin",
        function () {
            ajustarChatbotTeclado();
        }
    );

    entrada.addEventListener(
        "touchstart",
        function () {
            window.setTimeout(function () {
                enfocarEntradaConScrollSeguro();
            }, 0);
        },
        { passive: true }
    );

    if (window.visualViewport) {
        window.visualViewport.addEventListener(
            "resize",
            ajustarChatbotTeclado,
            { passive: true }
        );
    }

    entrada.addEventListener(
        "keydown",
        function (evento) {
            if (
                evento.key === "Enter" &&
                !evento.shiftKey
            ) {
                evento.preventDefault();
                enviarMensajeEntrada();
            }
        }
    );

    document.addEventListener(
        "keydown",
        function (evento) {
            if (
                evento.key === "Escape" &&
                caja.classList.contains("activo")
            ) {
                cerrarChatbot();
            }
        }
    );

    cargarPreguntasFrecuentes();
}


/* =========================================================
   COMPARTIR EN REDES SOCIALES Y COPIAR ENLACE
   ========================================================= */

function iniciarCompartir() {
    const botonesCompartir = document.querySelectorAll(
        ".btn-compartir-whatsapp, .btn-compartir-facebook, .btn-copiar-enlace"
    );

    if (botonesCompartir.length === 0) {
        return;
    }

    const urlActual = window.location.href;
    const titulo = document.querySelector("h1");
    const textoTitulo = titulo ? titulo.textContent.trim() : "Mira esto";

    function mostrarMensajeExito(mensaje) {
        const contenedor = document.getElementById(
            "mensajeCopiaExitosa"
        );

        if (contenedor) {
            contenedor.textContent = mensaje;
            contenedor.classList.add("visible");

            setTimeout(function () {
                contenedor.classList.remove("visible");
            }, 3000);
        }
    }

    botonesCompartir.forEach(function (boton) {
        boton.addEventListener("click", function (evento) {
            evento.preventDefault();

            const tipo = this.dataset.compartir;

            if (tipo === "whatsapp") {
                const enlaceWhatsApp =
                    "https://wa.me/?text=" +
                    encodeURIComponent(
                        `${textoTitulo}\n${urlActual}`
                    );

                window.open(
                    enlaceWhatsApp,
                    "_blank",
                    "noopener,noreferrer"
                );
            } else if (tipo === "facebook") {
                const enlaceFacebook =
                    "https://www.facebook.com/sharer/sharer.php?u=" +
                    encodeURIComponent(urlActual);

                window.open(
                    enlaceFacebook,
                    "_blank",
                    "width=600,height=400,noopener,noreferrer"
                );
            } else if (tipo === "copiar") {
                navigator.clipboard
                    .writeText(urlActual)
                    .then(function () {
                        mostrarMensajeExito(
                            "Enlace copiado al portapapeles"
                        );
                    })
                    .catch(function () {
                        console.error(
                            "Error al copiar el enlace"
                        );
                    });
            }
        });
    });
}


/* =========================================================
   MODAL DE GALERÍA
   ========================================================= */

function iniciarModalGaleria() {
    const modal =
        document.getElementById("modalGaleria");

    const imagen =
        document.getElementById("modalImagen");

    const titulo =
        document.getElementById("modalTitulo");

    const descripcion =
        document.getElementById("modalDescripcion");

    const botonCerrar =
        document.getElementById("cerrarModalGaleria");

    const elementos =
        document.querySelectorAll(".galeria-item");

    if (
        !modal ||
        !imagen ||
        !titulo ||
        !descripcion ||
        !botonCerrar ||
        elementos.length === 0
    ) {
        return;
    }

    function abrirModal(elemento) {
        const rutaImagen =
            elemento.dataset.imagen || "";

        const textoTitulo =
            elemento.dataset.titulo ||
            "Mirador Illari";

        const textoDescripcion =
            elemento.dataset.descripcion || "";

        imagen.src = rutaImagen;
        imagen.alt = textoTitulo;
        titulo.textContent = textoTitulo;
        descripcion.textContent = textoDescripcion;

        modal.hidden = false;
        document.body.classList.add("modal-abierto");

        botonCerrar.focus();
    }

    function cerrarModal() {
        modal.hidden = true;

        imagen.src = "";
        imagen.alt = "";
        titulo.textContent = "";
        descripcion.textContent = "";

        document.body.classList.remove(
            "modal-abierto"
        );
    }

    elementos.forEach(function (elemento) {
        elemento.addEventListener(
            "click",
            function () {
                abrirModal(elemento);
            }
        );
    });

    botonCerrar.addEventListener(
        "click",
        cerrarModal
    );

    modal.addEventListener(
        "click",
        function (evento) {
            if (evento.target === modal) {
                cerrarModal();
            }
        }
    );

    document.addEventListener(
        "keydown",
        function (evento) {
            if (
                evento.key === "Escape" &&
                !modal.hidden
            ) {
                cerrarModal();
            }
        }
    );
}


/* =========================================================
   BÚSQUEDA, FILTROS Y PAGINACIÓN EN SERVICIOS (AJAX)
   ========================================================= */

function iniciarServiciosAjax() {
    const formulario = document.getElementById("formServicios");
    const campoBusqueda = document.getElementById("buscarServicio");
    const selectorTipo = document.getElementById("tipoServicio");
    const resultados = document.getElementById("resultadosServicios");
    const cargando = document.getElementById("cargandoServicios");

    if (!formulario || !campoBusqueda || !selectorTipo || !resultados) {
        return;
    }

    let temporizador = null;
    let controlador = null;

    async function cargarServicios(parametros = null, actualizarUrl = true) {
        const datosFormulario = parametros
            ? new URLSearchParams(parametros)
            : new URLSearchParams(new FormData(formulario));

        const url = `${window.location.pathname}?${datosFormulario.toString()}`;

        if (controlador) {
            controlador.abort();
        }

        controlador = new AbortController();

        if (cargando) cargando.hidden = false;
        resultados.classList.add("cargando");

        try {
            const respuesta = await fetch(url, {
                method: "GET",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                },
                signal: controlador.signal
            });

            if (!respuesta.ok) {
                throw new Error("No fue posible cargar los servicios.");
            }

            const html = await respuesta.text();

            resultados.innerHTML = html;

            if (actualizarUrl) {
                window.history.replaceState({}, "", url);
            }

        } catch (error) {
            if (error.name !== "AbortError") {
                console.error(error);
            }

        } finally {
            if (cargando) cargando.hidden = true;
            resultados.classList.remove("cargando");
        }
    }

    formulario.addEventListener("submit", function (evento) {
        evento.preventDefault();
        cargarServicios();
    });

    campoBusqueda.addEventListener("input", function () {
        window.clearTimeout(temporizador);

        temporizador = window.setTimeout(function () {
            cargarServicios();
        }, 400);
    });

    selectorTipo.addEventListener("change", function () {
        cargarServicios();
    });

    resultados.addEventListener("click", function (evento) {
        const enlace = evento.target.closest(".paginacion a");

        if (!enlace) {
            return;
        }

        evento.preventDefault();

        const url = new URL(enlace.href, window.location.origin);

        cargarServicios(url.searchParams);
    });
}


/* =========================================================
   INICIALIZACIÓN
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        function ejecutarSeguro(
            nombre,
            funcion
        ) {
            try {
                funcion();
            } catch (error) {
                console.error(
                    `Error al iniciar ${nombre}:`,
                    error
                );
            }
        }

        ejecutarSeguro(
            "el carrusel",
            iniciarCarrusel
        );

        ejecutarSeguro(
            "las animaciones",
            iniciarAnimaciones
        );

        ejecutarSeguro(
            "el logotipo",
            iniciarLogo
        );

        ejecutarSeguro(
            "el menú móvil",
            iniciarMenuMovil
        );

        ejecutarSeguro(
            "el chatbot",
            iniciarChatbot
        );

        ejecutarSeguro(
            "la galería",
            iniciarModalGaleria
        );

        ejecutarSeguro(
            "la función compartir",
            iniciarCompartir
        );

        ejecutarSeguro(
            "los servicios",
            iniciarServiciosAjax
        );

        ejecutarSeguro(
            "los eventos",
            iniciarEventosAjax
        );

        ejecutarSeguro(
            "el cambio de tema",
            iniciarCambioTema
        );
    }
);

function iniciarCambioTema() {
    const botonTema =
        document.getElementById("botonTema");

    const iconoTema =
        document.getElementById("iconoTema");

    if (!botonTema || !iconoTema) {
        return;
    }

    function obtenerTemaActual() {
        return (
            document.documentElement.getAttribute(
                "data-tema"
            ) || "claro"
        );
    }

    function actualizarBoton() {
        const temaActual = obtenerTemaActual();
        const esOscuro = temaActual === "oscuro";

        iconoTema.textContent =
            esOscuro ? "☀️" : "🌙";

        botonTema.setAttribute(
            "aria-label",
            esOscuro
                ? "Activar modo claro"
                : "Activar modo oscuro"
        );

        botonTema.title =
            esOscuro
                ? "Activar modo claro"
                : "Activar modo oscuro";
    }

    botonTema.addEventListener(
        "click",
        function () {
            const nuevoTema =
                obtenerTemaActual() === "oscuro"
                    ? "claro"
                    : "oscuro";

            document.documentElement.setAttribute(
                "data-tema",
                nuevoTema
            );

            localStorage.setItem(
                "tema",
                nuevoTema
            );

            actualizarBoton();
        }
    );

    actualizarBoton();
}