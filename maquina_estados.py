

# Controla AUTOMATICO, MANUAL, VT_OU_LINK, IMPROVISO, FALHA.
# Centraliza o estado atual do teleprompter durante a execução.

from registrador_eventos import RegistradorEventos

# Estados principais do teleprompter.
# Eles ajudam o sistema a saber como deve se comportar em cada momento.
ESTADO_AUTOMATICO = "AUTOMATICO"
ESTADO_PAUSADO = "PAUSADO"
ESTADO_FINALIZADO = "FINALIZADO"
ESTADO_FALHA = "FALHA"
ESTADO_IMPROVISO = "IMPROVISO"


class MaquinaEstados:
    def __init__(self):
        self.linhas_roteiro = []
        self.linhas_exibidas = []
        self.falar_para_exibir = []
        self.idx_atual = 0
        # Estado operacional atual do teleprompter.
        # Começa pausado até o app.py iniciar o motor.
        self.estado_atual = ESTADO_PAUSADO
        self.correndo = False  # refere a se o sistema está ativo, captando áudio, ou não
        self.proc_audio = None
        self.tempo_ultimo_avanco = 0.0   # timestamp do último avanço
        self.descartar_buffer = False  # sinaliza descarte do buffer de áudio
        self.ultimo_texto_parcial = ""
        self.contagem_leitura_parcial = 0  # usado para verificações de segurança que determinam saltos no roteiro a partir de transcrições parciais
        self.recomecar_bloco_parcial = False

    def mudar_estado(self, novo_estado):
        # Guarda o estado anterior antes da mudança.
        estado_anterior = self.estado_atual

        # Altera o estado operacional atual do teleprompter.
        self.estado_atual = novo_estado

        # Registra a mudança de estado de forma centralizada.
        RegistradorEventos.mudanca_estado(
            estado_anterior,
            novo_estado
        )

    def esta_em_modo_automatico(self):
        # Retorna True quando o sistema está em modo automático.
        return self.estado_atual == ESTADO_AUTOMATICO

    def esta_pausado(self):
        # Retorna True quando o sistema está pausado.
        return self.estado_atual == ESTADO_PAUSADO

    def esta_finalizado(self):
        # Retorna True quando o roteiro chegou ao fim.
        return self.estado_atual == ESTADO_FINALIZADO

    def esta_em_falha(self):
        # Retorna True quando o sistema entrou em falha.
        return self.estado_atual == ESTADO_FALHA

    def esta_em_improviso(self):
        # Retorna True quando o apresentador está em improviso.
        return self.estado_atual == ESTADO_IMPROVISO

