import hashlib
import getpass
import sys
import time
import os
import json
import pyaudio
import unicodedata
import re
from difflib import SequenceMatcher
from flask import Flask, render_template
from flask_socketio import SocketIO
from vosk import Model, KaldiRecognizer

# --- 🔒 TRAVA DE SEGURANÇA ---
__AUTOR__ = "Diego Marcelo & Ana Luísa - SQUAD 29"
# -----------------------------

class Cores:
    BASE = "\033[0m" # Valor padrão de textos do teleprompt
    NEGRITO = "\033[1m"
    VERDE = "\033[92m"
    VERMELHO = "\033[91m"
    CIANO = "\033[96m"
    BG_CIANO = "\033[46m" # Valor de cor de fundo na cor ciano
    PRETO = "\033[30m"

def checagem_seguranca():
    os.system('cls' if os.name == 'nt' else 'clear')
    try:
        if globals().get("__AUTOR__") != "Diego Marcelo & Ana Luísa - SQUAD 29":
            raise ValueError("Falha na verificação de integridade")
    except:
        print("Erro de integridade.")
        sys.exit(1)

    print("\n" + "="*60)
    print(f"{Cores.BG_CIANO}{Cores.PRETO}{Cores.NEGRITO}  Mecanismo de transmissão de teleprompter - SQUAD 29  {Cores.BASE}")
    print(f"{Cores.CIANO}  Devs: {__AUTOR__} {Cores.BASE}")
    print("="*60 + "\n")
    
    # Hash é um algoritmo matemático que transforma data em uma sequência única de caracteres de comprimento fixo, seria um cpf para o dado
    # o Hash abaixo se trata da senha que está sendo usada para poder usar o nosso sistema.
    HASH_CORRETO = "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92"

    tentativas = 3
    while tentativas > 0:
        try:
            senha = getpass.getpass(f"Senha de Acesso ({tentativas}x): ")
        except:
            senha = input(f"Senha de Acesso ({tentativas}x): ")
            
        if hashlib.sha256(senha.encode()).hexdigest() == HASH_CORRETO:
            print(f"\n{Cores.VERDE}✔ Sistema Armado.{Cores.BASE}\n")
            time.sleep(1)
            return
        else:
            print(f"{Cores.VERMELHO}Senha incorreta.{Cores.BASE}")
            tentativas -= 1
    sys.exit(1)

app = Flask(__name__)
app.config['CHAVE_ACESSO'] = 'chave_squad29'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=60)

# --- CONFIGURAÇÕES ---
CONFIG = {
    "caminho_modelo": "model",
    "caminho_roteiro": "BDDF-07042026.txt",

    # Similaridade mínima para leitura sequencial
    "limite_similaridade": 0.60, 

    # Valores para consideração de saltos globais
    "caracteres_minimos": 37,  
    "limite_similaridade_alto": 0.92,  
    "limite_similaridade_baixo": 0.88,   

    # Mínimo de caracteres reconhecidos para tentar qualquer match
    "caracteres_minimos_reconhecimento": 8,

    # Cobertura mínima da linha que precisa ter sido falada antes de avançar.
    # Ex: linha tem 60 chars → precisa ter falado >= 33 chars (ratio 0.55)
    # Baixo demais = avanço precoce | Alto demais = precisa repetir a frase
    "cobertura_minima_final": 0.65, 

    # Na cobertura para parciais a exigência é um pouco maior (transcrição ainda incompleta)
    "cobertura_minima_parcial": 0.70, 
    
    "avanco_parcial": 0.88,

    # Segundos bloqueados após cada avanço de linha.
    # Impede cascata sem travar o ritmo normal de leitura.
    "intervalo_avanco": 1.0,
}

