# Motor_audio.py
# Responsável por abrir, ler e fechar o microfone com PyAudio.
# Separar isso facilita futuras melhorias, como áudio Dante/AoIP.

import pyaudio

from configuracoes import CONFIG


class MotorAudio:
    def __init__(self):
        # Instância principal do PyAudio.
        self.p = None

        # Stream do microfone.
        self.stream = None

        # Índice do dispositivo selecionado.
        self.device_index = None

    def listar_dispositivos(self):
        """
        Retorna lista de dispositivos de entrada de áudio disponíveis.
        Cada item: {"index": int, "name": str, "maxInputChannels": int, "defaultSampleRate": float}
        """
        if not self.p:
            self.p = pyaudio.PyAudio()

        dispositivos = []
        quantidade = self.p.get_device_count()

        for indice in range(quantidade):
            try:
                info = self.p.get_device_info_by_index(indice)
                if info.get("maxInputChannels", 0) > 0:
                    dispositivos.append({
                        "index": indice,
                        "name": info.get("name", f"Dispositivo {indice}"),
                        "maxInputChannels": info.get("maxInputChannels", 0),
                        "defaultSampleRate": info.get("defaultSampleRate", 16000)
                    })
            except Exception:
                continue

        return dispositivos

    def abrir_microfone(self, device_index=None):
        """
        Abre o microfone com o dispositivo especificado.
        Se device_index for None, usa o configurado ou auto-seleciona o primeiro disponível.
        """
        try:
            # Inicializa o PyAudio se necessário.
            if not self.p:
                self.p = pyaudio.PyAudio()

            # Determina qual dispositivo usar.
            audio_config = CONFIG.get("audio", {})
            target_index = device_index if device_index is not None else audio_config.get("device_index")
            sample_rate = audio_config.get("sample_rate", 16000)
            channels = audio_config.get("channels", 1)
            chunk_size = audio_config.get("chunk_size", 2048)
            open_chunk_size = audio_config.get("open_chunk_size", 2048)

            # Se não há índice alvo, auto-seleciona o primeiro com entrada.
            if target_index is None:
                dispositivos = self.listar_dispositivos()
                if not dispositivos:
                    raise RuntimeError("Nenhum microfone/dispositivo de entrada encontrado.")

                # Preferir dispositivos virtuais (pipewire, pulse, default) que suportam resampling
                preferidos = ["pipewire", "pulse", "default", "sysdefault"]
                target_index = None

                for pref in preferidos:
                    for d in dispositivos:
                        if pref.lower() in d["name"].lower():
                            target_index = d["index"]
                            print(f"Auto-selecionado dispositivo preferido: {d['name']} (index {target_index})")
                            break
                    if target_index is not None:
                        break

                # Fallback para o primeiro disponível
                if target_index is None:
                    target_index = dispositivos[0]["index"]
                    print(f"Auto-selecionado primeiro dispositivo: {dispositivos[0]['name']} (index {target_index})")
            else:
                # Valida se o dispositivo existe e tem entrada.
                try:
                    info = self.p.get_device_info_by_index(target_index)
                    if info.get("maxInputChannels", 0) <= 0:
                        raise RuntimeError(f"Dispositivo {target_index} não possui canais de entrada.")
                    print(f"Usando dispositivo de áudio configurado: {info.get('name')} (index {target_index})")
                except Exception as e:
                    print(f"Dispositivo {target_index} inválido: {e}. Tentando auto-seleção...")
                    dispositivos = self.listar_dispositivos()
                    if not dispositivos:
                        raise RuntimeError("Nenhum microfone/dispositivo de entrada encontrado.")
                    target_index = dispositivos[0]["index"]
                    print(f"Auto-selecionado dispositivo de áudio: {dispositivos[0]['name']} (index {target_index})")

            self.device_index = target_index

            # Abre microfone com configuração compatível com o Vosk.
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=target_index,
                frames_per_buffer=chunk_size
            )

            # Inicia o fluxo de áudio.
            self.stream.start_stream()

            # Descarta o primeiro buffer para estabilizar a entrada de áudio.
            return self.stream.read(open_chunk_size, exception_on_overflow=False)

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
