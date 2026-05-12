# Lê o JSON, limpa tags, remove comandos técnicos e gera segmentos faláveis.
# Responsável por carregar o roteiro do NewsHub, limpar marcações
# e separar o texto exibido do texto usado para reconhecimento de voz.

import os
import json
import re

from configuracoes import CONFIG

class ProcessadorRoteiro:
    def carregar_roteiro(self):
        if os.path.exists(CONFIG["caminho_roteiro"]):
            try:
                with open(CONFIG["caminho_roteiro"], "r", encoding="utf-8") as f:
                    data = json.load(f)

                texto_roteiro = ""
                texto_exibido = ""
                idx_exibido = 0 # index da linha atual que está sendo exibida no teleprompt
                self.falar_para_exibir = []

                if "slugs" in data:
                    # Processar também notesWithBody
                    for slug in data["slugs"]:
                        if "notesWithBody" in slug:
                            for nota in slug["notesWithBody"]:
                                if "text" in nota:
                                    for item_texto in nota["text"]:
                                        # body se refere aos dados que estão vindo do roteiro
                                        body_cru = item_texto

                                        # Normaliza quebras de linha antes de processar
                                        body_cru = body_cru.replace('\r\r\n', '\n').replace('\r', '\n')

                                        # Corpo de visualização: remove tags HTML, mas mantém o texto interno
                                        body_exibido = re.sub(r'<[^>]+>', '\n', body_cru)
                                        texto_exibido += body_exibido + "\n"

                                        # Corpo do roteiro falado: remove o conteúdo de <pi> antes de remover outras tags
                                        body_roteiro = re.sub(r'<pi>.*?</pi>', ' ', body_cru, flags=re.DOTALL)
                                        body_roteiro = re.sub(r'<[^>]+>', '\n', body_roteiro)

                                        linhas_limpas = []
                                        linhas_cruas_exibidas = body_exibido.split('\n')
                                        linhas_cruas_roteiro = body_roteiro.split('\n')

                                        for idx, linha in enumerate(linhas_cruas_exibidas):
                                            linha = linha.strip()
                                            if linha:
                                                idx_atualmente_exibido = idx_exibido
                                                idx_exibido += 1
                                            else:
                                                continue

                                            if idx < len(linhas_cruas_roteiro):
                                                linha_roteiro = linhas_cruas_roteiro[idx].strip()
                                            else:
                                                linha_roteiro = ''

                                            if not linha_roteiro:
                                                continue

                                            # Verifica se a linha original tinha <pi> — se sim, não adiciona ao falar_para_exibir
                                            if idx < len(linhas_cruas_exibidas) and '<pi>' in linhas_cruas_exibidas[idx]:
                                                continue

                                            # Pula comandos internos tipo {{FRED EM OFF}}
                                            if linha_roteiro.startswith('{{') or linha_roteiro.startswith('{'):
                                                continue
                                            # Pula comandos tipo {FRED}
                                            if linha_roteiro.startswith('{') and linha_roteiro.endswith('}'):
                                                continue

                                            # Pula separadores tipo ==========
                                            if re.fullmatch(r'=+', linha_roteiro):
                                                continue

                                            # Pula linhas sem letras
                                            if not re.search(r'[A-Za-zÀ-ÿ]', linha_roteiro):
                                                continue

                                            linha_falada = linha_roteiro

                                            linha_falada = re.sub(r'\{\{.*?\}\}', ' ', linha_falada)
                                            linha_falada = re.sub(r'\{.*?\}', ' ', linha_falada)
                                            linha_falada = re.sub(r'\[.*?\]', ' ', linha_falada)
                                            linha_falada = re.sub(r'\(.*?\)', ' ', linha_falada)

                                            # Remove barras e sinais usados como marcação
                                            linha_falada = linha_falada.replace('/', ' ')
                                            linha_falada = re.sub(r'=+', ' ', linha_falada)

                                            # Normaliza espaços
                                            linha_falada = re.sub(r'\s+', ' ', linha_falada).strip()

                                            if not linha_falada:
                                                continue

                                            self.falar_para_exibir.append(idx_atualmente_exibido)
                                            linhas_limpas.append(linha_falada)

                                        texto_roteiro += "\n".join(linhas_limpas) + "\n"


                self.linhas_exibidas = [
                    l.strip()
                    for l in texto_exibido.split('\n')
                    if l.strip()
                ]

                self.linhas_roteiro = [
                    l.strip()
                    for l in texto_roteiro.split('\n')
                    if l.strip()
                ]

            except Exception as e:
                self.linhas_roteiro = [f"ERRO: Falha ao carregar roteiro: {str(e)}"]
        else:
            self.linhas_roteiro = ["ERRO: Roteiro não encontrado"]