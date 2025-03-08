#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM-baserad Produktinformationsextraktor.

Detta är huvudpaketet för Produktinformationsextraktorn, ett system som använder
Large Language Models (LLM) för att extrahera strukturerad information från
ostrukturerad produktdokumentation.

Systemet kan extrahera följande typer av information:
    * Kompatibilitetsinformation mellan produkter
    * Tekniska specifikationer
    * Svarsgeneration för vanliga frågor (FAQ)

Huvudkomponenter:
    * config - Hantering av konfiguration
    * llm - Interaktion med LLM-tjänster
    * processors - Bearbetning av produktdokumentation
    * workflow - Arbetsflödeshantering och schemaläggning
    * utils - Hjälpverktyg och loggning
    * visualisering - Terminalvisualisering och rapportering
    * prompts - Mallar för prompter till LLM-tjänster

Systemet stödjer bearbetning av enskilda produkter eller batchbearbetning
av flera produkter med parallella arbetartrådar.
"""

from config import *
from workflow import *
from visualisering import *
from vault import *
from prompts import *
from Processor import *
from client import *



# Versionsinformation
__version__ = '1.0.0'
__author__ = 'Produktinformationsextraktor'