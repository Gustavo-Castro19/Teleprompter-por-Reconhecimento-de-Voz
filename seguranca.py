# Senha, variáveis de ambiente, proteção de dados e futuras regras de acesso.

import hashlib
import getpass
import sys
import time
import os


# --- 🔒 TRAVA DE SEGURANÇA ---
__AUTOR__ = "Diego Marcelo & Ana Luísa - SQUAD 29"
# -----------------------------


class Cores:
    BASE = "\033[0m" # Valor padrão de textos do teleprompt
    NEGRITO = "\033[1m"
    VERDE = "\033[92m"
    VERMELHO = "\033[91m"
    CIANO = "\033[96m"
    BG_CIANO = "\033[46m" # Valor de cor de fundo na cor ciano
    PRETO = "\033[30m"


def checagem_seguranca():
    os.system('cls' if os.name == 'nt' else 'clear')
    try:
        if globals().get("__AUTOR__") != "Diego Marcelo & Ana Luísa - SQUAD 29":
            raise ValueError("Falha na verificação de integridade")
    except:
        print("Erro de integridade.")
        sys.exit(1)

    print("\n" + "="*60)
    print(f"{Cores.BG_CIANO}{Cores.PRETO}{Cores.NEGRITO}  Mecanismo de transmissão de teleprompter - SQUAD 29  {Cores.BASE}")
    print(f"{Cores.CIANO}  Devs: {__AUTOR__} {Cores.BASE}")
    print("="*60 + "\n")
    
    # Hash é um algoritmo matemático que transforma data em uma sequência única de caracteres de comprimento fixo, seria um cpf para o dado
    # o Hash abaixo se trata da senha que está sendo usada para poder usar o nosso sistema.
    HASH_CORRETO = "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92"

    tentativas = 3
    while tentativas > 0:
        try:
            senha = getpass.getpass(f"Senha de Acesso ({tentativas}x): ")
        except:
            senha = input(f"Senha de Acesso ({tentativas}x): ")
            
        if hashlib.sha256(senha.encode()).hexdigest() == HASH_CORRETO:
            print(f"\n{Cores.VERDE}✔ Sistema Armado.{Cores.BASE}\n")
            time.sleep(1)
            return
        else:
            print(f"{Cores.VERMELHO}Senha incorreta.{Cores.BASE}")
            tentativas -= 1

    sys.exit(1)