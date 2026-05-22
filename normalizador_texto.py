# normalizador_texto.py
# ============================================================
# RESPONSABILIDADE:
# Normalizar textos vindos:
# - do roteiro;
# - do Vosk;
# - dos comparadores.
#
# IMPORTANTE:
# O Vosk costuma separar palavras compostas:
#
# "terça-feira"
# → "terça feira"
#
# Então precisamos normalizar hífens para espaço,
# evitando perda de cobertura.
# ============================================================

import re
import unicodedata
from difflib import SequenceMatcher

from configuracoes import CONFIG


class UtilTexto:

    @staticmethod
    def normaliza(text):

        if not text:
            return ""

        text = text.lower().strip()

        # Remove acentos.
        text = unicodedata.normalize("NFD", text)

        text = "".join(
            ch
            for ch in text
            if unicodedata.category(ch) != "Mn"
        )

        # ====================================================
        # IMPORTANTE:
        # Troca hífen e barra por espaço.
        #
        # Ex:
        # terça-feira
        # → terça feira
        # ====================================================
        text = re.sub(r"[-/]", " ", text)

        # Remove caracteres especiais restantes.
        text = re.sub(r"[^a-z0-9\s]", "", text)

        # Remove múltiplos espaços.
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @staticmethod
    def similaridade(a, b):

        return SequenceMatcher(
            None,
            a,
            b
        ).ratio()

    @staticmethod
    def verificar_correspondencia_normal(
        falado,
        linha,
        thresh,
        parcial=False
    ):
        """
        Verificação simples de correspondência.
        """

        n_falado = UtilTexto.normaliza(falado)
        n_linha = UtilTexto.normaliza(linha)

        if len(n_falado) < CONFIG["caracteres_minimos_reconhecimento"]:
            return False

        cobertura = (
            len(n_falado) /
            max(len(n_linha), 1)
        )

        cobertura_minima = (
            CONFIG["cobertura_minima_parcial"]
            if parcial
            else CONFIG["cobertura_minima_final"]
        )

        if cobertura < cobertura_minima:
            return False

        inicio_trecho = n_linha[:len(n_falado) + 5]

        inicio_sim = UtilTexto.similaridade(
            n_falado,
            inicio_trecho
        )

        melhor_sim = inicio_sim

        if melhor_sim >= thresh:
            return True

        # Recuperação simples.
        if len(n_falado) > len(n_linha):

            sufixo = n_falado[-(len(n_linha) + 5):]

            if n_linha in sufixo:
                return True

            if (
                UtilTexto.similaridade(
                    sufixo,
                    n_linha
                ) >= thresh
            ):
                return True

        return False

    @staticmethod
    def verificar_dinamica_correspondencia(
        falado,
        linha
    ):
        """
        Comparação usada para buscas maiores.
        """

        n_falado = UtilTexto.normaliza(falado)
        n_linha = UtilTexto.normaliza(linha)

        if len(n_falado) < CONFIG["caracteres_minimos"]:
            return False

        limite = (
            CONFIG["limite_similaridade_alto"]
            if len(n_falado) < 40
            else CONFIG["limite_similaridade_baixo"]
        )

        tam_trecho = min(
            len(n_falado),
            len(n_linha)
        )

        comeco_falado = n_falado[:tam_trecho]
        comeco_linha = n_linha[:tam_trecho]

        if (
            UtilTexto.similaridade(
                comeco_falado,
                comeco_linha
            ) >= limite
        ):
            return True

        if len(n_falado) > len(n_linha) + 5:

            sufixo = n_falado[-(len(n_linha) + 5):]

            if (
                UtilTexto.similaridade(
                    sufixo,
                    n_linha
                ) >= limite
            ):
                return True

        return False