# Motor_audio.py
# Responsável por abrir, ler e fechar o microfone com PyAudio.
# Separar isso facilita futuras melhorias, como áudio Dante/AoIP.

import pyaudio


class MotorAudio:
    def __init__(self):
        # Instância principal do PyAudio.
        self.p = None

        # Stream do microfone.
        self.stream = None

    def abrir_microfone(self):
        # Inicializa PyAudio.
        self.p = pyaudio.PyAudio()

        # Abre microfone com configuração compatível com Vosk.
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4096
        )

        self.stream.start_stream()

        # Descarta o primeiro buffer para estabilizar a entrada de áudio.
        self.stream.read(4096, exception_on_overflow=False)

    def ler_audio(self):
        # Lê um pedaço de áudio do microfone.
        return self.stream.read(4096, exception_on_overflow=False)

    def fechar_microfone(self):
        # Fecha o stream do microfone.
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        # Encerra o PyAudio.
        if self.p:
            self.p.terminate()
