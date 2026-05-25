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
        # Pega o caminho da pasta do modelo Vosk definido nas configurações.
        caminho_modelo = CONFIG["caminho_modelo"]

        if not os.path.exists(caminho_modelo):
            print(f"ERRO: modelo Vosk não encontrado em: {caminho_modelo}")
            return False

        try:
            # Mostra no terminal que o carregamento começou.
            print(f"Carregando modelo Vosk em: {caminho_modelo}")

            # Carrega o modelo Vosk para memória.
            self.modelo = Model(caminho_modelo)

            print("Modelo Vosk carregado com sucesso.")

            # Cria o reconhecedor de fala.
            # O valor 16000 representa a taxa de amostragem do áudio.
            self.reconhecedor = KaldiRecognizer(self.modelo, 16000)

            # Limpa qualquer estado anterior do reconhecedor.
            self.reconhecedor.Reset()

            print("Reconhecedor Vosk iniciado com sucesso.")

            return True

        except Exception as erro:
            # Caso aconteça qualquer erro ao carregar o modelo,
            # mostramos a mensagem no terminal.
            print(f"ERRO ao iniciar o Vosk: {erro}")
            return False

    def processar_audio(self, dados_audio):
        # Se o reconhecedor ainda não foi iniciado, evita erro no sistema.
        if not self.reconhecedor:
            print("ERRO: reconhecedor Vosk não foi iniciado.")
            return "ERRO", ""

        try:
            # Resultado final: o Vosk entendeu que a frase fechou.
            if self.reconhecedor.AcceptWaveform(dados_audio):
                resultado = json.loads(self.reconhecedor.Result())
                texto = resultado.get("text", "")
                return "FINAL", texto

            # Resultado parcial: o Vosk ainda está formando a frase.
            resultado = json.loads(self.reconhecedor.PartialResult())
            texto = resultado.get("partial", "")

            return "PARCIAL", texto

        except Exception as erro:
            # Caso ocorra erro ao processar áudio, retorna vazio sem quebrar o motor.
            print(f"ERRO ao processar áudio no Vosk: {erro}")
            return "ERRO", ""

    def resetar(self):
        # Reseta o reconhecedor para evitar repetição de áudio antigo.
        if self.reconhecedor:
            self.reconhecedor.Reset()
