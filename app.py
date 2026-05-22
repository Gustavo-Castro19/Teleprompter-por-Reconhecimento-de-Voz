
# app.py
# ============================================================
# TELEPROMPTER SQUAD 29
# MODO BACKEND / TERMINAL
# ============================================================
#
# OBJETIVO:
# Nesta fase NÃO utilizaremos interface web.
#
# O foco é estabilizar:
# - parser do roteiro;
# - reconhecimento de voz;
# - microfone;
# - comparação;
# - rolagem;
# - estados internos.
#
# O frontend voltará apenas após estabilização do motor para integração.
# ============================================================

from maquina_estados import MaquinaEstados
from processador_roteiro import ProcessadorRoteiro
from alinhador_roteiro import AlinhadorRoteiro
from controlador_rolagem import ControladorRolagem
from reconhecedor_fala import ReconhecedorFala
from motor_audio import MotorAudio
from registrador_eventos import RegistradorEventos
from seguranca import Cores


# ============================================================
# 1. ESTADO GLOBAL DO SISTEMA
# ============================================================

estado = MaquinaEstados()


# ============================================================
# 2. CARREGAMENTO DO ROTEIRO
# ============================================================

print("\nCarregando roteiro...")

processador = ProcessadorRoteiro()

(
    estado.linhas_roteiro,
    estado.linhas_exibidas,
    estado.falar_para_exibir
) = processador.carregar_roteiro()

print("Roteiro carregado com sucesso.\n")


# ============================================================
# 3. DIAGNÓSTICO INICIAL
# ============================================================

print("========== DIAGNÓSTICO ==========")

print(f"Linhas faláveis : {len(estado.linhas_roteiro)}")
print(f"Linhas visuais  : {len(estado.linhas_exibidas)}")
print(f"Mapeamentos     : {len(estado.falar_para_exibir)}")

print("\nPrimeiras linhas faláveis:\n")

for indice, linha in enumerate(estado.linhas_roteiro[:10]):
    print(f"{indice + 1}. {linha}")

print("\n=================================\n")


# ============================================================
# 4. ALINHADOR
# ============================================================

alinhador = AlinhadorRoteiro(
    estado.falar_para_exibir,
    estado.linhas_exibidas
)


# ============================================================
# 5. SOCKETIO FALSO
# ============================================================

class SocketIOSimulado:
    """
    Simula apenas o emit necessário para o controlador.
    """

    def emit(self, evento, dados):
        print("\n========== EVENTO ==========")
        print(f"Evento: {evento}")
        print(f"Tipo  : {dados.get('type')}")
        print(f"Índice: {dados.get('index')}")
        print(f"Texto : {dados.get('text')}")
        print("============================\n")


socketio_simulado = SocketIOSimulado()


# ============================================================
# 6. CONTROLADOR DE ROLAGEM
# ============================================================

controlador = ControladorRolagem(
    estado,
    alinhador,
    socketio_simulado
)


# ============================================================
# 7. RECONHECEDOR DE FALA
# ============================================================

reconhecedor = ReconhecedorFala()

print("Inicializando reconhecedor...")

if not reconhecedor.iniciar():
    print("ERRO: não foi possível iniciar o Vosk.")
    exit()

print("Reconhecedor iniciado com sucesso.\n")


# ============================================================
# 8. MOTOR DE ÁUDIO
# ============================================================

motor_audio = MotorAudio()

try:
    print("Abrindo microfone...\n")

    motor_audio.abrir_microfone()

    reconhecedor.resetar()

    RegistradorEventos.microfone_aberto()

except Exception as erro:
    print(f"ERRO ao abrir microfone: {erro}")
    exit()


# ============================================================
# 9. LOOP PRINCIPAL
# ============================================================

print(f"{Cores.VERDE}--- ENGINE ONLINE ---{Cores.BASE}\n")

# Coloca o teleprompter em modo automático.
# A partir daqui, o motor pode ouvir, comparar e avançar o roteiro.
estado.mudar_estado("AUTOMATICO")


estado.correndo = True

try:
    while estado.correndo:

        # Se o roteiro foi finalizado, encerramos o loop principal.
        if estado.esta_finalizado():
            RegistradorEventos.roteiro_finalizado()
            estado.correndo = False
            break

        # Descarta áudio residual após avanço.
        if estado.descartar_buffer:
            estado.descartar_buffer = False
            reconhecedor.resetar()
            continue

        try:
            # Captura áudio do microfone.
            dados_audio = motor_audio.ler_audio()

            # Processa áudio no Vosk.
            tipo_resultado, texto = reconhecedor.processar_audio(
                dados_audio
            )

            if texto:
                parcial = tipo_resultado == "PARCIAL"

                houve_rolagem = controlador.avaliar(
                    texto,
                    parcial
                )

                # Após avanço resetamos buffer.
                if houve_rolagem:
                    reconhecedor.resetar()

        except Exception as erro_loop:
            # Em caso de erro grave no loop principal,
            # mudamos o sistema para estado de falha.
            estado.mudar_estado("FALHA")

            # Registramos a falha de forma centralizada.
            RegistradorEventos.falha_sistema(erro_loop)

            # Encerramos o loop para evitar comportamento imprevisível.
            estado.correndo = False

except KeyboardInterrupt:
    print("\nSistema interrompido pelo usuário.")

finally:
    estado.correndo = False
    motor_audio.fechar_microfone()

    print("\nMicrofone encerrado.")
    print("Sistema finalizado.")

