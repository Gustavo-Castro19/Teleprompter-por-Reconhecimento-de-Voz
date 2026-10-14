// ============================================================
// TELEPROMPTER SQUAD 29 - FRONTEND (HYBRID SPEECH)
// ============================================================
// Reconhecimento híbrido:
//  1. Web Speech API (primário, no navegador) - online
//  2. Vosk (fallback, no servidor via WebSocket) - offline
//
// Events SocketIO novos:
//   speech_start {mode, language}  → inicia sessão
//   speech_stop {}                 → para sessão
//   speech_result {text, isFinal, source, confidence}  ← enviado pelo frontend
//   speech_audio {audio: base64}                     ← enviado pelo frontend (chunk Vosk)
//   speech_ready {mode, ready}        ← recebido do backend
//   speech_error {error, fallback}    ← recebido do backend
// ============================================================

const socket = io();

// === Elementos principais ===
const editor = document.getElementById("editor");
const display = document.getElementById("display");
const mainToolbar = document.getElementById("main-toolbar") || document.getElementById("top-toolbar");
const sidePanel = document.getElementById("side-speed-panel");
const btnRestore = document.getElementById("btn-restore");
const btnClose = document.getElementById("btn-close-toolbar");

const mirrorBtn =
    document.getElementById("invertBtn") ||
    document.getElementById("mirrorBtn") ||
    document.getElementById("mirrorBtnLocal");

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

const btnPrev =
    document.getElementById("btn-prev") ||
    document.getElementById("btn-prev-local");

const btnNext =
    document.getElementById("btn-next") ||
    document.getElementById("btn-next-local");

const btnPlayLocal = document.getElementById("btn-play-local");
const scrollToggleBtn = document.getElementById("scrollToggleBtn");

const winplusToggleBtn =
    document.getElementById("winplusToggleBtn") ||
    document.getElementById("btn-winplus-toggle");

const appBody = document.getElementById("app-body");

// === Estado local ===
let linhasRoteiro = [];
let indiceAtualVisual = 0;
let segmentosRoteiro = [];
let metadadosLinhas = [];
let configuracaoRolagem = null;

let deslocamentoBaseEditor = 0;
let deslocamentoBaseDisplay = 0;
let alvoDeslocamentoBaseEditor = 0;
let alvoDeslocamentoBaseDisplay = 0;
let suavidadeSincronizacao = 0.10;
let deslocamentoManual = 0;
let motorPausado = true;

const PONTO_LEITURA_DISPLAY = 0.51;
const PONTO_LEITURA_EDITOR_TELA_CHEIA = 0.50;
const PONTO_LEITURA_EDITOR_DIVIDIDO = 0.50;

const FATOR_ROLAGEM_EDITOR = 1;
const FATOR_ROLAGEM_DISPLAY = 1;

let rolagemContinuaAtiva = false;
let fatorManualVelocidade = Number(localStorage.getItem("tp_velocidade") || 1);
let ultimoFrame = null;
let posicaoRolagemContinua = 0;
let comandoManualPendente = false;
let suavizandoPorFala = false;

let rolagemBloqueadaPorSistema = false;
let motivoBloqueioRolagem = "";
let pausaTecnicaAte = 0;

let estadoVozAtual = "aguardando";
let ultimoMatchVozMs = Date.now();
let velocidadeVozFatorAtual = 1.0;
let velocidadeVozFatorAlvo = 1.0;
let rolagemInterrompidaManualmente = false;

const TEMPO_SEM_MATCH_IMPROVISO_MS = 2200;
const SUAUIDADE_VELOCIDADE_VOZ = 0.08;

let tempoInicioLinhaAtual = null;
let duracaoLinhaAtualMs = 0;

let estiloTexto = {
    fonte: localStorage.getItem("tp_fonte") || "Segoe UI",
    tamanho: Number(localStorage.getItem("tp_tamanho") || 72),
    negrito: localStorage.getItem("tp_negrito") === "true",
    italico: localStorage.getItem("tp_italico") === "true",
    sublinhado: localStorage.getItem("tp_sublinhado") === "true",
    espelhado: localStorage.getItem("tp_espelhado") === "true"
};

let canal = null;
try { canal = new BroadcastChannel("tp_channel"); } catch (e) { canal = null; }

// ============================================================
// Hybrid Speech Recognition (Web Speech API + Vosk fallback)
// ============================================================

const SPEECH_MODE = {
    WEB: "web",
    VOSK: "vosk",
};

let speechMode = SPEECH_MODE.WEB;
let speechRecognition = null;
let speechRecognitionSupported = false;
let speechReady = false;
let mediaStream = null;
let mediaRecorder = null;
let mediaRecorderChunks = [];
let isSpeaking = false;

// Check Web Speech API availability
if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
    speechRecognitionSupported = true;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    speechRecognition = new SpeechRecognition();
    speechRecognition.continuous = true;
    speechRecognition.interimResults = true;
    speechRecognition.lang = "pt-BR";
}

