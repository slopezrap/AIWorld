"""
Brave Rate Limiter - Rate limiting para Brave Search API.

Basado en HEFESTO - Funciones para integración con Brave Search.

Este módulo contiene:
- BraveRateLimiter: Rate limiter con retry y backoff
- get_brave_rate_limiter(): Singleton global
"""

import logging
import asyncio
from typing import Callable, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BraveRateLimiter:
    """
    Rate limiter para Brave Search API.
    
    - Semáforo: Solo 1 petición a Brave a la vez
    - Límite: 1 request/segundo por defecto (Brave free tier)
    - Retry con backoff exponencial en caso de 429
    
    Example:
        ```python
        limiter = get_brave_rate_limiter()
        
        async def search():
            return await brave_api.search("query")
        
        result = await limiter.execute_with_retry(search)
        ```
    """
    
    def __init__(self, requests_per_second: float = 1.0, max_retries: int = 3):
        """
        Inicializa el rate limiter.
        
        Args:
            requests_per_second: Peticiones por segundo permitidas
            max_retries: Número máximo de reintentos en caso de 429
        """
        self.min_interval = timedelta(seconds=1.0 / requests_per_second)
        self.max_retries = max_retries
        self.last_request = datetime.min
        self._lock = asyncio.Lock()
        # Semáforo: garantiza que SOLO 1 petición a Brave se ejecute a la vez
        self._semaphore = asyncio.Semaphore(1)
    
    async def wait_if_needed(self):
        """
        Espera si es necesario para respetar el rate limit.
        
        NOTA: Este método debe llamarse DENTRO del contexto del semáforo
        para garantizar que solo una petición esté en curso.
        """
        async with self._lock:
            now = datetime.now()
            elapsed = now - self.last_request
            if elapsed < self.min_interval:
                wait_time = (self.min_interval - elapsed).total_seconds()
                logger.debug(f"Brave rate limit: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            self.last_request = datetime.now()
    
    async def acquire(self):
        """Adquiere el semáforo (bloquea si hay otra petición en curso)."""
        await self._semaphore.acquire()
        logger.debug("Brave semaphore: acquired")
    
    def release(self):
        """Libera el semáforo."""
        self._semaphore.release()
        logger.debug("Brave semaphore: released")
    
    async def __aenter__(self):
        """Context manager: adquiere semáforo y espera rate limit."""
        await self.acquire()
        await self.wait_if_needed()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager: libera semáforo."""
        self.release()
        return False
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta una función con retry y backoff exponencial.
        
        Usa el semáforo para garantizar que solo una petición a Brave
        esté en curso a la vez.
        
        Args:
            func: Función async a ejecutar
            *args, **kwargs: Argumentos para la función
            
        Returns:
            Resultado de la función
            
        Raises:
            Exception: Si se agotan los reintentos
        """
        last_error = None
        wait_time = 2  # Default
        
        for attempt in range(self.max_retries):
            # Adquirir semáforo: solo 1 petición a la vez
            async with self:  # usa __aenter__ y __aexit__
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # Si es rate limit (429), hacer backoff
                    if "429" in error_str or "too many" in error_str or "rate limit" in error_str:
                        wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s
                        logger.warning(f"Brave 429 - retry {attempt + 1}/{self.max_retries} en {wait_time}s")
                        last_error = e
                    else:
                        # Otro error, no reintentar
                        raise
            
            # Esperar backoff FUERA del semáforo para no bloquear
            if last_error:
                await asyncio.sleep(wait_time)
        
        # Si llegamos aquí, se agotaron los reintentos
        raise last_error or Exception("Max retries exceeded")


# Singleton global del rate limiter
_brave_rate_limiter: Optional[BraveRateLimiter] = None


def get_brave_rate_limiter() -> BraveRateLimiter:
    """
    Obtiene el singleton del rate limiter de Brave.
    
    Returns:
        Instancia global del BraveRateLimiter
    """
    global _brave_rate_limiter
    if _brave_rate_limiter is None:
        _brave_rate_limiter = BraveRateLimiter(requests_per_second=1.0, max_retries=3)
    return _brave_rate_limiter


def reset_brave_rate_limiter():
    """Resetea el singleton (útil para tests)."""
    global _brave_rate_limiter
    _brave_rate_limiter = None
