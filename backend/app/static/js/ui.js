// ============================================================
// UI - Controls, buttons, file operations, undo/redo
// ============================================================

import { stateRef } from "./state.js";
const s = stateRef;
import { withAuth } from "./auth.js";
import { aplicarEstiloTexto, sincronizarTeleprompter, sincronizarTeleprompterImediato, absorverRolagemContinuaNaBase, renderizarRoteiro, destacarLinha } from "./renderer.js";
import { atualizarTextoBotaoRolagem, iniciarTemporizadorDaLinha, pararRolagemContinua, prepararComandoManual } from "./scroller.js";
import { publicarEstilo, initStorageSync } from "./storage.js";
import { enviarAvancoManual, enviarRetornoManual, alternarPausaMotor } from "./socket.js";
import { iniciarReconhecimentoVoz, pararReconhecimentoVoz, reconhecimentoAtivo } from "./voice.js";

// Undo/Redo stack
const undoStack = [];
const redoStack = [];
const MAX_HISTORY = 50;

function saveUndoState() {
    const container = s.editor || s.display;
    if (!container) return;
    const text = container.innerText;
    if (undoStack.length === 0 || undoStack[undoStack.length - 1] !== text) {
        undoStack.push(text);
        if (undoStack.length > MAX_HISTORY) undoStack.shift();
        redoStack.length = 0;
    }
}

function performUndo() {
    if (undoStack.length <= 1) return;
    const container = s.editor || s.display;
    if (!container) return;
    const current = container.innerText;
    const previous = undoStack[undoStack.length - 2];
    if (current !== previous) {
        redoStack.push(current);
    }
    undoStack.pop();
    container.innerText = undoStack[undoStack.length - 1];
    s.linhasRoteiro = container.innerText.split("\n").filter(l => l.trim() !== "");
    renderizarRoteiro(s.linhasRoteiro);
    requestAnimationFrame(() => sincronizarTeleprompterImediato(s.indiceAtualVisual));
}

function performRedo() {
    if (redoStack.length === 0) return;
    const container = s.editor || s.display;
    if (!container) return;
    const next = redoStack.pop();
    undoStack.push(next);
    container.innerText = next;
    s.linhasRoteiro = container.innerText.split("\n").filter(l => l.trim() !== "");
    renderizarRoteiro(s.linhasRoteiro);
    requestAnimationFrame(() => sincronizarTeleprompterImediato(s.indiceAtualVisual));
}