// Web Speech API event handlers
if (speechRecognition) {
    speechRecognition.onresult = (event) => {
        let interimTranscript = "";
        let finalTranscript = "";

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            const confidence = event.results[i][0].confidence || 0;

            if (event.results[i].isFinal) {
                finalTranscript += transcript;
                socket.emit("speech_result", {
                    text: finalTranscript,
                    isFinal: true,
                    source: "web",
                    confidence: confidence,
                });
            } else {
                interimTranscript += transcript;
                socket.emit("speech_result", {
                    text: interimTranscript,
                    isFinal: false,
                    source: "web",
                    confidence: 0,
                });
            }
        }

        console.log("Web Speech result:", interimTranscript || finalTranscript);
    };

    speechRecognition.onerror = (event) => {
        console.error("Web Speech error:", event.error, event.message);

        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
            console.warn("Web Speech permission denied - switching to Vosk fallback");
            switchToVoskMode();
            return;
        }

        // Restart recognition if server error
        if (event.error === "network" || event.error === "server-error") {
            console.warn("Web Speech network error - trying restart");
            setTimeout(() => {
                if (isSpeaking) reconnectSpeech();
            }, 1000);
        }
    };

    speechRecognition.onend = () => {
        console.log("Web Speech recognition ended");
        if (isSpeaking && speechMode === SPEECH_MODE.WEB) {
            // Auto-restart if still active
            setTimeout(() => {
                if (isSpeaking) reconnectSpeech();
            }, 50);
        }
    };
}

function startWebSpeech() {
    if (!speechRecognitionSupported) {
        console.warn("Web Speech not supported - falling back to Vosk");
        switchToVoskMode();
        return false;
    }

    try {
        socket.emit("speech_start", { mode: "web", language: "pt-BR" });
        speechRecognition.start();
        isSpeaking = true;
        console.log("Web Speech recognition started");
        return true;
    } catch (e) {
        console.error("Failed to start Web Speech:", e);
        return false;
    }
}

function stopWebSpeech() {
    isSpeaking = false;
    try {
        if (speechRecognition) {
            speechRecognition.stop();
        }
    } catch (e) {
        console.error("Failed to stop Web Speech:", e);
    }
    socket.emit("speech_stop");
}

function reconnectSpeech() {
    if (speechMode === SPEECH_MODE.WEB && speechRecognition) {
        try {
            speechRecognition.stop();
        } catch (e) {
            // ignore
        }
        setTimeout(() => {
            if (isSpeaking) {
                try {
                    speechRecognition.start();
                } catch (e) {
                    console.error("Failed to restart Web Speech:", e);
                }
            }
        }, 50);
    }
}

// === Vosk fallback (audio stream to server) ===

function switchToVoskMode() {
    if (speechMode === SPEECH_MODE.VOSK) return; // Already in Vosk mode
    console.warn("Switching to Vosk fallback mode");

    // Stop Web Speech
    isSpeaking = false;
    try {
        if (speechRecognition) speechRecognition.stop();
    } catch (e) {
        // ignore
    }

    speechMode = SPEECH_MODE.VOSK;
    socket.emit("speech_start", { mode: "vosk", language: "pt-BR" });

    // Request microphone access for Vosk fallback
    navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then((stream) => {
            mediaStream = stream;
            mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    const reader = new FileReader();
                    reader.onload = () => {
                        const base64Audio = reader.result.split(",")[1];
                        socket.emit("speech_audio", { audio: base64Audio });
                    };
                    reader.readAsDataURL(event.data);
                }
            };
            mediaRecorder.onstart = () => {
                console.log("Vosk audio recording started");
                isSpeaking = true;
            };
            mediaRecorder.onstop = () => {
                console.log("Vosk audio recording stopped");
            };
            showVoskToast("Modo offline Vosk ativado");
            startVoskRecording();
        })
        .catch((err) => {
            console.error("Failed to get microphone:", err);
            showVoskToast("Erro ao acessar microfone para Vosk");
        });
}

function startVoskRecording() {
    if (!mediaRecorder || mediaRecorder.state === "recording") return;
    mediaRecorder.start(500); // Capture 500ms chunks
    isSpeaking = true;
}

function stopVoskRecording() {
    isSpeaking = false;
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
    }
    if (mediaStream) {
        mediaStream.getTracks().forEach((track) => track.stop());
        mediaStream = null;
        mediaRecorder = null;
    }
    socket.emit("speech_stop");
}

function showVoskToast(msg) {
    if (typeof mostrarToast === "function") {
        mostrarToast(msg, "info");
    } else {
        console.log(msg);
    }
}

// Handle speech ready/error from backend
socket.on("speech_ready", (dados) => {
    console.log("Speech ready:", dados);
    speechReady = true;
});

socket.on("speech_error", (dados) => {
    console.warn("Speech error from backend:", dados);
    if (dados.fallback) {
        // Backend Vosk not available - switch back to Web speech
        speechMode = SPEECH_MODE.WEB;
        showVoskToast(dados.error || "Vosk indisponível");
    }
});

