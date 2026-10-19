// ============================================================
// SOCKET - SocketIO connection and event handlers
// ============================================================

import { stateRef } from "./state.js";
const s = stateRef;
import { withAuth } from "./auth.js";
// io is loaded globally from CDN script tag
const io = window.io;
import {
    sincronizarTeleprompter,
    sincronizarTeleprompterImediato,
    absorverRolagemContinuaNaBase,
} from "./renderer.js";
import {
    iniciarPausaTecnica,
    pararRolagemContinua,
    atualizarTextoBotaoRolagem,
    prepararComandoManual,
} from "./scroller.js";
import {
    handleVozRoteiro,
    handleEstadoRolagem,
    handleStatusMotor,
    handleSpeechReady,
    handleSpeechError,
} from "./voice.js";

export function enviarAvancoManual() {
    prepararComandoManual();
    s.socket.emit("manual_next", withAuth({}));
}
export function enviarRetornoManual() {
    prepararComandoManual();
    s.socket.emit("manual_prev", withAuth({}));
}
export function alternarPausaMotor() {
    s.socket.emit("alternar_pausa", withAuth({}));
}

export function initSocket() {
    // Create SocketIO connection with auth token (in both auth and query for compatibility)
    const token = window.AUTH_TOKEN || "";
    s.socket = io({
        auth: { token, teleprompter_id: window.TELEPROMPTER_ID || "" }
    });

    s.socket.on("connect", () => {
        console.log("Frontend conectado ao backend SocketIO.");
        console.log("ID da conexão:", s.socket.id);
        if (window.IS_OPERATOR) s.socket.emit("iniciar_motor", withAuth({}));
        s.socket.emit("solicitar_config_rolagem", withAuth({}));
        console.log("Eventos iniciar_motor e solicitar_config_rolagem enviados.");
    });

    s.socket.on("roteiro", (dados) => {
        console.log("Roteiro recebido do backend:", dados);

        s.linhasRoteiro = dados.linhas || [];
        s.segmentosRoteiro = dados.segmentos || [];
        s.metadadosLinhas = dados.metadadosLinhas || [];
        s.configuracaoRolagem = dados.configRolagem || null;

        console.log("Segmentos recebidos:", s.segmentosRoteiro);
        console.log("Metadados visuais recebidos:", s.metadadosLinhas);
        console.log("Configuração recebida no roteiro:", s.configuracaoRolagem);

        s.indiceAtualVisual = dados.indiceAtual || 0;

        renderizarRoteiro(s.linhasRoteiro);

        requestAnimationFrame(() => {
            sincronizarTeleprompterImediato(s.indiceAtualVisual);
        });
    });

    s.socket.on("config_rolagem", (dados) => {
        s.configuracaoRolagem = dados;
        console.log("Configuração de rolagem recebida:", dados);
    });

    s.socket.on("cmd", (dados) => {
        console.log("Comando de rolagem recebido:", dados);

        if (typeof dados.index === "number") {
            absorverRolagemContinuaNaBase();
            sincronizarTeleprompter(dados.index);
        }

        if (Number(dados.pausaAposSegundos) > 0) {
            iniciarPausaTecnica(
                Number(dados.pausaAposSegundos),
                dados.motivoPausa || "Pausa técnica após fala"
            );
        }
    });

    s.socket.on("voz_roteiro", handleVozRoteiro);

    s.socket.on("estado_rolagem", handleEstadoRolagem);

    s.socket.on("status_motor", handleStatusMotor);

    s.socket.on("config_tp_display", (dados) => {
        console.log("Configuração TP Display recebida:", dados);

        if (!dados) return;

        const root = document.documentElement;

        if (typeof dados.maxWidthVw === "number") {
            root.style.setProperty("--tp-max-width-vw", `${dados.maxWidthVw}vw`);
        }

        if (typeof dados.maxHeightVh === "number") {
            root.style.setProperty("--tp-max-height-vh", `${dados.maxHeightVh}vh`);
        }

        console.log("CSS variables atualizadas para TP Display");
    });

    s.socket.on("speech_ready", handleSpeechReady);
    s.socket.on("speech_error", handleSpeechError);
}
