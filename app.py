# App.py
# Arquivo principal do sistema.
# Ele sobe Flask, SocketIO e conecta todos os módulos.
# Nesta reestruturação, NÃO usamos motor.py.

from flask import Flask, render_template
from flask_socketio import SocketIO

from seguranca import checagem_seguranca, Cores
from registrador_eventos import RegistradorEventos
from maquina_estados import MaquinaEstados
from processador_roteiro import ProcessadorRoteiro
from alinhador_roteiro import AlinhadorRoteiro
from controlador_rolagem import ControladorRolagem
from reconhecedor_fala import ReconhecedorFala
from motor_audio import MotorAudio


# Cria a aplicação Flask.
app = Flask(__name__)

# Chave usada pelo Flask/SocketIO.
# Futuramente, deve ir para variável de ambiente.
app.config["SECRET_KEY"] = "squad29_final_key"

# Cria o servidor SocketIO.
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    ping_timeout=60
)

# Cria o objeto que guarda o estado do sistema.
estado = MaquinaEstados()

# Carrega e processa o roteiro.
processador = ProcessadorRoteiro()

(
    estado.linhas_roteiro,
    estado.linhas_exibidas,
    estado.falar_para_exibir
) = processador.carregar_roteiro()

# Cria o alinhador entre linha falada e linha visual.
alinhador = AlinhadorRoteiro(
    estado.falar_para_exibir,
    estado.linhas_exibidas
)

# Cria o controlador responsável pelas decisões de rolagem.
controlador = ControladorRolagem(
    estado,
    alinhador,
    socketio
)


def processar_audio_em_loop():
    # Loop principal de áudio, Vosk e avaliação de rolagem.
    RegistradorEventos.maquina_ativa(Cores)

    reconhecedor = ReconhecedorFala()

    # Inicia o Vosk.
    if not reconhecedor.iniciar():
        return

    motor_audio = MotorAudio()

    try:
        # Abre microfone.
        motor_audio.abrir_microfone()

        # Reseta o reconhecedor.
        reconhecedor.resetar()

        RegistradorEventos.microfone_aberto()

        # Enquanto o sistema estiver rodando, fica ouvindo áudio.
        while estado.correndo:
            socketio.sleep(0.001)

            # Quando ocorre avanço, descartamos áudio residual.
            if estado.descartar_buffer:
                estado.descartar_buffer = False
                reconhecedor.resetar()
                continue

            try:
                # Lê áudio do microfone.
                dados_audio = motor_audio.ler_audio()

                # Processa áudio com Vosk.
                tipo_resultado, texto = reconhecedor.processar_audio(dados_audio)

                if texto:
                    # Verifica se o resultado é parcial ou final.
                    parcial = tipo_resultado == "PARCIAL"

                    # Envia a transcrição para o controlador de rolagem.
                    if controlador.avaliar(texto, parcial):
                        reconhecedor.resetar()

            except Exception:
                # Mantido como no comportamento original.
                # Depois será substituído por log estruturado.
                continue

    finally:
        # Garante fechamento do microfone ao encerrar.
        motor_audio.fechar_microfone()


def iniciar_sistema():
    # Evita iniciar duas tarefas de áudio ao mesmo tempo.
    if estado.proc_audio:
        return

    estado.correndo = True

    # Inicia o loop de áudio em segundo plano.
    estado.proc_audio = socketio.start_background_task(processar_audio_em_loop)


@app.route("/")
def index():
    # Envia o roteiro visual para a interface HTML.
    return render_template(
        "index.html",
        script=estado.linhas_exibidas
    )


@socketio.on("connect")
def cliente_conectado():
    # Executa quando a interface web conecta ao backend.
    RegistradorEventos.cliente_conectado()

    primeiro_indice_visual = alinhador.obter_primeiro_indice_visual()

    # Sincroniza a interface com a primeira linha.
    socketio.emit(
        "cmd",
        {
            "index": primeiro_indice_visual,
            "type": "sync",
            "text": ""
        }
    )

    # Inicia áudio + Vosk + rolagem.
    iniciar_sistema()


if __name__ == "__main__":
    # Segurança comentada nesta fase para facilitar os testes.
    # checagem_seguranca()

    RegistradorEventos.servidor("http://127.0.0.1:5500")

    # Inicia servidor Flask/SocketIO.
    socketio.run(app, debug=True, port=5500)
