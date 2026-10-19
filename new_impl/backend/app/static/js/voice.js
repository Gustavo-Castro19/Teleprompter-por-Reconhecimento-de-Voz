// ============================================================
// VOICE - Speech recognition (Web Speech API + Vosk fallback)
// ============================================================

import { stateRef } from "./state.js";
const s = stateRef;
import { withAuth } from "./auth.js";
import {
    iniciarTemporizadorDaLinha,
    iniciarPausaTecnica,
    pausarRolagemPorImproviso,
    liberarRolagemPorRetornoAoRoteiro,
    ativarRolagemPorVozSePossivel,
    atualizarTextoBotaoRolagem,
    calcularFatorDeVoz,
} from "./scroller.js";

const SPEECH_MODE = {
    WEB: "web",
    VOSK: "vosk",
};

let speechMode = SPEECH_MODE.WEB;
let speechRecognition = null;
let speechRecognitionSupported = false;
let isSpeaking = false;
let mediaStream = null;
let mediaRecorder = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

export function initSpeechRecognition() {
    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        speechRecognition = new SpeechRecognition();
        speechRecognition.lang = "pt-BR";
        speechRecognition.continuous = true;
        speechRecognition.interimResults = true;
        speechRecognition.maxAlternatives = 1;
        speechRecognitionSupported = true;

        speechRecognition.onresult = (event) => {
            let interimTranscript = "";
            let finalTranscript = "";

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                const confidence = event.results[i][0].confidence || 0;

                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                    s.socket.emit("speech_result", withAuth({
                        text: finalTranscript,
                        isFinal: true,
                        source: "web",
                        confidence: confidence,
                    }));
                } else {
                    interimTranscript += transcript;
                    s.socket.emit("speech_result", withAuth({
                        text: interimTranscript,
                        isFinal: false,
                        source: "web",
                        confidence: 0,
                    }));
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
                setTimeout(() => {
                    if (isSpeaking) reconnectSpeech();
                }, 50);
            }
        };
    } else {
        speechRecognitionSupported = false;
        console.warn("Web Speech API not supported");
    }
}

function startWebSpeech() {
    if (!speechRecognitionSupported) {
        console.warn("Web Speech not supported - falling back to Vosk");
        switchToVoskMode();
        return false;
    }

    try {
        s.socket.emit("speech_start", withAuth({ mode: "web", language: "pt-BR" }));
        speechRecognition.start();
        isSpeaking = true;
        console.log("Web Speech recognition started");
        reconnectAttempts = 0;
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
    s.socket.emit("speech_stop", withAuth({}));
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
                    console.error("Reconnect failed:", e);
                }
            }
        }, 100);
    }
}

async function switchToVoskMode() {
    if (speechMode === SPEECH_MODE.VOSK) return;

    console.log("Switching to Vosk mode...");
    speechMode = SPEECH_MODE.VOSK;

    stopWebSpeech();

    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            },
        });

        mediaRecorder = new MediaRecorder(mediaStream, { mimeType: "audio/webm" });
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                const reader = new FileReader();
                reader.onload = () => {
                    const base64Audio = reader.result.split(",")[1];
                    s.socket.emit("speech_audio", withAuth({ audio: base64Audio }));
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

        s.socket.emit("speech_start", withAuth({ mode: "vosk", language: "pt-BR" }));

        mediaRecorder.start(100); // Send chunks every 100ms

        showVoskToast("Modo offline Vosk ativado");
    } catch (err) {
        console.error("Failed to start Vosk mode:", err);
        showVoskToast("Erro ao acessar microfone para Vosk", "error");
    }
}

function stopVoskMode() {
    isSpeaking = false;
    try {
        if (mediaRecorder && mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
        }
    } catch (e) {
        console.error("Failed to stop Vosk:", e);
    }
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
    s.socket.emit("speech_stop", withAuth({}));
}

export function iniciarReconhecimentoVoz() {
    if (isSpeaking) return;

    if (speechMode === SPEECH_MODE.WEB) {
        startWebSpeech();
    } else {
        switchToVoskMode();
    }
}

export function pararReconhecimentoVoz() {
    if (speechMode === SPEECH_MODE.WEB) {
        stopWebSpeech();
    } else {
        stopVoskMode();
    }
}