export function initUI() {
    if (s.micToggleBtn) {
        s.micToggleBtn.addEventListener("click", async () => {
            if (reconhecimentoAtivo()) {
                pararReconhecimentoVoz();
            } else {
                await iniciarReconhecimentoVoz();
            }
            const active = reconhecimentoAtivo();
            s.micToggleBtn.textContent = active ? "MICROFONE ATIVO" : "ATIVAR MICROFONE";
            s.micToggleBtn.classList.toggle("active", active);
            s.micToggleBtn.setAttribute("aria-pressed", String(active));
        });
    }

    // Capture undo state on input
    if (s.editor) {
        s.editor.addEventListener("input", () => {
            clearTimeout(s.editor._undoDebounce);
            s.editor._undoDebounce = setTimeout(saveUndoState, 300);
        });
        saveUndoState();
    }

    // Undo/Redo buttons
    if (s.btnUndo) s.btnUndo.addEventListener("click", performUndo);
    if (s.btnRedo) s.btnRedo.addEventListener("click", performRedo);

    // Font controls
    if (s.fontName) {
        s.fontName.addEventListener("change", () => {
            s.estiloTexto.fonte = s.fontName.value;
            aplicarEstiloTexto();
            publicarEstilo();
        });
    }

    if (s.fontSize) {
        s.fontSize.addEventListener("change", () => {
            s.estiloTexto.tamanho = Number(s.fontSize.value);
            aplicarEstiloTexto();
            publicarEstilo();
            sincronizarTeleprompter(s.indiceAtualVisual);
        });
    }

    if (s.btnBold) {
        s.btnBold.addEventListener("click", () => {
            s.estiloTexto.negrito = !s.estiloTexto.negrito;
            aplicarEstiloTexto();
            publicarEstilo();
        });
    }

    if (s.btnItalic) {
        s.btnItalic.addEventListener("click", () => {
            s.estiloTexto.italico = !s.estiloTexto.italico;
            aplicarEstiloTexto();
            publicarEstilo();
        });
    }

    if (s.btnUnderline) {
        s.btnUnderline.addEventListener("click", () => {
            s.estiloTexto.sublinhado = !s.estiloTexto.sublinhado;
            aplicarEstiloTexto();
            publicarEstilo();
        });
    }

    if (s.mirrorBtn) {
        s.mirrorBtn.addEventListener("click", () => {
            s.estiloTexto.espelhado = !s.estiloTexto.espelhado;
            aplicarEstiloTexto();
            publicarEstilo();
        });
    }

    // Speed wheel - limits will be set from config_rolagem
    function atualizarSpeedWheelLimites() {
        if (!s.speedWheel || !s.configuracaoRolagem) return;
        const min = s.configuracaoRolagem.velocidadeMinima ?? 0.25;
        const max = s.configuracaoRolagem.velocidadeMaxima ?? 2.5;
        s.speedWheel.min = String(min);
        s.speedWheel.max = String(max);
        s.speedWheel.step = "0.05";
        const val = Number(s.speedWheel.value);
        if (val < min) {
            s.speedWheel.value = String(min);
            s.fatorManualVelocidade = min;
            localStorage.setItem("tp_velocidade", String(min));
        } else if (val > max) {
            s.speedWheel.value = String(max);
            s.fatorManualVelocidade = max;
            localStorage.setItem("tp_velocidade", String(max));
        }
    }

    if (s.speedWheel) {
        s.speedWheel.min = "0.25";
        s.speedWheel.max = "2.5";
        s.speedWheel.step = "0.05";
        s.speedWheel.value = String(s.fatorManualVelocidade);

        s.speedWheel.addEventListener("input", () => {
            s.fatorManualVelocidade = Number(s.speedWheel.value);
            localStorage.setItem("tp_velocidade", String(s.fatorManualVelocidade));
            console.log("Fator manual da rolagem:", s.fatorManualVelocidade);
        });
    }

    // Update speed wheel limits when config arrives
    s.socket.on("config_rolagem", (dados) => {
        s.configuracaoRolagem = dados;
        atualizarSpeedWheelLimites();
    });

    // File operations
    if (s.btnOpenFile && s.fileInput) {
        s.btnOpenFile.addEventListener("click", () => s.fileInput.click());
    }

    if (s.fileInput) {
        s.fileInput.addEventListener("change", async () => {
            const arquivo = s.fileInput.files[0];
            if (!arquivo) return;

            try {
                const conteudo = await arquivo.text();
                const extensao = arquivo.name.split(".").pop().toLowerCase();
                let payload;

                if (extensao === "json") {
                    payload = JSON.parse(conteudo);
                } else if (extensao === "txt") {
                    payload = { slugs: [{ body: conteudo }] };
                } else {
                    throw new Error("Formato não suportado. Abra um arquivo .json ou .txt.");
                }

                if (!s.socket?.connected) {
                    throw new Error("A conexão com o servidor ainda não está pronta.");
                }

                const resultado = await new Promise((resolve, reject) => {
                    const timeout = setTimeout(
                        () => reject(new Error("O servidor demorou para processar o roteiro.")),
                        15000
                    );

                    s.socket.emit("load_script", withAuth({ payload }), resposta => {
                        clearTimeout(timeout);
                        if (resposta?.ok) {
                            resolve(resposta);
                        } else {
                            reject(new Error(resposta?.error || "Não foi possível interpretar o arquivo."));
                        }
                    });
                });

                console.info(`Roteiro carregado: ${resultado.lineCount} linhas.`);
            } catch (error) {
                window.alert(`Não foi possível abrir o roteiro: ${error.message}`);
            } finally {
                s.fileInput.value = "";
            }
        });
    }

    if (s.btnSaveFile) {
        s.btnSaveFile.addEventListener("click", () => {
            const container = s.editor || s.display;
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

    // Manual navigation
    if (s.btnNext) s.btnNext.addEventListener("click", enviarAvancoManual);
    if (s.btnPrev) s.btnPrev.addEventListener("click", enviarRetornoManual);
    if (s.btnPlayLocal) s.btnPlayLocal.addEventListener("click", alternarPausaMotor);

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

    // Scroll toggle
    if (s.scrollToggleBtn) {
        s.scrollToggleBtn.addEventListener("click", () => {
            s.rolagemContinuaAtiva = !s.rolagemContinuaAtiva;
            s.rolagemInterrompidaManualmente = !s.rolagemContinuaAtiva;
            atualizarTextoBotaoRolagem();
            if (s.rolagemContinuaAtiva) {
                iniciarTemporizadorDaLinha();
            } else {
                pararRolagemContinua();
            }
        });
    }

    // WinPlus toggle
    if (s.winplusToggleBtn && s.appBody) {
        s.winplusToggleBtn.addEventListener("click", () => {
            const isInactive = s.appBody.classList.contains("winplus-inactive");

            if (isInactive) {
                s.appBody.classList.remove("winplus-inactive");
                s.appBody.classList.add("winplus-active");
                s.winplusToggleBtn.textContent = "□ TELA CHEIA";
                s.winplusToggleBtn.classList.remove("active-stop");
            } else {
                s.appBody.classList.remove("winplus-active");
                s.appBody.classList.add("winplus-inactive");
                s.winplusToggleBtn.textContent = "▣ MODO OPERADOR";
                s.winplusToggleBtn.classList.remove("active-stop");
            }

            requestAnimationFrame(() => {
                s.ultimoFrame = null;
                sincronizarTeleprompter(s.indiceAtualVisual, { preservarRolagem: true });
            });
        });
    }

    document.addEventListener("keydown", (e) => {
        if (
            e.key === "Escape" &&
            s.appBody &&
            s.appBody.classList.contains("winplus-active") &&
            s.winplusToggleBtn
        ) {
            e.preventDefault();
            s.winplusToggleBtn.click();
        }
    });

    // Toolbar hide/restore
    if (s.btnClose) {
        s.btnClose.onclick = () => {
            if (s.mainToolbar) s.mainToolbar.classList.add("toolbar-hidden");
            if (s.sidePanel) s.sidePanel.classList.add("hidden");
            if (s.btnRestore) s.btnRestore.classList.remove("hidden");
        };
    }

    if (s.btnRestore) {
        s.btnRestore.onclick = () => {
            if (s.mainToolbar) s.mainToolbar.classList.remove("toolbar-hidden");
            if (s.sidePanel) s.sidePanel.classList.remove("hidden");
            s.btnRestore.classList.add("hidden");
        };
    }

    // Block selection on teleprompter text
    [s.editor, s.display].forEach(container => {
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

    initStorageSync();
}
