"""
Módulo de parsing de output para el ScraperAgent.

Encapsula la lógica de:
- Conversión de texto libre a structured output (post-processing con LLM)
- Parsing de texto libre (URLs, queries, uso de Playwright)
"""

import logging
from typing import Optional, Type

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from aifoundry.app.schemas.agent_responses import get_response_schema
from aifoundry.app.utils.parsing import parse_agent_output

logger = logging.getLogger(__name__)


class OutputParser:
    """
    Parser de output del agente.

    Responsabilidades:
    - Convertir texto libre a structured output via with_structured_output()
    - Parsear texto libre extrayendo URLs, queries y uso de Playwright
    """

    def __init__(
        self,
        response_model: Optional[Type[BaseModel]] = None,
        use_structured_output: bool = False,
    ):
        """
        Args:
            response_model: Clase Pydantic para structured output nativo.
            use_structured_output: Si True, fuerza structured output legacy.
        """
        self._response_model = response_model
        self._use_structured_output = use_structured_output

    async def extract_structured(
        self,
        result: dict,
        output: str,
        llm: BaseChatModel,
        config: dict,
    ) -> Optional[BaseModel]:
        """
        Extrae structured output del resultado del agente.

        Intenta en orden:
        1. Extraer structured_response nativo del resultado
        2. Fallback a post-processing con with_structured_output()
        3. Retorna None si no hay response_model

        Args:
            result: Resultado completo del agent executor (ainvoke)
            output: Texto del último mensaje AI
            llm: Instancia del LLM para fallback
            config: Config del agente (product, provider, etc.)

        Returns:
            Objeto Pydantic o None
        """
        if self._response_model is not None:
            # Intentar extraer respuesta nativa
            structured = result.get("structured_response")
            if structured is not None:
                logger.info(
                    "Structured output (native): %s",
                    type(structured).__name__,
                )
                return structured

            # Fallback a post-processing
            logger.warning(
                "response_format configurado pero structured_response "
                "no encontrado en el resultado. Usando fallback."
            )
            return await self._convert_to_structured(
                output=output,
                llm=llm,
                product=config.get("product", ""),
                config=config,
                schema_override=self._response_model,
            )

        elif self._use_structured_output:
            # Legacy: post-processing con segunda llamada LLM
            product = config.get("product", "")
            if product:
                return await self._convert_to_structured(
                    output=output,
                    llm=llm,
                    product=product,
                    config=config,
                )

        return None

    def parse_text(self, output: str) -> dict:
        """
        Parsea texto libre extrayendo queries, URLs y uso de Playwright.

        Delegado a utils/parsing.py para reutilización y testabilidad.
        """
        return parse_agent_output(output)

    async def _convert_to_structured(
        self,
        output: str,
        llm: BaseChatModel,
        product: str,
        config: dict,
        schema_override: Optional[Type[BaseModel]] = None,
    ) -> Optional[BaseModel]:
        """
        Convierte texto libre a formato estructurado usando
        with_structured_output() — POST-PROCESAMIENTO (2ª llamada LLM).

        Args:
            output: Output del agente en texto libre.
            llm: Instancia del LLM.
            product: Tipo de producto para seleccionar el esquema Pydantic.
            config: Config original para contexto adicional.
            schema_override: Clase Pydantic a usar directamente.

        Returns:
            Objeto Pydantic con datos estructurados, o None si falla.
        """
        try:
            schema = schema_override or get_response_schema(product)
            structured_llm = llm.with_structured_output(schema)

            structuring_prompt = (
                "Extrae y estructura la siguiente información en el formato solicitado.\n\n"
                "CONTEXTO:\n"
                f"- Empresa/Provider: {config.get('provider', 'N/A')}\n"
                f"- País: {config.get('country_code', 'N/A')}\n"
                f"- Query utilizada: {config.get('query', 'N/A')}\n\n"
                "INFORMACIÓN A ESTRUCTURAR:\n"
                f"{output}\n\n"
                "Extrae todos los datos relevantes y estructúralos según el esquema."
            )

            result = await structured_llm.ainvoke(structuring_prompt)

            logger.info(
                "Structured output (post-processing): %s",
                type(result).__name__,
            )

            return result

        except Exception as e:
            logger.warning("⚠️ Error generando structured output: %s", e)
            return None