# define as configurações das variáveis que estão formatando o texto sendo usado
# seja ele vindo das transcrições ou metodos para configurar avanços no roteiro
class UtilTexto:
    @staticmethod
    def normaliza(text):
        if not text: return ""
        text = text.lower().strip()
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        text = re.sub(r"[^a-z0-9\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def similaridade(a, b):
        return SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def verificar_correspondencia_normal(falado, linha, thresh, parcial=False):
        """
        Retorna True se o trecho falado corresponde ao início da linha.

        Correções contra avanço precoce:
          1. caracteres_minimos_reconhecimento   — ignora se falou muito pouco
          2. cobertura_minima                    — precisa ter falado boa parte da linha
          3. cobertura_minima_parcial            — parciais têm exigência ainda maior
        """
        n_falado = UtilTexto.normaliza(falado)
        n_linha   = UtilTexto.normaliza(linha)

        # 1. Muito pouco texto — ignora
        if len(n_falado) < CONFIG["caracteres_minimos_reconhecimento"]:
            return False

        # 2. Cobertura mínima
        cobertura  = len(n_falado) / max(len(n_linha), 1)
        cobertura_minima = (CONFIG["cobertura_minima_parcial"]
                     if parcial else CONFIG["cobertura_minima_final"])
        if cobertura < cobertura_minima:
            return False

        # 3a. Comparação com o INÍCIO da linha
        inicio_trecho = n_linha[:len(n_falado) + 5]
        inicio_sim = UtilTexto.similaridade(n_falado, inicio_trecho)

        # 3b. Comparação com o MEIO/FIM da linha
        # Cobre o caso em que o apresentador está lendo a parte final da linha
        final_sim = 0.0

        # 3c. Melhor similaridade encontrada em qualquer parte da linha
        # Também verifica se o falado está contido na linha (ex: trecho do meio)
        melhor_sim = max(inicio_sim, final_sim)

        # LOG: mostra quando quase deu match
        if melhor_sim >= 0.45 and melhor_sim < thresh:
            print(f"  [QUASE] sim_inicio={inicio_sim:.2f} sim_fim={final_sim:.2f} (precisa {thresh:.2f}) cobertura={cobertura:.2f}")
            print(f"  [QUASE] falado : '{n_falado[:70]}'")
            print(f"  [QUASE] roteiro: '{n_linha[:70]}'")

        if melhor_sim >= thresh:
            return True

        # 4. Recuperação de improviso: apresentador falou além da linha
        if len(n_falado) > len(n_linha):
            sufixo = n_falado[-(len(n_linha) + 5):]
            if n_linha in sufixo:
                return True
            if UtilTexto.similaridade(sufixo, n_linha) >= thresh:
                return True

        return False

    @staticmethod
    def verificar_dinamica_correspondencia(falado, linha):
        """Comparação rígida usada SOMENTE em saltos globais (final_resultado final)."""
        n_falado = UtilTexto.normaliza(falado)
        n_linha   = UtilTexto.normaliza(linha)

        if len(n_falado) < CONFIG["caracteres_minimos"]:
            return False

        limite = (CONFIG["limite_similaridade_alto"]
                     if len(n_falado) < 40 else CONFIG["limite_similaridade_baixo"])

        tam_trecho  = min(len(n_falado), len(n_linha))
        comeco_falado = n_falado[:tam_trecho]
        comeco_linha   = n_linha[:tam_trecho]
        if UtilTexto.similaridade(comeco_falado, comeco_linha) >= limite:
            return True

        if len(n_falado) > len(n_linha) + 5:
            sufixo = n_falado[-(len(n_linha) + 5):]
            if UtilTexto.similaridade(sufixo, n_linha) >= limite:
                return True

        return False


# indica as princiapis funções do teleprompt, definindo a abertura do roteiro e que partes do roteiro
# devem ser lidas ou mostradas
class EstruturaTelePrompt:
    def __init__(self):
        self.linhas_roteiro = []
        self.linhas_exibidas = []
        self.falar_para_exibir = []
        self.idx_atual = 0
        self.correndo = False  # refere a se o sistema está ativo, captando áudio, ou não
        self.proc_audio = None
        self.tempo_ultimo_avanco = 0.0   # timestamp do último avanço
        self.descartar_buffer = False  # sinaliza descarte do buffer de áudio
        self.ultimo_texto_parcial = ""
        self.contagem_leitura_parcial = 0  # usado para verificações de segurança que determinam saltos no roteiro a partir de transcrições parciais
        self.recomecar_bloco_parcial = False
        self.carregar_roteiro()

    def carregar_roteiro(self):
        if os.path.exists(CONFIG["caminho_roteiro"]):
            try:
                with open(CONFIG["caminho_roteiro"], "r", encoding="utf-8") as f:
                    data = json.load(f)

                texto_roteiro = ""
                texto_exibido = ""
                idx_exibido = 0 # index da linha atual que está sendo exibida no teleprompt
                self.falar_para_exibir = []

                if "slugs" in data:
                    # Processar também notesWithBody
                    for slug in data["slugs"]:
                        if "notesWithBody" in slug:
                            for nota in slug["notesWithBody"]:
                                if "text" in nota:
                                    for item_texto in nota["text"]:
                                        # body se refere aos dados que estão vindo do roteiro
                                        body_cru = item_texto

                                        # Normaliza quebras de linha antes de processar
                                        body_cru = body_cru.replace('\r\r\n', '\n').replace('\r', '\n')

                                        # Corpo de visualização: remove tags HTML, mas mantém o texto interno
                                        body_exibido = re.sub(r'<[^>]+>', '\n', body_cru)
                                        texto_exibido += body_exibido + "\n"

                                        # Corpo do roteiro falado: remove o conteúdo de <pi> antes de remover outras tags
                                        body_roteiro = re.sub(r'<pi>.*?</pi>', ' ', body_cru, flags=re.DOTALL)
                                        body_roteiro = re.sub(r'<[^>]+>', '\n', body_roteiro)

                                        linhas_limpas = []
                                        linhas_cruas_exibidas = body_exibido.split('\n')
                                        linhas_cruas_roteiro = body_roteiro.split('\n')

                                        for idx, linha in enumerate(linhas_cruas_exibidas):
                                            linha = linha.strip()
                                            if linha:
                                                idx_atualmente_exibido = idx_exibido
                                                idx_exibido += 1
                                            else:
                                                continue

                                            if idx < len(linhas_cruas_roteiro):
                                                linha_roteiro = linhas_cruas_roteiro[idx].strip()
                                            else:
                                                linha_roteiro = ''

                                            if not linha_roteiro:
                                                continue

                                            # Verifica se a linha original tinha <pi> — se sim, não adiciona ao falar_para_exibir
                                            if idx < len(linhas_cruas_exibidas) and '<pi>' in linhas_cruas_exibidas[idx]:
                                                continue

                                            # Pula comandos internos tipo {{FRED EM OFF}}
                                            if linha_roteiro.startswith('{{') or linha_roteiro.startswith('{'):
                                                continue
                                            # Pula comandos tipo {FRED}
                                            if linha_roteiro.startswith('{') and linha_roteiro.endswith('}'):
                                                continue

                                            # Pula separadores tipo ==========
                                            if re.fullmatch(r'=+', linha_roteiro):
                                                continue

                                            # Pula linhas sem letras
                                            if not re.search(r'[A-Za-zÀ-ÿ]', linha_roteiro):
                                                continue

                                            linha_falada = linha_roteiro

                                            linha_falada = re.sub(r'\{\{.*?\}\}', ' ', linha_falada)
                                            linha_falada = re.sub(r'\{.*?\}', ' ', linha_falada)
                                            linha_falada = re.sub(r'\[.*?\]', ' ', linha_falada)
                                            linha_falada = re.sub(r'\(.*?\)', ' ', linha_falada)

                                            # Remove barras e sinais usados como marcação
                                            linha_falada = linha_falada.replace('/', ' ')
                                            linha_falada = re.sub(r'=+', ' ', linha_falada)

                                            # Normaliza espaços
                                            linha_falada = re.sub(r'\s+', ' ', linha_falada).strip()

                                            if not linha_falada:
                                                continue

                                            self.falar_para_exibir.append(idx_atualmente_exibido)
                                            linhas_limpas.append(linha_falada)

                                        texto_roteiro += "\n".join(linhas_limpas) + "\n"


                self.linhas_exibidas = [
                    l.strip()
                    for l in texto_exibido.split('\n')
                    if l.strip()
                ]

                self.linhas_roteiro = [
                    l.strip()
                    for l in texto_roteiro.split('\n')
                    if l.strip()
                ]

            except Exception as e:
                self.linhas_roteiro = [f"ERRO: Falha ao carregar roteiro: {str(e)}"]
        else:
            self.linhas_roteiro = ["ERRO: Roteiro não encontrado"]

    def iniciar_maquina(self):
        if self.proc_audio: return
        self.correndo = True
        self.proc_audio = socketio.start_background_task(self.processar_laco_audio)

    def processar_laco_audio(self):
        print(f"{Cores.VERDE}--- MáQUINA ATIVA ---{Cores.BASE}")
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

            print("--- MICROFONE ABERTO ---")

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
        
        if idx < len(self.falar_para_exibir):
            mostrar_idx = self.falar_para_exibir[idx]
        else:
            mostrar_idx = len(self.linhas_exibidas) - 1

        socketio.emit('cmd', {'index': mostrar_idx, 'type': tipo_evento, 'text': txt})
        print(f"--> [{tipo_evento.upper()}] Indo para linha falada {idx + 1}, visual {mostrar_idx + 1}")
        
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
                print(f"[PARCIAL-BASE] '{texto}' | linha {self.idx_atual + 1}: '{linha_atual[:40]}'")
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

            print(f"[PARCIAL] '{texto}' | linha {self.idx_atual + 1}: '{linha_atual[:40]}'")
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
        print(f"[{'PARCIAL' if parcial else 'FINAL'}] '{texto}' | linha {self.idx_atual + 1}: '{linha_atual[:40]}'")
        return False


estrutura = EstruturaTelePrompt()

@app.route('/')
def index():
    return render_template('index.html', script=estrutura.linhas_exibidas)

@socketio.on('connect')
def gerenciar_conexao():
    print('CLIENTE CONECTADO')
    first_idx = estrutura.falar_para_exibir[0] if estrutura.falar_para_exibir else 0
    socketio.emit('cmd', {'index': first_idx, 'type': 'sync', 'text': ''})
    estrutura.iniciar_maquina()

if __name__ == '__main__':
    # checagem_seguranca()
    print(f"Servidor: http://127.0.0.1:5500")
    socketio.run(app, debug=True, port=5500)
