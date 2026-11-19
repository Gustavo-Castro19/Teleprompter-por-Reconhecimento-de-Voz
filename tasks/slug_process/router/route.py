import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from slug_process.security import require_token
from slug_process.service import ScriptImportError, import_script_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/health")
async def health():
    return {"status": "ok", "service": "slug_process"}


@router.post("/import", dependencies=[Depends(require_token)])
async def import_script(file: UploadFile = File(...)):
    filename = file.filename or ""
    raw = await file.read()
    logger.info("Importando '%s' (%s bytes)", filename, len(raw))

    try:
        script, saved_path = await run_in_threadpool(import_script_file, filename, raw)
    except ScriptImportError as error:
        logger.warning("Falha ao importar '%s': %s", filename, error)
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error

    logger.info("Roteiro salvo em %s", saved_path)
    return {
        "status": "ok",
        "file": str(saved_path),
        "meta": script.meta.model_dump(),
    }