// Public interface
function startSpeechRecognition() {
    if (speechRecognitionSupported) {
        speechMode = SPEECH_MODE.WEB;
        return startWebSpeech();
    } else {
        speechMode = SPEECH_MODE.VOSK;
        socket.emit("speech_start", { mode: "vosk", language: "pt-BR" });
        return false; // Vosk recording needs separate start
    }
}

function stopSpeechRecognition() {
    if (speechMode === SPEECH_MODE.WEB) {
        stopWebSpeech();
    } else {
        stopVoskRecording();
    }
}

// Auto-start speech when motor starts
socket.on("iniciar_motor", () => {
    // handled separately
});

// ============================================================
// Utilitários e scroll (mantém funções do script.js original)
// ============================================================

function obterContainerTexto() {
    if (appBody && appBody.classList.contains("winplus-active")) {
        return display || editor;
    }
    return editor || display;
}

function obterContainersTexto() {
    return [editor, display].filter(Boolean);
}

function salvarPreferencias() {
    localStorage.setItem("tp_fonte", estiloTexto.fonte);
    localStorage.setItem("tp_tamanho", String(estiloTexto.tamanho));
    localStorage.setItem("tp_negrito", String(estiloTexto.negrito));
    localStorage.setItem("tp_italico", String(estiloTexto.italico));
    localStorage.setItem("tp_sublinhado", String(estiloTexto.sublinhado));
    localStorage.setItem("tp_espelhado", String(estiloTexto.espelhado));
}

function publicarEstilo() {
    salvarPreferencias();
    if (canal) canal.postMessage({ tipo: "estilo", estilo: estiloTexto });
}

function aplicarEstiloTexto() {
    obterContainersTexto().forEach(container => {
        container.style.fontFamily = estiloTexto.fonte;
        if (container === editor) container.style.fontSize = `${estiloTexto.tamanho}px`;
        container.style.fontWeight = estiloTexto.negrito ? "bold" : "normal";
        container.style.fontStyle = estiloTexto.italico ? "italic" : "normal";
        container.style.textDecoration = estiloTexto.sublinhado ? "underline" : "none";
        container.style.setProperty("--tp-scale-x", estiloTexto.espelhado ? "-1" : "1");
    });
    if (fontName) fontName.value = estiloTexto.fonte;
    if (fontSize) fontSize.value = String(estiloTexto.tamanho);
    if (btnBold) btnBold.classList.toggle("active-format", estiloTexto.negrito);
    if (btnItalic) btnItalic.classList.toggle("active-format", estiloTexto.italico);
    if (btnUnderline) btnUnderline.classList.toggle("active-format", estiloTexto.sublinhado);
    if (mirrorBtn) mirrorBtn.classList.toggle("active", estiloTexto.espelhado);
    aplicarTransformacao();
    if (typeof indiceAtualVisual !== "undefined") destacarLinha(indiceAtualVisual);
}

function obterPontoLeitura(container) {
    if (container === display) return PONTO_LEITURA_DISPLAY;
    if (appBody && appBody.classList.contains("winplus-active")) return PONTO_LEITURA_EDITOR_DIVIDIDO;
    return PONTO_LEITURA_EDITOR_TELA_CHEIA;
}

function aplicarTransformacao() {
    obterContainersTexto().forEach(container => {
        const deslocamentoBaseContainer = container === editor ? deslocamentoBaseEditor : deslocamentoBaseDisplay;
        const fatorRolagem = container === display ? FATOR_ROLAGEM_DISPLAY : FATOR_ROLAGEM_EDITOR;
        const deslocamentoTotal = deslocamentoBaseContainer + deslocamentoManual + (posicaoRolagemContinua * fatorRolagem);
        container.style.setProperty("--tp-offset-y", `${deslocamentoTotal}px`);
        container.style.setProperty("--tp-scale-x", estiloTexto.espelhado ? "-1" : "1");
    });
}

function resetarDeslocamentosVisuais() {
    deslocamentoManual = 0;
    posicaoRolagemContinua = 0;
    ultimoFrame = null;
    aplicarTransformacao();
}

// Metadados
function obterMetaLinhaVisual(indiceVisual) {
    return metadadosLinhas.find(meta => meta.indiceVisual === indiceVisual) || null;
}
function obterSegmentoPorVisual(indiceVisual) {
    return segmentosRoteiro.find(seg => seg.indiceVisual === indiceVisual) || null;
}
function obterDuracaoLinhaAtualSegundos() {
    const segmento = obterSegmentoPorVisual(indiceAtualVisual);
    const meta = obterMetaLinhaVisual(indiceAtualVisual);
    if (segmento && Number(segmento.tempoEstimadoSegundos) > 0) return Number(segmento.tempoEstimadoSegundos);
    if (meta && Number(meta.duracaoSegundos) > 0) return Number(meta.duracaoSegundos);
    return 2.0;
}

