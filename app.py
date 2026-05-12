
import time
import os
import json
import pyaudio
import re
from flask import Flask, render_template
from flask_socketio import SocketIO
from vosk import Model, KaldiRecognizer

from configuracoes import CONFIG
from normalizador_texto import UtilTexto
from processador_roteiro import ProcessadorRoteiro
from alinhador_roteiro import AlinhadorRoteiro
from seguranca import Cores, checagem_seguranca
from maquina_estados import MaquinaEstados
from registrador_eventos import RegistradorEventos


app = Flask(__name__)
app.config['CHAVE_ACESSO'] = 'chave_squad29'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=60)


# indica as princiapis funções do teleprompt, definindo a abertura do roteiro e que partes do roteiro
# devem ser lidas ou mostradas
class EstruturaTelePrompt(ProcessadorRoteiro, MaquinaEstados):
    def __init__(self):
        MaquinaEstados.__init__(self)
        self.carregar_roteiro()

    def iniciar_maquina(self):
        if self.proc_audio: return
        self.correndo = True
        self.proc_audio = socketio.start_background_task(self.processar_laco_audio)

    def processar_laco_audio(self):
        RegistradorEventos.maquina_ativa(Cores)
        if not os.path.exists(CONFIG["caminho_modelo"]): return

        modelo      = Model(CONFIG["caminho_modelo"])
        reconhecedor = KaldiRecognizer(modelo, 16000) # reconhece o que está sendo falado e transcreve o áudio
        pa          = pyaudio.PyAudio()

        try:
            # o fluxo é onde o PyAudio é aberto para abrir o microfone e começar a receber o áudio
            fluxo = pa.open(format=pyaudio.paInt16, channels=1, rate=16000,
                            input=True, frames_per_buffer=4096)
            fluxo.start_stream()

            # Descarta o primeiro chunk (microfone inicializando)
            fluxo.read(4096, exception_on_overflow=False) # essa variavel vem do pyaudio então não é possivel alterar
            reconhecedor.Reset()

            RegistradorEventos.microfone_aberto()

            while self.correndo:
                socketio.sleep(0.001)

                # ── Flush pós-avanço ─────────────────────────────────────
                # Após avançar uma linha descartamos o áudio que ainda estava
                # no buffer do microfone para não reanalisar a mesma fala.
                if self.descartar_buffer:
                    self.descartar_buffer = False
                    reconhecedor.Reset()
                    continue
                # ─────────────────────────────────────────────────────────

                try:
                    dados = fluxo.read(4096, exception_on_overflow=False)

                    if reconhecedor.AcceptWaveform(dados):
                        # Resultado FINAL — frase completa
                        final_resultado = json.loads(reconhecedor.Result())
                        texto = final_resultado.get("text", "") 
                        if texto and self.avaliar(texto, parcial=False):
                            reconhecedor.Reset()
                    else:
                        # Resultado PARCIAL — Vosk ainda transcrevendo
                        parcial_resultado = json.loads(reconhecedor.PartialResult())
                        texto  = parcial_resultado.get("partial", "")
                        if texto and self.avaliar(texto, parcial=True):
                            reconhecedor.Reset()

                except Exception:
                    continue
        finally:
            pa.terminate()

    def enviar(self, idx, tipo_evento, txt):
        self.idx_atual     = idx
        self.tempo_ultimo_avanco = time.time()
        self.descartar_buffer     = True
        self.ultimo_texto_parcial = ""
        self.contagem_leitura_parcial = 0
        self.recomecar_bloco_parcial = False
        
        alinhador = AlinhadorRoteiro(self.falar_para_exibir, self.linhas_exibidas)
        mostrar_idx = alinhador.obter_indice_visual(idx)

        socketio.emit('cmd', {'index': mostrar_idx, 'type': tipo_evento, 'text': txt})
        RegistradorEventos.evento_rolagem(tipo_evento, idx, mostrar_idx)
        
    def avaliar(self, texto, parcial):
        total_linhas = len(self.linhas_roteiro)
        if self.idx_atual >= total_linhas:
            return False
        
        linha_atual = self.linhas_roteiro[self.idx_atual]

        # Parciais podem avançar só se a leitura estiver fluindo normal
        if parcial:
            n_texto = UtilTexto.normaliza(texto)
            n_linha_atual = UtilTexto.normaliza(linha_atual)

            # Se o parcial encolheu, a pessoa travou/recomeçou
            if len(n_texto) < len(self.ultimo_texto_parcial):
                self.ultimo_texto_parcial = n_texto
                self.contagem_leitura_parcial = 0
                self.recomecar_bloco_parcial = True
                RegistradorEventos.reconhecimento("PARCIAL-BASE", texto, self.idx_atual, linha_atual)
                return False

            self.ultimo_texto_parcial = n_texto

            # Se houve recomeço, só zera uma vez e libera o fluxo seguir
            if self.recomecar_bloco_parcial:
                self.contagem_leitura_parcial = 0
                self.recomecar_bloco_parcial = False

            cobertura = len(n_texto) / max(len(n_linha_atual), 1)

            if cobertura >= CONFIG["avanco_parcial"]:
                if UtilTexto.verificar_correspondencia_normal(
                    texto, linha_atual,
                    CONFIG["limite_similaridade"],
                    parcial=False
                ):
                    self.contagem_leitura_parcial += 1

                    # Se estiver MUITO perto do fim da frase, 1 confirmação basta
                    conf_necessarias = 1 if cobertura >= 0.95 else 2

                    if self.contagem_leitura_parcial >= conf_necessarias:
                        self.ultimo_texto_parcial = ""
                        self.contagem_leitura_parcial = 0
                        self.enviar(self.idx_atual + 1, 'next', linha_atual)
                        return True
                else:
                    self.contagem_leitura_parcial = 0
            else:
                self.contagem_leitura_parcial = 0

            RegistradorEventos.reconhecimento("PARCIAL", texto, self.idx_atual, linha_atual)
            return False
        
        # ── Cooldown pós-avanço ──────────────────────────────────────────
        # Bloqueia novos avanços pelos primeiros N segundos após o último.
        # Impede cascata causada por áudio residual no buffer.
        bloqueio = time.time() - self.tempo_ultimo_avanco
        if bloqueio < CONFIG["intervalo_avanco"]:
            return False
        # ────────────────────────────────────────────────────────────────

        
        
        # --- 1. REGRA DE OURO: Retorno à Linha 1 ---
        if total_linhas > 0 and self.idx_atual > 2:
            if UtilTexto.verificar_correspondencia_normal(
                texto, self.linhas_roteiro[0],
                CONFIG["limite_similaridade"],
                parcial=parcial
            ):
                self.enviar(0, 'back', self.linhas_roteiro[0])
                return True

        # --- 2. LEITURA SEQUENCIAL (linha atual) ---
        linha_atual = self.linhas_roteiro[self.idx_atual]
        n_texto = UtilTexto.normaliza(texto)
        n_linha_atual = UtilTexto.normaliza(linha_atual)

        if UtilTexto.verificar_correspondencia_normal(
            texto, linha_atual,
            CONFIG["limite_similaridade"],
            parcial=parcial
        ):
            

            self.recomecar_bloco_parcial = False
            self.enviar(self.idx_atual + 1, 'next', linha_atual)
            return True

        # --- 3. VARREDURA GLOBAL — SOMENTE resultados finais ---
        # Partials nunca disparam saltos; evita pulos causados por
        # transcrição incompleta que coincide com outra linha do roteiro.
        #________________________________________
        if len(texto) > CONFIG["caracteres_minimos"]:
            
            for i in range(total_linhas):
                if i == self.idx_atual: continue
                
                # Usa verificar_dinamica_correspondencia que também tem recuperação de improviso
                if UtilTexto.verificar_dinamica_correspondencia(texto, self.linhas_roteiro[i]):
                    # direção indica se o salto deve ir para frente ou para trás
                    direcao = 'jump' if i > self.idx_atual else 'back'
                    self.enviar(i + 1, direcao, self.linhas_roteiro[i])
                    return True
        #________________________________________

        linha_atual = self.linhas_roteiro[self.idx_atual]
        tipo_log = "PARCIAL" if parcial else "FINAL"
        RegistradorEventos.reconhecimento(tipo_log, texto, self.idx_atual, linha_atual)
        return False


estrutura = EstruturaTelePrompt()

@app.route('/')
def index():
    return render_template('index.html', script=estrutura.linhas_exibidas)

@socketio.on('connect')
def gerenciar_conexao():
    RegistradorEventos.cliente_conectado()
    alinhador = AlinhadorRoteiro(estrutura.falar_para_exibir, estrutura.linhas_exibidas)
    first_idx = alinhador.obter_primeiro_indice_visual()
    socketio.emit('cmd', {'index': first_idx, 'type': 'sync', 'text': ''})
    estrutura.iniciar_maquina()

if __name__ == '__main__':
    # checagem_seguranca()
    RegistradorEventos.servidor("http://127.0.0.1:5500")
    socketio.run(app, debug=True, port=5500)
