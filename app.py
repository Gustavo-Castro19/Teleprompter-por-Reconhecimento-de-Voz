# app.py
# ============================================================
# TELEPROMPTER SQUAD 29
# MODO WEB — FLASK + SOCKETIO
# ============================================================
#
# Agora o sistema:
# - sobe um servidor Flask;
# - renderiza as telas HTML;
# - usa SocketIO para enviar comandos ao frontend;
# - roda áudio/Vosk em background;
# - mantém a máquina de estados;
# - envia o roteiro carregado para o navegador;
# - permite avanço/retrocesso manual;
# - permite pausa/retomada do motor;
# - inicia o motor quando o frontend solicita via SocketIO.
# ============================================================

from flask import Flask, render_template, redirect
from flask_socketio import SocketIO

from maquina_estados import MaquinaEstados
from processador_roteiro import ProcessadorRoteiro
from alinhador_roteiro import AlinhadorRoteiro
from controlador_rolagem import ControladorRolagem
from reconhecedor_fala import ReconhecedorFala
from motor_audio import MotorAudio
from registrador_eventos import RegistradorEventos
from seguranca import Cores


# ============================================================
# 1. CONFIGURAÇÃO DO FLASK E SOCKETIO
# ============================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = "squad29_dev_key"

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    ping_timeout=60
)


# ============================================================
# 2. ESTADO GLOBAL DO SISTEMA
# ============================================================

estado = MaquinaEstados()


# ============================================================
# 3. CARREGAMENTO DO ROTEIRO
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
# 4. DIAGNÓSTICO INICIAL
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
# 5. ALINHADOR
# ============================================================

alinhador = AlinhadorRoteiro(
    estado.falar_para_exibir,
    estado.linhas_exibidas
)


# ============================================================
# 6. CONTROLADOR DE ROLAGEM
# ============================================================

controlador = ControladorRolagem(
    estado,
    alinhador,
    socketio
)


# ============================================================
# 7. RECONHECEDOR DE FALA E MOTOR DE ÁUDIO
# ============================================================

reconhecedor = ReconhecedorFala()
motor_audio = MotorAudio()


# ============================================================
# 8. FUNÇÕES AUXILIARES DE SOCKET
# ============================================================

def emitir_status():
    # Envia o estado atual do motor para o frontend.
    socketio.emit(
        "status_motor",
        {
            "estado": estado.estado_atual,
            "correndo": estado.correndo,
            "indiceAtual": estado.idx_atual
        }
    )


def emitir_roteiro_para_frontend():
    # Envia o roteiro visual completo para o frontend.
    primeiro_indice_visual = alinhador.obter_primeiro_indice_visual()

    socketio.emit(
        "roteiro",
        {
            "linhas": estado.linhas_exibidas,
            "indiceAtual": primeiro_indice_visual
        }
    )

    # Sincroniza a posição inicial.
    socketio.emit(
        "cmd",
        {
            "index": primeiro_indice_visual,
            "type": "sync",
            "text": ""
        }
    )


# ============================================================
# 9. LOOP PRINCIPAL DE ÁUDIO EM BACKGROUND
# ============================================================

