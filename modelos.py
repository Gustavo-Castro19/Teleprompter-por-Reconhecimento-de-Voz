# Modelos.py
# Guarda estruturas de dados usadas pelo teleprompter.
# Agora também carregamos metadados editoriais do JSON/iNEWS,
# como tempo de fala, tempo de VT/link e tempo total da retranca.

from dataclasses import dataclass
from typing import Optional


@dataclass
class ResultadoComparacao:
    # Representa o resultado de uma comparação entre fala e roteiro.
    encontrou: bool
    pontuacao: float = 0.0
    indice_destino: Optional[int] = None
    motivo: str = ""


@dataclass
class EventoSistema:
    # Representa um evento importante do sistema.
    tipo_evento: str
    texto: str = ""
    indice_atual: int = 0
    observacao: str = ""


@dataclass
class SegmentoRoteiro:
    # Representa uma linha falável do roteiro.
    texto_falado: str
    texto_visual: str
    tipo_linha: str = "fala"
    indice_falado: int = 0
    indice_visual: int = 0

    # Tempo usado para rolagem da fala.
    # Prioridade: speakingTime do JSON distribuído por palavras.
    # Fallback: estimativa por palavras por minuto.
    tempo_estimado: Optional[float] = None
    origem_tempo: str = "estimativa_por_palavras"

    # Metadados editoriais da retranca.
    apresentador: Optional[str] = None
    titulo: Optional[str] = None
    pagina: Optional[str] = None
    item_type: Optional[str] = None
    ordem_slug: Optional[int] = None
    slug_id: Optional[str] = None

    # Tempos oficiais do JSON/iNEWS, quando existirem.
    speaking_time: float = 0.0
    tape_time: float = 0.0
    total_time: float = 0.0
    start_time: Optional[float] = None

    # Se depois desta fala existe VT/link/vinheta/imagem,
    # o frontend pode pausar a rolagem por esse tempo.
    pausa_apos_segundos: float = 0.0
    motivo_pausa: str = ""


@dataclass
class LinhaVisualMeta:
    # Metadados de uma linha que aparece visualmente no teleprompter.
    indice_visual: int
    texto_visual: str
    tipo_linha: str = "fala"

    titulo: Optional[str] = None
    pagina: Optional[str] = None
    item_type: Optional[str] = None
    ordem_slug: Optional[int] = None
    slug_id: Optional[str] = None

    speaking_time: float = 0.0
    tape_time: float = 0.0
    total_time: float = 0.0

    # Tempo associado à linha visual.
    # Para fala: tempo distribuído do speakingTime.
    # Para comando técnico: possível tempo de VT/link/intervalo.
    duracao_segundos: float = 0.0
    origem_tempo: str = "sem_tempo"
    pausa_tecnica_segundos: float = 0.0
    motivo_pausa: str = ""
