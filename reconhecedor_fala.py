# Cuida do Vosk: parcial, final, reset e erros.

# Reconhecedor_fala.py
# Responsável por inicializar e usar o Vosk.
# Ele recebe áudio bruto e devolve texto parcial ou final.

import os
import json
from vosk import Model, KaldiRecognizer

from configuracoes import CONFIG


class ReconhecedorFala:
    def __init__(self):
        # Modelo Vosk carregado em memória.
        self.modelo = None

        # Objeto responsável por reconhecer a fala.
        self.reconhecedor = None

    def iniciar(self):
        # Verifica se o modelo Vosk existe.
        if not os.path.exists(CONFIG["caminho_modelo"]):
            return False

        # Carrega o modelo Vosk.
        self.modelo = Model(CONFIG["caminho_modelo"])

        # Cria o reconhecedor para áudio de 16 kHz.
        self.reconhecedor = KaldiRecognizer(self.modelo, 16000)

        # Limpa qualquer estado anterior.
        self.reconhecedor.Reset()

        return True

    def processar_audio(self, dados_audio):
        # Resultado final: o Vosk entendeu que a frase fechou.
        if self.reconhecedor.AcceptWaveform(dados_audio):
            resultado = json.loads(self.reconhecedor.Result())
            texto = resultado.get("text", "")
            return "FINAL", texto

        # Resultado parcial: o Vosk ainda está formando a frase.
        resultado = json.loads(self.reconhecedor.PartialResult())
        texto = resultado.get("partial", "")

        return "PARCIAL", texto

    def resetar(self):
        # Reseta o reconhecedor para evitar repetição de áudio antigo.
        if self.reconhecedor:
            self.reconhecedor.Reset()