function obterDistanciaAteProximaLinha(container) {
    if (!container) return 80;
    const linhaAtual = container.querySelector(`.linha-roteiro[data-index="${indiceAtualVisual}"], .comentario[data-index="${indiceAtualVisual}"]`);
    const proximaLinha = container.querySelector(`.linha-roteiro[data-index="${indiceAtualVisual + 1}"], .comentario[data-index="${indiceAtualVisual + 1}"]`);
    if (linhaAtual && proximaLinha) {
        const distancia = Math.abs(proximaLinha.offsetTop - linhaAtual.offsetTop);
        return Math.max(distancia, 40);
    }
    if (linhaAtual) return Math.max(linhaAtual.clientHeight + 18, 40);
    return 80;
}

function calcularVelocidadePxPorMs() {
    const container = obterContainerTexto();
    const duracaoSegundos = obterDuracaoLinhaAtualSegundos();
    const distanciaPx = obterDistanciaAteProximaLinha(container);
    const velocidadeBase = distanciaPx / Math.max(duracaoSegundos * 1000, 1);
    return velocidadeBase * fatorManualVelocidade * velocidadeVozFatorAtual;
}

function iniciarTemporizadorDaLinha() {
    tempoInicioLinhaAtual = performance.now();
    duracaoLinhaAtualMs = obterDuracaoLinhaAtualSegundos() * 1000;
}

function iniciarPausaTecnica(segundos, motivo) {
    const duracao = Number(segundos || 0);
    if (duracao <= 0) return;
    rolagemBloqueadaPorSistema = true;
    motivoBloqueioRolagem = motivo || "Pausa técnica";
    pausaTecnicaAte = performance.now() + (duracao * 1000);
    console.log(`Rolagem pausada por ${duracao}s. Motivo: ${motivoBloqueioRolagem}`);
}

function verificarFimPausaTecnica(timestamp) {
    if (!rolagemBloqueadaPorSistema) return;
    if (motivoBloqueioRolagem === "IMPROVISO") return;
    if (pausaTecnicaAte > 0 && timestamp >= pausaTecnicaAte) {
        rolagemBloqueadaPorSistema = false;
        motivoBloqueioRolagem = "";
        pausaTecnicaAte = 0;
        console.log("Pausa técnica encerrada. Rolagem liberada.");
    }
}

// Renderização
function renderizarRoteiro(linhas) {
    obterContainersTexto().forEach(container => {
        container.innerHTML = "";
        linhas.forEach((linha, indice) => {
            const texto = String(linha || "").trim();
            const meta = obterMetaLinhaVisual(indice);
            const divLinha = document.createElement("div");
            if (
                (meta && (meta.tipoLinha === "tecnico" || meta.tipoLinha === "pausa_tecnica" || meta.tipoLinha === "separador")) ||
                (texto.startsWith("{{") && texto.endsWith("}}"))
            ) {
                divLinha.classList.add("comentario");
            } else {
                divLinha.classList.add("linha-roteiro");
            }
            divLinha.classList.add("linha-roteiro");
            divLinha.dataset.index = indice;
            if (meta) {
                divLinha.dataset.tipoLinha = meta.tipoLinha || "fala";
                divLinha.dataset.duracao = meta.duracaoSegundos || 0;
                divLinha.dataset.pausa = meta.pausaTecnicaSegundos || 0;
                divLinha.dataset.titulo = meta.titulo || "";
            }
            divLinha.textContent = texto;
            container.appendChild(divLinha);
        });
    });
    aplicarEstiloTexto();
}

function destacarLinha(indice) {
    obterContainersTexto().forEach(container => {
        const linhas = container.querySelectorAll(".linha-roteiro, .comentario");
        linhas.forEach(linha => linha.classList.remove("linha-atual"));
        const linhaAtual = container.querySelector(
            `.linha-roteiro[data-index="${indice}"], .comentario[data-index="${indice}"]`
        );
        if (!linhaAtual) return;
        linhaAtual.classList.add("linha-atual");
        const area = container.parentElement;
        if (!area) return;
        const posicaoLinha = linhaAtual.offsetTop;
        const alturaLinha = linhaAtual.clientHeight;
        const pontoLeitura = area.clientHeight * obterPontoLeitura(container);
        const novoDeslocamentoBase = pontoLeitura - posicaoLinha - (alturaLinha / 2);
        if (container === editor) {
            alvoDeslocamentoBaseEditor = novoDeslocamentoBase;
        } else {
            alvoDeslocamentoBaseDisplay = novoDeslocamentoBase;
        }
    });
    aplicarTransformacao();
}

function sincronizarTeleprompter(indice, opcoes = {}) {
    indiceAtualVisual = indice;
    const preservarRolagem = opcoes.preservarRolagem === true;
    if (!preservarRolagem) posicaoRolagemContinua = 0;
    destacarLinha(indiceAtualVisual);
    if (!preservarRolagem) {
        velocidadeVozFatorAlvo = 1.0;
        iniciarTemporizadorDaLinha();
    }
}

