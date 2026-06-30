# maquina_estados.py
# Controla AUTOMATICO, PAUSADO, VT_OU_LINK, IMPROVISO, FINALIZADO e FALHA.
# Centraliza o estado atual do teleprompter durante a execução.

from registrador_eventos import RegistradorEventos

# Estados principais do teleprompter.
ESTADO_AUTOMATICO = "AUTOMATICO"
ESTADO_PAUSADO = "PAUSADO"
ESTADO_FINALIZADO = "FINALIZADO"
ESTADO_FALHA = "FALHA"
ESTADO_IMPROVISO = "IMPROVISO"
ESTADO_VT_OU_LINK = "VT_OU_LINK"


class MaquinaEstados:
    def __init__(self):
        self.linhas_roteiro = []
        self.linhas_exibidas = []
        self.falar_para_exibir = []

        # Metadados criados pelo processador_roteiro.py.
        self.segmentos = []
        self.metadados_linhas_visuais = []

        self.idx_atual = 0

        # Começa pausado até o app.py iniciar o motor.
        self.estado_atual = ESTADO_PAUSADO

        # Refere-se a se o sistema está ativo/captando áudio.
        self.correndo = False

        self.proc_audio = None

        # Timestamp do último avanço.
        self.tempo_ultimo_avanco = 0.0

        # Sinaliza descarte do buffer de áudio após avanço/retorno.
        self.descartar_buffer = False

        self.ultimo_texto_parcial = ""
        self.contagem_leitura_parcial = 0
        self.recomecar_bloco_parcial = False

        # Controle de improviso.
        self.ultimo_texto_improviso = ""
        self.tempo_inicio_improviso = None

    def mudar_estado(self, novo_estado):
        # Evita log repetido quando o estado não muda.
        if novo_estado == self.estado_atual:
            return

        estado_anterior = self.estado_atual
        self.estado_atual = novo_estado

        RegistradorEventos.mudanca_estado(
            estado_anterior,
            novo_estado
        )

    def esta_em_modo_automatico(self):
        return self.estado_atual == ESTADO_AUTOMATICO

    def esta_pausado(self):
        return self.estado_atual == ESTADO_PAUSADO

    def esta_finalizado(self):
        return self.estado_atual == ESTADO_FINALIZADO

    def esta_em_falha(self):
        return self.estado_atual == ESTADO_FALHA

    def esta_em_improviso(self):
        return self.estado_atual == ESTADO_IMPROVISO

    def esta_em_vt_ou_link(self):
        return self.estado_atual == ESTADO_VT_OU_LINK

    def pode_avaliar_audio(self):
        """
        O áudio deve ser avaliado tanto no automático quanto no improviso,
        porque é justamente no improviso que precisamos detectar
        a volta ao roteiro.
        """

        return self.estado_atual in [
            ESTADO_AUTOMATICO,
            ESTADO_IMPROVISO,
            ESTADO_VT_OU_LINK,
        ]
