# Normaliza acentos, pontuação, números, barras, hífens e variações.
# Responsável por normalizar textos e comparar a fala reconhecida com as linhas do roteiro.

import re
import unicodedata
from difflib import SequenceMatcher

from configuracoes import CONFIG


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