function sincronizarTeleprompterImediato(indice) {
    indiceAtualVisual = indice;
    posicaoRolagemContinua = 0;
    deslocamentoManual = 0;
    ultimoFrame = null;
    destacarLinha(indiceAtualVisual);
    deslocamentoBaseEditor = alvoDeslocamentoBaseEditor;
    deslocamentoBaseDisplay = alvoDeslocamentoBaseDisplay;
    aplicarTransformacao();
    iniciarTemporizadorDaLinha();
}

function absorverRolagemContinuaNaBase() {
    deslocamentoBaseEditor += posicaoRolagemContinua * FATOR_ROLAGEM_EDITOR;
    deslocamentoBaseDisplay += posicaoRolagemContinua * FATOR_ROLAGEM_DISPLAY;
    alvoDeslocamentoBaseEditor += posicaoRolagemContinua * FATOR_ROLAGEM_EDITOR;
    alvoDeslocamentoBaseDisplay += posicaoRolagemContinua * FATOR_ROLAGEM_DISPLAY;
    posicaoRolagemContinua = 0;
    deslocamentoManual = 0;
    ultimoFrame = null;
}

// ============================================================
// Voz assistida
// ============================================================

function calcularFatorDeVoz(dados) {
    const progresso = Number(dados.progressoEstimado || 0);
    const score = Number(dados.score || 0);
    if (!tempoInicioLinhaAtual) return 1.0;
    const duracaoSegundos = obterDuracaoLinhaAtualSegundos();
    if (duracaoSegundos <= 0) return 1.0;
    const tempoDecorrido = (performance.now() - tempoInicioLinhaAtual) / 1000;
    const progressoEsperado = Math.max(0, Math.min(tempoDecorrido / duracaoSegundos, 1));
    const diferenca = progresso - progressoEsperado;
    if (score < 0.40) return 0.45;
    if (diferenca >= 0.25) return 1.45;
    if (diferenca >= 0.12) return 1.25;
    if (diferenca <= -0.25) return 0.45;
    if (diferenca <= -0.12) return 0.70;
    return 1.0;
}

function ativarRolagemPorVozSePossivel() {
    if (rolagemInterrompidaManualmente) return;
    if (!rolagemContinuaAtiva) {
        rolagemContinuaAtiva = true;
        atualizarTextoBotaoRolagem();
    }
}

function pausarRolagemPorImproviso() {
    rolagemBloqueadaPorSistema = true;
    motivoBloqueioRolagem = "IMPROVISO";
    pausaTecnicaAte = 0;
    velocidadeVozFatorAlvo = 0;
}

function liberarRolagemPorRetornoAoRoteiro() {
    if (motivoBloqueioRolagem === "IMPROVISO") {
        rolagemBloqueadaPorSistema = false;
        motivoBloqueioRolagem = "";
        pausaTecnicaAte = 0;
    }
    ativarRolagemPorVozSePossivel();
}

function podeRolarAgora() {
    if (!rolagemContinuaAtiva) return false;
    if (motorPausado) return false;
    if (rolagemBloqueadaPorSistema) return false;
    return true;
}

function atualizarTextoBotaoRolagem() {
    if (!scrollToggleBtn) return;
    if (rolagemContinuaAtiva) {
        scrollToggleBtn.textContent = "⏸ PAUSAR ROLAGEM";
        scrollToggleBtn.classList.add("active");
    } else {
        scrollToggleBtn.textContent = "▶ INICIAR ROLAGEM";
        scrollToggleBtn.classList.remove("active");
    }
}

function pararRolagemContinua() {
    rolagemContinuaAtiva = false;
    rolagemInterrompidaManualmente = true;
    velocidadeVozFatorAlvo = 0;
    velocidadeVozFatorAtual = 0;
    ultimoFrame = null;
    atualizarTextoBotaoRolagem();
}

function animarRolagemContinua(timestamp) {
    if (ultimoFrame === null) ultimoFrame = timestamp;
    const delta = timestamp - ultimoFrame;
    ultimoFrame = timestamp;
    deslocamentoBaseEditor += (alvoDeslocamentoBaseEditor - deslocamentoBaseEditor) * suavidadeSincronizacao;
    deslocamentoBaseDisplay += (alvoDeslocamentoBaseDisplay - deslocamentoBaseDisplay) * suavidadeSincronizacao;
    verificarFimPausaTecnica(timestamp);
    velocidadeVozFatorAtual += (velocidadeVozFatorAlvo - velocidadeVozFatorAtual) * 0.08;
    const distanciaEditor = Math.abs(alvoDeslocamentoBaseEditor - deslocamentoBaseEditor);
    const distanciaDisplay = Math.abs(alvoDeslocamentoBaseDisplay - deslocamentoBaseDisplay);
    const aindaCorrigindoPosicao = distanciaEditor > 2 || distanciaDisplay > 2;
    if (podeRolarAgora() && !aindaCorrigindoPosicao) {
        const velocidadePxPorMs = calcularVelocidadePxPorMs();
        posicaoRolagemContinua -= velocidadePxPorMs * delta;
    }
    aplicarTransformacao();
    requestAnimationFrame(animarRolagemContinua);
}

