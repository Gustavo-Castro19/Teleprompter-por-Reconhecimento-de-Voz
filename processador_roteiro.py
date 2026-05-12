# Processador_roteiro.py
# Lê o JSON, limpa tags, remove comandos técnicos e gera linhas faláveis.
# Nesta fase, mantemos a lógica atual, apenas organizada em arquivo próprio.
# Correções como evitar duplicidade entre body e notesWithBody serão feitas depois.

import os
import json
import re

from configuracoes import CONFIG

class ProcessadorRoteiro:
    def carregar_roteiro(self):
        # Inicializa as listas que serão retornadas.
        self.linhas_roteiro = []
        self.linhas_exibidas = []
        self.falar_para_exibir = []

        # Verifica se o arquivo do roteiro existe.
        if os.path.exists(CONFIG["caminho_roteiro"]):
            try:
                with open(CONFIG["caminho_roteiro"], "r", encoding="utf-8") as f:
                    data = json.load(f)

                texto_roteiro = ""
                texto_exibido = ""
                idx_exibido = 0
                self.falar_para_exibir = []

                # O roteiro vem em uma lista de slugs/retrancas.
                if "slugs" in data:
                    for slug in data["slugs"]:

                        # Processa notesWithBody.
                        if "notesWithBody" in slug:
                            for nota in slug["notesWithBody"]:
                                if "text" in nota:
                                    for item_texto in nota["text"]:
                                        resultado = self.processar_body(item_texto, idx_exibido)

                                        texto_roteiro += resultado["texto_roteiro"]
                                        texto_exibido += resultado["texto_exibido"]
                                        self.falar_para_exibir.extend(resultado["falar_para_exibir"])
                                        idx_exibido = resultado["proximo_idx_exibido"]

                        # Processa body.
                        # OBS: ainda está igual ao comportamento atual.
                        # Depois vamos impedir duplicidade entre body e notesWithBody.
                        if "body" in slug:
                            resultado = self.processar_body(slug["body"], idx_exibido)

                            texto_roteiro += resultado["texto_roteiro"]
                            texto_exibido += resultado["texto_exibido"]
                            self.falar_para_exibir.extend(resultado["falar_para_exibir"])
                            idx_exibido = resultado["proximo_idx_exibido"]

                # Linhas exibidas na interface.
                self.linhas_exibidas = [
                    l.strip()
                    for l in texto_exibido.split("\n")
                    if l.strip()
                ]

                # Linhas usadas para comparação com a fala.
                self.linhas_roteiro = [
                    l.strip()
                    for l in texto_roteiro.split("\n")
                    if l.strip()
                ]

            except Exception as e:
                self.linhas_roteiro = [f"ERRO: Falha ao carregar roteiro: {str(e)}"]
                self.linhas_exibidas = []
                self.falar_para_exibir = []
        else:
            self.linhas_roteiro = ["ERRO: Roteiro não encontrado"]
            self.linhas_exibidas = []
            self.falar_para_exibir = []

        return self.linhas_roteiro, self.linhas_exibidas, self.falar_para_exibir

    def processar_body(self, body_cru, idx_exibido):
        # Normaliza quebras de linha.
        body_cru = body_cru.replace("\r\r\n", "\n").replace("\r", "\n")

        # Texto visual: remove tags HTML, mas mantém o texto interno.
        body_exibido = re.sub(r"<[^>]+>", "\n", body_cru)
        texto_exibido = body_exibido + "\n"

        # Texto falado: remove o conteúdo das tags <pi> antes de remover outras tags.
        body_roteiro = re.sub(r"<pi>.*?</pi>", " ", body_cru, flags=re.DOTALL)
        body_roteiro = re.sub(r"<[^>]+>", "\n", body_roteiro)

        linhas_limpas = []
        falar_para_exibir = []

        linhas_cruas_exibidas = body_exibido.split("\n")
        linhas_cruas_roteiro = body_roteiro.split("\n")

        for idx, linha in enumerate(linhas_cruas_exibidas):
            linha = linha.strip()

            # Se a linha visual existe, ela recebe um índice visual.
            if linha:
                idx_atualmente_exibido = idx_exibido
                idx_exibido += 1
            else:
                continue

            # Busca a linha correspondente no texto falado.
            if idx < len(linhas_cruas_roteiro):
                linha_roteiro = linhas_cruas_roteiro[idx].strip()
            else:
                linha_roteiro = ""

            if not linha_roteiro:
                continue

            # Mantém o comportamento original:
            # se a linha visual tinha <pi>, ela não entra como fala.
            if idx < len(linhas_cruas_exibidas) and "<pi>" in linhas_cruas_exibidas[idx]:
                continue

            # Ignora comandos técnicos.
            if linha_roteiro.startswith("{{") or linha_roteiro.startswith("{"):
                continue

            if linha_roteiro.startswith("{") and linha_roteiro.endswith("}"):
                continue

            # Ignora separadores visuais.
            if re.fullmatch(r"=+", linha_roteiro):
                continue

            # Ignora linhas sem letras.
            if not re.search(r"[A-Za-zÀ-ÿ]", linha_roteiro):
                continue

            linha_falada = linha_roteiro

            # Remove comandos e marcações internas.
            linha_falada = re.sub(r"\{\{.*?\}\}", " ", linha_falada)
            linha_falada = re.sub(r"\{.*?\}", " ", linha_falada)
            linha_falada = re.sub(r"\[.*?\]", " ", linha_falada)
            linha_falada = re.sub(r"\(.*?\)", " ", linha_falada)

            # Remove barras e sinais usados como marcação.
            linha_falada = linha_falada.replace("/", " ")
            linha_falada = re.sub(r"=+", " ", linha_falada)

            # Normaliza espaços.
            linha_falada = re.sub(r"\s+", " ", linha_falada).strip()

            if not linha_falada:
                continue

            # Guarda o mapeamento entre linha falada e linha visual.
            falar_para_exibir.append(idx_atualmente_exibido)

            # Guarda a linha falável.
            linhas_limpas.append(linha_falada)

        return {
            "texto_roteiro": "\n".join(linhas_limpas) + "\n",
            "texto_exibido": texto_exibido,
            "falar_para_exibir": falar_para_exibir,
            "proximo_idx_exibido": idx_exibido,
        }
