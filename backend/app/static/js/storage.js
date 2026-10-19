// ============================================================
// STORAGE - LocalStorage & BroadcastChannel sync
// ============================================================

const STORAGE_KEYS = {
    FONTE: "tp_fonte",
    TAMANHO: "tp_tamanho",
    NEGRITO: "tp_negrito",
    ITALICO: "tp_italico",
    SUBLINHADO: "tp_sublinhado",
    ESPELHADO: "tp_espelhado",
    VELOCIDADE: "tp_velocidade",
};

let estiloTexto = {
    fonte: localStorage.getItem(STORAGE_KEYS.FONTE) || "Segoe UI",
    tamanho: Number(localStorage.getItem(STORAGE_KEYS.TAMANHO) || 72),
    negrito: localStorage.getItem(STORAGE_KEYS.NEGRITO) === "true",
    italico: localStorage.getItem(STORAGE_KEYS.ITALICO) === "true",
    sublinhado: localStorage.getItem(STORAGE_KEYS.SUBLINHADO) === "true",
    espelhado: localStorage.getItem(STORAGE_KEYS.ESPELHADO) === "true",
};

let fatorManualVelocidade = Number(localStorage.getItem(STORAGE_KEYS.VELOCIDADE) || 1);

let canal = null;
try {
    canal = new BroadcastChannel("tp_channel");
} catch (erro) {
    canal = null;
    console.warn("BroadcastChannel not supported:", erro);
}

function salvarPreferencias() {
    localStorage.setItem(STORAGE_KEYS.FONTE, estiloTexto.fonte);
    localStorage.setItem(STORAGE_KEYS.TAMANHO, String(estiloTexto.tamanho));
    localStorage.setItem(STORAGE_KEYS.NEGRITO, String(estiloTexto.negrito));
    localStorage.setItem(STORAGE_KEYS.ITALICO, String(estiloTexto.italico));
    localStorage.setItem(STORAGE_KEYS.SUBLINHADO, String(estiloTexto.sublinhado));
    localStorage.setItem(STORAGE_KEYS.ESPELHADO, String(estiloTexto.espelhado));
}

function publicarEstilo() {
    salvarPreferencias();
    if (canal) {
        canal.postMessage({ tipo: "estilo", estilo: estiloTexto });
    }
}

function initStorageSync() {
    if (canal) {
        canal.onmessage = (evento) => {
            const dados = evento.data;
            if (!dados || dados.tipo !== "estilo") return;
            estiloTexto = { ...estiloTexto, ...dados.estilo };
            aplicarEstiloTexto();
        };
    }
}

function getVelocidadePref() {
    return fatorManualVelocidade;
}

function setVelocidadePref(value) {
    fatorManualVelocidade = value;
    localStorage.setItem(STORAGE_KEYS.VELOCIDADE, String(value));
}

export {
    estiloTexto,
    fatorManualVelocidade,
    getVelocidadePref,
    setVelocidadePref,
    salvarPreferencias,
    publicarEstilo,
    initStorageSync,
    STORAGE_KEYS,
};
