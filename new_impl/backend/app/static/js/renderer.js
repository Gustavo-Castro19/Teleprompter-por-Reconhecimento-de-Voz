// ============================================================
// RENDERER - DOM rendering, highlighting, style application
// ============================================================

import { stateRef } from "./state.js";
import { estiloTexto, publicarEstilo, initStorageSync } from "./storage.js";

const s = stateRef;

export function obterContainerTexto() {
    if (s.appBody && s.appBody.classList.contains("winplus-active")) {
        return s.display || s.editor;
    }
    return s.editor || s.display;
}

function obterContainersTexto() {
    return [s.editor, s.display].filter(Boolean);
}

export function aplicarEstiloTexto() {
    obterContainersTexto().forEach(container => {
        container.style.fontFamily = s.estiloTexto.fonte;

        if (container === s.editor) {
            container.style.fontSize = `${s.estiloTexto.tamanho}px`;
        }

        container.style.fontWeight = s.estiloTexto.negrito ? "bold" : "normal";
        container.style.fontStyle = s.estiloTexto.italico ? "italic" : "normal";
        container.style.textDecoration = s.estiloTexto.sublinhado ? "underline" : "none";
        container.style.setProperty("--tp-scale-x", s.estiloTexto.espelhado ? "-1" : "1");
    });

    if (s.fontName) s.fontName.value = s.estiloTexto.fonte;
    if (s.fontSize) s.fontSize.value = String(s.estiloTexto.tamanho);
    if (s.btnBold) s.btnBold.classList.toggle("active-format", s.estiloTexto.negrito);
    if (s.btnItalic) s.btnItalic.classList.toggle("active-format", s.estiloTexto.italico);
    if (s.btnUnderline) s.btnUnderline.classList.toggle("active-format", s.estiloTexto.sublinhado);
    if (s.mirrorBtn) s.mirrorBtn.classList.toggle("active", s.estiloTexto.espelhado);

    aplicarTransformacao();
}

export function aplicarTransformacao() {
    obterContainersTexto().forEach(container => {
        const deslocamentoBaseContainer =
            container === s.editor
                ? s.deslocamentoBaseEditor
                : s.deslocamentoBaseDisplay;

        const fatorRolagem =
            container === s.display
                ? s.FATOR_ROLAGEM_DISPLAY
                : s.FATOR_ROLAGEM_EDITOR;

        const deslocamentoTotal =
            deslocamentoBaseContainer +
            s.deslocamentoManual +
            (s.posicaoRolagemContinua * fatorRolagem);

        container.style.setProperty(
            "--tp-offset-y",
            `${deslocamentoTotal}px`
        );

        container.style.setProperty(
            "--tp-scale-x",
            s.estiloTexto.espelhado ? "-1" : "1"
        );
    });
}

export function resetarDeslocamentosVisuais() {
    s.deslocamentoManual = 0;
    s.posicaoRolagemContinua = 0;
    s.ultimoFrame = null;
    aplicarTransformacao();
}

export function obterMetaLinhaVisual(indiceVisual) {
    return s.metadadosLinhas.find(meta => meta.indiceVisual === indiceVisual) || null;
}

export function obterSegmentoPorVisual(indiceVisual) {
    return s.segmentosRoteiro.find(seg => seg.indiceVisual === indiceVisual) || null;
}

export function renderizarRoteiro(linhas) {
    s.linhasRoteiro = linhas;
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

function obterPontoLeitura(container) {
    if (container === s.display) {
        return s.PONTO_LEITURA_DISPLAY;
    }
    if (s.appBody && s.appBody.classList.contains("winplus-active")) {
        return s.PONTO_LEITURA_EDITOR_DIVIDIDO;
    }
    return s.PONTO_LEITURA_EDITOR_TELA_CHEIA;
}

export function destacarLinha(indice) {
    s.indiceAtualVisual = indice;
    obterContainersTexto().forEach(container => {
        const linhas = container.querySelectorAll(".linha-roteiro, .comentario");

        linhas.forEach(linha => {
            linha.classList.remove("linha-atual");
        });

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

        const novoDeslocamentoBase =
            pontoLeitura - posicaoLinha - (alturaLinha / 2);

        if (container === s.editor) {
            s.alvoDeslocamentoBaseEditor = novoDeslocamentoBase;
        } else {
            s.alvoDeslocamentoBaseDisplay = novoDeslocamentoBase;
        }
    });

    aplicarTransformacao();
}

export function sincronizarTeleprompter(indice, opcoes = {}) {
    s.indiceAtualVisual = indice;

    const preservarRolagem = opcoes.preservarRolagem === true;

    if (!preservarRolagem) {
        s.posicaoRolagemContinua = 0;
    }

    destacarLinha(indice);

    if (!preservarRolagem) {
        s.velocidadeVozFatorAlvo = 1.0;
        iniciarTemporizadorDaLinha();
    }
}

export function sincronizarTeleprompterImediato(indice) {
    s.indiceAtualVisual = indice;

    s.posicaoRolagemContinua = 0;
    s.deslocamentoManual = 0;
    s.ultimoFrame = null;

    destacarLinha(indice);

    s.deslocamentoBaseEditor = s.alvoDeslocamentoBaseEditor;
    s.deslocamentoBaseDisplay = s.alvoDeslocamentoBaseDisplay;

    aplicarTransformacao();
    iniciarTemporizadorDaLinha();
}

export function absorverRolagemContinuaNaBase() {
    s.deslocamentoBaseEditor += s.posicaoRolagemContinua * s.FATOR_ROLAGEM_EDITOR;
    s.deslocamentoBaseDisplay += s.posicaoRolagemContinua * s.FATOR_ROLAGEM_DISPLAY;

    s.alvoDeslocamentoBaseEditor += s.posicaoRolagemContinua * s.FATOR_ROLAGEM_EDITOR;
    s.alvoDeslocamentoBaseDisplay += s.posicaoRolagemContinua * s.FATOR_ROLAGEM_DISPLAY;

    s.posicaoRolagemContinua = 0;
    s.deslocamentoManual = 0;
    s.ultimoFrame = null;
}

export function obterDuracaoLinhaAtualSegundos() {
    const segmento = obterSegmentoPorVisual(s.indiceAtualVisual);
    const meta = obterMetaLinhaVisual(s.indiceAtualVisual);

    if (segmento && Number(segmento.tempoEstimadoSegundos) > 0) {
        return Number(segmento.tempoEstimadoSegundos);
    }

    if (meta && Number(meta.duracaoSegundos) > 0) {
        return Number(meta.duracaoSegundos);
    }

    return 2.0;
}

export function obterDistanciaAteProximaLinha(container) {
    if (!container) return 80;

    const linhaAtual = container.querySelector(
        `.linha-roteiro[data-index="${s.indiceAtualVisual}"], .comentario[data-index="${s.indiceAtualVisual}"]`
    );

    const proximaLinha = container.querySelector(
        `.linha-roteiro[data-index="${s.indiceAtualVisual + 1}"], .comentario[data-index="${s.indiceAtualVisual + 1}"]`
    );

    if (linhaAtual && proximaLinha) {
        const distancia = Math.abs(proximaLinha.offsetTop - linhaAtual.offsetTop);
        return Math.max(distancia, 40);
    }

    if (linhaAtual) {
        return Math.max(linhaAtual.clientHeight + 18, 40);
    }

    return 80;
}