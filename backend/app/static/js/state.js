// ============================================================
// STATE - Shared mutable state across modules
// ============================================================

// All mutable state wrapped in an object (ES modules are read-only)
export const stateRef = {
    // UI Elements
    editor: null,
    display: null,
    mainToolbar: null,
    sidePanel: null,
    btnRestore: null,
    btnClose: null,
    mirrorBtn: null,
    fontName: null,
    fontSize: null,
    btnBold: null,
    btnItalic: null,
    btnUnderline: null,
    speedWheel: null,
    btnOpenFile: null,
    btnSaveFile: null,
    fileInput: null,
    btnUndo: null,
    btnRedo: null,
    btnPrev: null,
    btnNext: null,
    btnPlayLocal: null,
    scrollToggleBtn: null,
    micToggleBtn: null,
    winplusToggleBtn: null,
    appBody: null,

    // Mutable socket holder
    socket: null,

    // Script data
    linhasRoteiro: [],
    indiceAtualVisual: 0,
    segmentosRoteiro: [],
    metadadosLinhas: [],
    configuracaoRolagem: null,

    // Scroll positions
    deslocamentoBaseEditor: 0,
    deslocamentoBaseDisplay: 0,
    alvoDeslocamentoBaseEditor: 0,
    alvoDeslocamentoBaseDisplay: 0,
    suavidadeSincronizacao: 0.10,
    deslocamentoManual: 0,
    motorPausado: true,

    // Continuous scroll
    rolagemContinuaAtiva: false,
    fatorManualVelocidade: 1,
    ultimoFrame: null,
    posicaoRolagemContinua: 0,
    comandoManualPendente: false,
    suavizandoPorFala: false,

    // System pause/improviso
    rolagemBloqueadaPorSistema: false,
    motivoBloqueioRolagem: "",
    pausaTecnicaAte: 0,

    // Voice adaptation
    estadoVozAtual: "aguardando",
    ultimoMatchVozMs: Date.now(),
    velocidadeVozFatorAtual: 1.0,
    velocidadeVozFatorAlvo: 1.0,
    rolagemInterrompidaManualmente: false,

    // Constants
    TEMPO_SEM_MATCH_IMPROVISO_MS: 2200,
    SUAVIDADE_VELOCIDADE_VOZ: 0.08,

    // Line timing
    tempoInicioLinhaAtual: null,
    duracaoLinhaAtualMs: 0,

    // Style
    estiloTexto: {
        fonte: "Segoe UI",
        tamanho: 72,
        negrito: false,
        italico: false,
        sublinhado: false,
        espelhado: false,
    },

    // BroadcastChannel
    canal: null,

    // Constants
    PONTO_LEITURA_DISPLAY: 0.51,
    PONTO_LEITURA_EDITOR_TELA_CHEIA: 0.50,
    PONTO_LEITURA_EDITOR_DIVIDIDO: 0.50,
    FATOR_ROLAGEM_EDITOR: 1,
    FATOR_ROLAGEM_DISPLAY: 1,
};

export function initElements() {
    stateRef.editor = document.getElementById("editor");
    stateRef.display = document.getElementById("display");
    stateRef.mainToolbar = document.getElementById("main-toolbar") || document.getElementById("top-toolbar");
    stateRef.sidePanel = document.getElementById("side-speed-panel");
    stateRef.btnRestore = document.getElementById("btn-restore");
    stateRef.btnClose = document.getElementById("btn-close-toolbar");

    stateRef.mirrorBtn =
        document.getElementById("invertBtn") ||
        document.getElementById("mirrorBtn") ||
        document.getElementById("mirrorBtnLocal");

    stateRef.fontName = document.getElementById("fontName");
    stateRef.fontSize = document.getElementById("fontSize");
    stateRef.btnBold = document.getElementById("btn-bold");
    stateRef.btnItalic = document.getElementById("btn-italic");
    stateRef.btnUnderline = document.getElementById("btn-underline");
    stateRef.speedWheel = document.getElementById("speedWheel");
    stateRef.btnOpenFile = document.getElementById("btn-open-file");
    stateRef.btnSaveFile = document.getElementById("btn-save-file");
    stateRef.fileInput = document.getElementById("file-input");
    stateRef.btnUndo = document.getElementById("btn-undo");
    stateRef.btnRedo = document.getElementById("btn-redo");

    stateRef.btnPrev =
        document.getElementById("btn-prev") ||
        document.getElementById("btn-prev-local");

    stateRef.btnNext =
        document.getElementById("btn-next") ||
        document.getElementById("btn-next-local");

    stateRef.btnPlayLocal = document.getElementById("btn-play-local");
    stateRef.scrollToggleBtn = document.getElementById("scrollToggleBtn");
    stateRef.micToggleBtn = document.getElementById("micToggleBtn");

    stateRef.winplusToggleBtn =
        document.getElementById("winplusToggleBtn") ||
        document.getElementById("btn-winplus-toggle");

    stateRef.appBody = document.getElementById("app-body");

    try {
        stateRef.canal = new BroadcastChannel("tp_channel");
    } catch (erro) {
        stateRef.canal = null;
        console.warn("BroadcastChannel not supported:", erro);
    }
}
