# Controlador_rolagem.py
# Decide quando o teleprompter deve avançar, voltar ou saltar.
# Mantém a lógica original, apenas separada do app.py.

import time

from configuracoes import CONFIG
from normalizador_texto import UtilTexto
from registrador_eventos import RegistradorEventos


class ControladorRolagem:
    def __init__(self, maquina_estados, alinhador_roteiro, socketio):
        # Guarda o estado compartilhado do sistema.
        self.estado = maquina_estados

        # Converte linha falada em linha visual.
        self.alinhador_roteiro = alinhador_roteiro

        # Envia comandos para o frontend.
        self.socketio = socketio

    def enviar_comando(self, idx, tipo_evento, texto):
        # Atualiza o índice atual da linha falada.
        self.estado.idx_atual = idx

        # Guarda o horário do avanço.
        self.estado.tempo_ultimo_avanco = time.time()

        # Solicita descarte do buffer de áudio.
        self.estado.descartar_buffer = True

        # Reseta os controles de transcrição parcial.
        self.estado.ultimo_texto_parcial = ""
        self.estado.contagem_leitura_parcial = 0
        self.estado.recomecar_bloco_parcial = False

        # Descobre qual linha visual deve ser destacada.
        mostrar_idx = self.alinhador_roteiro.obter_indice_visual(idx)

        # Envia comando para a interface.
        self.socketio.emit(
            "cmd",
            {
                "index": mostrar_idx,
                "type": tipo_evento,
                "text": texto
            }
        )

        RegistradorEventos.evento_rolagem(tipo_evento, idx, mostrar_idx)

    def avaliar(self, texto, parcial):
        # Avalia se o texto reconhecido deve provocar rolagem.
        total_linhas = len(self.estado.linhas_roteiro)

        if self.estado.idx_atual >= total_linhas:
            return False

        linha_atual = self.estado.linhas_roteiro[self.estado.idx_atual]

        # Se for parcial, usa a lógica específica de parciais.
        if parcial:
            return self.avaliar_parcial(texto, linha_atual)

        # Aplica cooldown após avanço.
        tempo_passado = time.time() - self.estado.tempo_ultimo_avanco

        if tempo_passado < CONFIG["intervalo_avanco"]:
            return False

        # Regra de retorno ao início.
        if total_linhas > 0 and self.estado.idx_atual > 2:
            if UtilTexto.verificar_correspondencia_normal(
                texto,
                self.estado.linhas_roteiro[0],
                CONFIG["limite_similaridade"],
                parcial=parcial
            ):
                self.enviar_comando(0, "back", self.estado.linhas_roteiro[0])
                return True

        # Leitura sequencial da linha atual.
        if UtilTexto.verificar_correspondencia_normal(
            texto,
            linha_atual,
            CONFIG["limite_similaridade"],
            parcial=parcial
        ):
            self.estado.recomecar_bloco_parcial = False
            self.enviar_comando(self.estado.idx_atual + 1, "next", linha_atual)
            return True

        # Varredura global.
        # OBS: esta lógica será melhorada depois, pois pode causar saltos indevidos.
        if len(texto) > CONFIG["caracteres_minimos"]:
            for i in range(total_linhas):
                if i == self.estado.idx_atual:
                    continue

                if UtilTexto.verificar_dinamica_correspondencia(
                    texto,
                    self.estado.linhas_roteiro[i]
                ):
                    direcao = "jump" if i > self.estado.idx_atual else "back"
                    self.enviar_comando(i + 1, direcao, self.estado.linhas_roteiro[i])
                    return True

        RegistradorEventos.reconhecimento(
            "FINAL",
            texto,
            self.estado.idx_atual,
            linha_atual
        )

        return False

    def avaliar_parcial(self, texto, linha_atual):
        # Avalia transcrições parciais do Vosk.
        texto_normalizado = UtilTexto.normaliza(texto)
        linha_normalizada = UtilTexto.normaliza(linha_atual)

        # Se o parcial diminuiu, pode indicar recomeço ou travamento.
        if len(texto_normalizado) < len(self.estado.ultimo_texto_parcial):
            self.estado.ultimo_texto_parcial = texto_normalizado
            self.estado.contagem_leitura_parcial = 0
            self.estado.recomecar_bloco_parcial = True

            RegistradorEventos.reconhecimento(
                "PARCIAL-RESET",
                texto,
                self.estado.idx_atual,
                linha_atual
            )

            return False

        self.estado.ultimo_texto_parcial = texto_normalizado

        if self.estado.recomecar_bloco_parcial:
            self.estado.contagem_leitura_parcial = 0
            self.estado.recomecar_bloco_parcial = False

        # Calcula a cobertura do parcial sobre a linha atual.
        cobertura = len(texto_normalizado) / max(len(linha_normalizada), 1)

        if cobertura >= CONFIG["avanco_parcial"]:
            if UtilTexto.verificar_correspondencia_normal(
                texto,
                linha_atual,
                CONFIG["limite_similaridade"],
                parcial=False
            ):
                self.estado.contagem_leitura_parcial += 1

                # Se estiver muito perto do fim, uma confirmação basta.
                confirmacoes_necessarias = 1 if cobertura >= 0.95 else 2

                if self.estado.contagem_leitura_parcial >= confirmacoes_necessarias:
                    self.estado.ultimo_texto_parcial = ""
                    self.estado.contagem_leitura_parcial = 0
                    self.enviar_comando(self.estado.idx_atual + 1, "next", linha_atual)
                    return True
            else:
                self.estado.contagem_leitura_parcial = 0
        else:
            self.estado.contagem_leitura_parcial = 0

        RegistradorEventos.reconhecimento(
            "PARCIAL",
            texto,
            self.estado.idx_atual,
            linha_atual
        )

        return False
