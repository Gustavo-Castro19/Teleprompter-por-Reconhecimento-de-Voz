
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
        try:
            # Inicializa o PyAudio.
            self.p = pyaudio.PyAudio()

            # Verifica se existe algum dispositivo de entrada disponível.
            quantidade_dispositivos = self.p.get_device_count()
            encontrou_microfone = False

            for indice in range(quantidade_dispositivos):
                dispositivo = self.p.get_device_info_by_index(indice)

                if dispositivo.get("maxInputChannels", 0) > 0:
                    encontrou_microfone = True
                    break

            if not encontrou_microfone:
                raise RuntimeError("Nenhum microfone/dispositivo de entrada encontrado.")

            print("Microfone/dispositivo de entrada encontrado.")

            # Abre microfone com configuração compatível com o Vosk.
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=4096
            )

            # Inicia o fluxo de áudio.
            self.stream.start_stream()

            # Descarta o primeiro buffer para estabilizar a entrada de áudio.
            self.stream.read(4096, exception_on_overflow=False)

            print("Microfone aberto com sucesso.")

        except Exception as erro:
            print(f"ERRO ao abrir microfone: {erro}")
            self.fechar_microfone()
            raise

    def ler_audio(self):
        # Verifica se o microfone foi aberto antes de tentar ler.
        if not self.stream:
            raise RuntimeError("Tentativa de ler áudio sem microfone aberto.")

        try:
            # Lê um pedaço de áudio do microfone.
            return self.stream.read(4096, exception_on_overflow=False)

        except Exception as erro:
            # Se der erro na leitura, mostra no terminal e repassa o erro.
            print(f"ERRO ao ler áudio do microfone: {erro}")
            raise

    def fechar_microfone(self):
        # Fecha o stream do microfone com segurança.
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None

        except Exception as erro:
            print(f"AVISO: erro ao fechar stream do microfone: {erro}")

        # Encerra o PyAudio com segurança.
        try:
            if self.p:
                self.p.terminate()
                self.p = None

        except Exception as erro:
            print(f"AVISO: erro ao encerrar PyAudio: {erro}")
