# Cria logs estruturados JSON.
# Neste primeiro momento, centraliza os prints do sistema sem alterar o comportamento.


class RegistradorEventos:
    @staticmethod
    def maquina_ativa(Cores):
        print(f"{Cores.VERDE}--- MáQUINA ATIVA ---{Cores.BASE}")
    
    @staticmethod
    def mudanca_estado(estado_anterior, novo_estado):
        # Registra no terminal quando o teleprompter muda de estado operacional.
        print(f"[ESTADO] {estado_anterior} -> {novo_estado}")
    
    @staticmethod
    def roteiro_finalizado():
        # Registra quando o roteiro chega ao fim.
        print("[SISTEMA] Roteiro finalizado. Encerrando motor.")
    
    @staticmethod
    def falha_sistema(erro):
        # Registra falhas graves do sistema.
        print(f"[FALHA] Erro crítico no sistema: {erro}")

    @staticmethod
    def microfone_aberto():
        print("--- MICROFONE ABERTO ---")

    @staticmethod
    def evento_rolagem(tipo_evento, idx, mostrar_idx):
        print(f"--> [{tipo_evento.upper()}] Indo para linha falada {idx + 1}, visual {mostrar_idx + 1}")

    @staticmethod
    def reconhecimento(tipo, texto, idx_atual, linha_atual):
        print(f"[{tipo}] '{texto}' | linha {idx_atual + 1}: '{linha_atual[:40]}'")

    @staticmethod
    def cliente_conectado():
        print("CLIENTE CONECTADO")

    @staticmethod
    def servidor(url):
        print(f"Servidor: {url}")
