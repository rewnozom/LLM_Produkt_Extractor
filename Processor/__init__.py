#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Processor-komponenter för LLM-baserad Produktinformationsextraktor.

Detta paket innehåller klasser för att bearbeta produktdokumentation med hjälp av LLM
(Large Language Models) för att extrahera strukturerad information från ostrukturerad text.
Modulen hanterar hela kedjan från inläsning av dokument till strukturerad dataextraktion,
validering och resultathantering.

Huvudkomponenter:
    * ProductProcessor - Huvudklass för bearbetning av produktdokumentation
    * ProductResult - Datastruktur för att representera ett bearbetningsresultat
    * ValidationResult - Struktur för validering av extraherad information
    * ResultMerger - Hjälpklass för att sammanfoga resultat från olika källor
    * ExtractionStatus - Enum för att representera status för extraktionsprocessen

Modulen tillhandahåller funktionalitet för att extrahera:
    * Kompatibilitetsinformation mellan produkter
    * Tekniska specifikationer
    * FAQ-baserade svar på vanliga frågor
"""

from .ProductProcessor import (
    ProductProcessor,
    ProductResult,
    ValidationResult,
    ResultMerger,
    ExtractionStatus
)

__all__ = [
    'ProductProcessor',
    'ProductResult',
    'ValidationResult',
    'ResultMerger',
    'ExtractionStatus'
]

# Versionsinformation
__version__ = '1.0.0'
__author__ = 'Produktinformationsextraktor Team'