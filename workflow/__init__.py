#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM-baserat arbetsflöde för produktinformationsextraktion.

Detta paket innehåller komponenter för att hantera arbetsflödet vid extraktion
av produktinformation med hjälp av Language Learning Models (LLM). Modulen ger
stöd för jobb-schemaläggning, arbetare, batch-bearbetning och övergripande hantering
av extraktionsprocessen.

Huvudkomponenter:
    * WorkflowManager - Huvudklass för att hantera hela arbetsflödet
    * ProcessingQueue - Hanterar köer av produkter att bearbeta
    * Worker - Representerar en arbetartråd som bearbetar jobb
    * BatchProcessor - Hanterar batch-bearbetning av produkter
    * JobScheduler - Schemaläggning av jobb för framtida bearbetning
    * Job - Representation av ett arbete som ska utföras
    * JobPriority - Enum för prioritetsnivåer
    * JobStatus - Enum för jobbstatus
"""

from .Arbetsflödeshantering import (
    WorkflowManager,
    ProcessingQueue,
    Worker,
    BatchProcessor,
    JobScheduler,
    Job,
    JobPriority,
    JobStatus,
    #
    ExtractionStatus,
    ProductResult,
    PromptManager,
    PromptTemplate,
    ExtractionPrompt,
    ValidationPrompt,
    CorrectionPrompt
)

__all__ = [
    'WorkflowManager',
    'ProcessingQueue',
    'Worker',
    'BatchProcessor',
    'JobScheduler',
    'Job',
    'JobPriority',
    'JobStatus',
    # funktioner som bör vara tillgängliga för tester
    'ExtractionStatus',
    'ProductResult',
    'PromptManager',
    'PromptTemplate',
    'ExtractionPrompt',
    'ValidationPrompt',
    'CorrectionPrompt'
]

# Versionsinformation
__version__ = '1.0.0'
__author__ = 'Produktinformationsextraktor Team'
