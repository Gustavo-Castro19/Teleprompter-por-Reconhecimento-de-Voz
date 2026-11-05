import { useCallback, useEffect, useRef, useState } from "react";
import { getActiveAudioInputConfigs } from "../lib/audioInputStorage";

type CaptureStatus = "idle" | "listening" | "reconnecting" | "error";

const LANG = "pt-BR";
const MAX_NETWORK_RETRIES = 6;
const NETWORK_RETRY_MS = 600;
/** Interim chega em rajadas; ~150ms reduz re-renders sem atrasar finais. */
const INTERIM_THROTTLE_MS = 150;

function getSpeechRecognitionCtor(): (new () => SpeechRecognition) | null {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

export function useSpeechCapture() {
  const [status, setStatus] = useState<CaptureStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState("");

  const listeningRef = useRef(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const committedRef = useRef("");
  const sessionFinalRef = useRef("");
  const networkRetriesRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const preferredLabelRef = useRef("default mic");
  const lastInterimEmitRef = useRef(0);
  const pendingInterimRef = useRef<string | null>(null);
  const interimTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearRetryTimer = useCallback(() => {
    if (retryTimerRef.current !== null) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
  }, []);

  const clearInterimTimer = useCallback(() => {
    if (interimTimerRef.current !== null) {
      clearTimeout(interimTimerRef.current);
      interimTimerRef.current = null;
    }
    pendingInterimRef.current = null;
  }, []);

  const publishTranscript = useCallback((full: string) => {
    console.log("[speech]", full);
    networkRetriesRef.current = 0;
    setError(null);
    setStatus("listening");
    setTranscript(full);
  }, []);

  const detachRecognition = useCallback(() => {
    const recognition = recognitionRef.current;
    recognitionRef.current = null;
    if (!recognition) return;

    recognition.onresult = null;
    recognition.onerror = null;
    recognition.onend = null;
    try {
      recognition.abort();
    } catch {
      /* already stopped */
    }
  }, []);

  const stop = useCallback(() => {
    listeningRef.current = false;
    networkRetriesRef.current = 0;
    clearRetryTimer();
    clearInterimTimer();
    detachRecognition();
    setStatus("idle");
  }, [clearRetryTimer, clearInterimTimer, detachRecognition]);

  const bindRecognition = useCallback(
    (recognition: SpeechRecognition) => {
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = LANG;

      recognition.onresult = (event) => {
        let sessionFinal = "";
        let interim = "";
        let sawFinal = false;

        for (let i = 0; i < event.results.length; i++) {
          const piece = event.results[i][0]?.transcript ?? "";
          if (event.results[i].isFinal) {
            sessionFinal += `${piece} `;
            sawFinal = true;
          } else {
            interim = piece;
          }
        }

        sessionFinalRef.current = sessionFinal.trim();
        const full = `${committedRef.current} ${sessionFinal} ${interim}`
          .replace(/\s+/g, " ")
          .trim();

        // Finais passam na hora; interim sofre throttle.
        if (sawFinal) {
          clearInterimTimer();
          lastInterimEmitRef.current = Date.now();
          publishTranscript(full);
          return;
        }

        const now = Date.now();
        const elapsed = now - lastInterimEmitRef.current;
        if (elapsed >= INTERIM_THROTTLE_MS) {
          lastInterimEmitRef.current = now;
          pendingInterimRef.current = null;
          if (interimTimerRef.current !== null) {
            clearTimeout(interimTimerRef.current);
            interimTimerRef.current = null;
          }
          publishTranscript(full);
          return;
        }

        pendingInterimRef.current = full;
        if (interimTimerRef.current === null) {
          interimTimerRef.current = setTimeout(() => {
            interimTimerRef.current = null;
            const pending = pendingInterimRef.current;
            pendingInterimRef.current = null;
            if (pending === null || !listeningRef.current) return;
            lastInterimEmitRef.current = Date.now();
            publishTranscript(pending);
          }, INTERIM_THROTTLE_MS - elapsed);
        }
      };

      recognition.onerror = (event) => {
        console.warn("[speech] error", event.error, event.message);

        if (event.error === "aborted" || event.error === "no-speech") {
          return;
        }

        if (event.error === "network") {
          if (!listeningRef.current) return;

          if (networkRetriesRef.current >= MAX_NETWORK_RETRIES) {
            listeningRef.current = false;
            clearRetryTimer();
            clearInterimTimer();
            detachRecognition();
            setStatus("error");
            setError(
              "Falha de rede no reconhecimento de voz. Verifique a conexão e tente de novo.",
            );
            return;
          }

          networkRetriesRef.current += 1;
          setStatus("reconnecting");
          setError(null);
          console.log(
            "[speech] network — recreating recognizer",
            networkRetriesRef.current,
          );

          clearRetryTimer();
          clearInterimTimer();
          detachRecognition();

          retryTimerRef.current = setTimeout(() => {
            if (!listeningRef.current) return;
            const Ctor = getSpeechRecognitionCtor();
            if (!Ctor) return;

            if (sessionFinalRef.current) {
              committedRef.current =
                `${committedRef.current} ${sessionFinalRef.current}`
                  .replace(/\s+/g, " ")
                  .trim();
              sessionFinalRef.current = "";
            }

            const next = new Ctor();
            recognitionRef.current = next;
            bindRecognition(next);
            try {
              next.start();
              console.log("[speech] reconnected", preferredLabelRef.current);
            } catch (err) {
              console.warn("[speech] reconnect start failed", err);
            }
          }, NETWORK_RETRY_MS);
          return;
        }

        if (!listeningRef.current) return;
        listeningRef.current = false;
        clearRetryTimer();
        clearInterimTimer();
        detachRecognition();
        setStatus("error");
        setError(event.message || `Erro de reconhecimento: ${event.error}`);
      };

      recognition.onend = () => {
        if (sessionFinalRef.current) {
          committedRef.current =
            `${committedRef.current} ${sessionFinalRef.current}`
              .replace(/\s+/g, " ")
              .trim();
          sessionFinalRef.current = "";
        }

        if (!listeningRef.current) return;
        if (recognitionRef.current !== recognition) return;

        try {
          recognition.start();
        } catch (err) {
          console.warn("[speech] restart failed", err);
        }
      };
    },
    [clearRetryTimer, clearInterimTimer, detachRecognition, publishTranscript],
  );

  const start = useCallback(async () => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      setStatus("error");
      setError("Reconhecimento de voz não é suportado neste navegador.");
      return;
    }

    stop();
    listeningRef.current = true;
    networkRetriesRef.current = 0;
    committedRef.current = "";
    sessionFinalRef.current = "";
    lastInterimEmitRef.current = 0;
    setTranscript("");
    setError(null);
    setStatus("listening");

    const preferred = getActiveAudioInputConfigs()[0];
    preferredLabelRef.current = preferred?.label ?? "default mic";

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: preferred?.deviceId
          ? { deviceId: { ideal: preferred.deviceId } }
          : true,
      });
      stream.getTracks().forEach((track) => track.stop());
    } catch (err) {
      console.error("[speech] getUserMedia failed", err);
      listeningRef.current = false;
      setStatus("error");
      setError("Não foi possível acessar o microfone.");
      return;
    }

    if (!listeningRef.current) return;

    const recognition = new Ctor();
    recognitionRef.current = recognition;
    bindRecognition(recognition);

    try {
      recognition.start();
      console.log("[speech] started", preferredLabelRef.current);
    } catch (err) {
      console.error("[speech] start failed", err);
      listeningRef.current = false;
      setStatus("error");
      setError("Não foi possível iniciar o reconhecimento de voz.");
    }
  }, [bindRecognition, stop]);

  const clearTranscript = useCallback(() => {
    committedRef.current = "";
    sessionFinalRef.current = "";
    clearInterimTimer();
    setTranscript("");
  }, [clearInterimTimer]);

  const toggle = useCallback(() => {
    if (listeningRef.current) {
      stop();
    } else {
      void start();
    }
  }, [start, stop]);

  useEffect(() => {
    return () => {
      listeningRef.current = false;
      clearRetryTimer();
      clearInterimTimer();
      detachRecognition();
    };
  }, [clearRetryTimer, clearInterimTimer, detachRecognition]);

  return {
    status,
    error,
    transcript,
    clearTranscript,
    start,
    stop,
    toggle,
    isSupported: getSpeechRecognitionCtor() !== null,
  };
}