function iniciarPausaTecnicaPorEstado(tipo, motivo, pausaSegundos, estadoVoz) { /* alias */ }

// ============================================================
// Eventos SocketIO
// ============================================================

socket.on("connect", () => {
    console.log("Frontend conectado ao backend SocketIO.");
    console.log("ID da conexão:", socket.id);
    socket.emit("iniciar_motor");
    socket.emit("solicitar_config_rolagem");
    console.log("Eventos enviados.");
});

socket.on("roteiro", (dados) => {
    console.log("Roteiro recebido do backend:", dados);
    linhasRoteiro = dados.linhas || [];
    segmentosRoteiro = dados.segmentos || [];
    metadadosLinhas = dados.metadadosLinhas || [];
    configuracaoRolagem = dados.configRolagem || null;
    indiceAtualVisual = dados.indiceAtual || 0;
    renderizarRoteiro(linhasRoteiro);
    requestAnimationFrame(() => sincronizarTeleprompterImediato(indiceAtualVisual));
});

socket.on("config_rolagem", (dados) => {
    configuracaoRolagem = dados;
    console.log("Configuração de rolagem recebida:", dados);
});

socket.on("cmd", (dados) => {
    console.log("Comando de rolagem recebido:", dados);
    if (typeof dados.index === "number") {
        absorverRolagemContinuaNaBase();
        sincronizarTeleprompter(dados.index);
    }
    if (Number(dados.pausaAposSegundos) > 0) {
        iniciarPausaTecnica(Number(dados.pausaAposSegundos), dados.motivoPausa || "Pausa técnica após fala");
    }
});

socket.on("voz_roteiro", (dados) => {
    console.log("Andamento da voz recebido:", dados);
    if (!dados) return;
    estadoVozAtual = dados.estadoVoz || "aguardando";
    if (estadoVozAtual === "acompanhando" || estadoVozAtual === "retomou") {
        ultimoMatchVozMs = Date.now();
        if (estadoVozAtual === "retomou") {
            liberarRolagemPorRetornoAoRoteiro();
        } else if (!rolagemBloqueadaPorSistema) {
            ativarRolagemPorVozSePossivel();
        }
        velocidadeVozFatorAlvo = calcularFatorDeVoz(dados);
        console.log("Fator de velocidade pela voz:", velocidadeVozFatorAlvo);
        return;
    }
    if (estadoVozAtual === "improviso") {
        const tempoSemMatch = Date.now() - ultimoMatchVozMs;
        if (tempoSemMatch >= TEMPO_SEM_MATCH_IMPROVISO_MS) {
            pausarRolagemPorImproviso();
            console.log("Improviso detectado. Rolagem pausada pela voz.");
        } else {
            velocidadeVozFatorAlvo = 0.35;
        }
    }
});

socket.on("estado_rolagem", (dados) => {
    console.log("Estado de rolagem recebido:", dados);
    if (!dados) return;
    if (dados.tipo === "IMPROVISO") { pausarRolagemPorImproviso(); return; }
    if (dados.tipo === "VT_OU_LINK") {
        iniciarPausaTecnica(Number(dados.pausaSegundos || 0), dados.motivo || "VT/link"); return;
    }
    if (dados.tipo === "RECONECTANDO_AUDIO") {
        rolagemBloqueadaPorSistema = true;
        motivoBloqueioRolagem = "RECONECTANDO_AUDIO";
        mostrarToast("Trocando dispositivo de áudio...", "info"); return;
    }
    if (dados.tipo === "AUTOMATICO") {
        liberarRolagemPorRetornoAoRoteiro();
        velocidadeVozFatorAlvo = 1.0;
        iniciarTemporizadorDaLinha(); return;
    }
    if (dados.tipo === "FINALIZADO") {
        rolagemBloqueadaPorSistema = true;
        motivoBloqueioRolagem = dados.tipo;
        pararRolagemContinua(); return;
    }
    if (dados.tipo === "PAUSADO" || dados.tipo === "FALHA") {
        rolagemBloqueadaPorSistema = true;
        motivoBloqueioRolagem = dados.tipo;
    }
});

socket.on("status_motor", (dados) => {
    console.log("Status do motor recebido:", dados);
    motorPausado = dados.estado === "PAUSADO";
    if (dados.estado === "FINALIZADO") pararRolagemContinua();
    if (dados.estado === "IMPROVISO") pausarRolagemPorImproviso();
    if (dados.estado === "AUTOMATICO" && motivoBloqueioRolagem === "IMPROVISO") liberarRolagemPorRetornoAoRoteiro();
    if (dados.estado === "RECONECTANDO_AUDIO") {
        rolagemBloqueadaPorSistema = true;
        motivoBloqueioRolagem = "RECONECTANDO_AUDIO";
        mostrarToast("Trocando dispositivo de áudio...", "info");
    }
});

socket.on("config_tp_display", (dados) => {
    console.log("Configuração TP Display recebida:", dados);
    if (!dados) return;
    const root = document.documentElement;
    if (typeof dados.maxWidthVw === "number") root.style.setProperty("--tp-max-width-vw", `${dados.maxWidthVw}vw`);
    if (typeof dados.maxHeightVh === "number") root.style.setProperty("--tp-max-height-vh", `${dados.maxHeightVh}vh`);
});

