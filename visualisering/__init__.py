#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Visualiserings- och loggningskomponenter för LLM-baserad Produktinformationsextraktor.

Detta paket tillhandahåller avancerade loggnings- och visualiseringsverktyg för att
presentera och logga information på ett tydligt, strukturerat sätt i terminalbaserade miljöer.
Modulen stödjer rik formatering med färger, paneler och tabeller för att göra komplexa
arbetsflöden mer överskådliga.

Huvudkomponenter:
    * ColoredLogger - Utökad loggningsklass med kategorisering och färgkodning
    * TerminalVisualizer - Kraftfull visualisering av data, status och framsteg
    * ProgressTracker - Spårning och visualisering av framsteg för långvariga operationer
    * LogCategory - Enum för olika kategorier av loggmeddelanden
    * ColoredFormatter - Anpassad formatterare för färgkodad loggning
    * setup_logger - Hjälpfunktion för att konfigurera loggning

Modulen stödjer både avancerad visualisering med rich-paketet om det är tillgängligt,
och fallbackalternativ med ANSI-färgkoder för mer begränsade miljöer.
"""

from .visualiseringshanterare import (
    ColoredLogger,
    TerminalVisualizer,
    ProgressTracker,
    LogCategory,
    ColoredFormatter,
    setup_logger,
    TermColors,
    RICH_AVAILABLE
)

__all__ = [
    'ColoredLogger',
    'TerminalVisualizer',
    'ProgressTracker',
    'LogCategory',
    'ColoredFormatter',
    'setup_logger',
    'TermColors',
    'RICH_AVAILABLE'
]

# Versionsinformation
__version__ = '1.0.0'
__author__ = 'Produktinformationsextraktor Team'