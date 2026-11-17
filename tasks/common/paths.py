from pathlib import Path
from platformdirs import user_data_dir, user_config_dir

APP_NAME = "TeproG"
APP_AUTHOR = "Squad42"

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    return path

# Dados da AppData/Local -> Armazenamento/Processos pesados
LOCAL_DIR = Path(
    user_data_dir(APP_NAME, APP_AUTHOR, ensure_exists=True)
)

# Dados na AppData/Roaming -> Configurações no geral
ROAMING_DIR = Path(
    user_config_dir(APP_NAME, APP_AUTHOR, roaming=True, ensure_exists=True)
)

CONFIG_DIR = ensure_dir(ROAMING_DIR / "config")

MODELS_DIR = ensure_dir(LOCAL_DIR / "models")

_LOG_DIR = ensure_dir(LOCAL_DIR / "logs")

LOG_SLUG_DIR = ensure_dir(_LOG_DIR / "slug_process")

LOG_TP_DIR = ensure_dir(_LOG_DIR / "tp_process")