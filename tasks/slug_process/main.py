import socket
import json
import asyncio
import logging
import uvicorn

from fastapi import FastAPI
from common.logging_config import setup_logging
from common.paths import LOG_SLUG_DIR
from slug_process.router import router
from slug_process.security import TOKEN

setup_logging(LOG_SLUG_DIR, "slug_process")
logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(router)

async def main():
    logger.info("Iniciando slug_process")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    sock.setblocking(False)

    host = sock.getsockname()[0]
    port = sock.getsockname()[1]
    logger.info(f"IPv4: {host} | Port: {port}")

    logger.info("Enviando informações de inicialização para o Frontend")
    # Informa ao frontend a porta escolhida
    print(json.dumps({
        "service": "slug_process",
        "host": "127.0.0.1",
        "port": port,
        "token": TOKEN
    }), flush=True)
    logger.info("Informações iniciadas")

    logger.info("Iniciando Uvicorn")
    config = uvicorn.Config(app, log_level="warning")
    server = uvicorn.Server(config)

    await server.serve(sockets=[sock])

if __name__ == "__main__":
    asyncio.run(main())