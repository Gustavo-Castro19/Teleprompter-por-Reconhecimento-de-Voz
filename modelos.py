# Modelos.py
# Guarda estruturas de dados que serão usadas nas próximas melhorias.
# Nesta fase, ainda usamos listas simples, mas já deixamos a base preparada.

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
