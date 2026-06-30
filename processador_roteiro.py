# processador_roteiro.py
# ============================================================
# RESPONSABILIDADE:
# Processar o roteiro JSON vindo do NewsHub/iNEWS.
#
# REGRA IMPORTANTE DO TELEPROMPTER:
# - comandos técnicos DEVEM aparecer na tela;
# - comandos técnicos NÃO devem ser lidos;
# - tempos editoriais do JSON devem ser preservados;
# - speakingTime controla tempo de fala;
# - tapeTime/totalTime ajudam em VT, link, imagens, vinheta e intervalo.
# ============================================================

import json
import re

from configuracoes import CONFIG
from modelos import SegmentoRoteiro, LinhaVisualMeta


class ProcessadorRoteiro:
    def __init__(self):
        self.linhas_roteiro = []
        self.linhas_exibidas = []
        self.falar_para_exibir = []
        self.tipos_linhas_exibidas = []
        self.segmentos = []
        self.metadados_linhas_visuais = []

    # ============================================================
    # UTILITÁRIOS GERAIS
    # ============================================================

    def garantir_texto(self, valor):
        """
        Garante que o valor recebido seja texto.
        O JSON pode trazer string, lista, número, None etc.
        """

        if valor is None:
            return ""

        if isinstance(valor, list):
            return "\n".join(str(item) for item in valor)

        return str(valor)

    def converter_segundos(self, valor):
        """
        Converte campos como speakingTime, tapeTime e totalTime.
        Quando o valor vier vazio, inválido ou None, retorna 0.0.
        """

        try:
            if valor is None:
                return 0.0

            texto = str(valor).strip()

            if not texto:
                return 0.0

            return float(texto)

        except (ValueError, TypeError):
            return 0.0

    def limpar_espacos(self, texto):
        texto = re.sub(r"\s+", " ", texto or "")
        return texto.strip()

    def contar_palavras(self, texto):
        texto = self.limpar_espacos(texto)
        if not texto:
            return 0
        return len(re.findall(r"[A-Za-zÀ-ÿ0-9]+", texto))

    # ============================================================
    # LIMPEZA / CLASSIFICAÇÃO DE LINHAS
    # ============================================================

    def remover_tags_html_preservando_texto(self, texto):
        """
        Remove tags HTML, mas preserva o conteúdo visual.
        Ex: <pi>{{//ABRE SOM VT//}}</pi> vira {{//ABRE SOM VT//}}
        """

        if not texto:
            return ""

        texto = self.garantir_texto(texto)
        texto = texto.replace("\r\r\n", "\n").replace("\r", "\n")
        texto = re.sub(r"<[^>]+>", "\n", texto)

        return texto

    def remover_comandos_tecnicos_para_fala(self, texto):
        """
        Remove comandos técnicos SOMENTE do texto falável.
        O visual continua preservando esses comandos.
        """

        if not texto:
            return ""

        texto = self.garantir_texto(texto)
        texto = texto.replace("\r\r\n", "\n").replace("\r", "\n")

        # Remove blocos <pi>...</pi> do texto falável.
        texto = re.sub(r"<pi>.*?</pi>", " ", texto, flags=re.DOTALL)

        # Remove tags HTML restantes.
        texto = re.sub(r"<[^>]+>", "\n", texto)

        # Remove comandos técnicos.
        texto = re.sub(r"\{\{.*?\}\}", " ", texto)
        texto = re.sub(r"\{.*?\}", " ", texto)
        texto = re.sub(r"\[.*?\]", " ", texto)

        # Não removemos todos os parênteses cegamente para não apagar texto útil.
        # Removemos apenas linhas que são inteiramente comentário técnico em outra função.
        texto = texto.replace("/", " ")
        texto = re.sub(r"=+", " ", texto)

        return texto

    def linha_eh_separador(self, linha):
        if not linha:
            return False

        return bool(re.fullmatch(r"[=\-_/\\ ]+", linha.strip()))

    def linha_eh_tecnica(self, linha):
        """
        Identifica comandos técnicos que aparecem no roteiro,
        mas não devem ser lidos pelo apresentador.
        """

        if not linha:
            return False

        linha = linha.strip()

        if self.linha_eh_separador(linha):
            return True

        if linha.startswith("{{") and linha.endswith("}}"):
            return True

        if linha.startswith("{") and linha.endswith("}"):
            return True

        if linha.startswith("[") and linha.endswith("]"):
            return True

        if linha.startswith("(") and linha.endswith(")"):
            return True

        texto_upper = linha.upper()

        palavras_tecnicas = [
            "ABRE SOM",
            "RODA VT",
            "RODA IMAGEM",
            "RODA IMAGENS",
            "VINHETA",
            "INTERVALO",
            "LINK NO AR",
            "PROC.",
            "GLOBODRONE",
            "IMAGENS//OFF",
            "DEIXA:",
            "LOCUTOR",
            "MOSAIC",
        ]

        return any(palavra in texto_upper for palavra in palavras_tecnicas)

    def linha_eh_comando_de_pausa(self, linha):
        """
        Linhas desse tipo normalmente representam um período em que
        o apresentador não lê o texto corrido: VT, link, imagens,
        vinheta, intervalo etc.
        """

        if not linha:
            return False

        texto = linha.upper()

        gatilhos_pausa = [
            "ABRE SOM VT",
            "RODA VT",
            "ABRE SOM LINK",
            "LINK NO AR",
            "NARRA VIVO",
            "RODA IMAGEM",
            "RODA IMAGENS",
            "IMAGENS NO AR",
            "GLOBODRONE",
            "VINHETA",
            "INTERVALO",
            "ABRE SOM VINHETA",
        ]

        return any(gatilho in texto for gatilho in gatilhos_pausa)

    def classificar_linha_visual(self, linha):
        """
        Classifica linha visual para o frontend.
        """

        if self.linha_eh_separador(linha):
            return "separador"

        if self.linha_eh_comando_de_pausa(linha):
            return "pausa_tecnica"

        if self.linha_eh_tecnica(linha):
            return "tecnico"

        return "fala"

    def linha_parece_falavel(self, texto):
        """
        Define se a linha deve entrar no roteiro falado.
        """

        if not texto:
            return False

        texto = texto.strip()

        if len(texto) < 2:
            return False

        if self.linha_eh_tecnica(texto):
            return False

        if self.linha_eh_separador(texto):
            return False

        if not re.search(r"[A-Za-zÀ-ÿ]", texto):
            return False

        return True

    # ============================================================
    # PROCESSAMENTO DE BLOCOS
    # ============================================================

    def processar_bloco_texto(self, texto_bruto, indice_visual_inicial):
        """
        Processa um bloco do JSON.

        Retorna:
        - linhas visuais;
        - tipos das linhas visuais;
        - linhas faláveis;
        - mapeamento fala -> visual.
        """

        texto_bruto = self.garantir_texto(texto_bruto)

        linhas_exibidas = []
        tipos_linhas_exibidas = []
        linhas_roteiro = []
        falar_para_exibir = []

        texto_visual = self.remover_tags_html_preservando_texto(texto_bruto)
        texto_falavel = self.remover_comandos_tecnicos_para_fala(texto_bruto)

        linhas_visuais_brutas = texto_visual.split("\n")
        linhas_falaveis_brutas = texto_falavel.split("\n")

        indice_visual_atual = indice_visual_inicial

        for indice_linha, linha_visual in enumerate(linhas_visuais_brutas):
            linha_visual = self.limpar_espacos(linha_visual)

            if not linha_visual:
                continue

            linhas_exibidas.append(linha_visual)
            tipos_linhas_exibidas.append(
                self.classificar_linha_visual(linha_visual)
            )

            indice_visual_da_linha = indice_visual_atual
            indice_visual_atual += 1

            if indice_linha < len(linhas_falaveis_brutas):
                linha_falavel = self.limpar_espacos(
                    linhas_falaveis_brutas[indice_linha]
                )
            else:
                linha_falavel = ""

            if self.linha_parece_falavel(linha_falavel):
                linhas_roteiro.append(linha_falavel)
                falar_para_exibir.append(indice_visual_da_linha)

        return {
            "linhas_exibidas": linhas_exibidas,
            "tipos_linhas_exibidas": tipos_linhas_exibidas,
            "linhas_roteiro": linhas_roteiro,
            "falar_para_exibir": falar_para_exibir,
            "proximo_indice_visual": indice_visual_atual,
        }

    # ============================================================
    # TEMPOS DO JSON
    # ============================================================

    def extrair_meta_slug(self, slug):
        """
        Extrai os metadados principais da retranca.
        O JSON do iNEWS traz estes tempos por slug/retranca,
        não por linha. Depois distribuímos por palavras.
        """

        return {
            "slug_id": slug.get("id") or slug.get("storyId"),
            "titulo": self.limpar_espacos(slug.get("title", "")),
            "pagina": self.limpar_espacos(slug.get("page", "")),
            "item_type": self.limpar_espacos(slug.get("itemType", "")),
            "apresentador": self.limpar_espacos(slug.get("presenter", "")),
            "ordem_slug": slug.get("order"),
            "speaking_time": self.converter_segundos(slug.get("speakingTime")),
            "tape_time": self.converter_segundos(slug.get("tapeTime")),
            "total_time": self.converter_segundos(slug.get("totalTime")),
            "start_time": slug.get("startTime"),
        }

    def estimar_tempo_leitura(self, texto, palavras_por_minuto=None):
        """
        Estima tempo quando o JSON não possui speakingTime útil.
        """

        texto = self.limpar_espacos(texto)

        if not texto:
            return 0.0

        if palavras_por_minuto is None:
            palavras_por_minuto = CONFIG.get("palavras_por_minuto_base", 150)

        quantidade_palavras = self.contar_palavras(texto)

        return (quantidade_palavras / palavras_por_minuto) * 60

    def distribuir_tempos_de_fala(self, linhas_roteiro, speaking_time):
        """
        Distribui o speakingTime da retranca proporcionalmente
        à quantidade de palavras de cada linha falável.
        """

        if not linhas_roteiro:
            return []

        total_palavras = sum(
            self.contar_palavras(linha)
            for linha in linhas_roteiro
        )

        if speaking_time > 0 and total_palavras > 0:
            tempos = []

            for linha in linhas_roteiro:
                palavras = self.contar_palavras(linha)
                tempo = (palavras / total_palavras) * speaking_time
                tempos.append(round(tempo, 2))

            return tempos

        # Fallback quando não há speakingTime.
        return [
            round(self.estimar_tempo_leitura(linha), 2)
            for linha in linhas_roteiro
        ]

    def obter_pausa_tecnica_do_slug(self, meta):
        """
        Decide se a retranca possui pausa técnica relevante.
        tapeTime é prioridade para VT/link/vinheta/imagem.
        Se speakingTime for 0 e totalTime existir, totalTime também pode ser pausa.
        """

        tape_time = meta["tape_time"]
        total_time = meta["total_time"]
        speaking_time = meta["speaking_time"]

        if tape_time > 0:
            return tape_time, "tapeTime_json"

        if speaking_time <= 0 and total_time > 0:
            return total_time, "totalTime_json_sem_fala"

        return 0.0, ""

    # ============================================================
    # CARREGAMENTO PRINCIPAL
    # ============================================================

    def carregar_roteiro(self):
        self.linhas_roteiro = []
        self.linhas_exibidas = []
        self.falar_para_exibir = []
        self.tipos_linhas_exibidas = []
        self.segmentos = []
        self.metadados_linhas_visuais = []

        with open(CONFIG["caminho_roteiro"], "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        indice_visual_global = 0
        indice_falado_global = 0

        for slug in dados.get("slugs", []):
            meta = self.extrair_meta_slug(slug)

            linhas_exibidas_slug = []
            tipos_linhas_slug = []
            linhas_roteiro_slug = []
            falar_para_exibir_slug = []

            tem_notes_with_body = (
                "notesWithBody" in slug
                and slug["notesWithBody"]
            )

            if tem_notes_with_body:
                blocos = []

                for nota in slug["notesWithBody"]:
                    textos_nota = nota.get("text", [])

                    if isinstance(textos_nota, list):
                        blocos.extend(textos_nota)
                    else:
                        blocos.append(textos_nota)
            else:
                blocos = [slug.get("body", "")]

            for item_texto in blocos:
                resultado = self.processar_bloco_texto(
                    item_texto,
                    indice_visual_global
                )

                linhas_exibidas_slug.extend(resultado["linhas_exibidas"])
                tipos_linhas_slug.extend(resultado["tipos_linhas_exibidas"])
                linhas_roteiro_slug.extend(resultado["linhas_roteiro"])
                falar_para_exibir_slug.extend(resultado["falar_para_exibir"])

                indice_visual_global = resultado["proximo_indice_visual"]

            tempos_fala = self.distribuir_tempos_de_fala(
                linhas_roteiro_slug,
                meta["speaking_time"]
            )

            pausa_tecnica, motivo_pausa = self.obter_pausa_tecnica_do_slug(meta)

            # Metadados visuais por linha.
            pausa_tecnica_aplicada = False

            for indice_local, linha_visual in enumerate(linhas_exibidas_slug):
                indice_visual = (
                    len(self.linhas_exibidas) + indice_local
                )

                tipo_linha = (
                    tipos_linhas_slug[indice_local]
                    if indice_local < len(tipos_linhas_slug)
                    else "fala"
                )

                pausa_linha = 0.0
                motivo_linha = ""

                # A pausa técnica é aplicada apenas uma vez por retranca,
                # evitando duplicar tapeTime em vários comandos técnicos.
                if (
                    not pausa_tecnica_aplicada
                    and pausa_tecnica > 0
                    and tipo_linha == "pausa_tecnica"
                ):
                    pausa_linha = pausa_tecnica
                    motivo_linha = motivo_pausa
                    pausa_tecnica_aplicada = True

                self.metadados_linhas_visuais.append(
                    LinhaVisualMeta(
                        indice_visual=indice_visual,
                        texto_visual=linha_visual,
                        tipo_linha=tipo_linha,
                        titulo=meta["titulo"],
                        pagina=meta["pagina"],
                        item_type=meta["item_type"],
                        ordem_slug=meta["ordem_slug"],
                        slug_id=meta["slug_id"],
                        speaking_time=meta["speaking_time"],
                        tape_time=meta["tape_time"],
                        total_time=meta["total_time"],
                        duracao_segundos=0.0,
                        origem_tempo="json_tecnico" if pausa_linha > 0 else "sem_tempo",
                        pausa_tecnica_segundos=pausa_linha,
                        motivo_pausa=motivo_linha,
                    )
                )

            # Segmentos faláveis.
            for indice_local, linha_falada in enumerate(linhas_roteiro_slug):
                indice_visual = falar_para_exibir_slug[indice_local]
                texto_visual = ""

                if 0 <= indice_visual < indice_visual_global:
                    # O índice visual já é global.
                    # Como self.linhas_exibidas ainda não recebeu o slug,
                    # calculamos usando a lista local quando possível.
                    deslocamento_local = indice_visual - len(self.linhas_exibidas)
                    if 0 <= deslocamento_local < len(linhas_exibidas_slug):
                        texto_visual = linhas_exibidas_slug[deslocamento_local]

                if not texto_visual:
                    texto_visual = linha_falada

                tempo_linha = (
                    tempos_fala[indice_local]
                    if indice_local < len(tempos_fala)
                    else round(self.estimar_tempo_leitura(linha_falada), 2)
                )

                origem_tempo = (
                    "speakingTime_json_distribuido"
                    if meta["speaking_time"] > 0
                    else "estimativa_por_palavras"
                )

                pausa_apos = 0.0
                motivo_segmento = ""

                # Quando não houve comando técnico visual marcado,
                # mas a retranca possui tapeTime, associamos a pausa
                # à última fala da retranca.
                if (
                    pausa_tecnica > 0
                    and not pausa_tecnica_aplicada
                    and indice_local == len(linhas_roteiro_slug) - 1
                ):
                    pausa_apos = pausa_tecnica
                    motivo_segmento = motivo_pausa

                segmento = SegmentoRoteiro(
                    texto_falado=linha_falada,
                    texto_visual=texto_visual,
                    tipo_linha="fala",
                    indice_falado=indice_falado_global,
                    indice_visual=indice_visual,
                    tempo_estimado=tempo_linha,
                    origem_tempo=origem_tempo,
                    apresentador=meta["apresentador"],
                    titulo=meta["titulo"],
                    pagina=meta["pagina"],
                    item_type=meta["item_type"],
                    ordem_slug=meta["ordem_slug"],
                    slug_id=meta["slug_id"],
                    speaking_time=meta["speaking_time"],
                    tape_time=meta["tape_time"],
                    total_time=meta["total_time"],
                    start_time=meta["start_time"],
                    pausa_apos_segundos=pausa_apos,
                    motivo_pausa=motivo_segmento,
                )

                self.segmentos.append(segmento)
                indice_falado_global += 1

                # Atualiza a duração no metadado visual correspondente.
                for meta_visual in self.metadados_linhas_visuais:
                    if meta_visual.indice_visual == indice_visual:
                        meta_visual.duracao_segundos = tempo_linha
                        meta_visual.origem_tempo = origem_tempo
                        break

            self.linhas_exibidas.extend(linhas_exibidas_slug)
            self.tipos_linhas_exibidas.extend(tipos_linhas_slug)
            self.linhas_roteiro.extend(linhas_roteiro_slug)
            self.falar_para_exibir.extend(falar_para_exibir_slug)

        print("\n========== DIAGNÓSTICO DO PARSER ==========")
        print(f"Linhas exibidas : {len(self.linhas_exibidas)}")
        print(f"Tipos visuais   : {len(self.tipos_linhas_exibidas)}")
        print(f"Linhas faláveis : {len(self.linhas_roteiro)}")
        print(f"Mapeamentos     : {len(self.falar_para_exibir)}")
        print(f"Segmentos       : {len(self.segmentos)}")

        tempo_fala_json = sum(
            segmento.tempo_estimado or 0.0
            for segmento in self.segmentos
        )

        tempo_pausa_json = sum(
            (linha.pausa_tecnica_segundos or 0.0)
            for linha in self.metadados_linhas_visuais
        ) + sum(
            (segmento.pausa_apos_segundos or 0.0)
            for segmento in self.segmentos
        )

        print(f"Tempo fala calculado (s) : {round(tempo_fala_json, 2)}")
        print(f"Tempo técnico/VT (s)     : {round(tempo_pausa_json, 2)}")

        print("\nPrimeiros segmentos com tempo:")
        for indice, segmento in enumerate(self.segmentos[:10]):
            print(
                f"{indice + 1}. {segmento.tempo_estimado}s "
                f"[{segmento.origem_tempo}] - {segmento.texto_falado[:60]}"
            )

        print("===========================================\n")

        return (
            self.linhas_roteiro,
            self.linhas_exibidas,
            self.falar_para_exibir
        )
