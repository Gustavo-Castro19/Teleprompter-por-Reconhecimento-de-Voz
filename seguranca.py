
# seguranca.py
# ============================================================
# RESPONSABILIDADE:
# Centralizar funções relacionadas à segurança do sistema.
#
# Nesta fase:
# - não usamos senha fixa no código;
# - não armazenamos autores ou dados sensíveis;
# - deixamos a base preparada para variáveis de ambiente;
# - futuramente este arquivo pode validar políticas do cliente.
# ============================================================

import os


class Cores:
    # Cores usadas apenas para melhorar a leitura no terminal.
    BASE = "\033[0m"
    NEGRITO = "\033[1m"
    VERDE = "\033[92m"
    VERMELHO = "\033[91m"
    CIANO = "\033[96m"
    BG_CIANO = "\033[46m"
    PRETO = "\033[30m"


def obter_variavel_ambiente(nome, valor_padrao=None):
    # Busca uma variável de ambiente.
    # Se ela não existir, retorna o valor padrão.
    return os.getenv(nome, valor_padrao)


def modo_seguro_ativo():
    # Verifica se o modo seguro está ativo.
    # Por padrão, consideramos ativo.
    valor = os.getenv("MODO_SEGURO", "true")

    return valor.lower() in ["true", "1", "sim", "yes"]


def validar_politica_basica():
    # Validação inicial de segurança.
    # Nesta fase, apenas confirma que o sistema não depende de senha fixa.
    if not modo_seguro_ativo():
        print("[SEGURANÇA] Aviso: modo seguro está desativado.")

    return True


def ocultar_texto_sensivel(texto, limite=20):
    # Reduz exposição de texto sensível em logs.
    if not texto:
        return ""

    if len(texto) <= limite:
        return texto

    return texto[:limite] + "..."

