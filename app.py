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
# - envia roteiro, segmentos e metadados de tempo ao navegador;
# - respeita speakingTime, tapeTime e totalTime vindos do JSON;
# - permite pausa/retomada em VT, link, vinheta e improviso.
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
from configuracoes import CONFIG


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

# Guarda os metadados no estado para que outros módulos também possam consultar.
estado.segmentos = processador.segmentos
estado.metadados_linhas_visuais = processador.metadados_linhas_visuais

print("Roteiro carregado com sucesso.\n") 


# ============================================================
# 4. DIAGNÓSTICO INICIAL
# ============================================================

print("========== DIAGNÓSTICO ==========")
print(f"Linhas faláveis : {len(estado.linhas_roteiro)}")
print(f"Linhas visuais  : {len(estado.linhas_exibidas)}")
print(f"Mapeamentos     : {len(estado.falar_para_exibir)}")
print(f"Segmentos       : {len(estado.segmentos)}")
print(f"Metadados visuais: {len(estado.metadados_linhas_visuais)}")

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

def obter_segmentos_para_frontend():
    """
    Converte os segmentos faláveis para objetos enviados ao frontend.
    """

    segmentos_frontend = []

    for segmento in getattr(processador, "segmentos", []):
        segmentos_frontend.append(
            {
                "textoFalado": segmento.texto_falado,
                "textoVisual": segmento.texto_visual,
                "tipoLinha": segmento.tipo_linha,
                "indiceFalado": segmento.indice_falado,
                "indiceVisual": segmento.indice_visual,
                "quantidadePalavras": len(segmento.texto_falado.split()),
                "tempoEstimadoSegundos": round(segmento.tempo_estimado or 0.0, 2),
                "origemTempo": segmento.origem_tempo,
                "apresentador": segmento.apresentador,
                "titulo": segmento.titulo,
                "pagina": segmento.pagina,
                "itemType": segmento.item_type,
                "ordemSlug": segmento.ordem_slug,
                "slugId": segmento.slug_id,
                "speakingTime": segmento.speaking_time,
                "tapeTime": segmento.tape_time,
                "totalTime": segmento.total_time,
                "startTime": segmento.start_time,
                "pausaAposSegundos": round(segmento.pausa_apos_segundos or 0.0, 2),
                "motivoPausa": segmento.motivo_pausa,
            }
        )

    return segmentos_frontend


def obter_metadados_visuais_para_frontend():
    """
    Converte metadados de linhas visuais para envio ao frontend.
    Esses dados são usados pela rolagem contínua visual.
    """

    metadados = []

    for linha in getattr(processador, "metadados_linhas_visuais", []):
        metadados.append(
            {
                "indiceVisual": linha.indice_visual,
                "textoVisual": linha.texto_visual,
                "tipoLinha": linha.tipo_linha,
                "titulo": linha.titulo,
                "pagina": linha.pagina,
                "itemType": linha.item_type,
                "ordemSlug": linha.ordem_slug,
                "slugId": linha.slug_id,
                "speakingTime": linha.speaking_time,
                "tapeTime": linha.tape_time,
                "totalTime": linha.total_time,
                "duracaoSegundos": round(linha.duracao_segundos or 0.0, 2),
                "origemTempo": linha.origem_tempo,
                "pausaTecnicaSegundos": round(linha.pausa_tecnica_segundos or 0.0, 2),
                "motivoPausa": linha.motivo_pausa,
            }
        )

    return metadados


def calcular_configuracao_rolagem():
    """
    Monta um resumo geral para a rolagem.
    Agora a prioridade é o tempo oficial do JSON.
    """

    segmentos = getattr(processador, "segmentos", [])
    metadados_visuais = getattr(processador, "metadados_linhas_visuais", [])

    tempo_fala = sum(
        segmento.tempo_estimado or 0.0
        for segmento in segmentos
    )

    tempo_pausas = sum(
        linha.pausa_tecnica_segundos or 0.0
        for linha in metadados_visuais
    ) + sum(
        segmento.pausa_apos_segundos or 0.0
        for segmento in segmentos
    )

    total_palavras = sum(
        len(segmento.texto_falado.split())
        for segmento in segmentos
    )

    total_speaking_json = sum(
        segmento.speaking_time or 0.0
        for segmento in segmentos
        if segmento.indice_falado == 0
    )

    # Como cada segmento repete o speakingTime da retranca,
    # o valor acima não serve para soma geral. Mantemos o tempo_fala
    # como fonte de verdade para a rolagem.
    return {
        "palavrasPorMinutoBase": CONFIG.get("palavras_por_minuto_base", 150),
        "totalPalavrasFalaveis": total_palavras,
        "totalSegmentosFalaveis": len(segmentos),
        "totalLinhasVisuais": len(estado.linhas_exibidas),
        "tempoTotalFalaSegundos": round(tempo_fala, 2),
        "tempoTotalPausasTecnicasSegundos": round(tempo_pausas, 2),
        "tempoTotalEstimadoSegundos": round(tempo_fala + tempo_pausas, 2),
        "origemDoTempo": "speakingTime_tapeTime_totalTime_json_com_fallback",
        "velocidadeMinima": CONFIG.get("velocidade_minima_rolagem", 0.05),
        "velocidadeMaxima": CONFIG.get("velocidade_maxima_rolagem", 3.0),
    }


