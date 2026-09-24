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

function limpiarTextoParaChat(texto) {
    if (!texto) {
        return "";
    }

    return textoPlano(texto)
        .replace(/\*\*(.*?)\*\*/g, "$1")
        .replace(/\*(.*?)\*/g, "$1")
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

async function consultarChatbotLocal(mensaje, preguntaId = null) {
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
            ...(preguntaId !== null ? { pregunta_id: preguntaId } : {}),
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
        "Hola, soy Jeyson, tu guía virtual del Mirador Illari. ¿En qué puedo ayudarte?";

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

    const botonMicrofono =
        document.getElementById("chatbotMicBtn");

    const botonVoz =
        document.getElementById("chatbotVoiceBtn");

    const botonVozInicial =
        document.getElementById("initialVoiceBtn");

    let timerViewport;
    let ultimaAlturaViewport = 0;

    function actualizarAlturaChat() {
        const viewport = window.visualViewport;
        const visibleHeight = Math.round(viewport
            ? viewport.height
            : window.innerHeight);

        if (Math.abs(visibleHeight - ultimaAlturaViewport) < 2) {
            return;
        }

        ultimaAlturaViewport = visibleHeight;

        document.documentElement.style.setProperty(
            "--chat-visible-height",
            `${visibleHeight}px`
        );
    }

    function programarActualizacionViewport() {
        window.clearTimeout(timerViewport);
        timerViewport = window.setTimeout(
            actualizarAlturaChat,
            100
        );
    }

    function ajustarChatbotTeclado() {
        actualizarAlturaChat();
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

    let preguntasDisponibles = [];
    let paginaPreguntas = 0;
    const preguntasPorPagina = 4;

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
    let vozActivada = true;

    function leerBanderaSaludoHablado() {
        try {
            return sessionStorage.getItem("illari_saludo_hablado") === "1";
        } catch (error) {
            return false;
        }
    }

    function guardarBanderaSaludoHablado() {
        try {
            sessionStorage.setItem("illari_saludo_hablado", "1");
        } catch (error) {
        }
    }

    function esSaludo(texto) {
        const normalizado = normalizarTextoVoz(texto);
        return /^(hola+|holi|buenos dias|buen dia|buenas tardes|buenas noches|que tal)(\s|$)/.test(normalizado);
    }

    function esAgradecimientoODespedida(texto) {
        const normalizado = normalizarTextoVoz(texto);
        return /^(gracias|muchas gracias|eso era todo|nos vemos|adios|chao)(\s|$)/.test(normalizado);
    }

    function debeHablarAutomaticamente(texto) {
        return esSaludo(texto) || esAgradecimientoODespedida(texto);
    }

    if (horaInicial) {
        horaInicial.textContent = obtenerHoraActual();
    }

    function scrollChatToBottom() {
        if (!contenedorMensajes) {
            return;
        }

        requestAnimationFrame(function () {
            contenedorMensajes.scrollTo({
                top: contenedorMensajes.scrollHeight,
                behavior: "smooth"
            });
        });
    }

    function desplazarAlFinal(forzar = false) {
        if (!contenedorMensajes) {
            return;
        }

        const cercaDelFinal =
            contenedorMensajes.scrollHeight - contenedorMensajes.scrollTop - contenedorMensajes.clientHeight < 180;

        if (!forzar && !cercaDelFinal) {
            return;
        }

        scrollChatToBottom();
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

    function abrirChatbot() {
        bloquearScrollFondo();
        document.body.classList.add("chatbot-mobile-open");
        caja.classList.add("activo");
        caja.classList.remove("minimized");
        widget.classList.add("chat-open");

        caja.setAttribute("aria-hidden", "false");
        botonAbrir.setAttribute("aria-expanded", "true");
        botonAbrir.setAttribute(
            "aria-label",
            "Cerrar asistente virtual"
        );

        mostrarSaludoInicial();

        window.setTimeout(function () {
            desplazarAlFinal();
        }, 150);
    }

    function cerrarChatbot() {
        caja.classList.remove("activo");
        caja.classList.remove("minimized");
        caja.classList.remove("chatbot-mobile-expanded");
        widget.classList.remove("chat-open");
        widget.classList.remove("chatbot-mobile-expanded");
        document.body.classList.remove("chatbot-mobile-open");
        document.body.classList.remove("chatbot-mobile-expanded");
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

    function activarExpansionMovilChatbot() {
        if (!window.matchMedia("(max-width: 600px)").matches) {
            return;
        }

        caja.classList.add("chatbot-mobile-expanded");
        widget.classList.add("chatbot-mobile-expanded");
        document.body.classList.add("chatbot-mobile-expanded");
    }

    function restaurarTamanoMovilChatbot() {
        if (!window.matchMedia("(max-width: 600px)").matches) {
            return;
        }

        caja.classList.remove("chatbot-mobile-expanded");
        widget.classList.remove("chatbot-mobile-expanded");
        document.body.classList.remove("chatbot-mobile-expanded");
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
        if (!opcionesRapidas || preguntasDisponibles.length === 0) {
            return;
        }

        const cantidadPaginas = Math.ceil(
            preguntasDisponibles.length / preguntasPorPagina
        );

        paginaPreguntas =
            paginaPreguntas + 1 >= cantidadPaginas
                ? 0
                : paginaPreguntas + 1;

        renderizarPreguntasFrecuentes();
    }

    function actualizarBotonPreguntas() {
        if (!botonMostrarOpciones) {
            return;
        }

        const hayMasDeUnaPagina = preguntasDisponibles.length > preguntasPorPagina;
        botonMostrarOpciones.hidden = !hayMasDeUnaPagina;

        if (!hayMasDeUnaPagina) {
            return;
        }

        const ultimaPagina =
            paginaPreguntas >= Math.ceil(
                preguntasDisponibles.length / preguntasPorPagina
            ) - 1;

        botonMostrarOpciones.textContent = ultimaPagina
            ? "↺ Volver al inicio"
            : "Ver más opciones";
    }

    function renderizarPreguntasFrecuentes() {
        if (!opcionesRapidas) {
            return;
        }

        const inicio = paginaPreguntas * preguntasPorPagina;
        const grupoActual = preguntasDisponibles.slice(
            inicio,
            inicio + preguntasPorPagina
        );

        opcionesRapidas.innerHTML = "";
        opcionesRapidas.classList.remove("oculto");

        grupoActual.forEach(function (registro) {
            const boton = document.createElement("button");

            boton.type = "button";
            boton.className = "quick-chip";
            boton.textContent = registro.pregunta;
            boton.dataset.mensaje = registro.pregunta;
            boton.dataset.preguntaId = String(registro.id);

            boton.addEventListener("click", function () {
                enviarConsulta(
                    registro.pregunta,
                    registro.id,
                );
            });

            opcionesRapidas.appendChild(boton);
        });

        actualizarBotonPreguntas();
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

        if (tipo === "bot" && texto) {
            const botonLectura = document.createElement("button");
            botonLectura.type = "button";
            botonLectura.className = "chatbot-message-voice";
            botonLectura.textContent = "🔊";
            botonLectura.title = "Escuchar respuesta";
            botonLectura.setAttribute("aria-label", "Escuchar respuesta");
            botonLectura.addEventListener("click", function () {
                hablar(texto, true);
            });
            burbuja.appendChild(botonLectura);
        }

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

    function mostrarSaludoInicial() {
        if (contenedorMensajes.querySelector(".message")) {
            return;
        }

        crearMensaje(introWidget, "bot");
    }

    function removerIndicadorEscritura() {
        const indicador = document.querySelector(".message.bot.loader");

        if (indicador) {
            indicador.remove();
        }
    }

    function mostrarIndicadorEscritura() {
        removerIndicadorEscritura();

        const mensaje = document.createElement("div");
        mensaje.className = "message bot loader";

        const burbuja = document.createElement("div");
        burbuja.className = "bubble";

        const textoIndicador = document.createElement("div");
        textoIndicador.className = "chatbot-loader";
        textoIndicador.setAttribute("aria-live", "polite");
        textoIndicador.innerHTML = "<span>Illari está escribiendo</span><span class=\"dot\"></span><span class=\"dot\"></span><span class=\"dot\"></span>";

        burbuja.appendChild(textoIndicador);
        mensaje.appendChild(burbuja);
        contenedorMensajes.appendChild(mensaje);

        desplazarAlFinal();

        return mensaje;
    }

    function normalizarTextoVoz(texto) {
        return String(texto || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[¿?¡!.,;:]/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    }

    function normalizarComando(texto) {
        return normalizarTextoVoz(texto);
    }

    function obtenerEtiquetaSugerencia(texto) {
        const normalizado = normalizarTextoVoz(texto);

        if (normalizado.includes("horario") || normalizado.includes("atencion")) {
            return "🕒 Horarios";
        }

        if (normalizado.includes("precio") || normalizado.includes("costo") || normalizado.includes("cuanto cuesta")) {
            return "💲 Precios";
        }

        if (normalizado.includes("servicio")) {
            return "🌿 Servicios";
        }

        if (normalizado.includes("ubicacion") || normalizado.includes("donde queda")) {
            return "📍 Ubicación";
        }

        if (normalizado.includes("parqueadero") || normalizado.includes("estacionamiento")) {
            return "🅿️ Parqueadero";
        }

        if (normalizado.includes("ingresar") || normalizado.includes("entrada")) {
            return "🚶 Acceso";
        }

        if (normalizado.includes("evento") || normalizado.includes("novedad")) {
            return "📅 Eventos";
        }

        if (normalizado.includes("contacto") || normalizado.includes("whatsapp")) {
            return "💬 Contacto";
        }

        if (normalizado.includes("glamping")) {
            return "🏕️ Glamping";
        }

        return texto.length > 28
            ? `${texto.slice(0, 25).trim()}...`
            : texto;
    }

    function detectarNavegacion(texto) {
        const normalizado = normalizarComando(texto);
        const destinosDirectos = {
            inicio: /\b(inicio|pagina principal)\b/,
            nosotros: /\b(nosotros|quienes somos|quienes son)\b/,
            servicios: /\b(servicio|servicios)\b/,
            eventos: /\b(evento|eventos|novedad|novedades)\b/,
            galeria: /\b(galeria|foto|fotos|imagen|imagenes)\b/,
            contacto: /\b(contacto|contactarlos|comunicarnos)\b/
        };

        if (/^(inicio|pagina principal)$/.test(normalizado)) {
            return "inicio";
        }

        const tieneIntencionExplicita =
            /\b(ir|ve|vete|dirigete|llevame|llevarme|abre|abrir|muestrame|mostrar|navega|regresa|regresar|volver)\b/.test(normalizado) ||
            /\bquiero (ir|ver|conocer)\b/.test(normalizado) ||
            /\bquiero contactarlos\b/.test(normalizado);

        if (!tieneIntencionExplicita) {
            return null;
        }

        for (const [destino, patron] of Object.entries(destinosDirectos)) {
            if (patron.test(normalizado)) {
                return destino;
            }
        }

        return null;
    }

    function detectarComandoNavegacion(texto) {
        return detectarNavegacion(texto);
    }

    function procesarIntencionNavegacion(textoOriginal) {
        const destino = detectarNavegacion(textoOriginal);

        if (!destino) {
            return false;
        }

        crearMensaje(textoOriginal, "user");
        return ejecutarNavegacion(destino);
    }

    function hablar(texto, forzar = false) {
        if ((!vozActivada && !forzar) || !("speechSynthesis" in window)) {
            return;
        }

        try {
            window.speechSynthesis.cancel();

            const mensaje = new SpeechSynthesisUtterance(texto);
            mensaje.lang = "es-EC";
            mensaje.rate = 1;
            mensaje.pitch = 1;
            window.speechSynthesis.speak(mensaje);
        } catch (error) {
            console.error("No fue posible reproducir la respuesta por voz:", error);
        }
    }

    function responderConVoz(texto, datos = null, hablarAutomaticamente = false) {
        const textoLimpio = limpiarTextoParaChat(texto);

        if (!textoLimpio) {
            return;
        }

        crearMensaje(textoLimpio, "bot", datos);

        if (hablarAutomaticamente) {
            hablar(textoLimpio);
        }
    }

    function programarNavegacion(texto, url) {
        responderConVoz(texto);
        window.setTimeout(function () {
            window.location.href = url;
        }, 650);
    }

    const rutasChatbot = {
        inicio: widget.dataset.inicio || widget.dataset.urlInicio,
        nosotros: widget.dataset.nosotros || widget.dataset.urlNosotros,
        servicios: widget.dataset.servicios || widget.dataset.urlServicios,
        eventos: widget.dataset.eventos || widget.dataset.urlEventos,
        galeria: widget.dataset.galeria || widget.dataset.urlGaleria,
        contacto: widget.dataset.contacto || widget.dataset.urlContacto
    };

    function ejecutarNavegacion(destino) {
        const url = rutasChatbot[destino];

        if (!url) {
            console.error("No existe URL para:", destino);
            return false;
        }

        const mensajes = {
            inicio: "Claro, te llevaré al inicio.",
            nosotros: "Claro, te llevaré a la sección Nosotros.",
            servicios: "Claro, te llevaré a la sección Servicios.",
            eventos: "Claro, te llevaré a Eventos y Novedades.",
            galeria: "Claro, te llevaré a la Galería.",
            contacto: "Claro, te llevaré a la sección Contacto."
        };

        programarNavegacion(mensajes[destino], url);
        return true;
    }

    function procesarComandoVoz(textoOriginal) {
        const normalizado = normalizarComando(textoOriginal);

        if (/^(ir al principio|ir arriba de todo)$/.test(normalizado)) {
            window.scrollTo({ top: 0, behavior: "smooth" });
            responderConVoz("Claro, te llevaré al principio.");
            return true;
        }

        if (normalizado === "ir al final") {
            window.scrollTo({
                top: document.body.scrollHeight,
                behavior: "smooth"
            });
            responderConVoz("Claro, te llevaré al final.");
            return true;
        }

        if (/^(subir|sube|arriba|ir arriba)$/.test(normalizado)) {
            window.scrollBy({
                top: -window.innerHeight * 0.8,
                behavior: "smooth"
            });
            responderConVoz("Claro, subimos un poco.");
            return true;
        }

        if (/^(bajar|baja|abajo|seguir abajo)$/.test(normalizado)) {
            window.scrollBy({
                top: window.innerHeight * 0.8,
                behavior: "smooth"
            });
            responderConVoz("Claro, bajamos un poco.");
            return true;
        }

        if (/^(abre|abrir) (el )?(chatbot|asistente)$/.test(normalizado)) {
            abrirChatbot();
            return true;
        }

        if (/^(minimiza|minimizar) (el )?chatbot$/.test(normalizado)) {
            minimizarChatbot();
            return true;
        }

        if (/^(cierra|cerrar) (el )?chatbot$/.test(normalizado)) {
            cerrarChatbot();
            return true;
        }

        if (/^(que puedo decir|comandos|ayuda de voz|que puedes hacer)$/.test(normalizado)) {
            responderConVoz(
                "Puedes pedirme información o decir: ir a servicios, abrir galería, ver eventos, ir a contacto, subir, bajar o volver al inicio."
            );
            return true;
        }

        if (procesarIntencionNavegacion(textoOriginal)) {
            return true;
        }

        const busqueda = normalizado.match(
            /^(muestrame|quiero ver|buscar|ver)\s+(.+)$/
        );

        if (
            busqueda &&
            rutasChatbot.servicios &&
            busqueda[2] &&
            !normalizado.includes("servicios")
        ) {
            const url = new URL(rutasChatbot.servicios, window.location.origin);
            url.searchParams.set("buscar", busqueda[2]);
            programarNavegacion(
                `Claro, buscaré ${busqueda[2]} en nuestros servicios.`,
                url.href
            );
            return true;
        }

        return false;
    }

    function cambiarEstadoEnvio(estado) {
        enviando = estado;
        botonEnviar.disabled = estado;
        entrada.disabled = estado;

        botonEnviar.innerHTML = estado
            ? "..."
            : contenidoOriginalBoton;
    }

    async function enviarConsulta(texto, preguntaId = null) {
        const mensaje = String(texto || "").trim();

        if (!mensaje || enviando) {
            return;
        }

        if (procesarIntencionNavegacion(mensaje)) {
            return;
        }

        crearMensaje(mensaje, "user");

        mostrarIndicadorEscritura();

        cambiarEstadoEnvio(true);

        try {
            const resultado = await consultarChatbotLocal(
                mensaje,
                preguntaId,
            );

            const respuesta = resultado.respuesta;
            const respuestaLimpia = limpiarTextoParaChat(
                respuesta
            );

            removerIndicadorEscritura();
            const hablarRespuesta = debeHablarAutomaticamente(mensaje);
            responderConVoz(respuestaLimpia, resultado, hablarRespuesta);

            if (esSaludo(mensaje)) {
                guardarBanderaSaludoHablado();
            }

        } catch (error) {
            console.error(
                "Error al consultar el chatbot:",
                error
            );

            removerIndicadorEscritura();

            crearMensaje(
                "No pude procesar tu mensaje en este momento. Inténtalo nuevamente.",
                "bot"
            );
        } finally {
            removerIndicadorEscritura();
            cambiarEstadoEnvio(false);
            if (document.activeElement === entrada) {
                entrada.blur();
            }
        }
    }

    async function enviarMensajeEntrada() {
        const texto = entrada.value.trim();

        if (!texto) {
            return;
        }

        entrada.value = "";
        entrada.blur();
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
                            boton.dataset.mensaje || boton.textContent.trim()
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

            preguntasDisponibles = datos.preguntas
                .map(function (registro) {
                    return {
                        id: registro.id,
                        pregunta: String(registro.pregunta || ""),
                    };
                })
                .filter(function (registro) {
                    return registro.pregunta.trim().length > 0;
                });
            paginaPreguntas = 0;
            renderizarPreguntasFrecuentes();
        } catch (error) {
            asignarEventosOpciones();
        }
    }

    const botonNuevaConversacion = document.getElementById("chatbotNuevaConversacion");

    async function resetearChatbot() {
        const botonReset = document.getElementById("chatbotNuevaConversacion");

        if (botonReset) {
            botonReset.disabled = true;
        }

        removerIndicadorEscritura();

        preguntasDisponibles = [];
        paginaPreguntas = 0;
        if (botonMostrarOpciones) {
            botonMostrarOpciones.hidden = true;
            botonMostrarOpciones.textContent = "Ver más opciones";
        }

        const mensajes = contenedorMensajes.querySelectorAll(".message");
        mensajes.forEach(function (mensaje) {
            mensaje.remove();
        });

        mostrarSaludoInicial();

        try {
            await fetch("/api/chatbot/limpiar/", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": obtenerTokenCsrf(),
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: JSON.stringify({}),
            });
        } catch (error) {
            console.error("No fue posible limpiar la sesión del chatbot:", error);
        }

        if (opcionesRapidas) {
            opcionesRapidas.innerHTML = "";
            cargarPreguntasFrecuentes();
        }

        if (botonReset) {
            botonReset.disabled = false;
        }
    }

    botonNuevaConversacion.addEventListener("click", resetearChatbot);

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

    if (botonVoz) {
        botonVoz.addEventListener("click", function () {
            vozActivada = !vozActivada;
            botonVoz.textContent = vozActivada ? "🔊" : "🔇";
            botonVoz.setAttribute("aria-pressed", String(vozActivada));
            botonVoz.setAttribute(
                "aria-label",
                vozActivada
                    ? "Desactivar lectura de respuestas"
                    : "Activar lectura de respuestas"
            );
            botonVoz.title = vozActivada
                ? "Desactivar lectura"
                : "Activar lectura";

            if (!vozActivada && "speechSynthesis" in window) {
                window.speechSynthesis.cancel();
            }
        });
    }

    if (botonVozInicial) {
        botonVozInicial.addEventListener("click", function () {
            hablar(introWidget, true);
        });
    }

    if (botonMicrofono) {
        const SpeechRecognition =
            window.SpeechRecognition ||
            window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            botonMicrofono.addEventListener("click", function () {
                responderConVoz(
                    "Tu navegador no admite reconocimiento de voz. Puedes continuar utilizando el chat escrito."
                );
            });
        } else {
            const reconocimiento = new SpeechRecognition();
            let microfonoActivo = false;
            reconocimiento.lang = "es-EC";
            reconocimiento.continuous = false;
            reconocimiento.interimResults = false;

            reconocimiento.onstart = function () {
                microfonoActivo = true;
                botonMicrofono.classList.add(
                    "microfono-activo"
                );
                botonMicrofono.textContent = "🎤";
                botonMicrofono.title = "Escuchando...";
                botonMicrofono.setAttribute(
                    "aria-label",
                    "Escuchando"
                );
            };

            reconocimiento.onspeechstart = function () {
                botonMicrofono.classList.add("microfono-hablando");
            };

            reconocimiento.onspeechend = function () {
                botonMicrofono.classList.remove("microfono-hablando");
            };

            reconocimiento.onend = function () {
                microfonoActivo = false;
                botonMicrofono.classList.remove(
                    "microfono-activo",
                    "microfono-hablando"
                );
                botonMicrofono.textContent = "🎤";
                botonMicrofono.title = "Hablar";
                botonMicrofono.setAttribute(
                    "aria-label",
                    "Hablar con el chatbot"
                );
            };

            reconocimiento.onerror = function (evento) {
                microfonoActivo = false;
                botonMicrofono.classList.remove(
                    "microfono-activo",
                    "microfono-hablando"
                );
                botonMicrofono.textContent = "🎤";
                botonMicrofono.title = "Hablar";
                botonMicrofono.setAttribute(
                    "aria-label",
                    "Hablar con el chatbot"
                );

                if (evento.error === "not-allowed") {
                    responderConVoz(
                        "No se pudo acceder al micrófono. Verifica el permiso del navegador."
                    );
                } else if (evento.error === "audio-capture") {
                    responderConVoz(
                        "No se encontró un micrófono disponible. Puedes continuar utilizando el chat escrito."
                    );
                }
            };

            reconocimiento.onresult = function (evento) {
                const textoOriginal =
                    evento.results[evento.results.length - 1][0]
                        .transcript
                        .trim();
                entrada.value = textoOriginal;

                if (procesarComandoVoz(textoOriginal)) {
                    return;
                }

                enviarConsulta(textoOriginal);
            };

            botonMicrofono.addEventListener("click", function () {
                try {
                    reconocimiento.start();
                } catch (error) {
                    if (error.name !== "InvalidStateError") {
                        console.error("No fue posible iniciar el micrófono:", error);
                    }
                }
            });
        }
    }

    entrada.addEventListener(
        "focusin",
        function () {
            ajustarChatbotTeclado();
            activarExpansionMovilChatbot();
        }
    );

    entrada.addEventListener(
        "blur",
        function () {
            if (window.matchMedia("(max-width: 600px)").matches) {
                restaurarTamanoMovilChatbot();
            }
        }
    );

    if (window.visualViewport) {
        window.visualViewport.addEventListener(
            "resize",
            programarActualizacionViewport,
            { passive: true }
        );
    }

    actualizarAlturaChat();

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