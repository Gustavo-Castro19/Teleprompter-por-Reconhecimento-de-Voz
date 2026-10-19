// ============================================================
// MAIN - Teleprompter entry point (ES Module)
// ============================================================

import { stateRef } from "./state.js";
const s = stateRef;
import { initElements } from "./state.js";
import { initUI } from "./ui.js";
import { initSocket } from "./socket.js";
import { animarRolagemContinua } from "./scroller.js";
import { initSpeechRecognition, iniciarReconhecimentoVoz, pararReconhecimentoVoz } from "./voice.js";

function init() {
    // Initialize DOM elements
    initElements();

    // Initialize SocketIO FIRST (UI depends on it)
    initSocket();

    // Initialize UI controls
    initUI();

    // Initialize Speech Recognition
    initSpeechRecognition();

    // Start animation loop
    requestAnimationFrame(animarRolagemContinua);

    // Auto-start speech recognition when motor starts
    let motorStarted = false;
    s.socket.on("status_motor", (dados) => {
        if (!window.IS_OPERATOR) return;
        if (dados.correndo && !motorStarted) {
            motorStarted = true;
            setTimeout(() => {
                iniciarReconhecimentoVoz();
            }, 500);
        }
        if (!dados.correndo) {
            motorStarted = false;
            pararReconhecimentoVoz();
        }
    });

    console.log("Teleprompter frontend (modular) loaded.");
    console.log("Web Speech API supported:", "webkitSpeechRecognition" in window || "SpeechRecognition" in window);
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}
