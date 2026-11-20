import asyncio
import json
import logging
import socket
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from common.logging_config import setup_logging
from common.paths import LOCAL_DIR, LOG_TP_DIR, MODELS_DIR
from tp_process.router import router, ws_router
from tp_process.security import TOKEN
from tp_process.service.device_config import ensure_device_config

setup_logging(LOG_TP_DIR, "tp_process")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        config = ensure_device_config()
        logger.info(
            "Config de áudio pronta: device_id=%s name=%r",
            config.device_id,
            config.name,
        )
    except Exception as error:
        logger.warning("Não foi possível preparar config de áudio: %s", error)

    script_path = LOCAL_DIR / "slug_script.json"
    model_path = MODELS_DIR / "model-pt"
    logger.info("Roteiro: %s (existe=%s)", script_path, script_path.exists())
    logger.info("Modelo Vosk: %s (existe=%s)", model_path, model_path.exists())
    if not model_path.exists():
        logger.warning(
            'Modelo ausente — baixe o Vosk pt-BR e renomeie a pasta para "model-pt".'
        )
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)
app.include_router(ws_router)


async def main():
    logger.info("Iniciando tp_process")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    sock.setblocking(False)

    host = sock.getsockname()[0]
    port = sock.getsockname()[1]
    logger.info("IPv4: %s | Port: %s", host, port)

    logger.info("Enviando informações de inicialização para o Frontend")
    print(
        json.dumps(
            {
                "service": "tp_process",
                "host": "127.0.0.1",
                "port": port,
                "token": TOKEN,
            }
        ),
        flush=True,
    )
    logger.info("Informações iniciadas")

    logger.info("Iniciando Uvicorn")
    config = uvicorn.Config(app, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve(sockets=[sock])


if __name__ == "__main__":
    asyncio.run(main())