def emitir_status():
    # Envia o estado atual do motor para o frontend.
    socketio.emit(
        "status_motor",
        {
            "estado": estado.estado_atual,
            "correndo": estado.correndo,
            "indiceAtual": estado.idx_atual,
            "modoImproviso": estado.esta_em_improviso(),
        }
    )


def emitir_roteiro_para_frontend():
    """
    Envia ao frontend:
    - linhas visuais;
    - posição inicial;
    - segmentos faláveis com tempo;
    - metadados de linhas visuais;
    - configuração geral de rolagem.
    """

    primeiro_indice_visual = alinhador.obter_primeiro_indice_visual()

    segmentos_frontend = obter_segmentos_para_frontend()
    metadados_visuais = obter_metadados_visuais_para_frontend()
    configuracao_rolagem = calcular_configuracao_rolagem()

    socketio.emit(
        "roteiro",
        {
            "linhas": estado.linhas_exibidas,
            "indiceAtual": primeiro_indice_visual,
            "segmentos": segmentos_frontend,
            "metadadosLinhas": metadados_visuais,
            "configRolagem": configuracao_rolagem,
        }
    )

    socketio.emit("config_rolagem", configuracao_rolagem)

    socketio.emit(
        "cmd",
        {
            "index": primeiro_indice_visual,
            "type": "sync",
            "text": "",
            "segmento": None,
            "pausaAposSegundos": 0,
        }
    )

    print("\n========== CONFIGURAÇÃO DE ROLAGEM ==========")
    print(f"Segmentos enviados        : {len(segmentos_frontend)}")
    print(f"Linhas visuais enviadas   : {len(metadados_visuais)}")
    print(f"Palavras faláveis         : {configuracao_rolagem['totalPalavrasFalaveis']}")
    print(f"Tempo fala (s)            : {configuracao_rolagem['tempoTotalFalaSegundos']}")
    print(f"Tempo pausas técnicas (s) : {configuracao_rolagem['tempoTotalPausasTecnicasSegundos']}")
    print(f"Tempo total (s)           : {configuracao_rolagem['tempoTotalEstimadoSegundos']}")
    print(f"Origem do tempo           : {configuracao_rolagem['origemDoTempo']}")
    print("============================================\n")


def emitir_estado_rolagem(tipo, motivo="", pausa_segundos=0):
    """
    Evento específico para o frontend controlar a rolagem visual.
    """

    socketio.emit(
        "estado_rolagem",
        {
            "tipo": tipo,
            "motivo": motivo,
            "pausaSegundos": round(pausa_segundos or 0.0, 2),
            "indiceFalado": estado.idx_atual,
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

    estado.mudar_estado("AUTOMATICO")
    estado.correndo = True
    emitir_status()
    emitir_estado_rolagem("AUTOMATICO", "Motor iniciado")

    print("Inicializando reconhecedor...")

    if not reconhecedor.iniciar():
        estado.mudar_estado("FALHA")
        RegistradorEventos.falha_sistema(
            "Não foi possível iniciar o Vosk."
        )
        estado.correndo = False
        emitir_status()
        emitir_estado_rolagem("FALHA", "Falha ao iniciar Vosk")
        return

    print("Reconhecedor iniciado com sucesso.\n")

    try:
        print("Abrindo microfone...\n")

        motor_audio.abrir_microfone()
        reconhecedor.resetar()
        RegistradorEventos.microfone_aberto()

        while estado.correndo:
            socketio.sleep(0.001)

            if estado.esta_finalizado():
                RegistradorEventos.roteiro_finalizado()
                estado.correndo = False
                emitir_status()
                emitir_estado_rolagem("FINALIZADO", "Roteiro finalizado")
                break

            if estado.esta_pausado():
                socketio.sleep(0.05)
                continue

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
                        emitir_status()

            except Exception as erro_loop:
                estado.mudar_estado("FALHA")
                RegistradorEventos.falha_sistema(erro_loop)
                estado.correndo = False
                emitir_status()
                emitir_estado_rolagem("FALHA", str(erro_loop))

    except Exception as erro_audio:
        estado.mudar_estado("FALHA")
        RegistradorEventos.falha_sistema(erro_audio)
        estado.correndo = False
        emitir_status()
        emitir_estado_rolagem("FALHA", str(erro_audio))

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


@socketio.on("solicitar_config_rolagem")
def reenviar_configuracao_rolagem():
    """
    Permite ao frontend pedir novamente a configuração.
    """

    socketio.emit("config_rolagem", calcular_configuracao_rolagem())
    print("[SOCKET] Configuração de rolagem reenviada ao frontend.")


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
        emitir_estado_rolagem("PAUSADO", "Pausa manual")

    emitir_status()


@socketio.on("retomar_motor")
def retomar_motor():
    """
    Retoma o processamento automático.
    """

    if not estado.esta_finalizado():
        estado.mudar_estado("AUTOMATICO")
        emitir_estado_rolagem("AUTOMATICO", "Retomada manual")

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
        emitir_estado_rolagem("AUTOMATICO", "Retomada manual")
    else:
        estado.mudar_estado("PAUSADO")
        emitir_estado_rolagem("PAUSADO", "Pausa manual")

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
