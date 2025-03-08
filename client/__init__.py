#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM-klient för Produktinformationsextraktor.

Detta paket innehåller klasser för att interagera med olika LLM-tjänster (Large Language Models)
och extrahera strukturerad information från produktdokumentation. Modulen stödjer
flera LLM-providers och hanterar allt från nätverkskommunikation till tolkning av svar.

Huvudkomponenter:
    * LLMClient - Huvudklass för interaktion med LLM-tjänster
    * ResponseParser - Tolkar och strukturerar LLM-svar
    * ChunkManager - Hanterar uppdelning av stora texter
    * LLMProvider - Enum för olika LLM-tjänster
    * LLMProviderBase - Basklass för provider-implementationer
    * Konkreta providers:
        - OllamaProvider - För Ollama-tjänsten
        - LMStudioProvider - För LM Studio
        - OobaboogaProvider - För Oobabooga Text Generation Web UI
    * ProviderFactory - Fabrisklass för att skapa rätt provider

Modulen stödjer avancerade funktioner som automatiska återförsök, fallback-providers,
begränsning av API-anrop, och strukturerad tolkning av svar.
"""

from .LLMClient import (
    LLMClient,
    ResponseParser,
    ChunkManager,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMProviderBase,
    OllamaProvider,
    LMStudioProvider,
    OobaboogaProvider,
    ProviderFactory
)

__all__ = [
    'LLMClient',
    'ResponseParser',
    'ChunkManager',
    'LLMProvider',
    'LLMRequest',
    'LLMResponse',
    'LLMProviderBase',
    'OllamaProvider',
    'LMStudioProvider',
    'OobaboogaProvider',
    'ProviderFactory'
]

# Versionsinformation
__version__ = '1.0.0'
__author__ = 'Produktinformationsextraktor Team'