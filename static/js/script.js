// ============================================================
// TELEPROMPTER SQUAD 29 - FRONTEND CHAVEADO WINPLUS
// ============================================================
// Esta versão usa os tempos do JSON/iNEWS enviados pelo backend:
// - speakingTime para fala;
// - tapeTime para VT/link/imagens;
// - totalTime para blocos sem fala;
// - pausa em improviso;
// - retomada quando o backend reconhece a volta ao roteiro.
// ============================================================

const socket = io();

// Elementos Principais
const editor = document.getElementById("editor");
const display = document.getElementById("display");
const mainToolbar = document.getElementById("main-toolbar") || document.getElementById("top-toolbar");
const sidePanel = document.getElementById("side-speed-panel");
const btnRestore = document.getElementById("btn-restore");
const btnClose = document.getElementById("btn-close-toolbar");

// Compatibilidade com nomes usados nas duas telas.
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

// Chaveadores WinPlus
const winplusToggleBtn =
    document.getElementById("winplusToggleBtn") ||
    document.getElementById("btn-winplus-toggle");

const appBody = document.getElementById("app-body");

// Estado Local
let linhasRoteiro = [];
let indiceAtualVisual = 0;

// Metadados enviados pelo backend
let segmentosRoteiro = [];
let metadadosLinhas = [];
let configuracaoRolagem = null;

// Cada tela precisa manter sua própria posição-base.
let deslocamentoBaseEditor = 0;
let deslocamentoBaseDisplay = 0;

let alvoDeslocamentoBaseEditor = 0;
let alvoDeslocamentoBaseDisplay = 0;
let suavidadeSincronizacao = 0.10;

let deslocamentoManual = 0;
let motorPausado = true;

// Ponto fixo de leitura.
// A seta e a frase reconhecida devem apontar para esta mesma região.
const PONTO_LEITURA_DISPLAY = 0.51;

// Esquerda em tela cheia
const PONTO_LEITURA_EDITOR_TELA_CHEIA = 0.50;

// Esquerda no modo dividido
const PONTO_LEITURA_EDITOR_DIVIDIDO = 0.50;

const FATOR_ROLAGEM_EDITOR = 1;
const FATOR_ROLAGEM_DISPLAY = 1;

// Controle da rolagem contínua automática
let rolagemContinuaAtiva = false;

// Valor manual do operador.
// O tempo do JSON calcula a velocidade base; o slider funciona como ajuste fino.
let fatorManualVelocidade = Number(localStorage.getItem("tp_velocidade") || 1);

let ultimoFrame = null;
let posicaoRolagemContinua = 0;
let comandoManualPendente = false;
let suavizandoPorFala = false;

// Controle de pausa técnica/improviso
let rolagemBloqueadaPorSistema = false;
let motivoBloqueioRolagem = "";
let pausaTecnicaAte = 0;

// Controle da rolagem assistida por voz.
// O JSON define a velocidade base, mas a fala real ajusta o ritmo.
let estadoVozAtual = "aguardando";
let ultimoMatchVozMs = Date.now();
let velocidadeVozFatorAtual = 1.0;
let velocidadeVozFatorAlvo = 1.0;
let rolagemInterrompidaManualmente = false;

const TEMPO_SEM_MATCH_IMPROVISO_MS = 2200;
const SUAVIDADE_VELOCIDADE_VOZ = 0.08;

// Controle para calcular velocidade de cada trecho
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
try { canal = new BroadcastChannel("tp_channel"); } catch (erro) { canal = null; }

// ============================================================
// UTILITÁRIOS
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

    if (canal) {
        canal.postMessage({ tipo: "estilo", estilo: estiloTexto });
    }
}

