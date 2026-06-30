# controlador_rolagem.py
# ============================================================
# RESPONSABILIDADE:
# - receber texto do Vosk;
# - comparar com o roteiro;
# - decidir se avança;
# - decidir se bloqueia;
# - evitar saltos indevidos;
# - tolerar erros do ASR;
# - detectar improviso;
# - pausar a rolagem visual durante improviso/VT/link;
# - retomar a rolagem quando a fala voltar ao roteiro.
# ============================================================

import time
from difflib import SequenceMatcher

from configuracoes import CONFIG
from normalizador_texto import UtilTexto
from registrador_eventos import RegistradorEventos


class ControladorRolagem:

    def __init__(
        self,
        maquina_estados,
        alinhador_roteiro,
        socketio
    ):

        self.estado = maquina_estados
        self.alinhador_roteiro = alinhador_roteiro
        self.socketio = socketio

        self.ultimo_texto_final = ""
        self.ultimo_parcial_processado = ""

    # ============================================================
    # MÉTRICAS
    # ============================================================

    def calcular_similaridade(
        self,
        texto_a,
        texto_b
    ):

        texto_a = UtilTexto.normaliza(texto_a)
        texto_b = UtilTexto.normaliza(texto_b)

        if not texto_a or not texto_b:
            return 0.0

        return SequenceMatcher(
            None,
            texto_a,
            texto_b
        ).ratio()

    def calcular_cobertura_por_tokens(
        self,
        texto_falado,
        linha_roteiro
    ):

        texto_falado = UtilTexto.normaliza(texto_falado)
        linha_roteiro = UtilTexto.normaliza(linha_roteiro)

        palavras_faladas = texto_falado.split()
        palavras_linha = linha_roteiro.split()

        if not palavras_faladas or not palavras_linha:
            return 0.0

        conjunto_linha = set(palavras_linha)

        acertos = 0

        for palavra in palavras_faladas:

            if palavra in conjunto_linha:
                acertos += 1

        return acertos / max(len(palavras_linha), 1)

    def calcular_score_palavras_relevantes(
        self,
        texto_falado,
        linha_roteiro
    ):
        """
        Mede quantas palavras importantes do roteiro
        apareceram na fala reconhecida.

        Isso ajuda quando o Vosk erra palavras.
        """

        texto_falado = UtilTexto.normaliza(texto_falado)
        linha_roteiro = UtilTexto.normaliza(linha_roteiro)

        palavras_fracas = {
            "a", "o", "e", "de", "do", "da", "dos", "das",
            "em", "no", "na", "nos", "nas", "um", "uma",
            "para", "pra", "com", "por", "que", "se",
            "ao", "as", "os", "ou"
        }

        palavras_faladas = {
            palavra
            for palavra in texto_falado.split()
            if palavra not in palavras_fracas
        }

        palavras_roteiro = {
            palavra
            for palavra in linha_roteiro.split()
            if palavra not in palavras_fracas
        }

        if not palavras_roteiro:
            return 0.0

        acertos = 0

        for palavra in palavras_roteiro:

            if palavra in palavras_faladas:
                acertos += 1
                continue

            for palavra_falada in palavras_faladas:

                similaridade = self.calcular_similaridade(
                    palavra,
                    palavra_falada
                )

                if similaridade >= 0.72:
                    acertos += 1
                    break

        return acertos / len(palavras_roteiro)

    def existe_palavra_relevante_em_comum(
        self,
        texto_falado,
        linha_roteiro
    ):

        texto_falado = UtilTexto.normaliza(texto_falado)
        linha_roteiro = UtilTexto.normaliza(linha_roteiro)

        palavras_faladas = texto_falado.split()
        palavras_linha = linha_roteiro.split()

        if not palavras_faladas or not palavras_linha:
            return False

        palavras_fracas = {
            "a", "o", "e", "de", "do", "da", "dos", "das",
            "em", "no", "na", "nos", "nas", "um", "uma",
            "para", "pra", "com", "por", "que", "se",
            "ao", "as", "os", "ou"
        }

        conjunto_linha = {
            palavra
            for palavra in palavras_linha
            if palavra not in palavras_fracas and len(palavra) >= 3
        }

        conjunto_falado = {
            palavra
            for palavra in palavras_faladas
            if palavra not in palavras_fracas and len(palavra) >= 3
        }

        return bool(
            conjunto_linha.intersection(conjunto_falado)
        )

    # ============================================================
    # FILTRO DE RUÍDO
    # ============================================================

    def texto_parece_ruido(
        self,
        texto,
        linha_atual
    ):

        texto_normalizado = UtilTexto.normaliza(texto)

        if not texto_normalizado:
            return True

        if len(texto_normalizado) < 4:
            return True

        palavras = texto_normalizado.split()

        if len(palavras) == 1:

            return not self.existe_palavra_relevante_em_comum(
                texto_normalizado,
                linha_atual
            )

        return False

    # ============================================================
    # BUSCA LOCAL E RECUPERAÇÃO
    # ============================================================

    def obter_indices_candidatos_locais(self):

        total_linhas = len(self.estado.linhas_roteiro)
        indice_atual = self.estado.idx_atual

        candidatos = []

        if 0 <= indice_atual < total_linhas:
            candidatos.append(indice_atual)

        # Olha algumas linhas à frente para permitir retomada
        # quando o apresentador pula ou improvisa e volta adiante.
        for deslocamento in range(1, 5):

            proximo_indice = indice_atual + deslocamento

            if proximo_indice < total_linhas:
                candidatos.append(proximo_indice)

        indice_anterior = indice_atual - 1

        if indice_anterior >= 0:
            candidatos.append(indice_anterior)

        candidatos_unicos = []

        for indice in candidatos:

            if indice not in candidatos_unicos:
                candidatos_unicos.append(indice)

        return candidatos_unicos

    def encontrar_melhor_linha_candidata(
        self,
        texto
    ):

        melhor_indice = None
        melhor_pontuacao = 0.0
        melhor_similaridade = 0.0
        melhor_cobertura = 0.0
        melhor_relevancia = 0.0

        for indice in self.obter_indices_candidatos_locais():

            linha = self.estado.linhas_roteiro[indice]

            similaridade = self.calcular_similaridade(
                texto,
                linha
            )

            cobertura = self.calcular_cobertura_por_tokens(
                texto,
                linha
            )

            relevancia = self.calcular_score_palavras_relevantes(
                texto,
                linha
            )

            pontuacao = (
                (similaridade * 0.45) +
                (cobertura * 0.30) +
                (relevancia * 0.25)
            )

            if pontuacao > melhor_pontuacao:
                melhor_pontuacao = pontuacao
                melhor_indice = indice
                melhor_similaridade = similaridade
                melhor_cobertura = cobertura
                melhor_relevancia = relevancia

        return (
            melhor_indice,
            melhor_pontuacao,
            melhor_similaridade,
            melhor_cobertura,
            melhor_relevancia
        )

    # ============================================================
    # LOGS
    # ============================================================

    def mostrar_diagnostico_completo(
        self,
        tipo_resultado,
        texto_reconhecido,
        linha_atual,
        melhor_indice,
        score,
        similaridade,
        cobertura,
        relevancia
    ):

        print("\n======================================================")
        print(f"TIPO RESULTADO      : {tipo_resultado}")
        print("======================================================")

        print("\nFALA RECONHECIDA:")
        print(texto_reconhecido)

        print("\nLINHA ATUAL ESPERADA:")
        print(f"{self.estado.idx_atual + 1}. {linha_atual}")

        if melhor_indice is not None:
            linha_encontrada = self.estado.linhas_roteiro[melhor_indice]

            indice_visual = self.alinhador_roteiro.obter_indice_visual(
                melhor_indice
            )

            print("\nMELHOR LINHA ENCONTRADA:")
            print(f"Linha falada : {melhor_indice + 1}")
            print(f"Linha visual : {indice_visual + 1}")
            print(linha_encontrada)

        print("\nMÉTRICAS:")
        print(f"Score         : {score:.2f}")
        print(f"Similaridade  : {similaridade:.2f}")
        print(f"Cobertura     : {cobertura:.2f}")
        print(f"Relevância    : {relevancia:.2f}")
        print("======================================================\n")

    def mostrar_linha_atual_e_proxima(
        self,
        texto_lido
    ):

        indice_atual = self.estado.idx_atual
        total_linhas = len(self.estado.linhas_roteiro)

        print("\n========== POSIÇÃO DO TELEPROMPTER ==========")
        print("LINHA CONSIDERADA LIDA:")
        print(texto_lido)

        print("\nPRÓXIMA LINHA ESPERADA:")

        if indice_atual < total_linhas:
            print(
                f"{indice_atual + 1}. "
                f"{self.estado.linhas_roteiro[indice_atual]}"
            )
        else:
            print("Fim do roteiro.")

        print("============================================\n")

    # ============================================================
    # DADOS DE SEGMENTO
    # ============================================================

    def obter_segmento_por_indice_falado(self, indice_falado):
        for segmento in getattr(self.estado, "segmentos", []):
            if segmento.indice_falado == indice_falado:
                return segmento

        return None

    def segmento_para_socket(self, segmento):
        if not segmento:
            return None

        return {
            "textoFalado": segmento.texto_falado,
            "textoVisual": segmento.texto_visual,
            "indiceFalado": segmento.indice_falado,
            "indiceVisual": segmento.indice_visual,
            "tempoEstimadoSegundos": round(segmento.tempo_estimado or 0.0, 2),
            "origemTempo": segmento.origem_tempo,
            "titulo": segmento.titulo,
            "pagina": segmento.pagina,
            "itemType": segmento.item_type,
            "speakingTime": segmento.speaking_time,
            "tapeTime": segmento.tape_time,
            "totalTime": segmento.total_time,
            "pausaAposSegundos": round(segmento.pausa_apos_segundos or 0.0, 2),
            "motivoPausa": segmento.motivo_pausa,
        }

    # ============================================================
    # ESTADO VISUAL DA ROLAGEM
    # ============================================================

    def emitir_estado_rolagem(
        self,
        tipo,
        motivo="",
        pausa_segundos=0.0
    ):
        self.socketio.emit(
            "estado_rolagem",
            {
                "tipo": tipo,
                "motivo": motivo,
                "pausaSegundos": round(pausa_segundos or 0.0, 2),
                "indiceFalado": self.estado.idx_atual,
            }
        )

    def emitir_andamento_voz(
        self,
        estado_voz,
        tipo_resultado,
        texto_reconhecido,
        melhor_indice,
        score,
        cobertura,
        relevancia
    ):
        """
        Envia ao frontend o progresso da fala em tempo real.

        Esse evento é diferente do evento "cmd":
        - "cmd" muda a linha quando o backend decide avançar;
        - "voz_roteiro" ajuda a rolagem visual a ajustar velocidade
          enquanto a pessoa ainda está falando.

        Assim o teleprompter fica realmente guiado por voz:
        se a pessoa fala rápido, o frontend acelera;
        se fala devagar, desacelera;
        se improvisa, pausa;
        se volta ao roteiro, retoma.
        """

        indice_visual = None

        if melhor_indice is not None:
            indice_visual = self.alinhador_roteiro.obter_indice_visual(
                melhor_indice
            )

        # A cobertura indica aproximadamente quanto da linha
        # já apareceu na fala reconhecida pelo Vosk.
        progresso_estimado = max(
            0.0,
            min(cobertura or 0.0, 1.0)
        )

        self.socketio.emit(
            "voz_roteiro",
            {
                "estadoVoz": estado_voz,
                "tipoResultado": tipo_resultado,
                "textoReconhecido": texto_reconhecido,
                "indiceFalado": melhor_indice,
                "indiceVisual": indice_visual,
                "score": round(score or 0.0, 2),
                "cobertura": round(cobertura or 0.0, 2),
                "relevancia": round(relevancia or 0.0, 2),
                "progressoEstimado": round(progresso_estimado, 2),
            }
        )

    def entrar_em_improviso(self, texto):
        """
        Pausa a rolagem visual quando a fala reconhecida
        não bate com a linha esperada.
        """

        if not CONFIG.get("habilitar_improviso", True):
            return

        texto_normalizado = UtilTexto.normaliza(texto)

        if len(texto_normalizado.split()) < CONFIG.get("min_palavras_improviso", 3):
            return

        if self.estado.esta_em_improviso():
            self.estado.ultimo_texto_improviso = texto_normalizado
            return

        self.estado.mudar_estado("IMPROVISO")
        self.estado.tempo_inicio_improviso = time.time()
        self.estado.ultimo_texto_improviso = texto_normalizado

        print("\n========== IMPROVISO DETECTADO ==========")
        print("AÇÃO: rolagem visual pausada até a fala voltar ao roteiro.")
        print(f"Fala: {texto}")
        print("=========================================\n")

        self.emitir_estado_rolagem(
            "IMPROVISO",
            "Fala fora do roteiro. Aguardando retorno ao texto."
        )

    def sair_de_improviso(self):
        if self.estado.esta_em_improviso() or self.estado.esta_em_vt_ou_link():
            self.estado.mudar_estado("AUTOMATICO")
            self.emitir_estado_rolagem(
                "AUTOMATICO",
                "Fala voltou ao roteiro. Rolagem retomada."
            )

    # ============================================================
    # ENVIO DE EVENTO
    # ============================================================

    def enviar_comando(
        self,
        indice_destino,
        tipo_evento,
        texto
    ):

        total_linhas = len(self.estado.linhas_roteiro)

        if indice_destino > total_linhas:
            indice_destino = total_linhas

        if indice_destino < 0:
            indice_destino = 0

        # Segmento considerado lido.
        # Em avanço normal, destino é a próxima linha,
        # então a linha lida é destino - 1.
        indice_lido = indice_destino - 1

        if tipo_evento == "back":
            indice_lido = indice_destino

        segmento_lido = self.obter_segmento_por_indice_falado(
            indice_lido
        )

        pausa_apos = 0.0
        motivo_pausa = ""

        if segmento_lido:
            pausa_apos = segmento_lido.pausa_apos_segundos or 0.0
            motivo_pausa = segmento_lido.motivo_pausa or ""

        self.estado.idx_atual = indice_destino

        if self.estado.idx_atual >= total_linhas:
            self.estado.mudar_estado("FINALIZADO")
        else:
            self.sair_de_improviso()

        self.estado.tempo_ultimo_avanco = time.time()
        self.estado.descartar_buffer = True
        self.estado.ultimo_texto_parcial = ""
        self.estado.contagem_leitura_parcial = 0
        self.estado.recomecar_bloco_parcial = False
        self.ultimo_parcial_processado = ""

        mostrar_idx = self.alinhador_roteiro.obter_indice_visual(
            indice_destino
        )

        payload = {
            "index": mostrar_idx,
            "type": tipo_evento,
            "text": texto,
            "segmento": self.segmento_para_socket(segmento_lido),
            "pausaAposSegundos": round(pausa_apos, 2),
            "motivoPausa": motivo_pausa,
        }

        self.socketio.emit("cmd", payload)

        if pausa_apos > 0:
            self.estado.mudar_estado("VT_OU_LINK")
            self.emitir_estado_rolagem(
                "VT_OU_LINK",
                motivo_pausa or "Pausa técnica após fala",
                pausa_apos
            )

        RegistradorEventos.evento_rolagem(
            tipo_evento,
            indice_destino,
            mostrar_idx
        )

        self.mostrar_linha_atual_e_proxima(texto)

    # ============================================================
    # LIMITES DINÂMICOS
    # ============================================================

    def obter_limite_minimo_por_distancia(
        self,
        distancia
    ):

        if distancia == 0:
            return 0.55

        if distancia == 1:
            return 0.68

        if distancia == 2:
            return 0.82

        if distancia == 3:
            return 0.88

        return None

    # ============================================================
    # AVALIAÇÃO PRINCIPAL
    # ============================================================

    def avaliar(
        self,
        texto,
        parcial
    ):
        # Em improviso também avaliamos áudio para detectar retorno ao roteiro.
        if not self.estado.pode_avaliar_audio():
            return False

        total_linhas = len(self.estado.linhas_roteiro)

        if self.estado.idx_atual >= total_linhas:
            return False

        linha_atual = self.estado.linhas_roteiro[self.estado.idx_atual]

        if self.texto_parece_ruido(texto, linha_atual):
            return False

        if parcial:
            # Em improviso, usamos o parcial apenas para perceber
            # que a fala começou a voltar ao roteiro.
            # A confirmação de avanço continua mais segura no resultado FINAL.
            if self.estado.esta_em_improviso() or self.estado.esta_em_vt_ou_link():
                return self.avaliar_parcial(
                    texto,
                    linha_atual,
                    permitir_avanco=False
                )

            return self.avaliar_parcial(
                texto,
                linha_atual,
                permitir_avanco=True
            )

        texto_final_normalizado = UtilTexto.normaliza(texto)

        if texto_final_normalizado == self.ultimo_texto_final:
            return False

        self.ultimo_texto_final = texto_final_normalizado

        tempo_passado = time.time() - self.estado.tempo_ultimo_avanco

        if tempo_passado < CONFIG["intervalo_avanco"]:
            return False

        (
            melhor_indice,
            melhor_pontuacao,
            melhor_similaridade,
            melhor_cobertura,
            melhor_relevancia
        ) = self.encontrar_melhor_linha_candidata(texto)

        self.mostrar_diagnostico_completo(
            "FINAL",
            texto,
            linha_atual,
            melhor_indice,
            melhor_pontuacao,
            melhor_similaridade,
            melhor_cobertura,
            melhor_relevancia
        )

        if (
            melhor_indice is not None
            and melhor_pontuacao >= CONFIG.get("score_minimo_andamento_voz", 0.35)
        ):
            self.emitir_andamento_voz(
                "acompanhando",
                "FINAL",
                texto,
                melhor_indice,
                melhor_pontuacao,
                melhor_cobertura,
                melhor_relevancia
            )

        if melhor_indice is None:
            self.emitir_andamento_voz(
                "improviso",
                "FINAL",
                texto,
                None,
                0.0,
                0.0,
                0.0
            )
            self.entrar_em_improviso(texto)
            return False

        distancia = melhor_indice - self.estado.idx_atual

        if distancia < -1:
            self.emitir_andamento_voz(
                "improviso",
                "FINAL",
                texto,
                melhor_indice,
                melhor_pontuacao,
                melhor_cobertura,
                melhor_relevancia
            )

            self.entrar_em_improviso(texto)
            return False

        limite_minimo = self.obter_limite_minimo_por_distancia(distancia)

        if limite_minimo is None:

            print("\n========== POSSÍVEL SALTO DETECTADO ==========")
            print("AÇÃO: salto bloqueado por segurança.")
            print("================================================\n")

            self.emitir_andamento_voz(
                "improviso",
                "FINAL",
                texto,
                melhor_indice,
                melhor_pontuacao,
                melhor_cobertura,
                melhor_relevancia
            )

            self.entrar_em_improviso(texto)
            return False

        if round(melhor_pontuacao, 2) < round(limite_minimo, 2):

            print("\n========== DECISÃO DO MOTOR ==========")
            print("AÇÃO: não avançou.")
            print("Motivo: score abaixo do limite para esta distância.")
            print(f"Distância: {distancia}")
            print(f"Score obtido: {melhor_pontuacao:.2f}")
            print(f"Score mínimo exigido: {limite_minimo:.2f}")
            print("======================================\n")

            self.emitir_andamento_voz(
                "improviso",
                "FINAL",
                texto,
                melhor_indice,
                melhor_pontuacao,
                melhor_cobertura,
                melhor_relevancia
            )

            self.entrar_em_improviso(texto)
            return False

        # A fala voltou ao roteiro.
        self.emitir_andamento_voz(
            "retomou",
            "FINAL",
            texto,
            melhor_indice,
            melhor_pontuacao,
            melhor_cobertura,
            melhor_relevancia
        )

        self.sair_de_improviso()

        # Linha atual.
        if melhor_indice == self.estado.idx_atual:

            destino = self.estado.idx_atual + 1

            self.enviar_comando(
                destino,
                "next",
                linha_atual
            )

            return True

        # Linha futura.
        if melhor_indice > self.estado.idx_atual:

            destino = melhor_indice + 1

            self.enviar_comando(
                destino,
                "next",
                self.estado.linhas_roteiro[melhor_indice]
            )

            return True

        # Pequeno retorno.
        if melhor_indice == self.estado.idx_atual - 1:

            self.enviar_comando(
                melhor_indice,
                "back",
                self.estado.linhas_roteiro[melhor_indice]
            )

            return True

        return False

    # ============================================================
    # PARCIAIS
    # ============================================================

    def avaliar_parcial(
        self,
        texto,
        linha_atual,
        permitir_avanco=True
    ):

        texto_normalizado = UtilTexto.normaliza(texto)

        if texto_normalizado == self.ultimo_parcial_processado:
            return False

        if len(texto_normalizado) <= len(self.ultimo_parcial_processado) + 2:
            return False

        self.ultimo_parcial_processado = texto_normalizado

        linha_normalizada = UtilTexto.normaliza(linha_atual)

        if not self.existe_palavra_relevante_em_comum(
            texto_normalizado,
            linha_normalizada
        ):
            return False

        if len(texto_normalizado) < len(self.estado.ultimo_texto_parcial):

            self.estado.ultimo_texto_parcial = texto_normalizado
            self.estado.contagem_leitura_parcial = 0
            self.estado.recomecar_bloco_parcial = True

            return False

        self.estado.ultimo_texto_parcial = texto_normalizado

        if self.estado.recomecar_bloco_parcial:
            self.estado.contagem_leitura_parcial = 0
            self.estado.recomecar_bloco_parcial = False

        similaridade = self.calcular_similaridade(
            texto_normalizado,
            linha_normalizada
        )

        cobertura = self.calcular_cobertura_por_tokens(
            texto_normalizado,
            linha_normalizada
        )

        relevancia = self.calcular_score_palavras_relevantes(
            texto_normalizado,
            linha_normalizada
        )

        pontuacao = (
            (similaridade * 0.45) +
            (cobertura * 0.30) +
            (relevancia * 0.25)
        )

        self.mostrar_diagnostico_completo(
            "PARCIAL",
            texto,
            linha_atual,
            self.estado.idx_atual,
            pontuacao,
            similaridade,
            cobertura,
            relevancia
        )

        if pontuacao >= CONFIG.get("score_minimo_andamento_voz", 0.35):
            estado_voz = "retomou" if self.estado.esta_em_improviso() or self.estado.esta_em_vt_ou_link() else "acompanhando"

            self.emitir_andamento_voz(
                estado_voz,
                "PARCIAL",
                texto,
                self.estado.idx_atual,
                pontuacao,
                cobertura,
                relevancia
            )

            # Quando a pessoa volta ao roteiro, liberamos a rolagem visual
            # antes mesmo do avanço final, mas sem pular linha.
            if estado_voz == "retomou":
                self.sair_de_improviso()
        else:
            self.emitir_andamento_voz(
                "improviso",
                "PARCIAL",
                texto,
                self.estado.idx_atual,
                pontuacao,
                cobertura,
                relevancia
            )

        if pontuacao >= 0.72:
            self.estado.contagem_leitura_parcial += 1
        else:
            self.estado.contagem_leitura_parcial = 0

        if self.estado.contagem_leitura_parcial >= 2:

            self.estado.ultimo_texto_parcial = ""
            self.estado.contagem_leitura_parcial = 0

            if not permitir_avanco:
                # No improviso, parcial serve apenas para retomar a rolagem visual.
                # O avanço real aguarda o resultado FINAL do Vosk.
                return False

            destino = self.estado.idx_atual + 1

            self.enviar_comando(
                destino,
                "next",
                linha_atual
            )

            return True

        return False
