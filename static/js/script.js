// script.js
// ============================================================
// TELEPROMPTER SQUAD 29
// FRONTEND — INTEGRAÇÃO COM FLASK + SOCKETIO
// ============================================================
//
// RESPONSABILIDADE:
// - conectar com o backend via SocketIO;
// - pedir início do motor;
// - receber o roteiro;
// - renderizar linhas na tela;
// - receber comandos de rolagem;
// - destacar a linha atual;
// - permitir avanço/retorno manual;
// - permitir pausa/retomada;
// - permitir troca de fonte;
// - permitir troca de tamanho;
// - permitir negrito, itálico e sublinhado;
// - permitir ajuste manual de rolagem;
// - manter funções visuais da interface.
// ============================================================


// ============================================================
// 1. CONEXÃO COM SOCKETIO
// ============================================================

const socket = io();


// ============================================================
// 2. ELEMENTOS DA TELA
// ============================================================

const editor = document.getElementById("editor");
const display = document.getElementById("display");

const topToolbar = document.getElementById("top-toolbar");
const mainToolbar = document.getElementById("main-toolbar");
const sidePanel = document.getElementById("side-speed-panel");
const btnRestore = document.getElementById("btn-restore");
const btnClose = document.getElementById("btn-close-toolbar");

const mirrorBtn = document.getElementById("mirrorBtn");
const mirrorBtnLocal = document.getElementById("mirrorBtnLocal");

const btnPlayLocal = document.getElementById("btn-play-local");

const btnPrev = document.getElementById("btn-prev");
const btnNext = document.getElementById("btn-next");
const btnPrevLocal = document.getElementById("btn-prev-local");
const btnNextLocal = document.getElementById("btn-next-local");

const fontName = document.getElementById("fontName");
const fontSize = document.getElementById("fontSize");

const btnBold = document.getElementById("btn-bold");
const btnItalic = document.getElementById("btn-italic");
const btnUnderline = document.getElementById("btn-underline");

const speedWheel = document.getElementById("speedWheel");

const btnOpenFile = document.getElementById("btn-open-file");
const btnSaveFile = document.getElementById("btn-save-file");
const fileInput = document.getElementById("file-input");

const btnUndo = document.getElementById("btn-undo");
const btnRedo = document.getElementById("btn-redo");


// ============================================================
// 3. ESTADO LOCAL DO FRONTEND
// ============================================================

let linhasRoteiro = [];
let indiceAtualVisual = 0;

let deslocamentoBase = 0;
let deslocamentoManual = 0;

let motorPausado = false;

let estiloTexto = {
    fonte: localStorage.getItem("tp_fonte") || "Segoe UI",
    tamanho: Number(localStorage.getItem("tp_tamanho") || 72),
    negrito: localStorage.getItem("tp_negrito") === "true",
    italico: localStorage.getItem("tp_italico") === "true",
    sublinhado: localStorage.getItem("tp_sublinhado") === "true",
    espelhado: localStorage.getItem("tp_espelhado") === "true"
};


// Canal para sincronizar estilo entre /comando e /tp.
let canal = null;

try {
    canal = new BroadcastChannel("tp_channel");
} catch (erro) {
    canal = null;
}


// ============================================================
// 4. FUNÇÕES BASE
// ============================================================

function obterContainerTexto() {
    if (editor) {
        return editor;
    }

    if (display) {
        return display;
    }

    return null;
}


function salvarPreferencias() {
    localStorage.setItem("tp_fonte", estiloTexto.fonte);
    localStorage.setItem("tp_tamanho", String(estiloTexto.tamanho));
    localStorage.setItem("tp_negrito", String(estiloTexto.negrito));
    localStorage.setItem("tp_italico", String(estiloTexto.italico));
    localStorage.setItem("tp_sublinhado", String(estiloTexto.sublinhado));
    localStorage.setItem("tp_espelhado", String(estiloTexto.espelhado));
}


function aplicarEstiloTexto() {
    const container = obterContainerTexto();

    if (!container) {
        return;
    }

    container.style.fontFamily = estiloTexto.fonte;
    container.style.fontSize = `${estiloTexto.tamanho}px`;
    container.style.fontWeight = estiloTexto.negrito ? "bold" : "normal";
    container.style.fontStyle = estiloTexto.italico ? "italic" : "normal";
    container.style.textDecoration = estiloTexto.sublinhado ? "underline" : "none";

    container.style.setProperty(
        "--tp-scale-x",
        estiloTexto.espelhado ? "-1" : "1"
    );

    if (fontName) {
        fontName.value = estiloTexto.fonte;
    }

    if (fontSize) {
        fontSize.value = String(estiloTexto.tamanho);
    }

    if (btnBold) {
        btnBold.classList.toggle("active-format", estiloTexto.negrito);
    }

    if (btnItalic) {
        btnItalic.classList.toggle("active-format", estiloTexto.italico);
    }

    if (btnUnderline) {
        btnUnderline.classList.toggle("active-format", estiloTexto.sublinhado);
    }

    if (mirrorBtn) {
        mirrorBtn.classList.toggle("active", estiloTexto.espelhado);
    }

    if (mirrorBtnLocal) {
        mirrorBtnLocal.classList.toggle("active", estiloTexto.espelhado);
    }

    aplicarTransformacao();
}