function aplicarEstiloTexto() {
    obterContainersTexto().forEach(container => {
        container.style.fontFamily = estiloTexto.fonte;

        if (container === editor) {
            container.style.fontSize = `${estiloTexto.tamanho}px`;
        }

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

    if (typeof indiceAtualVisual !== "undefined") {
        destacarLinha(indiceAtualVisual);
    }
}

function obterPontoLeitura(container) {
    if (container === display) {
        return PONTO_LEITURA_DISPLAY;
    }

    if (appBody && appBody.classList.contains("winplus-active")) {
        return PONTO_LEITURA_EDITOR_DIVIDIDO;
    }

    return PONTO_LEITURA_EDITOR_TELA_CHEIA;
}

function aplicarTransformacao() {
    obterContainersTexto().forEach(container => {
        const deslocamentoBaseContainer =
            container === editor
                ? deslocamentoBaseEditor
                : deslocamentoBaseDisplay;

        const fatorRolagem =
            container === display
                ? FATOR_ROLAGEM_DISPLAY
                : FATOR_ROLAGEM_EDITOR;

        const deslocamentoTotal =
            deslocamentoBaseContainer +
            deslocamentoManual +
            (posicaoRolagemContinua * fatorRolagem);

        container.style.setProperty(
            "--tp-offset-y",
            `${deslocamentoTotal}px`
        );

        container.style.setProperty(
            "--tp-scale-x",
            estiloTexto.espelhado ? "-1" : "1"
        );
    });
}

function resetarDeslocamentosVisuais() {
    deslocamentoManual = 0;
    posicaoRolagemContinua = 0;
    ultimoFrame = null;

    aplicarTransformacao();
}

// ============================================================
// TEMPOS / METADADOS
// ============================================================

function obterMetaLinhaVisual(indiceVisual) {
    return metadadosLinhas.find(meta => meta.indiceVisual === indiceVisual) || null;
}

function obterSegmentoPorVisual(indiceVisual) {
    return segmentosRoteiro.find(seg => seg.indiceVisual === indiceVisual) || null;
}

function obterDuracaoLinhaAtualSegundos() {
    const segmento = obterSegmentoPorVisual(indiceAtualVisual);
    const meta = obterMetaLinhaVisual(indiceAtualVisual);

    if (segmento && Number(segmento.tempoEstimadoSegundos) > 0) {
        return Number(segmento.tempoEstimadoSegundos);
    }

    if (meta && Number(meta.duracaoSegundos) > 0) {
        return Number(meta.duracaoSegundos);
    }

    // Fallback seguro para linhas sem tempo oficial.
    return 2.0;
}

function obterDistanciaAteProximaLinha(container) {
    if (!container) return 80;

    const linhaAtual = container.querySelector(
        `.linha-roteiro[data-index="${indiceAtualVisual}"], .comentario[data-index="${indiceAtualVisual}"]`
    );

    const proximaLinha = container.querySelector(
        `.linha-roteiro[data-index="${indiceAtualVisual + 1}"], .comentario[data-index="${indiceAtualVisual + 1}"]`
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

    if (duracao <= 0) {
        return;
    }

    rolagemBloqueadaPorSistema = true;
    motivoBloqueioRolagem = motivo || "Pausa técnica";
    pausaTecnicaAte = performance.now() + (duracao * 1000);

    console.log(
        `Rolagem pausada por ${duracao}s. Motivo: ${motivoBloqueioRolagem}`
    );
}

function verificarFimPausaTecnica(timestamp) {
    if (!rolagemBloqueadaPorSistema) {
        return;
    }

    if (motivoBloqueioRolagem === "IMPROVISO") {
        // Improviso só termina quando o backend reconhecer retorno ao roteiro.
        return;
    }

    if (pausaTecnicaAte > 0 && timestamp >= pausaTecnicaAte) {
        rolagemBloqueadaPorSistema = false;
        motivoBloqueioRolagem = "";
        pausaTecnicaAte = 0;

        console.log("Pausa técnica encerrada. Rolagem liberada.");
    }
}

// ============================================================
// RENDERIZAÇÃO
// ============================================================

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

    // Quando o comando vem do backend/NEXT/PREV, zeramos a rolagem acumulada.
    // Quando é só troca de tela, preservamos para não reiniciar visualmente.
    if (!preservarRolagem) {
        posicaoRolagemContinua = 0;
    }

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
// ROLAGEM ASSISTIDA POR VOZ
// ============================================================

function calcularFatorDeVoz(dados) {
    /*
        Compara o progresso real da fala com o progresso esperado
        pelo tempo do JSON.

        Exemplo:
        - JSON espera 10s para a linha;
        - depois de 3s, o esperado seria 30% da linha;
        - se a cobertura da fala já está em 70%, a pessoa falou rápido;
        - se a cobertura está em 10%, a pessoa falou devagar.
    */

    const progresso = Number(dados.progressoEstimado || 0);
    const score = Number(dados.score || 0);

    const duracaoSegundos = obterDuracaoLinhaAtualSegundos();

    if (!tempoInicioLinhaAtual || duracaoSegundos <= 0) {
        return 1.0;
    }

    const tempoDecorridoSegundos =
        (performance.now() - tempoInicioLinhaAtual) / 1000;

    const progressoEsperado = Math.max(
        0,
        Math.min(tempoDecorridoSegundos / duracaoSegundos, 1)
    );

    const diferenca = progresso - progressoEsperado;

    // Se o score está baixo, não aceleramos muito,
    // porque pode ser erro de transcrição do Vosk.
    if (score < 0.40) {
        return 0.45;
    }

    // Falou bem mais rápido do que o tempo previsto.
    if (diferenca >= 0.25) {
        return 1.45;
    }

    // Falou um pouco mais rápido.
    if (diferenca >= 0.12) {
        return 1.25;
    }

    // Falou bem mais lento.
    if (diferenca <= -0.25) {
        return 0.45;
    }

    // Falou um pouco mais lento.
    if (diferenca <= -0.12) {
        return 0.70;
    }

    // Está dentro do ritmo planejado pelo JSON.
    return 1.0;
}

function ativarRolagemPorVozSePossivel() {
    /*
        O teleprompter precisa ser guiado pela fala.
        Então, quando a voz está acompanhando o roteiro,
        a rolagem pode ser ligada automaticamente, desde que
        o operador não tenha parado manualmente.
    */

    if (rolagemInterrompidaManualmente) {
        return;
    }

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

// ============================================================
// ROLAGEM CONTÍNUA
// ============================================================

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

function podeRolarAgora() {
    if (!rolagemContinuaAtiva) return false;
    if (motorPausado) return false;
    if (rolagemBloqueadaPorSistema) return false;
    return true;
}

function animarRolagemContinua(timestamp) {
    if (ultimoFrame === null) {
        ultimoFrame = timestamp;
    }

    const delta = timestamp - ultimoFrame;
    ultimoFrame = timestamp;

    deslocamentoBaseEditor +=
        (alvoDeslocamentoBaseEditor - deslocamentoBaseEditor) *
        suavidadeSincronizacao;

    deslocamentoBaseDisplay +=
        (alvoDeslocamentoBaseDisplay - deslocamentoBaseDisplay) *
        suavidadeSincronizacao;

    verificarFimPausaTecnica(timestamp);

    // A velocidade real se aproxima da velocidade alvo calculada pela voz.
    // Isso evita trancos quando o apresentador acelera ou desacelera.
    velocidadeVozFatorAtual +=
        (velocidadeVozFatorAlvo - velocidadeVozFatorAtual) *
        SUAVIDADE_VELOCIDADE_VOZ;

    const distanciaEditor = Math.abs(alvoDeslocamentoBaseEditor - deslocamentoBaseEditor);
    const distanciaDisplay = Math.abs(alvoDeslocamentoBaseDisplay - deslocamentoBaseDisplay);

    const aindaCorrigindoPosicao =
        distanciaEditor > 2 ||
        distanciaDisplay > 2;

    if (podeRolarAgora() && !aindaCorrigindoPosicao) {
        const velocidadePxPorMs = calcularVelocidadePxPorMs();

        // Move o texto para cima.
        posicaoRolagemContinua -= velocidadePxPorMs * delta;
    }

    aplicarTransformacao();

    requestAnimationFrame(animarRolagemContinua);
}

// ============================================================
// EVENTOS SOCKETIO
// ============================================================

socket.on("connect", () => {
    console.log("Frontend conectado ao backend SocketIO.");
    console.log("ID da conexão:", socket.id);

    socket.emit("iniciar_motor");
    socket.emit("solicitar_config_rolagem");

    console.log("Eventos iniciar_motor e solicitar_config_rolagem enviados.");
});

socket.on("roteiro", (dados) => {
    console.log("Roteiro recebido do backend:", dados);

    linhasRoteiro = dados.linhas || [];
    segmentosRoteiro = dados.segmentos || [];
    metadadosLinhas = dados.metadadosLinhas || [];
    configuracaoRolagem = dados.configRolagem || null;

    console.log("Segmentos recebidos:", segmentosRoteiro);
    console.log("Metadados visuais recebidos:", metadadosLinhas);
    console.log("Configuração recebida no roteiro:", configuracaoRolagem);

    indiceAtualVisual = dados.indiceAtual || 0;

    renderizarRoteiro(linhasRoteiro);

    requestAnimationFrame(() => {
        sincronizarTeleprompterImediato(indiceAtualVisual);
    });
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
        iniciarPausaTecnica(
            Number(dados.pausaAposSegundos),
            dados.motivoPausa || "Pausa técnica após fala"
        );
    }
});

socket.on("voz_roteiro", (dados) => {
    console.log("Andamento da voz recebido:", dados);

    if (!dados) return;

    estadoVozAtual = dados.estadoVoz || "aguardando";

    if (
        estadoVozAtual === "acompanhando" ||
        estadoVozAtual === "retomou"
    ) {
        ultimoMatchVozMs = Date.now();

        if (estadoVozAtual === "retomou") {
            liberarRolagemPorRetornoAoRoteiro();
        } else if (!rolagemBloqueadaPorSistema) {
            ativarRolagemPorVozSePossivel();
        }

        velocidadeVozFatorAlvo = calcularFatorDeVoz(dados);

        console.log(
            "Fator de velocidade pela voz:",
            velocidadeVozFatorAlvo
        );

        return;
    }

    if (estadoVozAtual === "improviso") {
        const tempoSemMatch = Date.now() - ultimoMatchVozMs;

        // Não pausamos no primeiro erro do Vosk.
        // Só travamos se a fala continuar fora do roteiro por alguns instantes.
        if (tempoSemMatch >= TEMPO_SEM_MATCH_IMPROVISO_MS) {
            pausarRolagemPorImproviso();
            console.log("Improviso detectado. Rolagem pausada pela voz.");
        } else {
            // Enquanto ainda não temos certeza se é improviso,
            // reduzimos a velocidade para evitar avanço indevido.
            velocidadeVozFatorAlvo = 0.35;
        }
    }
});

socket.on("estado_rolagem", (dados) => {
    console.log("Estado de rolagem recebido:", dados);

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

    if (dados.tipo === "AUTOMATICO") {
        liberarRolagemPorRetornoAoRoteiro();
        velocidadeVozFatorAlvo = 1.0;
        iniciarTemporizadorDaLinha();
        return;
    }

    if (dados.tipo === "FINALIZADO") {
        rolagemBloqueadaPorSistema = true;
        motivoBloqueioRolagem = dados.tipo;
        pararRolagemContinua();
        return;
    }

    if (dados.tipo === "PAUSADO" || dados.tipo === "FALHA") {
        rolagemBloqueadaPorSistema = true;
        motivoBloqueioRolagem = dados.tipo;
    }
});

socket.on("status_motor", (dados) => {
    console.log("Status do motor recebido:", dados);

    motorPausado = dados.estado === "PAUSADO";

    if (dados.estado === "FINALIZADO") {
        pararRolagemContinua();
    }

    if (dados.estado === "IMPROVISO") {
        pausarRolagemPorImproviso();
    }

    if (dados.estado === "AUTOMATICO" && motivoBloqueioRolagem === "IMPROVISO") {
        liberarRolagemPorRetornoAoRoteiro();
    }
});

// ============================================================
// COMANDOS MANUAIS
// ============================================================

function prepararComandoManual() {
    comandoManualPendente = true;

    absorverRolagemContinuaNaBase();

    velocidadeVozFatorAlvo = 1.0;
    velocidadeVozFatorAtual = 1.0;

    rolagemBloqueadaPorSistema = false;
    motivoBloqueioRolagem = "";
    pausaTecnicaAte = 0;

    // Depois de NEXT/PREV manual, permitimos que a voz volte a acionar a rolagem.
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

// Botão específico para ligar/desligar rolagem contínua visual.
if (scrollToggleBtn) {
    scrollToggleBtn.addEventListener("click", () => {
        rolagemContinuaAtiva = !rolagemContinuaAtiva;

        // Se o operador parar manualmente, a voz não religa sozinha.
        // Se ele iniciar manualmente, a voz volta a poder ajustar o ritmo.
        rolagemInterrompidaManualmente = !rolagemContinuaAtiva;

        atualizarTextoBotaoRolagem();

        if (rolagemContinuaAtiva) {
            iniciarTemporizadorDaLinha();
        }
    });
}

// ============================================================
// CHAVEADOR WINPLUS
// ============================================================

if (winplusToggleBtn && appBody) {
    winplusToggleBtn.addEventListener("click", () => {
        const isInactive = appBody.classList.contains("winplus-inactive");

        if (isInactive) {
            appBody.classList.remove("winplus-inactive");
            appBody.classList.add("winplus-active");

            winplusToggleBtn.textContent = "□ TELA CHEIA";
            winplusToggleBtn.classList.remove("active-stop");
        } else {
            appBody.classList.remove("winplus-active");
            appBody.classList.add("winplus-inactive");

            winplusToggleBtn.textContent = "▣ MODO OPERADOR";
            winplusToggleBtn.classList.remove("active-stop");
        }

        requestAnimationFrame(() => {
            ultimoFrame = null;

            sincronizarTeleprompter(indiceAtualVisual, {
                preservarRolagem: true
            });
        });
    });
}

document.addEventListener("keydown", (e) => {
    if (
        e.key === "Escape" &&
        appBody &&
        appBody.classList.contains("winplus-active") &&
        winplusToggleBtn
    ) {
        e.preventDefault();
        winplusToggleBtn.click();
    }
});

// ============================================================
// FORMATAÇÃO
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

// Slider agora é fator multiplicador.
// 1 = tempo exato do JSON.
// 0.5 = metade da velocidade.
// 2 = dobro da velocidade.
if (speedWheel) {
    speedWheel.min = "0.25";
    speedWheel.max = "2.5";
    speedWheel.step = "0.05";
    speedWheel.value = String(fatorManualVelocidade);

    speedWheel.addEventListener("input", () => {
        fatorManualVelocidade = Number(speedWheel.value);

        localStorage.setItem(
            "tp_velocidade",
            String(fatorManualVelocidade)
        );

        console.log("Fator manual da rolagem:", fatorManualVelocidade);
    });
}

// ============================================================
// ARQUIVO / EDIÇÃO LOCAL
// ============================================================

if (btnOpenFile && fileInput) {
    btnOpenFile.addEventListener("click", () => fileInput.click());
}

if (fileInput) {
    fileInput.addEventListener("change", async () => {
        const arquivo = fileInput.files[0];

        if (!arquivo) return;

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

        const blob = new Blob(
            [container.innerText],
            { type: "text/plain;charset=utf-8" }
        );

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
// ESCONDER / RESTAURAR BARRAS
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
// SINCRONIZAÇÃO ENTRE TELAS
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
// INICIALIZAÇÃO
// ============================================================

function bloquearSelecaoNoTeleprompter() {
    [editor, display].forEach(container => {
        if (!container) return;

        container.addEventListener("mousedown", (evento) => {
            const clicouEmLinha = evento.target.closest(".linha-roteiro, .comentario");

            if (clicouEmLinha) {
                evento.preventDefault();

                if (window.getSelection) {
                    window.getSelection().removeAllRanges();
                }

                container.blur();
            }
        });
    });
}

bloquearSelecaoNoTeleprompter();


aplicarEstiloTexto();
atualizarTextoBotaoRolagem();
requestAnimationFrame(animarRolagemContinua);



