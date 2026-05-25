# controlador_rolagem.py
# ============================================================
# # RESPONSABILIDADE:
# - receber texto do Vosk;
# - comparar com o roteiro;
# - decidir se avança;
# - decidir se bloqueia;
# - evitar saltos indevidos;
# - tolerar erros do ASR.
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

        return (
            acertos /
            max(len(palavras_linha), 1)
        )
    
    def calcular_score_palavras_relevantes(
        self,
        texto_falado,
        linha_roteiro
    ):
        """
        Mede quantas palavras importantes do roteiro
        apareceram na fala reconhecida.

        Isso ajuda MUITO quando o Vosk erra palavras,
        principalmente em frases curtas.
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

            # Palavra exata.
            if palavra in palavras_faladas:
                acertos += 1
                continue

            # Similaridade aproximada.
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
    # BUSCA LOCAL
    # ============================================================

    def obter_indices_candidatos_locais(self):

        total_linhas = len(self.estado.linhas_roteiro)

        indice_atual = self.estado.idx_atual

        candidatos = []

        if 0 <= indice_atual < total_linhas:
            candidatos.append(indice_atual)

        for deslocamento in range(1, 4):

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

        print(
            f"{self.estado.idx_atual + 1}. "
            f"{linha_atual}"
        )

        if melhor_indice is not None:

            linha_encontrada = (
                self.estado.linhas_roteiro[
                    melhor_indice
                ]
            )

            indice_visual = (
                self.alinhador_roteiro.obter_indice_visual(
                    melhor_indice
                )
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

        self.estado.idx_atual = indice_destino

        # Se o índice destino chegou ao total de linhas,
        # significa que o roteiro foi concluído.
        if self.estado.idx_atual >= total_linhas:
            self.estado.mudar_estado("FINALIZADO")

        self.estado.tempo_ultimo_avanco = time.time()

        self.estado.descartar_buffer = True

        self.estado.ultimo_texto_parcial = ""

        self.estado.contagem_leitura_parcial = 0

        self.estado.recomecar_bloco_parcial = False

        self.ultimo_parcial_processado = ""

        mostrar_idx = (
            self.alinhador_roteiro.obter_indice_visual(
                indice_destino
            )
        )

        self.socketio.emit(
            "cmd",
            {
                "index": mostrar_idx,
                "type": tipo_evento,
                "text": texto
            }
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

        return None

    # ============================================================
    # AVALIAÇÃO PRINCIPAL
    # ============================================================

    def avaliar(
        self,
        texto,
        parcial
    ):
        # Se o sistema não estiver em modo automático,
        # o controlador não deve avaliar nem avançar o roteiro.
        if not self.estado.esta_em_modo_automatico():
            return False

        total_linhas = len(self.estado.linhas_roteiro)

        if self.estado.idx_atual >= total_linhas:
            return False

        linha_atual = (
            self.estado.linhas_roteiro[
                self.estado.idx_atual
            ]
        )

        if self.texto_parece_ruido(
            texto,
            linha_atual
        ):
            return False

        if parcial:
            return self.avaliar_parcial(
                texto,
                linha_atual
            )

        texto_final_normalizado = (
            UtilTexto.normaliza(texto)
        )

        if texto_final_normalizado == self.ultimo_texto_final:
            return False

        self.ultimo_texto_final = texto_final_normalizado

        tempo_passado = (
            time.time() -
            self.estado.tempo_ultimo_avanco
        )

        if tempo_passado < CONFIG["intervalo_avanco"]:
            return False

        (
            melhor_indice,
            melhor_pontuacao,
            melhor_similaridade,
            melhor_cobertura,
            melhor_relevancia
        ) = self.encontrar_melhor_linha_candidata(
            texto
        )

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

        if melhor_indice is None:
            return False

        distancia = (
            melhor_indice -
            self.estado.idx_atual
        )

        if distancia < -1:
            return False

        limite_minimo = (
            self.obter_limite_minimo_por_distancia(
                distancia
            )
        )

        if limite_minimo is None:

            print("\n========== POSSÍVEL SALTO DETECTADO ==========")

            print("AÇÃO: salto bloqueado por segurança.")

            print("================================================\n")

            return False

        # ========================================================
        # CORREÇÃO DE FLOAT
        # ========================================================
        if round(melhor_pontuacao, 2) < round(limite_minimo, 2):

            print("\n========== DECISÃO DO MOTOR ==========")

            print("AÇÃO: não avançou.")

            print(
                "Motivo: score abaixo do limite "
                "para esta distância."
            )

            print(f"Distância: {distancia}")

            print(
                f"Score obtido: "
                f"{melhor_pontuacao:.2f}"
            )

            print(
                f"Score mínimo exigido: "
                f"{limite_minimo:.2f}"
            )

            print("======================================\n")

            return False

        # ========================================================
        # LINHA ATUAL
        # ========================================================
        if melhor_indice == self.estado.idx_atual:

            destino = self.estado.idx_atual + 1

            self.enviar_comando(
                destino,
                "next",
                linha_atual
            )

            return True

        # ========================================================
        # LINHA FUTURA
        # ========================================================
        if melhor_indice > self.estado.idx_atual:

            destino = melhor_indice + 1

            self.enviar_comando(
                destino,
                "next",
                self.estado.linhas_roteiro[
                    melhor_indice
                ]
            )

            return True

        # ========================================================
        # PEQUENO RETORNO
        # ========================================================
        if melhor_indice == self.estado.idx_atual - 1:

            self.enviar_comando(
                melhor_indice,
                "back",
                self.estado.linhas_roteiro[
                    melhor_indice
                ]
            )

            return True

        return False

    # ============================================================
    # PARCIAIS
    # ============================================================

    def avaliar_parcial(
        self,
        texto,
        linha_atual
    ):

        texto_normalizado = (
            UtilTexto.normaliza(texto)
        )

        if texto_normalizado == self.ultimo_parcial_processado:
            return False

        if len(texto_normalizado) <= len(self.ultimo_parcial_processado) + 2:
            return False

        self.ultimo_parcial_processado = texto_normalizado

        linha_normalizada = (
            UtilTexto.normaliza(linha_atual)
        )

        if not self.existe_palavra_relevante_em_comum(
            texto_normalizado,
            linha_normalizada
        ):
            return False

        if (
            len(texto_normalizado) <
            len(self.estado.ultimo_texto_parcial)
        ):

            self.estado.ultimo_texto_parcial = (
                texto_normalizado
            )

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

        if pontuacao >= 0.72:
            self.estado.contagem_leitura_parcial += 1
        else:
            self.estado.contagem_leitura_parcial = 0

        if self.estado.contagem_leitura_parcial >= 2:

            self.estado.ultimo_texto_parcial = ""

            self.estado.contagem_leitura_parcial = 0

            destino = self.estado.idx_atual + 1

            self.enviar_comando(
                destino,
                "next",
                linha_atual
            )

            return True

        return False