def loop_audio():
    """
    Loop principal do motor.

    Roda em segundo plano para não travar o Flask.
    """

    print(f"{Cores.VERDE}--- ENGINE ONLINE ---{Cores.BASE}\n")

    # Coloca o sistema em modo automático.
    estado.mudar_estado("AUTOMATICO")
    estado.correndo = True
    emitir_status()

    # Inicializa o Vosk.
    print("Inicializando reconhecedor...")

    if not reconhecedor.iniciar():
        estado.mudar_estado("FALHA")
        RegistradorEventos.falha_sistema(
            "Não foi possível iniciar o Vosk."
        )
        estado.correndo = False
        emitir_status()
        return

    print("Reconhecedor iniciado com sucesso.\n")

    try:
        print("Abrindo microfone...\n")

        motor_audio.abrir_microfone()

        reconhecedor.resetar()

        RegistradorEventos.microfone_aberto()

        while estado.correndo:

            socketio.sleep(0.001)

            # Se o roteiro foi finalizado, encerra o motor.
            if estado.esta_finalizado():
                RegistradorEventos.roteiro_finalizado()
                estado.correndo = False
                emitir_status()
                break

            # Se estiver pausado, mantém o loop vivo,
            # mas não processa áudio.
            if estado.esta_pausado():
                socketio.sleep(0.05)
                continue

            # Descarta áudio residual após avanço.
            if estado.descartar_buffer:
                estado.descartar_buffer = False
                reconhecedor.resetar()
                continue

            try:
                dados_audio = motor_audio.ler_audio()

                tipo_resultado, texto = reconhecedor.processar_audio(
                    dados_audio
                )

                if texto:
                    parcial = tipo_resultado == "PARCIAL"

                    houve_rolagem = controlador.avaliar(
                        texto,
                        parcial
                    )

                    if houve_rolagem:
                        reconhecedor.resetar()

            except Exception as erro_loop:
                estado.mudar_estado("FALHA")
                RegistradorEventos.falha_sistema(erro_loop)
                estado.correndo = False
                emitir_status()

    except Exception as erro_audio:
        estado.mudar_estado("FALHA")
        RegistradorEventos.falha_sistema(erro_audio)
        estado.correndo = False
        emitir_status()

    finally:
        motor_audio.fechar_microfone()

        print("\nMicrofone encerrado.")
        print("Sistema finalizado.")


def iniciar_motor_se_necessario():
    """
    Inicia o loop de áudio apenas uma vez.
    """

    if estado.proc_audio and estado.correndo:
        print("[MOTOR] Motor já está em execução.")
        return

    print("[MOTOR] Iniciando tarefa de áudio em background.")
    estado.proc_audio = socketio.start_background_task(loop_audio)


# ============================================================
# 10. ROTAS WEB
# ============================================================

@app.route("/")
def inicio():
    return redirect("/comando")


@app.route("/comando")
def tela_comando():
    return render_template("comando.html")


@app.route("/tp")
def tela_teleprompter():
    return render_template("tp.html")


# ============================================================
# 11. EVENTOS SOCKETIO
# ============================================================

@socketio.on("connect")
def cliente_conectado():
    """
    Executa sempre que uma tela conecta ao backend.
    """

    RegistradorEventos.cliente_conectado()

    emitir_roteiro_para_frontend()
    emitir_status()


@socketio.on("iniciar_motor")
def iniciar_motor_pelo_frontend():
    """
    Inicia o motor quando o frontend solicita explicitamente.
    """

    print("[SOCKET] Pedido recebido para iniciar o motor.")

    iniciar_motor_se_necessario()


@socketio.on("manual_next")
def avancar_manual():
    """
    Avanço manual vindo do frontend.
    """

    destino = estado.idx_atual + 1

    if destino <= len(estado.linhas_roteiro):
        controlador.enviar_comando(
            destino,
            "next",
            "Avanço manual"
        )

    emitir_status()


@socketio.on("manual_prev")
def voltar_manual():
    """
    Retorno manual vindo do frontend.
    """

    destino = max(estado.idx_atual - 1, 0)

    controlador.enviar_comando(
        destino,
        "back",
        "Retorno manual"
    )

    emitir_status()


@socketio.on("pausar_motor")
def pausar_motor():
    """
    Pausa o processamento automático.
    """

    if not estado.esta_finalizado():
        estado.mudar_estado("PAUSADO")

    emitir_status()


@socketio.on("retomar_motor")
def retomar_motor():
    """
    Retoma o processamento automático.
    """

    if not estado.esta_finalizado():
        estado.mudar_estado("AUTOMATICO")

    emitir_status()


@socketio.on("alternar_pausa")
def alternar_pausa():
    """
    Alterna entre PAUSADO e AUTOMATICO.
    """

    if estado.esta_finalizado():
        emitir_status()
        return

    if estado.esta_pausado():
        estado.mudar_estado("AUTOMATICO")
    else:
        estado.mudar_estado("PAUSADO")

    emitir_status()


# ============================================================
# 12. START DO SERVIDOR
# ============================================================

if __name__ == "__main__":
    print("Servidor: http://127.0.0.1:5500")

    socketio.run(
        app,
        debug=True,
        port=5500,
        use_reloader=False
    )