function publicarEstilo() {
    salvarPreferencias();

    if (canal) {
        canal.postMessage({
            tipo: "estilo",
            estilo: estiloTexto
        });
    }
}


function aplicarTransformacao() {
    const container = obterContainerTexto();

    if (!container) {
        return;
    }

    const deslocamentoTotal = deslocamentoBase + deslocamentoManual;

    container.style.setProperty(
        "--tp-offset-y",
        `${deslocamentoTotal}px`
    );

    container.style.setProperty(
        "--tp-scale-x",
        estiloTexto.espelhado ? "-1" : "1"
    );
}


// ============================================================
// 5. RENDERIZAÇÃO DO ROTEIRO
// ============================================================

function renderizarRoteiro(linhas) {
    const container = obterContainerTexto();

    if (!container) {
        return;
    }

    container.innerHTML = "";

    linhas.forEach((linha, indice) => {
        const divLinha = document.createElement("div");

        divLinha.classList.add("linha-roteiro");
        divLinha.dataset.index = indice;
        divLinha.textContent = linha;

        container.appendChild(divLinha);
    });

    aplicarEstiloTexto();
}


function destacarLinha(indice) {
    const container = obterContainerTexto();

    if (!container) {
        return;
    }

    const linhas = container.querySelectorAll(".linha-roteiro");

    linhas.forEach((linha) => {
        linha.classList.remove("linha-atual");
    });

    const linhaAtual = container.querySelector(
        `.linha-roteiro[data-index="${indice}"]`
    );

    if (!linhaAtual) {
        return;
    }

    linhaAtual.classList.add("linha-atual");

    const area = container.parentElement;

    if (!area) {
        return;
    }

    const posicaoLinha = linhaAtual.offsetTop;
    const alturaLinha = linhaAtual.clientHeight;
    const centroArea = area.clientHeight / 2;

    deslocamentoBase = centroArea - posicaoLinha - (alturaLinha / 2);

    aplicarTransformacao();

    console.log("Linha destacada no frontend:", indice);
}


function sincronizarTeleprompter(indice) {
    indiceAtualVisual = indice;
    destacarLinha(indiceAtualVisual);
}


// ============================================================
// 6. EVENTOS RECEBIDOS DO BACKEND
// ============================================================

socket.on("connect", () => {
    console.log("Frontend conectado ao backend SocketIO.");

    // Pede explicitamente para o backend iniciar o motor.
    socket.emit("iniciar_motor");
});


socket.on("roteiro", (dados) => {
    console.log("Roteiro recebido:", dados);

    linhasRoteiro = dados.linhas || [];
    indiceAtualVisual = dados.indiceAtual || 0;

    renderizarRoteiro(linhasRoteiro);
    sincronizarTeleprompter(indiceAtualVisual);
});


socket.on("cmd", (dados) => {
    console.log("Comando recebido:", dados);

    if (typeof dados.index === "number") {
        sincronizarTeleprompter(dados.index);
    }
});


socket.on("status_motor", (dados) => {
    console.log("Status do motor:", dados);

    motorPausado = dados.estado === "PAUSADO";

    if (btnPlayLocal) {
        btnPlayLocal.classList.toggle("active-format", motorPausado);
    }
});


// ============================================================
// 7. COMANDOS MANUAIS DO FRONTEND
// ============================================================

function enviarAvancoManual() {
    socket.emit("manual_next");
}


function enviarRetornoManual() {
    socket.emit("manual_prev");
}


function alternarPausaMotor() {
    socket.emit("alternar_pausa");
}


if (btnNext) {
    btnNext.addEventListener("click", enviarAvancoManual);
}


if (btnPrev) {
    btnPrev.addEventListener("click", enviarRetornoManual);
}


if (btnNextLocal) {
    btnNextLocal.addEventListener("click", enviarAvancoManual);
}


if (btnPrevLocal) {
    btnPrevLocal.addEventListener("click", enviarRetornoManual);
}


if (btnPlayLocal) {
    btnPlayLocal.addEventListener("click", alternarPausaMotor);
}


// Teclado para controle manual.
document.addEventListener("keydown", (evento) => {
    if (evento.key === "ArrowDown") {
        evento.preventDefault();
        enviarAvancoManual();
    }

    if (evento.key === "ArrowUp") {
        evento.preventDefault();
        enviarRetornoManual();
    }

    if (evento.code === "Space") {
        evento.preventDefault();
        alternarPausaMotor();
    }
});


