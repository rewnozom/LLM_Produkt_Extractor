#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Konfigurationshantering för LLM-baserad Produktinformationsextraktor.

Detta paket tillhandahåller verktyg för att hantera systemkonfiguration genom
att läsa in, validera och ge åtkomst till konfigurationsinställningar från
olika källor, inklusive filer (YAML/JSON) och miljövariabler.

Huvudkomponenter:
    * ConfigManager - Huvudklass för att hantera konfiguration
    * ValidationError - Klass för att representera valideringsfel i konfiguration
    * DEFAULT_CONFIG - Standardkonfiguration som används när ingen annan anges

ConfigManager ger enkel åtkomst till konfigurationsinställningar via en punkt-notation,
har inbyggd validering, och stödjer dynamisk konfigurationsuppdatering.
"""

from .ConfigManager import (
    ConfigManager,
    ValidationError,
    DEFAULT_CONFIG
)

__all__ = [
    'ConfigManager',
    'ValidationError',
    'DEFAULT_CONFIG'
]

# Versionsinformation
__version__ = '1.0.0'
__author__ = 'Produktinformationsextraktor Team'