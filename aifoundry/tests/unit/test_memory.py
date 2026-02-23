"""
Tests unitarios del módulo de memoria.
"""

import pytest
from unittest.mock import MagicMock, patch

from aifoundry.app.core.agents.scraper.memory import (
    BaseMemoryManager,
    InMemoryManager,
    NullMemoryManager,
)


class TestInMemoryManager:
    """Tests de InMemoryManager."""

    def test_get_checkpointer_returns_memory_saver(self):
        """get_checkpointer() retorna un MemorySaver."""
        manager = InMemoryManager()
        cp = manager.get_checkpointer()
        assert cp is not None
        # Verificar que es un MemorySaver de LangGraph
        from langgraph.checkpoint.memory import MemorySaver

        assert isinstance(cp, MemorySaver)

    def test_clear_session_creates_new_checkpointer(self):
        """clear_session() crea un nuevo MemorySaver."""
        manager = InMemoryManager()
        old_cp = manager.get_checkpointer()

        manager.clear_session("test-thread-123")
        new_cp = manager.get_checkpointer()

        assert new_cp is not old_cp

    def test_generate_thread_id_unique(self):
        """generate_thread_id() genera IDs únicos."""
        manager = InMemoryManager()
        id1 = manager.generate_thread_id()
        id2 = manager.generate_thread_id()

        assert id1 != id2
        assert len(id1) > 10  # UUID tiene al menos 32 chars + guiones

    def test_get_history_empty_thread(self):
        """get_history() retorna lista vacía para thread sin datos."""
        manager = InMemoryManager()
        history = manager.get_history("nonexistent-thread")

        assert history == [] or history is None


class TestNullMemoryManager:
    """Tests de NullMemoryManager."""

    def test_get_checkpointer_returns_none(self):
        """get_checkpointer() retorna None."""
        manager = NullMemoryManager()
        assert manager.get_checkpointer() is None

    def test_clear_session_noop(self):
        """clear_session() no hace nada (no lanza error)."""
        manager = NullMemoryManager()
        manager.clear_session("any-thread")  # No debe lanzar

    def test_get_history_returns_none(self):
        """get_history() retorna None."""
        manager = NullMemoryManager()
        assert manager.get_history("any-thread") is None

    def test_generate_thread_id(self):
        """generate_thread_id() funciona incluso en NullMemoryManager."""
        manager = NullMemoryManager()
        tid = manager.generate_thread_id()
        assert isinstance(tid, str)
        assert len(tid) > 10


class TestBaseMemoryManagerInterface:
    """Tests de la interfaz abstracta."""

    def test_cannot_instantiate_directly(self):
        """BaseMemoryManager no se puede instanciar directamente."""
        with pytest.raises(TypeError):
            BaseMemoryManager()

    def test_inmemory_is_instance(self):
        """InMemoryManager es instancia de BaseMemoryManager."""
        manager = InMemoryManager()
        assert isinstance(manager, BaseMemoryManager)

    def test_null_is_instance(self):
        """NullMemoryManager es instancia de BaseMemoryManager."""
        manager = NullMemoryManager()
        assert isinstance(manager, BaseMemoryManager)