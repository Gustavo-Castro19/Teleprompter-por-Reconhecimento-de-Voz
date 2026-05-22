# processador_roteiro.py
# ============================================================
# RESPONSABILIDADE:
# Processar o roteiro JSON vindo do NewsHub/iNEWS.
#
# REGRA IMPORTANTE DO TELEPROMPTER:
# - comandos técnicos DEVEM aparecer na tela;
# - comandos técnicos NÃO devem ser lidos;
# - comandos técnicos serão marcados como "tecnico"
#   para futuramente aparecerem com outra cor na interface.
# ============================================================

import json
import re

from configuracoes import CONFIG


class ProcessadorRoteiro:
    def __init__(self):
        self.linhas_roteiro = []
        self.linhas_exibidas = []
        self.falar_para_exibir = []
        self.tipos_linhas_exibidas = []

    def garantir_texto(self, valor):
        """
        Garante que o valor recebido seja texto.

        O JSON pode trazer:
        - string
        - lista de strings
        - lista com outros tipos
        - valor vazio

        Essa função evita erro como:
        AttributeError: 'list' object has no attribute 'replace'
        """

        if valor is None:
            return ""

        if isinstance(valor, list):
            return "\n".join(str(item) for item in valor)

        return str(valor)

    def remover_tags_html_preservando_texto(self, texto):
        if not texto:
            return ""

        texto = self.garantir_texto(texto)

        texto = texto.replace("\r\r\n", "\n").replace("\r", "\n")
        texto = re.sub(r"<[^>]+>", "\n", texto)

        return texto

    def remover_comandos_tecnicos_para_fala(self, texto):
        """
        Remove comandos técnicos SOMENTE para gerar texto falável.
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
        texto = re.sub(r"\(.*?\)", " ", texto)

        texto = texto.replace("/", " ")
        texto = re.sub(r"=+", " ", texto)

        return texto

    def limpar_espacos(self, texto):
        texto = re.sub(r"\s+", " ", texto or "")
        return texto.strip()

    def linha_eh_tecnica(self, linha):
        """
        Identifica comandos técnicos que aparecem no roteiro,
        mas não devem ser lidos pelo apresentador.
        """

        if not linha:
            return False

        linha = linha.strip()

        if linha.startswith("{{") and linha.endswith("}}"):
            return True

        if linha.startswith("{") and linha.endswith("}"):
            return True

        if linha.startswith("[") and linha.endswith("]"):
            return True

        if linha.startswith("(") and linha.endswith(")"):
            return True

        return False

    def linha_eh_separador(self, linha):
        if not linha:
            return False

        return bool(re.fullmatch(r"[=\-_/\\ ]+", linha.strip()))

    def classificar_linha_visual(self, linha):
        """
        Classifica linha visual para uso futuro na interface.
        """

        if self.linha_eh_separador(linha):
            return "separador"

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

    def linha_parece_continuacao(self, linha_anterior, linha_atual):
        """
        Junta linhas quebradas sem depender de frases específicas.
        """

        if not linha_anterior or not linha_atual:
            return False

        linha_anterior = linha_anterior.strip()
        linha_atual = linha_atual.strip()

        if linha_anterior.endswith((".", "!", "?", ":")):
            return False

        termina_com_conectivo = linha_anterior.lower().endswith((
            " e",
            " de",
            " da",
            " do",
            " das",
            " dos",
            " para",
            " com",
            " ou",
            " em",
            " no",
            " na",
            " nos",
            " nas",
            " ao",
            " à",
        ))

        comeca_minuscula = linha_atual[:1].islower()

        return termina_com_conectivo or comeca_minuscula

    def juntar_linhas_quebradas(self, linhas_faladas, mapeamento_original):
        linhas_juntas = []
        mapeamento_junto = []

        buffer_texto = ""
        buffer_visual = None

        for indice, linha in enumerate(linhas_faladas):
            linha = linha.strip()

            if not linha:
                continue

            if not buffer_texto:
                buffer_texto = linha
                buffer_visual = mapeamento_original[indice]
                continue

            if self.linha_parece_continuacao(buffer_texto, linha):
                buffer_texto += " " + linha
            else:
                linhas_juntas.append(buffer_texto)
                mapeamento_junto.append(buffer_visual)

                buffer_texto = linha
                buffer_visual = mapeamento_original[indice]

        if buffer_texto:
            linhas_juntas.append(buffer_texto)
            mapeamento_junto.append(buffer_visual)

        return linhas_juntas, mapeamento_junto

    def processar_bloco_texto(self, texto_bruto, indice_visual_inicial):
        """
        Processa um bloco de texto do JSON.

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

    def carregar_roteiro(self):
        self.linhas_roteiro = []
        self.linhas_exibidas = []
        self.falar_para_exibir = []
        self.tipos_linhas_exibidas = []

        with open(CONFIG["caminho_roteiro"], "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        indice_visual = 0

        for slug in dados.get("slugs", []):
            tem_notes_with_body = (
                "notesWithBody" in slug
                and slug["notesWithBody"]
            )

            if tem_notes_with_body:
                for nota in slug["notesWithBody"]:
                    textos_nota = nota.get("text", [])

                    if isinstance(textos_nota, list):
                        itens_texto = textos_nota
                    else:
                        itens_texto = [textos_nota]

                    for item_texto in itens_texto:
                        resultado = self.processar_bloco_texto(
                            item_texto,
                            indice_visual
                        )

                        self.linhas_exibidas.extend(resultado["linhas_exibidas"])
                        self.tipos_linhas_exibidas.extend(resultado["tipos_linhas_exibidas"])
                        self.linhas_roteiro.extend(resultado["linhas_roteiro"])
                        self.falar_para_exibir.extend(resultado["falar_para_exibir"])

                        indice_visual = resultado["proximo_indice_visual"]

            elif "body" in slug:
                resultado = self.processar_bloco_texto(
                    slug["body"],
                    indice_visual
                )

                self.linhas_exibidas.extend(resultado["linhas_exibidas"])
                self.tipos_linhas_exibidas.extend(resultado["tipos_linhas_exibidas"])
                self.linhas_roteiro.extend(resultado["linhas_roteiro"])
                self.falar_para_exibir.extend(resultado["falar_para_exibir"])

                indice_visual = resultado["proximo_indice_visual"]

        (
            self.linhas_roteiro,
            self.falar_para_exibir
        ) = self.juntar_linhas_quebradas(
            self.linhas_roteiro,
            self.falar_para_exibir
        )

        print("\n========== DIAGNÓSTICO DO PARSER ==========")
        print(f"Linhas exibidas : {len(self.linhas_exibidas)}")
        print(f"Tipos visuais   : {len(self.tipos_linhas_exibidas)}")
        print(f"Linhas faláveis : {len(self.linhas_roteiro)}")
        print(f"Mapeamentos     : {len(self.falar_para_exibir)}")

        print("\nPrimeiras linhas exibidas:")
        for indice, linha in enumerate(self.linhas_exibidas[:10]):
            tipo = self.tipos_linhas_exibidas[indice]
            print(f"{indice + 1}. [{tipo}] {linha}")

        print("\nPrimeiras linhas faláveis:")
        for indice, linha in enumerate(self.linhas_roteiro[:10]):
            print(f"{indice + 1}. {linha}")

        print("===========================================\n")

        return (
            self.linhas_roteiro,
            self.linhas_exibidas,
            self.falar_para_exibir
        )