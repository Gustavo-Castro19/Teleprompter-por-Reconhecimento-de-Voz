# Controla AUTOMATICO, MANUAL, VT_OU_LINK, IMPROVISO, FALHA.
# Centraliza o estado atual do teleprompter durante a execução.


class MaquinaEstados:
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