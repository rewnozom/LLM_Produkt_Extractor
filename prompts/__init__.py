#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Prompt-hantering för LLM-baserad Produktinformationsextraktor.

Detta paket innehåller klasser och funktioner för att skapa, anpassa och hantera 
specialiserade promptar för Large Language Models (LLM) med fokus på extraktion
av strukturerad produktinformation.

Huvudkomponenter:
    * PromptTemplate - Basklass för alla promptmallar med platshållare
    * ExtractionPrompt - Specialiserad promptmall för extraktion av strukturerad information
    * ValidationPrompt - Specialiserad promptmall för validering av LLM-svar
    * CorrectionPrompt - Specialiserad promptmall för korrigering av felaktiga LLM-svar
    * PromptLoader - Klass för att ladda promptmallar från YAML-filer
    * PromptManager - Klass för att hantera en samling av promptmallar
    * prompt_utils - Hjälpfunktioner för prompthantering

De fördefinierade mallarna är optimerade för att extrahera strukturerad information
från produktdokumentation med hög precision, och inkluderar strategier för att
förebygga vanliga feltyper i LLM-svar.
"""

# Importera huvudklasser
from .PromptTemplate import PromptTemplate
from .ExtractionPrompt import ExtractionPrompt
from .ValidationPrompt import ValidationPrompt
from .CorrectionPrompt import CorrectionPrompt
from .PromptLoader import PromptLoader
from .PromptManager import PromptManager

# Importera hjälpfunktioner från prompt_utils
from .prompt_utils import (
    enhance_prompt_with_examples,
    create_specialized_prompt,
    fix_json_format,
    extract_schema_from_json,
    extract_json_from_text,
    improve_prompt_based_on_feedback,
    create_conditional_prompt
)

# Importera fördefinierade mallar
# Dessa kommer att laddas automatiskt av PromptLoader.load_default_prompts

# Exportera alla huvudklasser och funktioner
__all__ = [
    'PromptTemplate',
    'ExtractionPrompt',
    'ValidationPrompt', 
    'CorrectionPrompt',
    'PromptLoader',
    'PromptManager',
    'enhance_prompt_with_examples',
    'create_specialized_prompt',
    'fix_json_format',
    'extract_schema_from_json',
    'extract_json_from_text',
    'improve_prompt_based_on_feedback',
    'create_conditional_prompt'
]

# Versionsinformation
__version__ = '2.0.0'
__author__ = 'Rewnozom'