// Toast helper
function showVoskToast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 8px;
            pointer-events: none;
        `;
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.textContent = message;
    toast.style.cssText = `
        padding: 12px 20px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 500;
        color: #fff;
        background: ${type === "error" ? "#cc2929" : type === "success" ? "#2e7d32" : "#0076ff"};
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        animation: slideIn 0.3s ease-out;
        pointer-events: auto;
    `;

    if (!document.getElementById("toast-styles")) {
        const style = document.createElement("style");
        style.id = "toast-styles";
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = "slideOut 0.3s ease-in forwards";
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Socket event handlers for speech
export function handleSpeechReady(dados) {
    if (dados.mode === "vosk" && !dados.ready) {
        console.warn("Vosk not ready, staying on Web Speech");
        speechMode = SPEECH_MODE.WEB;
        startWebSpeech();
    }
}

export function handleSpeechError(dados) {
    console.error("Speech error from backend:", dados.error);
    if (dados.fallback && speechMode === SPEECH_MODE.VOSK) {
        console.log("Falling back to Web Speech");
        speechMode = SPEECH_MODE.WEB;
        stopVoskMode();
        startWebSpeech();
    }
}

// Called when motor status changes
export function handleStatusMotor(dados) {
    s.motorPausado = dados.estado === "PAUSADO";

    if (dados.estado === "FINALIZADO") {
        pararRolagemContinua();
    }

    if (dados.estado === "IMPROVISO") {
        pausarRolagemPorImproviso();
    }

    if (dados.estado === "AUTOMATICO" && s.motivoBloqueioRolagem === "IMPROVISO") {
        liberarRolagemPorRetornoAoRoteiro();
    }

    if (dados.estado === "RECONECTANDO_AUDIO") {
        s.rolagemBloqueadaPorSistema = true;
        s.motivoBloqueioRolagem = "RECONECTANDO_AUDIO";
        showVoskToast("Trocando dispositivo de áudio...", "info");
    }
}

export function handleVozRoteiro(dados) {
    if (!dados) return;

    s.estadoVozAtual = dados.estadoVoz || "aguardando";

    if (
        s.estadoVozAtual === "acompanhando" ||
        s.estadoVozAtual === "retomou"
    ) {
        s.ultimoMatchVozMs = Date.now();

        if (s.estadoVozAtual === "retomou") {
            liberarRolagemPorRetornoAoRoteiro();
        } else if (!s.rolagemBloqueadaPorSistema) {
            ativarRolagemPorVozSePossivel();
        }

        s.velocidadeVozFatorAlvo = calcularFatorDeVoz(dados);

        console.log(
            "Fator de velocidade pela voz:",
            s.velocidadeVozFatorAlvo
        );

        return;
    }

    if (s.estadoVozAtual === "improviso") {
        const tempoSemMatch = Date.now() - s.ultimoMatchVozMs;

        if (tempoSemMatch >= s.TEMPO_SEM_MATCH_IMPROVISO_MS) {
            pausarRolagemPorImproviso();
            console.log("Improviso detectado. Rolagem pausada pela voz.");
        } else {
            s.velocidadeVozFatorAlvo = 0.35;
        }
    }
}

export function handleEstadoRolagem(dados) {
    if (!dados) return;

    if (dados.tipo === "IMPROVISO") {
        pausarRolagemPorImproviso();
        return;
    }

    if (dados.tipo === "VT_OU_LINK") {
        iniciarPausaTecnica(
            Number(dados.pausaSegundos || 0),
            dados.motivo || "VT/link"
        );
        return;
    }

    if (dados.tipo === "RECONECTANDO_AUDIO") {
        s.rolagemBloqueadaPorSistema = true;
        s.motivoBloqueioRolagem = "RECONECTANDO_AUDIO";
        showVoskToast("Trocando dispositivo de áudio...", "info");
        return;
    }

    if (dados.tipo === "AUTOMATICO") {
        liberarRolagemPorRetornoAoRoteiro();
        s.velocidadeVozFatorAlvo = 1.0;
        iniciarTemporizadorDaLinha();
        return;
    }

    if (dados.tipo === "FINALIZADO") {
        s.rolagemBloqueadaPorSistema = true;
        s.motivoBloqueioRolagem = dados.tipo;
        pararRolagemContinua();
        return;
    }

    if (dados.tipo === "PAUSADO" || dados.tipo === "FALHA") {
        s.rolagemBloqueadaPorSistema = true;
        s.motivoBloqueioRolagem = dados.tipo;
    }
}