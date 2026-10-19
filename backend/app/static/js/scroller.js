// ============================================================
// SCROLLER - Continuous scrolling, voice-adaptive scrolling
// ============================================================

import { stateRef } from "./state.js";
const s = stateRef;
import {
    aplicarTransformacao,
    obterContainerTexto,
    obterMetaLinhaVisual,
    obterSegmentoPorVisual,
    obterDuracaoLinhaAtualSegundos,
    obterDistanciaAteProximaLinha,
    absorverRolagemContinuaNaBase,
} from "./renderer.js";
import { getVelocidadePref } from "./storage.js";

export function prepararComandoManual() {
    s.comandoManualPendente = true;

    absorverRolagemContinuaNaBase();

    s.velocidadeVozFatorAlvo = 1.0;
    s.velocidadeVozFatorAtual = 1.0;

    s.rolagemBloqueadaPorSistema = false;
    s.motivoBloqueioRolagem = "";
    s.pausaTecnicaAte = 0;

    // Depois de NEXT/PREV manual, permitimos que a voz volte a acionar a rolagem.
    s.rolagemInterrompidaManualmente = false;

    atualizarTextoBotaoRolagem();
}

export function calcularVelocidadePxPorMs() {
    const container = obterContainerTexto();
    const duracaoSegundos = obterDuracaoLinhaAtualSegundos();
    const distanciaPx = obterDistanciaAteProximaLinha(container);

    const velocidadeBase = distanciaPx / Math.max(duracaoSegundos * 1000, 1);

    return velocidadeBase * getVelocidadePref() * s.velocidadeVozFatorAtual;
}

export function iniciarTemporizadorDaLinha() {
    s.tempoInicioLinhaAtual = performance.now();
    s.duracaoLinhaAtualMs = obterDuracaoLinhaAtualSegundos() * 1000;
}

export function iniciarPausaTecnica(segundos, motivo) {
    const duracao = Number(segundos || 0);

    if (duracao <= 0) {
        return;
    }

    s.rolagemBloqueadaPorSistema = true;
    s.motivoBloqueioRolagem = motivo || "Pausa técnica";
    s.pausaTecnicaAte = performance.now() + (duracao * 1000);

    console.log(
        `Rolagem pausada por ${duracao}s. Motivo: ${s.motivoBloqueioRolagem}`
    );
}

export function verificarFimPausaTecnica(timestamp) {
    if (!s.rolagemBloqueadaPorSistema) {
        return;
    }

    if (s.motivoBloqueioRolagem === "IMPROVISO") {
        return;
    }

    if (s.pausaTecnicaAte > 0 && timestamp >= s.pausaTecnicaAte) {
        s.rolagemBloqueadaPorSistema = false;
        s.motivoBloqueioRolagem = "";
        s.pausaTecnicaAte = 0;

        console.log("Pausa técnica encerrada. Rolagem liberada.");
    }
}

export function calcularFatorDeVoz(dados) {
    const progresso = Number(dados.progressoEstimado || 0);
    const score = Number(dados.score || 0);

    const duracaoSegundos = obterDuracaoLinhaAtualSegundos();

    if (!s.tempoInicioLinhaAtual || duracaoSegundos <= 0) {
        return 1.0;
    }

    const tempoDecorridoSegundos =
        (performance.now() - s.tempoInicioLinhaAtual) / 1000;

    const progressoEsperado = Math.max(
        0,
        Math.min(tempoDecorridoSegundos / duracaoSegundos, 1)
    );

    const diferenca = progresso - progressoEsperado;

    if (score < 0.40) {
        return 0.45;
    }

    if (diferenca >= 0.25) {
        return 1.45;
    }

    if (diferenca >= 0.12) {
        return 1.25;
    }

    if (diferenca <= -0.25) {
        return 0.45;
    }

    if (diferenca <= -0.12) {
        return 0.70;
    }

    return 1.0;
}

export function ativarRolagemPorVozSePossivel() {
    if (s.rolagemInterrompidaManualmente) {
        return;
    }

    if (!s.rolagemContinuaAtiva) {
        s.rolagemContinuaAtiva = true;
        atualizarTextoBotaoRolagem();
    }
}

export function pausarRolagemPorImproviso() {
    s.rolagemBloqueadaPorSistema = true;
    s.motivoBloqueioRolagem = "IMPROVISO";
    s.pausaTecnicaAte = 0;
    s.velocidadeVozFatorAlvo = 0;
}

export function liberarRolagemPorRetornoAoRoteiro() {
    if (s.motivoBloqueioRolagem === "IMPROVISO") {
        s.rolagemBloqueadaPorSistema = false;
        s.motivoBloqueioRolagem = "";
        s.pausaTecnicaAte = 0;
    }

    ativarRolagemPorVozSePossivel();
}

export function atualizarTextoBotaoRolagem() {
    if (!s.scrollToggleBtn) return;

    if (s.rolagemContinuaAtiva) {
        s.scrollToggleBtn.textContent = "⏸ PAUSAR ROLAGEM";
        s.scrollToggleBtn.classList.add("active");
    } else {
        s.scrollToggleBtn.textContent = "▶ INICIAR ROLAGEM";
        s.scrollToggleBtn.classList.remove("active");
    }
}

export function podeRolarAgora() {
    if (!s.rolagemContinuaAtiva) return false;
    if (s.motorPausado) return false;
    if (s.rolagemBloqueadaPorSistema) return false;
    return true;
}

export function animarRolagemContinua(timestamp) {
    if (s.ultimoFrame === null) {
        s.ultimoFrame = timestamp;
    }

    // Ignore excess elapsed time after a stalled/background frame so the
    // teleprompter never catches up with one visible jump.
    const delta = Math.min(timestamp - s.ultimoFrame, 50);
    s.ultimoFrame = timestamp;

    const alinhamento = 1 - Math.exp(-delta / s.tempoSincronizacaoMs);
    const ajusteVoz = 1 - Math.exp(-delta / s.TEMPO_AJUSTE_VOZ_MS);

    s.deslocamentoBaseEditor +=
        (s.alvoDeslocamentoBaseEditor - s.deslocamentoBaseEditor) *
        alinhamento;

    s.deslocamentoBaseDisplay +=
        (s.alvoDeslocamentoBaseDisplay - s.deslocamentoBaseDisplay) *
        alinhamento;

    verificarFimPausaTecnica(timestamp);

    s.velocidadeVozFatorAtual +=
        (s.velocidadeVozFatorAlvo - s.velocidadeVozFatorAtual) *
        ajusteVoz;

    const distanciaEditor = Math.abs(s.alvoDeslocamentoBaseEditor - s.deslocamentoBaseEditor);
    const distanciaDisplay = Math.abs(s.alvoDeslocamentoBaseDisplay - s.deslocamentoBaseDisplay);

    const aindaCorrigindoPosicao =
        distanciaEditor > 2 ||
        distanciaDisplay > 2;

    if (podeRolarAgora() && !aindaCorrigindoPosicao) {
        const velocidadePxPorMs = calcularVelocidadePxPorMs();
        s.posicaoRolagemContinua -= velocidadePxPorMs * delta;
    }

    aplicarTransformacao();

    requestAnimationFrame(animarRolagemContinua);
}

export function pararRolagemContinua() {
    s.rolagemContinuaAtiva = false;
    s.rolagemInterrompidaManualmente = true;
    s.velocidadeVozFatorAlvo = 0;
    s.velocidadeVozFatorAtual = 0;
    s.ultimoFrame = null;
    atualizarTextoBotaoRolagem();
}
