# Teleprompter por Reconhecimento de Voz - New Implementation

Backend unificado para deploy web (Docker + Render/Fly.io/Railway).

## Arquitetura

```
new_impl/
├── backend/
│   ├── app/                    # Flask application
│   │   ├── __init__.py         # App factory + SocketIO
│   │   ├── config.py           # Pydantic settings
│   │   ├── routes/             # HTTP endpoints
│   │   │   ├── health.py       # /health, /ready
│   │   │   ├── scripts.py      # POST /api/scripts (BDDF upload)
│   │   │   └── teleprompter.py # GET /comando, /tp (SSR)
│   │   ├── services/           # Business logic
│   │   │   ├── state_machine.py
│   │   │   ├── script_processor.py
│   │   │   ├── scroll_controller.py
│   │   │   ├── aligner.py
│   │   │   ├── speech_recognizer.py  # Hybrid: Web Speech + Vosk
│   │   │   ├── audio_manager.py
│   │   │   └── bddf_processor.py
│   │   ├── websocket/          # SocketIO handlers
│   │   │   ├── handlers.py
│   │   ├── models/             # Data models
│   │   ├── utils/              # Utilities
│   │   │   ├── logger.py
│   │   │   └── text_normalizer.py
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
├── docker-compose.yml
├── .env.example               # Compose environment (copy to .env locally)
├── .github/workflows/ci.yml
└── download_model.py
```

## Características Principais

- **Hybrid Speech Recognition**: Web Speech API (browser) como primário, Vosk (servidor) como fallback
- **Multi-user**: estado isolado por sessão de navegador; `/comando` e `/tp` compartilham a sessão no mesmo navegador
- **BDDF Processing**: Upload e processamento de roteiros BDDF via API
- **Docker-first**: Multi-stage build, health checks, non-root user
- **Observability**: Structured logging, health endpoints, metrics ready

As sessões ficam em memória e o deploy usa um único worker. Redis não é usado.
Para executar várias instâncias/workers, será necessário adicionar armazenamento
compartilhado e configuração de fila Socket.IO antes de escalar.

## Desenvolvimento Local

```bash
# Run these commands from new_impl/
cp .env.example .env
# Replace SECRET_KEY with a long random value.

# Download model into backend/models (mounted by Docker Compose)
cd backend
python download_model.py
cp .env.example .env
cd ..

# Start the container
docker compose up --build

# Ou rodar direto com Python
cd backend
pip install -r requirements-dev.txt
python -m app
```

## Deploy

### Render
```yaml
# render.yaml
services:
  - type: web
    name: teleprompter-backend
    env: docker
    dockerfilePath: ./backend/Dockerfile
    envVars:
      - key: SECRET_KEY
        generateValue: true
```

### Fly.io
```toml
# fly.toml
app = "teleprompter-backend"
primary_region = "gru"

[build]
  dockerfile = "backend/Dockerfile"

[env]
  FLASK_ENV = "production"

[mounts]
  source = "vosk_model"
  destination = "/app/models"

[processes]
  app = "gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8000 backend.app:create_app()"
```

### Railway
```toml
# railway.toml
[build]
builder = "dockerfile"
dockerfilePath = "backend/Dockerfile"

[deploy]
healthcheckPath = "/healthz"
healthcheckTimeout = 100

[env]
FLASK_ENV = "production"
```

## API Endpoints

### Health
- `GET /health` - Liveness probe
- `GET /ready` - Readiness probe
- `GET /healthz` - Simple health check

### Scripts (BDDF)
- `POST /api/scripts` - Upload BDDF file or JSON
  - Form-data: `file` (JSON/TXT)
  - JSON body: BDDF payload directly

### Teleprompter (SSR)
- `GET /comando` - Operator interface
- `GET /tp` - Teleprompter display

### WebSocket Events

#### Client → Server
| Event | Payload | Description |
|-------|---------|-------------|
| `iniciar_motor` | `{}` | Start recognition engine |
| `manual_next` | `{}` | Manual advance |
| `manual_prev` | `{}` | Manual back |
| `pausar_motor` | `{}` | Pause |
| `retomar_motor` | `{}` | Resume |
| `alternar_pausa` | `{}` | Toggle pause |
| `speech_result` | `{text, isFinal, source, confidence}` | Web Speech API result |
| `speech_audio` | `{audio: base64}` | PCM 16 kHz mono chunk for Vosk |
| `speech_start` | `{mode, language}` | Start recognition session |
| `speech_stop` | `{}` | Stop recognition |

#### Server → Client
| Event | Payload | Description |
|-------|---------|-------------|
| `roteiro` | `{linhas, indiceAtual, segmentos, metadadosLinhas, configRolagem}` | Full script data |
| `cmd` | `{index, type, text, segmento, pausaAposSegundos}` | Scroll command |
| `estado_rolagem` | `{tipo, motivo, pausaSegundos, indiceFalado}` | Scroll state |
| `voz_roteiro` | `{estadoVoz, tipoResultado, textoReconhecido, ...}` | Voice progress |
| `status_motor` | `{estado, correndo, indiceAtual, modoImproviso}` | Engine status |
| `config_rolagem` | `{...}` | Scroll configuration |
| `config_tp_display` | `{maxWidthVw, maxHeightVh, aspectRatio}` | Display config |

## Estrutura do Script (Frontend)

O frontend recebe `segmentos` com:
```json
{
  "textoFalado": "string",
  "textoVisual": "string",
  "tipoLinha": "fala|tecnico|pausa_tecnica|separador",
  "indiceFalado": 0,
  "indiceVisual": 0,
  "tempoEstimadoSegundos": 2.5,
  "origemTempo": "speakingTime_json_distribuido|estimativa_por_palavras",
  "pausaAposSegundos": 0,
  "motivoPausa": "",
  "speakingTime": 10.0,
  "tapeTime": 0,
  "totalTime": 10.0
}
```

## Modelo Vosk

O modelo não é incluído no repositório. Baixe antes do build:

```bash
cd backend
python download_model.py
```

Ou no Dockerfile (descomente a seção de download).

## Variáveis de Ambiente

Veja `.env.example` para todas as opções.

## Testes

```bash
cd backend
pytest -v --cov=app
```

## Licença

Projeto da Squad 29 - Porto Digital.