// ============================================================
// 8. FONTE, TAMANHO E FORMATAÇÃO
// ============================================================

if (fontName) {
    fontName.addEventListener("change", () => {
        estiloTexto.fonte = fontName.value;
        aplicarEstiloTexto();
        publicarEstilo();
    });
}


if (fontSize) {
    fontSize.addEventListener("change", () => {
        estiloTexto.tamanho = Number(fontSize.value);
        aplicarEstiloTexto();
        publicarEstilo();
        sincronizarTeleprompter(indiceAtualVisual);
    });
}


if (btnBold) {
    btnBold.addEventListener("click", () => {
        estiloTexto.negrito = !estiloTexto.negrito;
        aplicarEstiloTexto();
        publicarEstilo();
    });
}


if (btnItalic) {
    btnItalic.addEventListener("click", () => {
        estiloTexto.italico = !estiloTexto.italico;
        aplicarEstiloTexto();
        publicarEstilo();
    });
}


if (btnUnderline) {
    btnUnderline.addEventListener("click", () => {
        estiloTexto.sublinhado = !estiloTexto.sublinhado;
        aplicarEstiloTexto();
        publicarEstilo();
    });
}


// ============================================================
// 9. ESPELHAMENTO DA TELA
// ============================================================

function alternarEspelhamento() {
    estiloTexto.espelhado = !estiloTexto.espelhado;

    aplicarEstiloTexto();
    publicarEstilo();
}


if (mirrorBtn) {
    mirrorBtn.addEventListener("click", alternarEspelhamento);
}


if (mirrorBtnLocal) {
    mirrorBtnLocal.addEventListener("click", alternarEspelhamento);
}


// ============================================================
// 10. AJUSTE MANUAL DE ROLAGEM PELO SLIDER
// ============================================================

if (speedWheel) {
    speedWheel.addEventListener("input", () => {
        const valor = Number(speedWheel.value);

        // Valor negativo sobe o texto; valor positivo desce.
        deslocamentoManual = valor * -35;

        aplicarTransformacao();
    });

    speedWheel.addEventListener("change", () => {
        // Mantém o slider centralizado depois do ajuste.
        speedWheel.value = 0;
    });
}


// ============================================================
// 11. ABRIR E SALVAR ROTEIRO LOCALMENTE NO FRONT
// ============================================================

if (btnOpenFile && fileInput) {
    btnOpenFile.addEventListener("click", () => {
        fileInput.click();
    });
}


if (fileInput) {
    fileInput.addEventListener("change", async () => {
        const arquivo = fileInput.files[0];

        if (!arquivo) {
            return;
        }

        const texto = await arquivo.text();

        const container = obterContainerTexto();

        if (container) {
            container.innerText = texto;
        }
    });
}


if (btnSaveFile) {
    btnSaveFile.addEventListener("click", () => {
        const container = obterContainerTexto();

        if (!container) {
            return;
        }

        const conteudo = container.innerText;
        const blob = new Blob([conteudo], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");
        link.href = url;
        link.download = "roteiro_teleprompter.txt";
        link.click();

        URL.revokeObjectURL(url);
    });
}


// ============================================================
// 12. DESFAZER / REFAZER SIMPLES
// ============================================================

if (btnUndo) {
    btnUndo.addEventListener("click", () => {
        document.execCommand("undo");
    });
}


if (btnRedo) {
    btnRedo.addEventListener("click", () => {
        document.execCommand("redo");
    });
}


// ============================================================
// 13. OCULTAR / MOSTRAR BARRA DE COMANDOS
// ============================================================

if (btnClose) {
    btnClose.onclick = () => {
        if (topToolbar) {
            topToolbar.classList.add("toolbar-hidden");
        }

        if (mainToolbar) {
            mainToolbar.classList.add("toolbar-hidden");
        }

        if (sidePanel) {
            sidePanel.classList.add("hidden");
        }

        if (btnRestore) {
            btnRestore.classList.remove("hidden");
        }
    };
}


if (btnRestore) {
    btnRestore.onclick = () => {
        if (topToolbar) {
            topToolbar.classList.remove("toolbar-hidden");
        }

        if (mainToolbar) {
            mainToolbar.classList.remove("toolbar-hidden");
        }

        if (sidePanel) {
            sidePanel.classList.remove("hidden");
        }

        btnRestore.classList.add("hidden");
    };
}


// ============================================================
// 14. SINCRONIZAÇÃO ENTRE ABAS
// ============================================================

if (canal) {
    canal.onmessage = (evento) => {
        const dados = evento.data;

        if (!dados || dados.tipo !== "estilo") {
            return;
        }

        estiloTexto = {
            ...estiloTexto,
            ...dados.estilo
        };

        aplicarEstiloTexto();
    };
}


// ============================================================
// 15. INICIALIZAÇÃO LOCAL
// ============================================================

aplicarEstiloTexto();