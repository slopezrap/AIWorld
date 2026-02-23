"""
Módulo de memoria para el ScraperAgent.

Abstracción del checkpointer de LangGraph para facilitar
la migración futura a Redis/SQLite.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Optional, List

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


class BaseMemoryManager(ABC):
    """
    Interfaz abstracta para gestión de memoria conversacional.

    Todas las implementaciones deben proveer:
    - get_checkpointer(): retorna el checkpointer de LangGraph
    - clear_session(): limpia una sesión específica
    - generate_thread_id(): genera un nuevo thread_id
    """

    @abstractmethod
    def get_checkpointer(self):
        """Retorna el checkpointer compatible con LangGraph."""
        ...

    @abstractmethod
    def clear_session(self, thread_id: str) -> None:
        """Limpia el estado de una sesión específica."""
        ...

    def generate_thread_id(self) -> str:
        """Genera un nuevo thread_id único."""
        return str(uuid.uuid4())

    @abstractmethod
    def get_history(self, thread_id: str) -> Optional[List]:
        """Obtiene el historial de mensajes de un thread."""
        ...


class InMemoryManager(BaseMemoryManager):
    """
    Implementación de memoria en RAM usando InMemorySaver de LangGraph.

    Adecuado para desarrollo y testing. Los datos se pierden al
    reiniciar el proceso.
    """

    def __init__(self):
        self._checkpointer = MemorySaver()
        logger.info("InMemoryManager inicializado")

    def get_checkpointer(self):
        """Retorna el MemorySaver de LangGraph."""
        return self._checkpointer

    def clear_session(self, thread_id: str) -> None:
        """
        Limpia la sesión creando un nuevo MemorySaver.

        InMemorySaver no soporta borrado selectivo por thread,
        así que recreamos el checkpointer completo.
        """
        self._checkpointer = MemorySaver()
        logger.info(f"Sesión limpiada (nuevo MemorySaver). Thread: {thread_id[:8]}...")

    def get_history(self, thread_id: str) -> Optional[List]:
        """Obtiene el historial de mensajes del thread actual."""
        try:
            config = {"configurable": {"thread_id": thread_id}}
            checkpoint = self._checkpointer.get(config)
            if checkpoint and "channel_values" in checkpoint:
                return checkpoint["channel_values"].get("messages", [])
            return []
        except Exception as e:
            logger.warning(f"Error obteniendo historial: {e}")
            return None


class NullMemoryManager(BaseMemoryManager):
    """
    Implementación sin memoria — para agentes que no necesitan
    persistir conversaciones.
    """

    def get_checkpointer(self):
        return None

    def clear_session(self, thread_id: str) -> None:
        pass

    def get_history(self, thread_id: str) -> Optional[List]:
        return None