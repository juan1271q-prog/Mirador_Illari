document.addEventListener("DOMContentLoaded", () => {
    let elementoAnterior = null;
    let objectUrlTemporalPreview = null;

    function limpiarObjectUrlTemporal() {
        if (objectUrlTemporalPreview) {
            URL.revokeObjectURL(objectUrlTemporalPreview);
            objectUrlTemporalPreview = null;
        }
    }

    function obtenerContenedorVistaPrevia() {
        const selectores = [
            ".field-vista_previa_imagen .readonly",
            ".field-vista_previa_imagen",
            ".field-imagen_preview .readonly",
            ".field-imagen_preview",
        ];

        for (const selector of selectores) {
            const contenedor = document.querySelector(selector);
            if (contenedor) {
                return contenedor;
            }
        }

        return null;
    }

    function crearEnlaceVistaPrevia(url) {
        const contenedor = obtenerContenedorVistaPrevia();

        if (!contenedor) {
            return null;
        }

        const esServicio = !!contenedor.closest(".field-vista_previa_imagen");

        let enlaceExistente = contenedor.querySelector(
            ".image-preview-toggle"
        );

        if (!enlaceExistente) {
            enlaceExistente = document.createElement("a");
            enlaceExistente.className = "image-preview-toggle";
            enlaceExistente.title = "Ver imagen en modal";
            enlaceExistente.setAttribute("aria-label", "Vista previa de la imagen");

            const imagenNueva = document.createElement("img");
            imagenNueva.alt = "Vista previa de la imagen";
            imagenNueva.style.maxWidth = esServicio ? "220px" : "200px";
            imagenNueva.style.maxHeight = esServicio ? "180px" : "120px";
            imagenNueva.style.objectFit = esServicio ? "contain" : "cover";
            imagenNueva.style.borderRadius = "10px";
            imagenNueva.style.display = "block";
            imagenNueva.style.verticalAlign = "middle";

            enlaceExistente.appendChild(imagenNueva);
            enlaceExistente.style.display = "inline-flex";
            enlaceExistente.style.alignItems = "center";
            enlaceExistente.style.marginLeft = "12px";

            contenedor.textContent = "";
            contenedor.appendChild(enlaceExistente);
        }

        return enlaceExistente;
    }

    function actualizarVistaPreviaArchivo(file) {
        if (!file || !file.type || !file.type.startsWith("image/")) {
            return;
        }

        const urlTemporal = URL.createObjectURL(file);
        limpiarObjectUrlTemporal();
        objectUrlTemporalPreview = urlTemporal;

        const enlaceVistaPrevia = crearEnlaceVistaPrevia(urlTemporal) || document.querySelector(
            '.image-preview-toggle[data-image-url]'
        );

        if (enlaceVistaPrevia) {
            enlaceVistaPrevia.href = urlTemporal;
            enlaceVistaPrevia.dataset.imageUrl = urlTemporal;

            const imagenPrevia = enlaceVistaPrevia.querySelector("img");
            if (imagenPrevia) {
                imagenPrevia.src = urlTemporal;
                imagenPrevia.alt = "Vista previa de la nueva imagen seleccionada";
            }
        }

        if (modal && modal.classList.contains("open")) {
            imagenModal.src = urlTemporal;
            imagenModal.alt = "Vista previa de la nueva imagen seleccionada";
        }
    }

    function crearModalImagen() {
        const modalExistente = document.getElementById(
            "image-preview-modal"
        );

        if (modalExistente) {
            return modalExistente;
        }

        const modal = document.createElement("div");

        modal.id = "image-preview-modal";
        modal.className = "image-preview-modal";
        modal.setAttribute("aria-hidden", "true");

        modal.innerHTML = `
            <div
                class="image-preview-backdrop"
                data-cerrar-imagen
            ></div>

            <div
                class="image-preview-content"
                role="dialog"
                aria-modal="true"
                aria-labelledby="image-preview-title"
            >
                <button
                    type="button"
                    class="image-preview-close"
                    aria-label="Cerrar imagen"
                    title="Cerrar"
                    data-cerrar-imagen
                >
                    ×
                </button>

                <h2
                    id="image-preview-title"
                    class="image-preview-title"
                >
                    Vista previa
                </h2>

                <img
                    id="image-preview-img"
                    class="image-preview-img"
                    src=""
                    alt=""
                >
            </div>
        `;

        document.body.appendChild(modal);

        return modal;
    }

    const modal = crearModalImagen();

    const imagenModal = modal.querySelector(
        "#image-preview-img"
    );

    const tituloModal = modal.querySelector(
        "#image-preview-title"
    );

    const botonCerrar = modal.querySelector(
        ".image-preview-close"
    );

    function esArchivoImagen(enlace) {
        if (!enlace) {
            return false;
        }

        try {
            const url = new URL(
                enlace.href,
                window.location.origin
            );

            return /\.(jpg|jpeg|png|gif|webp|bmp|svg)$/i.test(
                url.pathname
            );
        } catch (error) {
            return false;
        }
    }

    function abrirImagen(url, titulo) {
        if (!url) {
            return;
        }

        elementoAnterior = document.activeElement;

        imagenModal.src = url;
        imagenModal.alt = titulo || "Vista previa de imagen";
        tituloModal.textContent = titulo || "Vista previa";

        modal.classList.add("open");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("image-preview-open");

        botonCerrar.focus();
    }

    function cerrarImagen() {
        modal.classList.remove("open");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("image-preview-open");

        imagenModal.src = "";
        imagenModal.alt = "";

        if (
            elementoAnterior &&
            typeof elementoAnterior.focus === "function"
        ) {
            elementoAnterior.focus();
        }
    }

    const inputsImagen = [
        document.getElementById("id_imagen"),
        document.getElementById("id_imagen_principal"),
        document.querySelector('input[type="file"][name="imagen"]'),
        document.querySelector('input[type="file"][name="imagen_principal"]'),
    ].filter(Boolean);

    inputsImagen.forEach((inputImagen) => {
        inputImagen.addEventListener("change", (event) => {
            const archivo = event.target.files && event.target.files[0];

            if (!archivo || !archivo.type || !archivo.type.startsWith("image/")) {
                return;
            }

            actualizarVistaPreviaArchivo(archivo);
        });
    });

    document.body.addEventListener("click", (event) => {
        const botonVistaPrevia = event.target.closest(
            ".image-preview-toggle"
        );

        if (botonVistaPrevia) {
            event.preventDefault();

            abrirImagen(
                botonVistaPrevia.dataset.imageUrl ||
                    botonVistaPrevia.href,
                botonVistaPrevia.dataset.imageTitle ||
                    "Vista previa"
            );

            return;
        }

        const enlaceArchivo = event.target.closest(
            ".file-upload a"
        );

        if (
            enlaceArchivo &&
            esArchivoImagen(enlaceArchivo)
        ) {
            event.preventDefault();
            event.stopPropagation();

            abrirImagen(
                enlaceArchivo.href,
                enlaceArchivo.textContent.trim() ||
                    "Vista previa"
            );
        }
    });

    modal.addEventListener("click", (event) => {
        if (event.target.closest("[data-cerrar-imagen]")) {
            cerrarImagen();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (
            event.key === "Escape" &&
            modal.classList.contains("open")
        ) {
            cerrarImagen();
        }
    });
});
