from __future__ import annotations

import asyncio
import logging
import secrets

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.concurrency import run_in_threadpool

from common.paths import LOCAL_DIR, MODELS_DIR
from tp_process.security import TOKEN, require_token
from tp_process.service.device_config import (
    list_input_devices,
    load_device_config,
    select_device,
)
from tp_process.service.engine import engine
from tp_process.service.models import DeviceSelectRequest, parse_incoming

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")
ws_router = APIRouter()


def _token_is_valid(token: str) -> bool:
    if not token:
        return False
    try:
        return secrets.compare_digest(token, TOKEN)
    except (TypeError, ValueError):
        return False


@router.get("/health")
async def health():
    script_path = LOCAL_DIR / "slug_script.json"
    model_path = MODELS_DIR / "model-pt"
    return {
        "status": "ok",
        "service": "tp_process",
        "active": engine.active,
        "script_ready": script_path.exists(),
        "model_ready": model_path.exists(),
        "script_path": str(script_path),
        "model_path": str(model_path),
    }


@router.get("/devices", dependencies=[Depends(require_token)])
async def get_devices():
    devices = await run_in_threadpool(list_input_devices)
    selected = await run_in_threadpool(load_device_config)
    return {
        "devices": [item.model_dump() for item in devices],
        "selected": selected.model_dump(),
    }


@router.post("/devices", dependencies=[Depends(require_token)])
async def post_devices(body: DeviceSelectRequest):
    try:
        selected = await run_in_threadpool(select_device, body.device_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "ok", "selected": selected.model_dump()}


@ws_router.websocket("/ws/teleprompter")
async def teleprompter_ws(
    websocket: WebSocket,
    token: str = Query(default=""),
):
    if not _token_is_valid(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    loop = asyncio.get_running_loop()
    client = websocket.client
    logger.info("WebSocket conectado: %s", client)

    async def emit(message) -> None:
        payload = message.model_dump()
        await websocket.send_json(payload)
        logger.info("WS → %s", payload)

    engine.bind(loop, emit)

    try:
        while True:
            raw = await websocket.receive_json()
            logger.info("WS ← %s", raw)
            try:
                message = parse_incoming(raw)
            except Exception as error:
                logger.warning("Mensagem WS inválida: %s (%s)", raw, error)
                await websocket.send_json(
                    {"type": "error", "detail": f"Mensagem inválida: {error}"}
                )
                continue

            try:
                outgoing = await run_in_threadpool(engine.handle_message, message)
            except FileNotFoundError as error:
                logger.warning("Recurso ausente: %s", error)
                await websocket.send_json({"type": "error", "detail": str(error)})
                continue
            except Exception as error:
                logger.exception("Erro ao processar mensagem WS")
                await websocket.send_json({"type": "error", "detail": str(error)})
                continue

            for item in outgoing:
                await emit(item)
    except WebSocketDisconnect:
        logger.info("WebSocket desconectado: %s", client)
    finally:
        engine.unbind()