socket.on("dispositivos_audio", (dados) => {
    // In hybrid mode, audio comes from browser - no device list UI needed
    console.log("Dispositivos de áudio do servidor (fallback):", dados);
});

// ============================================================
// Comandos manuais
// ============================================================

function prepararComandoManual() {
    comandoManualPendente = true;
    absorverRolagemContinuaNaBase();
    velocidadeVozFatorAlvo = 1.0;
    velocidadeVozFatorAtual = 1.0;
    rolagemBloqueadaPorSistema = false;
    motivoBloqueioRolagem = "";
    pausaTecnicaAte = 0;
    rolagemInterrompidaManualmente = false;
    atualizarTextoBotaoRolagem();
}

function enviarAvancoManual() {
    prepararComandoManual();
    socket.emit("manual_next");
}

function enviarRetornoManual() {
    prepararComandoManual();
    socket.emit("manual_prev");
}

function alternarPausaMotor() {
    socket.emit("alternar_pausa");
}

if (btnNext) btnNext.addEventListener("click", enviarAvancoManual);
if (btnPrev) btnPrev.addEventListener("click", enviarRetornoManual);
if (btnPlayLocal) btnPlayLocal.addEventListener("click", alternarPausaMotor);

document.addEventListener("keydown", (evento) => {
    if (evento.key === "ArrowDown") { evento.preventDefault(); enviarAvancoManual(); }
    if (evento.key === "ArrowUp") { evento.preventDefault(); enviarRetornoManual(); }
    if (evento.code === "Space") { evento.preventDefault(); alternarPausaMotor(); }
});

// Botão de rolagem
if (scrollToggleBtn) {
    scrollToggleBtn.addEventListener("click", () => {
        rolagemContinuaAtiva = !rolagemContinuaAtiva;
        rolagemInterrompidaManualmente = !rolagemContinuaAtiva;
        atualizarTextoBotaoRolagem();
        if (rolagemContinuaAtiva) iniciarTemporizadorDaLinha();
    });
}

// ============================================================
// Speech Recognition Control
// ============================================================

function iniciarReconhecimentoVoz() {
    if (!isSpeaking) {
        isSpeaking = true;
        if (speechMode === SPEECH_MODE.WEB) {
            startWebSpeech();
        } else {
            startVoskRecording();
        }
    }
}

function pararReconhecimentoVoz() {
    if (isSpeaking) {
        isSpeaking = false;
        if (speechMode === SPEECH_MODE.WEB) {
            stopWebSpeech();
        } else {
            stopVoskRecording();
        }
    }
}

// Web Speech recognition is independent of motor paused state
// It runs continuously alongside the motor
socket.on("connect", () => {
    // Already handled above
});

// When motor starts, also start speech recognition
const origEmitIniciarMotor = socket.emit;
// Wrap emit to track motor start
socket.on("status_motor", (dados) => {
    // Already handled above
});

// Auto-start speech recognition on motor start
socket.on("iniciar_motor", function () {
    // handled by original connect event
});

// ============================================================
// Formatação
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

if (mirrorBtn) {
    mirrorBtn.addEventListener("click", () => {
        estiloTexto.espelhado = !estiloTexto.espelhado;
        aplicarEstiloTexto();
        publicarEstilo();
    });
}

if (speedWheel) {
    speedWheel.min = "0.25";
    speedWheel.max = "2.5";
    speedWheel.step = "0.05";
    speedWheel.value = String(fatorManualVelocidade);

    speedWheel.addEventListener("input", () => {
        fatorManualVelocidade = Number(speedWheel.value);
        localStorage.setItem("tp_velocidade", String(fatorManualVelocidade));
        console.log("Fator manual da rolagem:", fatorManualVelocidade);
    });
}

// ============================================================
// Arquivo / Edição Local
// ============================================================

if (btnOpenFile && fileInput) {
    btnOpenFile.addEventListener("click", () => fileInput.click());
}

if (fileInput) {
    fileInput.addEventListener("change", async () => {
        const arquivo = fileInput.files[0];
        if (!arquivo) return;

        if (arquivo.name.toLowerCase().endsWith(".json")) {
            try {
                const conteudo = await arquivo.text();
                const resp = await fetch("/api/scripts", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: conteudo,
                });
                const dados = await resp.json();
                console.log("Script parseado pelo backend:", dados);
                if (dados.programs) {
                    linhasRoteiro = [];
                    dados.programs.forEach((p) => {
                        (p.blocks || []).forEach((b) => {
                            (b.subblocks || []).forEach((sb) => {
                                (sb.lines || []).forEach((l) => linhasRoteiro.push(l));
                            });
                        });
                    });
                    segmentosRoteiro = [];
                    metadadosLinhas = [];
                    renderizarRoteiro(linhasRoteiro);
                    mostrarToast("Roteiro carregado via backend", "success");
                }
            } catch (err) {
                console.error("Erro ao enviar roteiro ao backend:", err);
                mostrarToast("Falha ao processar roteiro", "error");
            }
            return;
        }

        const texto = await arquivo.text();
        if (editor) {
            editor.innerText = texto;
            linhasRoteiro = texto.split("\n").filter(l => l.trim() !== "");
            segmentosRoteiro = [];
            metadadosLinhas = [];
            renderizarRoteiro(linhasRoteiro);
        }
    });
}

