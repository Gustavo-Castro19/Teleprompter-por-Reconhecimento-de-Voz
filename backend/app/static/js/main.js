// ============================================================
// MAIN - Teleprompter entry point (ES Module)
// ============================================================

import { initElements } from "./state.js";
import { initUI } from "./ui.js";
import { initSocket } from "./socket.js";
import { animarRolagemContinua } from "./scroller.js";
import { initSpeechRecognition } from "./voice.js";

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

    console.log("Teleprompter frontend (modular) loaded.");
    console.log("Web Speech API supported:", "webkitSpeechRecognition" in window || "SpeechRecognition" in window);
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}