if (btnSaveFile) {
    btnSaveFile.addEventListener("click", () => {
        const container = obterContainerTexto();
        if (!container) return;
        const blob = new Blob([container.innerText], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "roteiro_teleprompter.txt";
        link.click();
        URL.revokeObjectURL(url);
    });
}

if (btnUndo) btnUndo.addEventListener("click", () => document.execCommand("undo"));
if (btnRedo) btnRedo.addEventListener("click", () => document.execCommand("redo"));

// ============================================================
// Esconder / Restaurar barras
// ============================================================

if (btnClose) {
    btnClose.onclick = () => {
        if (mainToolbar) mainToolbar.classList.add("toolbar-hidden");
        if (sidePanel) sidePanel.classList.add("hidden");
        if (btnRestore) btnRestore.classList.remove("hidden");
    };
}

if (btnRestore) {
    btnRestore.onclick = () => {
        if (mainToolbar) mainToolbar.classList.remove("toolbar-hidden");
        if (sidePanel) sidePanel.classList.remove("hidden");
        btnRestore.classList.add("hidden");
    };
}

// ============================================================
// Sincronização entre telas
// ============================================================

if (canal) {
    canal.onmessage = (evento) => {
        const dados = evento.data;
        if (!dados || dados.tipo !== "estilo") return;
        estiloTexto = { ...estiloTexto, ...dados.estilo };
        aplicarEstiloTexto();
    };
}

// ============================================================
// WinPlus toggle
// ============================================================

if (winplusToggleBtn && appBody) {
    winplusToggleBtn.addEventListener("click", () => {
        const isInactive = appBody.classList.contains("winplus-inactive");
        if (isInactive) {
            appBody.classList.remove("winplus-inactive");
            appBody.classList.add("winplus-active");
            winplusToggleBtn.textContent = "□ TELA CHEIA";
        } else {
            appBody.classList.remove("winplus-active");
            appBody.classList.add("winplus-inactive");
            winplusToggleBtn.textContent = "▣ MODO OPERADOR";
        }
        requestAnimationFrame(() => {
            ultimoFrame = null;
            sincronizarTeleprompter(indiceAtualVisual, { preservarRolagem: true });
        });
    });
}

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && appBody && appBody.classList.contains("winplus-active") && winplusToggleBtn) {
        e.preventDefault();
        winplusToggleBtn.click();
    }
});

// ============================================================
// Toast helper
// ============================================================

function mostrarToast(mensagem, tipo = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.style.cssText = `
            position: fixed; bottom: 20px; right: 20px; z-index: 10000;
            display: flex; flex-direction: column; gap: 8px; pointer-events: none;
        `;
        document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.textContent = mensagem;
    toast.style.cssText = `
        padding: 12px 20px; border-radius: 6px; font-size: 14px; font-weight: 500;
        color: #fff; background: ${tipo === "error" ? "#cc2929" : tipo === "success" ? "#2e7d32" : "#0076ff"};
        box-shadow: 0 4px 12px rgba(0,0,0,0.3); pointer-events: auto;
    `;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100%)";
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================================
// Bloquear seleção (UX)
// ============================================================

function bloquearSelecaoNoTeleprompter() {
    [editor, display].forEach(container => {
        if (!container) return;
        container.addEventListener("mousedown", (evento) => {
            const clicouEmLinha = evento.target.closest(".linha-roteiro, .comentario");
            if (clicouEmLinha) {
                evento.preventDefault();
                if (window.getSelection) window.getSelection().removeAllRanges();
                container.blur();
            }
        });
    });
}
bloquearSelecaoNoTeleprompter();

// ============================================================
// Inicialização
// ============================================================

aplicarEstiloTexto();
atualizarTextoBotaoRolagem();
requestAnimationFrame(animarRolagemContinua);

// Start speech recognition when motor starts
// The motor start event is triggered by backend via socket
socket.on("iniciar_motor", () => {
    // Speech recognition is browser-driven
});

// When connect fires, wait for motor start and then begin speech
let motorStarted = false;
socket.on("status_motor", (dados) => {
    if (dados.correndo && !motorStarted) {
        motorStarted = true;
        // Delay to ensure UI is ready
        setTimeout(() => {
            iniciarReconhecimentoVoz();
        }, 500);
    }
    if (!dados.correndo) {
        motorStarted = false;
        pararReconhecimentoVoz();
    }
});

console.log("Teleprompter frontend (hybrid speech) loaded.");
console.log("Web Speech API supported:", speechRecognitionSupported);