#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ./workflow/Arbetsflödeshantering.py

"""
Arbetsflödeshantering för LLM-baserad Produktinformationsextraktor

Denna modul hanterar hela arbetsflödet för produktinformationsextrahering, från
schemaläggning till resultathantering. Modulen är uppbyggd kring flera samverkande
komponenter som tillsammans utgör ett robust system för storskalig produktbearbetning.

Modulen är organiserad i flera logiska sektioner:
- Jobbhantering och prioritering
- Schemaläggning
- Kösystem
- Arbetare och parallellism
- Batch-bearbetning
- Projektövervakning och statistik
- Rapportering och visualisering
- Sökindexering och sökning
"""

import os
import re
import json
import time
import queue
import signal
import logging
import threading
import traceback
import uuid
import shutil
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Union, Callable, Set
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import csv


# Importera våra moduler
from Processor.ProductProcessor import ProductProcessor, ProductResult, ExtractionStatus
from visualisering.visualiseringshanterare import LogCategory
from config.ConfigManager import ConfigManager
from prompts import (
    PromptManager, PromptTemplate, ExtractionPrompt, ValidationPrompt, CorrectionPrompt
)

## ===================================
##   Jobbhantering och prioritering
## ===================================

class JobPriority(Enum):
    """Prioritetsnivåer för jobb"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3
    
    @classmethod
    def from_string(cls, priority_str: str) -> 'JobPriority':
        """Konverterar en strängrepresentation till JobPriority"""
        priority_map = {
            "low": cls.LOW,
            "normal": cls.NORMAL,
            "high": cls.HIGH,
            "critical": cls.CRITICAL
        }
        
        return priority_map.get(priority_str.lower(), cls.NORMAL)


class JobStatus(Enum):
    """Status för schemalagda jobb"""
    PENDING = "pending"
    IN_QUEUE = "in_queue"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"  # Ny status för pausade jobb

    def is_terminal(self) -> bool:
        """Returnerar om statusen representerar ett slutfört jobb"""
        return self in [self.COMPLETED, self.FAILED, self.CANCELLED]
    
    def is_active(self) -> bool:
        """Returnerar om statusen representerar ett aktivt jobb"""
        return self in [self.IN_QUEUE, self.PROCESSING]


@dataclass
class Job:
    """Representerar ett schemalagt jobb"""
    id: str
    product_id: str
    file_path: Path
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_for: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[ProductResult] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    tags: List[str] = field(default_factory=list)  # Nya taggar för kategorisering
    metadata: Dict[str, Any] = field(default_factory=dict)  # Nya metadata för flexibilitet
    
    def __post_init__(self):
        """Initialiserar jobbet"""
        if not self.id:
            self.id = str(uuid.uuid4())
        
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)
    
    def mark_queued(self) -> None:
        """Markerar jobbet som köat"""
        self.status = JobStatus.IN_QUEUE
    
    def mark_processing(self) -> None:
        """Markerar jobbet som under bearbetning"""
        self.status = JobStatus.PROCESSING
        self.started_at = datetime.now()
    
    def mark_completed(self, result: ProductResult) -> None:
        """
        Markerar jobbet som slutfört
        
        Args:
            result: Resultatet av bearbetningen
        """
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result
    
    def mark_failed(self, error: str) -> None:
        """
        Markerar jobbet som misslyckat
        
        Args:
            error: Felbeskrivning
        """
        self.status = JobStatus.FAILED
        self.completed_at = datetime.now()
        self.error = error
    
    def mark_paused(self) -> None:
        """Markerar jobbet som pausat"""
        self.status = JobStatus.PAUSED
    
    def mark_cancelled(self) -> None:
        """Markerar jobbet som avbrutet"""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.now()
    
    def should_retry(self) -> bool:
        """
        Kontrollerar om jobbet ska försökas igen
        
        Returns:
            bool: True om jobbet ska försökas igen, annars False
        """
        return self.status == JobStatus.FAILED and self.retries < self.max_retries
    
    def increase_retry_count(self) -> None:
        """Ökar antalet återförsök"""
        self.retries += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Konverterar jobbet till en ordbok för serialisering
        
        Returns:
            Dict[str, Any]: Jobbet som ordbok
        """
        return {
            "id": self.id,
            "product_id": self.product_id,
            "file_path": str(self.file_path),
            "priority": self.priority.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """
        Skapar ett jobb från en ordbok
        
        Args:
            data: Ordboken att skapa jobbet från
            
        Returns:
            Job: Det skapade jobbet
        """
        job = cls(
            id=data["id"],
            product_id=data["product_id"],
            file_path=data["file_path"],
            priority=JobPriority[data["priority"]],
            status=JobStatus(data["status"]),
            retries=data.get("retries", 0),
            max_retries=data.get("max_retries", 3),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )
        
        # Återställ tidsstämplar
        if data.get("created_at"):
            job.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("scheduled_for"):
            job.scheduled_for = datetime.fromisoformat(data["scheduled_for"])
        if data.get("started_at"):
            job.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            job.completed_at = datetime.fromisoformat(data["completed_at"])
        
        job.error = data.get("error")
        
        return job


## ===================================
##   Kösystem
## ===================================

class ProcessingQueue:
    """
    Klass för att hantera kön av produkter att bearbeta
    """
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        """
        Initierar processeringskön
        
        Args:
            config: Konfiguration för kön
            logger: Logger för att logga meddelanden
        """
        self.config = config
        self.logger = logger
        
        # Konfigurera köstorlek
        self.queue_size = config.get("queue_size", 1000)
        
        # Prioritetskö för jobben
        self.queues = {
            JobPriority.LOW: queue.PriorityQueue(self.queue_size),
            JobPriority.NORMAL: queue.PriorityQueue(self.queue_size),
            JobPriority.HIGH: queue.PriorityQueue(self.queue_size),
            JobPriority.CRITICAL: queue.PriorityQueue(self.queue_size)
        }
        
        # Lås för trådsäkerhet
        self.lock = threading.RLock()
        
        # Spårning av jobb
        self.jobs = {}
        self.active_jobs = set()
        self.completed_jobs = set()
        self.failed_jobs = set()
        self.paused_jobs = set()  # Nya för pausade jobb
        
        # Statistik
        self.stats = {
            "enqueued": 0,
            "dequeued": 0,
            "completed": 0,
            "failed": 0,
            "retried": 0,
            "paused": 0,  # Nya för pausstatistik
            "cancelled": 0  # Nya för avbrottsstatistik
        }
        
        # Händelser
        self.job_added_event = threading.Event()
        self.shutdown_event = threading.Event()
        self.pause_event = threading.Event()  # Nya för paushantering
        
        # Filter för jobbtaggar
        self.tag_filter = set()  # Om tom, ingen filtrering
    
    def add_job(self, job: Job) -> bool:
        """
        Lägger till ett jobb i kön
        
        Args:
            job: Jobbet att lägga till
            
        Returns:
            bool: True om jobbet lades till, annars False
        """
        with self.lock:
            # Kontrollera om jobbet redan finns
            if job.id in self.jobs:
                self.logger.warning(f"Jobb {job.id} finns redan i kön")
                return False
            
            # Om taggfiltrering är aktiverad, kontrollera jobbet
            if self.tag_filter and not any(tag in job.tags for tag in self.tag_filter):
                self.logger.debug(f"Jobb {job.id} filtrerades bort pga taggar: {job.tags}")
                return False
            
            # Markera jobbet som köat
            job.mark_queued()
            
            # Beräkna prioritet inom prioritetsgruppen (lägre värde = högre prioritet)
            sub_priority = job.created_at.timestamp()
            
            try:
                # Lägg till i rätt prioritetskö
                self.queues[job.priority].put((sub_priority, job.id))
                
                # Lägg till i jobbspårningen
                self.jobs[job.id] = job
                
                # Uppdatera statistik
                self.stats["enqueued"] += 1
                
                # Signalera att ett jobb har lagts till
                self.job_added_event.set()
                
                self.logger.workflow(f"Lade till jobb {job.id} för produkt {job.product_id} i kön med prioritet {job.priority.name}")
                return True
            
            except queue.Full:
                self.logger.error(f"Kön är full, kunde inte lägga till jobb {job.id}")
                return False
            except Exception as e:
                self.logger.error(f"Fel vid tillägg av jobb {job.id}: {str(e)}")
                return False
    
    def get_next_job(self) -> Optional[Job]:
        """
        Hämtar nästa jobb från kön baserat på prioritet
        
        Returns:
            Optional[Job]: Nästa jobb eller None om kön är tom eller systemet pausat
        """
        # Kontrollera om nedstängning är begärd
        if self.shutdown_event.is_set():
            return None
        
        # Kontrollera om systemet är pausat
        if self.pause_event.is_set():
            # Vänta tills pausen är hävd eller nedstängning begärd
            while self.pause_event.is_set() and not self.shutdown_event.is_set():
                # Vänta en kort stund och kontrollera igen
                time.sleep(0.5)
            
            # Kontrollera igen om nedstängning är begärd efter paus
            if self.shutdown_event.is_set():
                return None
        
        # Försök hämta från varje prioritetskö i ordning (högst först)
        for priority in sorted(self.queues.keys(), reverse=True):
            try:
                if not self.queues[priority].empty():
                    _, job_id = self.queues[priority].get(block=False)
                    
                    with self.lock:
                        job = self.jobs.get(job_id)
                        
                        if job:
                            # Markera jobbet som under bearbetning
                            job.mark_processing()
                            
                            # Lägg till i aktiva jobb
                            self.active_jobs.add(job.id)
                            
                            # Uppdatera statistik
                            self.stats["dequeued"] += 1
                            
                            self.logger.workflow(f"Hämtade jobb {job.id} för produkt {job.product_id} från kön")
                            return job
                        else:
                            self.logger.warning(f"Jobbet {job_id} hittades inte i jobbspårningen")
                            return None
            
            except queue.Empty:
                continue
        
        # Alla köer är tomma
        return None
    
    def mark_job_completed(self, job_id: str, result: ProductResult) -> None:
        """
        Markerar ett jobb som slutfört
        
        Args:
            job_id: ID för jobbet
            result: Resultatet av bearbetningen
        """
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                
                # Markera jobbet som slutfört
                job.mark_completed(result)
                
                # Ta bort från aktiva jobb och lägg till i slutförda
                self.active_jobs.discard(job_id)
                self.completed_jobs.add(job_id)
                
                # Uppdatera statistik
                self.stats["completed"] += 1
                
                self.logger.workflow(f"Markerade jobb {job_id} för produkt {job.product_id} som slutfört")
            else:
                self.logger.warning(f"Försökte markera okänt jobb {job_id} som slutfört")
    
    def mark_job_failed(self, job_id: str, error: str) -> None:
        """
        Markerar ett jobb som misslyckat
        
        Args:
            job_id: ID för jobbet
            error: Felbeskrivning
        """
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                
                # Markera jobbet som misslyckat
                job.mark_failed(error)
                
                # Ta bort från aktiva jobb och lägg till i misslyckade
                self.active_jobs.discard(job_id)
                self.failed_jobs.add(job_id)
                
                # Uppdatera statistik
                self.stats["failed"] += 1
                
                self.logger.workflow(f"Markerade jobb {job_id} för produkt {job.product_id} som misslyckat: {error}")
                
                # Kontrollera om jobbet ska försökas igen
                if job.should_retry():
                    job.increase_retry_count()
                    job.status = JobStatus.PENDING
                    self.requeue_job(job)
            else:
                self.logger.warning(f"Försökte markera okänt jobb {job_id} som misslyckat")
    
    def requeue_job(self, job: Job) -> bool:
        """
        Lägger tillbaka ett jobb i kön (för återförsök)
        
        Args:
            job: Jobbet att lägga tillbaka
            
        Returns:
            bool: True om jobbet lades till igen, annars False
        """
        with self.lock:
            # Uppdatera statistik
            self.stats["retried"] += 1
            
            # Återställ jobbets status
            job.status = JobStatus.PENDING
            
            # Lägg till i kön igen med lägre prioritet om det inte redan var lägst
            if job.priority != JobPriority.LOW:
                job.priority = JobPriority(max(JobPriority.LOW.value, job.priority.value - 1))
            
            self.logger.retry(f"Försöker igen med jobb {job.id} för produkt {job.product_id}, försök {job.retries}/{job.max_retries}")
            
            # Ta bort från misslyckade jobb
            self.failed_jobs.discard(job.id)
            
            # Returnera resultatet av add_job
            return self.add_job(job)
    
    def pause_job(self, job_id: str) -> bool:
        """
        Pausar ett specifikt jobb
        
        Args:
            job_id: ID för jobbet att pausa
            
        Returns:
            bool: True om pausningen lyckades, annars False
        """
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                
                # Kontrollera att det är ett jobb som kan pausas
                if job.status in [JobStatus.PENDING, JobStatus.IN_QUEUE]:
                    # Markera jobbet som pausat
                    job.mark_paused()
                    
                    # Uppdatera statistik
                    self.stats["paused"] += 1
                    
                    # Lägg till i pausade jobb
                    self.paused_jobs.add(job_id)
                    
                    self.logger.workflow(f"Pausade jobb {job_id} för produkt {job.product_id}")
                    return True
                else:
                    self.logger.warning(f"Kunde inte pausa jobb {job_id} med status {job.status.value}")
                    return False
            else:
                self.logger.warning(f"Försökte pausa okänt jobb {job_id}")
                return False
    
    def resume_job(self, job_id: str) -> bool:
        """
        Återupptar ett pausat jobb
        
        Args:
            job_id: ID för jobbet att återuppta
            
        Returns:
            bool: True om återupptagningen lyckades, annars False
        """
        with self.lock:
            if job_id in self.jobs and job_id in self.paused_jobs:
                job = self.jobs[job_id]
                
                # Återställ jobbets status
                job.status = JobStatus.PENDING
                
                # Ta bort från pausade jobb
                self.paused_jobs.discard(job_id)
                
                # Lägg till i kön igen
                result = self.add_job(job)
                
                if result:
                    self.logger.workflow(f"Återupptog jobb {job_id} för produkt {job.product_id}")
                
                return result
            else:
                self.logger.warning(f"Försökte återuppta okänt/icke-pausat jobb {job_id}")
                return False
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Avbryter ett jobb
        
        Args:
            job_id: ID för jobbet att avbryta
            
        Returns:
            bool: True om avbrytning lyckades, annars False
        """
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                
                # Kontrollera att det inte redan är slutfört
                if job.status.is_terminal():
                    self.logger.warning(f"Kunde inte avbryta jobb {job_id} då det redan är i slutstatus {job.status.value}")
                    return False
                
                # Markera jobbet som avbrutet
                job.mark_cancelled()
                
                # Uppdatera statistik
                self.stats["cancelled"] += 1
                
                # Ta bort från spårningsuppsättningar
                self.active_jobs.discard(job_id)
                self.paused_jobs.discard(job_id)
                
                self.logger.workflow(f"Avbröt jobb {job_id} för produkt {job.product_id}")
                return True
            else:
                self.logger.warning(f"Försökte avbryta okänt jobb {job_id}")
                return False
    
    def pause_all(self) -> int:
        """
        Pausar alla väntande jobb
        
        Returns:
            int: Antal jobb som pausades
        """
        with self.lock:
            paused_count = 0
            
            # Sätt paus-flaggan
            self.pause_event.set()
            
            # Pausa alla väntande jobb
            for job in self.jobs.values():
                if job.status in [JobStatus.PENDING, JobStatus.IN_QUEUE]:
                    job.mark_paused()
                    self.paused_jobs.add(job.id)
                    paused_count += 1
            
            # Uppdatera statistik
            self.stats["paused"] += paused_count
            
            self.logger.workflow(f"Pausade {paused_count} jobb")
            return paused_count
    
    def resume_all(self) -> int:
        """
        Återupptar alla pausade jobb
        
        Returns:
            int: Antal jobb som återupptogs
        """
        with self.lock:
            resumed_count = 0
            
            # Återställ paus-flaggan
            self.pause_event.clear()
            
            # Återuppta alla pausade jobb
            for job_id in list(self.paused_jobs):  # Använd en kopia eftersom vi modifierar under iteration
                job = self.jobs[job_id]
                job.status = JobStatus.PENDING
                
                # Lägg till i kön igen
                if self.add_job(job):
                    resumed_count += 1
                    self.paused_jobs.discard(job_id)
            
            self.logger.workflow(f"Återupptog {resumed_count} jobb")
            return resumed_count
    
    def set_tag_filter(self, tags: List[str]) -> None:
        """
        Sätter filter för jobbtaggar
        
        Args:
            tags: Lista med taggar att filtrera på (tom lista = ingen filtrering)
        """
        with self.lock:
            self.tag_filter = set(tags)
            self.logger.info(f"Satte taggfilter: {', '.join(tags) if tags else 'ingen filtrering'}")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Hämtar status för kön
        
        Returns:
            Dict[str, Any]: Status för kön
        """
        with self.lock:
            status = {
                "total_jobs": len(self.jobs),
                "active_jobs": len(self.active_jobs),
                "completed_jobs": len(self.completed_jobs),
                "failed_jobs": len(self.failed_jobs),
                "paused_jobs": len(self.paused_jobs),
                "pending_jobs": sum(q.qsize() for q in self.queues.values()),
                "stats": self.stats.copy(),
                "queue_sizes": {p.name: q.qsize() for p, q in self.queues.items()},
                "queue_capacity": self.queue_size,
                "is_paused": self.pause_event.is_set(),
                "tag_filter": list(self.tag_filter) if self.tag_filter else []
            }
            
            return status
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Hämtar ett jobb från jobbspårningen
        
        Args:
            job_id: ID för jobbet
            
        Returns:
            Optional[Job]: Jobbet eller None om det inte finns
        """
        with self.lock:
            return self.jobs.get(job_id)
    
    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """
        Hämtar alla jobb med en viss status
        
        Args:
            status: Status att filtrera på
            
        Returns:
            List[Job]: Lista med jobb som matchar statusen
        """
        with self.lock:
            return [job for job in self.jobs.values() if job.status == status]
    
    def get_jobs_by_tag(self, tag: str) -> List[Job]:
        """
        Hämtar alla jobb med en viss tagg
        
        Args:
            tag: Tagg att filtrera på
            
        Returns:
            List[Job]: Lista med jobb som har taggen
        """
        with self.lock:
            return [job for job in self.jobs.values() if tag in job.tags]
    
    def get_all_jobs(self) -> List[Job]:
        """
        Hämtar alla jobb
        
        Returns:
            List[Job]: Lista med alla jobb
        """
        with self.lock:
            return list(self.jobs.values())
    
    def is_empty(self) -> bool:
        """
        Kontrollerar om kön är tom
        
        Returns:
            bool: True om kön är tom, annars False
        """
        return all(q.empty() for q in self.queues.values())
    
    def is_paused(self) -> bool:
        """
        Kontrollerar om kön är pausad
        
        Returns:
            bool: True om kön är pausad, annars False
        """
        return self.pause_event.is_set()
    
    def shutdown(self) -> None:
        """Stänger ned kön"""
        self.shutdown_event.set()
        self.logger.workflow("Stänger ned kön")
    
    def clear(self) -> None:
        """Tömmer kön och återställer allt"""
        with self.lock:
            # Töm alla köer
            for q in self.queues.values():
                while not q.empty():
                    try:
                        q.get(block=False)
                        q.task_done()
                    except queue.Empty:
                        break
            
            # Återställ spårning och statistik
            self.jobs = {}
            self.active_jobs = set()
            self.completed_jobs = set()
            self.failed_jobs = set()
            self.paused_jobs = set()
            
            self.stats = {
                "enqueued": 0,
                "dequeued": 0,
                "completed": 0,
                "failed": 0,
                "retried": 0,
                "paused": 0,
                "cancelled": 0
            }
            
            # Återställ händelser
            self.job_added_event.clear()
            self.shutdown_event.clear()
            self.pause_event.clear()
            
            # Återställ taggfilter
            self.tag_filter = set()
            
            self.logger.workflow("Kön tömd och återställd")
    
    def save_state(self, file_path: Union[str, Path]) -> bool:
        """
        Sparar köns tillstånd till fil
        
        Args:
            file_path: Sökväg att spara till
            
        Returns:
            bool: True om lyckad, annars False
        """
        file_path = Path(file_path)
        
        try:
            with self.lock:
                # Skapa en kopia av jobbspårningen med serializerbara jobb
                serialized_jobs = {job_id: job.to_dict() for job_id, job in self.jobs.items()}
                
                # Skapa tillståndsobjekt
                state = {
                    "jobs": serialized_jobs,
                    "active_jobs": list(self.active_jobs),
                    "completed_jobs": list(self.completed_jobs),
                    "failed_jobs": list(self.failed_jobs),
                    "paused_jobs": list(self.paused_jobs),
                    "stats": self.stats,
                    "is_paused": self.pause_event.is_set(),
                    "tag_filter": list(self.tag_filter),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Spara till fil
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"Sparade köns tillstånd till {file_path}")
                return True
        except Exception as e:
            self.logger.error(f"Fel vid sparande av köns tillstånd: {str(e)}")
            return False
    


    def load_state(self, file_path: Union[str, Path]) -> bool:
        """
        Laddar köns tillstånd från fil
        
        Args:
            file_path: Sökväg att ladda från
            
        Returns:
            bool: True om lyckad, annars False
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            self.logger.error(f"Tillståndsfilen {file_path} existerar inte")
            return False
        
        try:
            # Töm nuvarande tillstånd
            self.clear()
            
            # Ladda från fil
            with open(file_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            with self.lock:
                # Återskapa jobb
                for job_id, job_dict in state.get("jobs", {}).items():
                    job = Job.from_dict(job_dict)
                    
                    # Lägg till i jobbspårning
                    self.jobs[job_id] = job
                    
                    # Lägg till i rätt spårningsuppsättningar
                    if job.status == JobStatus.PROCESSING:
                        self.active_jobs.add(job_id)
                    elif job.status == JobStatus.COMPLETED:
                        self.completed_jobs.add(job_id)
                    elif job.status == JobStatus.FAILED:
                        self.failed_jobs.add(job_id)
                    elif job.status == JobStatus.PAUSED:
                        self.paused_jobs.add(job_id)
                    elif job.status in [JobStatus.PENDING, JobStatus.IN_QUEUE]:
                        # Lägg till i kön igen
                        sub_priority = job.created_at.timestamp()
                        self.queues[job.priority].put((sub_priority, job_id))
                
                # Återställ statistik
                self.stats = state.get("stats", self.stats)
                
                # Återställ paus-läge om det var aktivt
                if state.get("is_paused", False):
                    self.pause_event.set()
                else:
                    self.pause_event.clear()
                
                # Återställ taggfilter
                self.tag_filter = set(state.get("tag_filter", []))
                
                self.logger.info(f"Laddade köns tillstånd från {file_path}")
                return True
        except Exception as e:
            self.logger.error(f"Fel vid laddande av köns tillstånd: {str(e)}")
            return False


## ===================================
##   Arbetare och parallellism
## ===================================

class Worker:
    """
    Klass för att representera en arbetartråd som bearbetar jobb från kön
    """
    
    def __init__(
        self, worker_id: int, queue: ProcessingQueue, processor: ProductProcessor, 
        config: Dict[str, Any], logger: logging.Logger, output_dir: Union[str, Path]
    ):
        """
        Initierar arbetaren
        
        Args:
            worker_id: ID för arbetaren
            queue: Kön att hämta jobb från
            processor: Processorn att använda för bearbetning
            config: Konfiguration för arbetaren
            logger: Logger för att logga meddelanden
            output_dir: Katalog att spara resultat i
        """
        self.worker_id = worker_id
        self.queue = queue
        self.processor = processor
        self.config = config
        self.logger = logger
        self.output_dir = Path(output_dir)
        
        # Skapa en arbetartråd
        self.thread = threading.Thread(
            target=self._worker_loop,
            name=f"Worker-{worker_id}",
            daemon=True
        )
        
        # Flaggor för kontroll
        self.running = False
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()  # Ny för pausning av enskild arbetare
        
        # Statistik
        self.stats = {
            "jobs_processed": 0,
            "jobs_succeeded": 0,
            "jobs_failed": 0,
            "total_processing_time": 0,
            "last_active": None,
            "current_job_id": None,
            "current_product_id": None
        }
        
        # Prestationsövervakning
        self.processing_times = []  # Lista med bearbetningstider för statistik
    
    def start(self) -> None:
        """Startar arbetartråden"""
        if not self.running:
            self.running = True
            self.stop_event.clear()
            self.pause_event.clear()
            self.thread.start()
            self.logger.workflow(f"Arbetare {self.worker_id} startad")
    
    def stop(self) -> None:
        """Stoppar arbetartråden"""
        if self.running:
            self.logger.workflow(f"Stoppar arbetare {self.worker_id}...")
            self.stop_event.set()
            self.running = False
    
    def pause(self) -> None:
        """Pausar arbetartråden"""
        self.logger.workflow(f"Pausar arbetare {self.worker_id}...")
        self.pause_event.set()
    
    def resume(self) -> None:
        """Återupptar arbetartråden"""
        self.logger.workflow(f"Återupptar arbetare {self.worker_id}...")
        self.pause_event.clear()
    
    def join(self, timeout: float = None) -> None:
        """
        Väntar på att arbetartråden ska avslutas
        
        Args:
            timeout: Tidsgräns i sekunder, eller None för att vänta obegränsat
        """
        if self.thread.is_alive():
            self.thread.join(timeout)
    
    def is_alive(self) -> bool:
        """
        Kontrollerar om arbetartråden är aktiv
        
        Returns:
            bool: True om tråden är aktiv, annars False
        """
        return self.thread.is_alive()
    
    def is_paused(self) -> bool:
        """
        Kontrollerar om arbetartråden är pausad
        
        Returns:
            bool: True om tråden är pausad, annars False
        """
        return self.pause_event.is_set()
    
    def is_processing(self) -> bool:
        """
        Kontrollerar om arbetaren bearbetar ett jobb
        
        Returns:
            bool: True om arbetaren bearbetar ett jobb, annars False
        """
        return self.stats["current_job_id"] is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Hämtar statistik för arbetaren
        
        Returns:
            Dict[str, Any]: Statistik för arbetaren
        """
        avg_time = 0
        if self.processing_times:
            avg_time = sum(self.processing_times) / len(self.processing_times)
        
        return {
            "worker_id": self.worker_id,
            "running": self.running,
            "alive": self.is_alive(),
            "paused": self.is_paused(),
            "processing_job": self.is_processing(),
            "current_job_id": self.stats["current_job_id"],
            "current_product_id": self.stats["current_product_id"],
            "jobs_processed": self.stats["jobs_processed"],
            "jobs_succeeded": self.stats["jobs_succeeded"],
            "jobs_failed": self.stats["jobs_failed"],
            "total_processing_time": self.stats["total_processing_time"],
            "average_processing_time": avg_time,
            "last_active": self.stats["last_active"]
        }
    
    def _worker_loop(self) -> None:
        """Huvudloop för arbetartråden"""
        self.logger.workflow(f"Arbetare {self.worker_id} startar arbetsloop")
        
        while not self.stop_event.is_set():
            try:
                # Kontrollera om arbetaren är pausad
                if self.pause_event.is_set():
                    # Vänta tills pausen är hävd eller stopp begärd
                    while self.pause_event.is_set() and not self.stop_event.is_set():
                        time.sleep(0.5)
                    
                    # Kontrollera om arbetaren har stoppats under pausen
                    if self.stop_event.is_set():
                        break
                
                # Uppdatera sista aktivitetstid
                self.stats["last_active"] = datetime.now().isoformat()
                
                # Hämta nästa jobb från kön
                job = self.queue.get_next_job()
                
                if job is None:
                    # Ingen jobb tillgängligt, vänta på signal eller timeout
                    signaled = self.queue.job_added_event.wait(timeout=1.0)
                    
                    if signaled:
                        # Återställ signalen
                        self.queue.job_added_event.clear()
                    
                    continue
                
                # Bearbeta jobbet
                self._process_job(job)
                
            except Exception as e:
                self.logger.error(f"Oväntat fel i arbetare {self.worker_id}: {str(e)}")
                self.logger.error(traceback.format_exc())
                
                # Kort paus för att undvika snabba loopar vid fel
                time.sleep(1.0)
        
        self.logger.workflow(f"Arbetare {self.worker_id} avslutar arbetsloop")
    
    def _process_job(self, job: Job) -> None:
        """
        Bearbetar ett jobb
        
        Args:
            job: Jobbet att bearbeta
        """
        self.logger.workflow(f"Arbetare {self.worker_id} bearbetar jobb {job.id} för produkt {job.product_id}")
        
        # Uppdatera statistik för aktuellt jobb
        self.stats["current_job_id"] = job.id
        self.stats["current_product_id"] = job.product_id
        
        start_time = time.time()
        
        try:
            # Kontrollera att filen existerar
            if not job.file_path.exists():
                error_msg = f"Filen {job.file_path} existerar inte"
                self.logger.error(error_msg)
                self.queue.mark_job_failed(job.id, error_msg)
                return
            
            # Bearbeta produkten
            result = self.processor.process_product(job.product_id, job.file_path)
            
            # Validera resultatet
            validation = self.processor.validate_result(result)
            
            if not validation.valid:
                self.logger.warning(f"Valideringsfel för produkt {job.product_id}")
            
            # Strukturerad organisering av resultatfiler
            output_category = self._determine_output_category(result)
            output_dir = self.output_dir / output_category
            
            # Spara resultatet
            success, saved_path = self.processor.save_result(result, output_dir)
            
            if success:
                self.logger.info(f"Sparade resultat för produkt {job.product_id} till {saved_path}")
                
                # Spara strukturerad data
                structured_dir = self.output_dir / "structured"
                saved_files = self.processor.save_structured_data(result, structured_dir)
                
                if saved_files:
                    self.logger.info(f"Sparade strukturerad data för produkt {job.product_id}")
                    
                    # Lägg till sökvägar i jobb-metadata för referens
                    job.metadata["result_files"] = {k: str(v) for k, v in saved_files.items()}
                    job.metadata["output_dir"] = str(output_dir)
                    job.metadata["result_file"] = str(saved_path)
            else:
                self.logger.error(f"Kunde inte spara resultat för produkt {job.product_id}")
            
            # Markera jobbet som slutfört
            self.queue.mark_job_completed(job.id, result)
            
            # Uppdatera statistik
            self.stats["jobs_processed"] += 1
            self.stats["jobs_succeeded"] += 1
            
        except Exception as e:
            # Hantera fel
            error_msg = f"Fel vid bearbetning av produkt {job.product_id}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            
            # Markera jobbet som misslyckat
            self.queue.mark_job_failed(job.id, error_msg)
            
            # Uppdatera statistik
            self.stats["jobs_processed"] += 1
            self.stats["jobs_failed"] += 1
        
        finally:
            # Uppdatera bearbetningstid
            processing_time = time.time() - start_time
            self.stats["total_processing_time"] += processing_time
            self.processing_times.append(processing_time)
            
            # Rensa aktuellt jobb-info
            self.stats["current_job_id"] = None
            self.stats["current_product_id"] = None
            
            self.logger.workflow(
                f"Arbetare {self.worker_id} slutförde bearbetning av jobb {job.id} "
                f"på {processing_time:.2f} sekunder"
            )
    
    def _determine_output_category(self, result: ProductResult) -> str:
        """
        Bestämmer i vilken kategori ett resultat ska sparas
        
        Args:
            result: Resultatet att kategorisera
            
        Returns:
            str: Kategorin för resultatet
        """
        # Kategorisera baserat på status och innehåll
        if result.status == ExtractionStatus.VALIDATED:
            return "validated"
        elif result.status == ExtractionStatus.CORRECTED:
            return "corrected"
        elif result.status in [ExtractionStatus.COMPLETED, ExtractionStatus.PARTIALLY_COMPLETED]:
            if result.get_compatibility_count() > 0 or result.get_technical_count() > 0 or result.product_info:
                return "unvalidated"
            else:
                return "empty"
        elif result.status == ExtractionStatus.FAILED:
            return "failed"
        else:
            return "other"


## ===================================
##   Schemaläggning
## ===================================

class JobScheduler:
   """
   Klass för att schemalägga jobb för framtida bearbetning
   """
   
   def __init__(self, processing_queue: ProcessingQueue, config: Dict[str, Any], logger: logging.Logger):
       """
       Initierar schemaläggaren
       
       Args:
           processing_queue: Kön att lägga till jobb i
           config: Konfiguration för schemaläggaren
           logger: Logger för att logga meddelanden
       """
       self.queue = processing_queue
       self.config = config
       self.logger = logger
       
       # Schemalagda jobb
       self.scheduled_jobs = {}
       
       # Återkommande jobb
       self.recurring_jobs = {}
       
       # Lås för trådsäkerhet
       self.lock = threading.RLock()
       
       # Tråd för schemaläggning
       self.scheduler_thread = threading.Thread(
           target=self._scheduler_loop,
           name="JobScheduler",
           daemon=True
       )
       
       # Kontrollvariabler
       self.running = False
       self.stop_event = threading.Event()
   
   def start(self) -> None:
       """Startar schemaläggartråden"""
       if not self.running:
           self.running = True
           self.stop_event.clear()
           self.scheduler_thread.start()
           self.logger.workflow("Schemaläggare startad")
   
   def stop(self) -> None:
       """Stoppar schemaläggartråden"""
       if self.running:
           self.logger.workflow("Stoppar schemaläggare...")
           self.stop_event.set()
           self.running = False
   
   def join(self, timeout: float = None) -> None:
       """
       Väntar på att schemaläggartråden ska avslutas
       
       Args:
           timeout: Tidsgräns i sekunder, eller None för att vänta obegränsat
       """
       if self.scheduler_thread.is_alive():
           self.scheduler_thread.join(timeout)
   
   def schedule_job(
       self, product_id: str, file_path: Union[str, Path], scheduled_time: datetime,
       priority: JobPriority = JobPriority.NORMAL, tags: List[str] = None
   ) -> str:
       """
       Schemalägger ett jobb för framtida bearbetning
       
       Args:
           product_id: ID för produkten
           file_path: Sökväg till filen
           scheduled_time: Tidpunkt för schemaläggning
           priority: Prioritet för jobbet
           tags: Taggar för jobbet
           
       Returns:
           str: ID för det schemalagda jobbet
       """
       with self.lock:
           # Skapa ett jobb för produkten
           job = Job(
               id="",  # Genereras automatiskt
               product_id=product_id,
               file_path=file_path,
               priority=priority,
               scheduled_for=scheduled_time,
               tags=tags or []
           )
           
           # Lägg till i schemalagda jobb
           self.scheduled_jobs[job.id] = job
           
           self.logger.workflow(
               f"Schemalade jobb {job.id} för produkt {product_id} "
               f"till {scheduled_time.isoformat()}"
           )
           
           return job.id
   
   def schedule_recurring_job(
       self, product_id: str, file_path: Union[str, Path], 
       interval_hours: float, priority: JobPriority = JobPriority.NORMAL,
       tags: List[str] = None, max_runs: int = None
   ) -> str:
       """
       Schemalägger ett återkommande jobb med angivet intervall
       
       Args:
           product_id: ID för produkten
           file_path: Sökväg till filen
           interval_hours: Intervall i timmar mellan körningar
           priority: Prioritet för jobbet
           tags: Taggar för jobbet
           max_runs: Maximalt antal körningar (None = obegränsat)
           
       Returns:
           str: ID för det återkommande jobbet
       """
       with self.lock:
           # Skapa ett unikt ID för det återkommande jobbet
           recurring_id = str(uuid.uuid4())
           
           # Beräkna första körningstid
           first_run = datetime.now() + timedelta(hours=interval_hours)
           
           # Skapa återkommande jobbkonfiguration
           recurring_config = {
               "product_id": product_id,
               "file_path": str(file_path),
               "interval_hours": interval_hours,
               "priority": priority.name,
               "tags": tags or [],
               "next_run": first_run.isoformat(),
               "runs_completed": 0,
               "max_runs": max_runs,
               "last_job_id": None
           }
           
           # Lägg till i återkommande jobb
           self.recurring_jobs[recurring_id] = recurring_config
           
           # Schemalägg första körningen
           job_id = self.schedule_job(
               product_id=product_id,
               file_path=file_path,
               scheduled_time=first_run,
               priority=priority,
               tags=(tags or []) + ["recurring", f"recurring_id:{recurring_id}"]
           )
           
           # Uppdatera sista jobb-ID
           self.recurring_jobs[recurring_id]["last_job_id"] = job_id
           
           self.logger.workflow(
               f"Schemalade återkommande jobb {recurring_id} för produkt {product_id} "
               f"med {interval_hours}h intervall, första körning: {first_run.isoformat()}"
           )
           
           return recurring_id
   
   def cancel_job(self, job_id: str) -> bool:
       """
       Avbryter ett schemalagt jobb
       
       Args:
           job_id: ID för jobbet att avbryta
           
       Returns:
           bool: True om jobbet avbröts, annars False
       """
       with self.lock:
           if job_id in self.scheduled_jobs:
               job = self.scheduled_jobs.pop(job_id)
               job.status = JobStatus.CANCELLED
               
               self.logger.workflow(f"Avbröt schemalagt jobb {job_id} för produkt {job.product_id}")
               return True
           else:
               self.logger.warning(f"Försökte avbryta okänt jobb {job_id}")
               return False
   
   def cancel_recurring_job(self, recurring_id: str) -> bool:
       """
       Avbryter ett återkommande jobb
       
       Args:
           recurring_id: ID för det återkommande jobbet att avbryta
           
       Returns:
           bool: True om jobbet avbröts, annars False
       """
       with self.lock:
           if recurring_id in self.recurring_jobs:
               # Ta bort återkommande jobb
               recurring_config = self.recurring_jobs.pop(recurring_id)
               
               # Avbryt eventuellt pågående jobb
               last_job_id = recurring_config.get("last_job_id")
               if last_job_id and last_job_id in self.scheduled_jobs:
                   self.cancel_job(last_job_id)
               
               self.logger.workflow(f"Avbröt återkommande jobb {recurring_id}")
               return True
           else:
               self.logger.warning(f"Försökte avbryta okänt återkommande jobb {recurring_id}")
               return False
   
   def get_scheduled_jobs(self) -> List[Job]:
       """
       Hämtar alla schemalagda jobb
       
       Returns:
           List[Job]: Lista med schemalagda jobb
       """
       with self.lock:
           return list(self.scheduled_jobs.values())
   
   def get_recurring_jobs(self) -> Dict[str, Dict[str, Any]]:
       """
       Hämtar alla återkommande jobb
       
       Returns:
           Dict[str, Dict[str, Any]]: Återkommande jobb med konfiguration
       """
       with self.lock:
           return self.recurring_jobs.copy()
   
   def _scheduler_loop(self) -> None:
       """Huvudloop för schemaläggartråden"""
       self.logger.workflow("Schemaläggare startar arbetsloop")
       
       while not self.stop_event.is_set():
           try:
               # Hitta jobb som är redo att köas
               current_time = datetime.now()
               jobs_to_queue = []
               
               with self.lock:
                   # Hantera engångsjobb
                   for job_id, job in list(self.scheduled_jobs.items()):
                       if job.scheduled_for and job.scheduled_for <= current_time:
                           jobs_to_queue.append(job)
                           del self.scheduled_jobs[job_id]
                   
                   # Hantera återkommande jobb
                   for recurring_id, config in list(self.recurring_jobs.items()):
                       next_run = datetime.fromisoformat(config["next_run"])
                       
                       if next_run <= current_time:
                           # Kontrollera om maximalt antal körningar är uppnått
                           if config["max_runs"] is not None and config["runs_completed"] >= config["max_runs"]:
                               self.logger.workflow(f"Återkommande jobb {recurring_id} har nått max antal körningar ({config['max_runs']})")
                               del self.recurring_jobs[recurring_id]
                               continue
                           
                           # Schemalägg nästa körning
                           product_id = config["product_id"]
                           file_path = config["file_path"]
                           priority = JobPriority[config["priority"]]
                           tags = config["tags"]
                           
                           # Skapa ett nytt jobb
                           job = Job(
                               id="",  # Genereras automatiskt
                               product_id=product_id,
                               file_path=file_path,
                               priority=priority,
                               tags=tags + ["recurring", f"recurring_id:{recurring_id}"]
                           )
                           
                           # Lägg till i kö direkt
                           jobs_to_queue.append(job)
                           
                           # Beräkna nästa körningstid
                           next_time = current_time + timedelta(hours=config["interval_hours"])
                           
                           # Uppdatera återkommande jobb
                           config["next_run"] = next_time.isoformat()
                           config["runs_completed"] += 1
                           config["last_job_id"] = job.id
                           
                           self.logger.workflow(
                               f"Återkommande jobb {recurring_id} för produkt {product_id} körning {config['runs_completed']}, "
                               f"nästa körning: {next_time.isoformat()}"
                           )
               
               # Köa jobben
               for job in jobs_to_queue:
                   self.logger.workflow(
                       f"Schemalagt jobb {job.id} för produkt {job.product_id} är redo att köas"
                   )
                   self.queue.add_job(job)
               
               # Vänta en stund
               time.sleep(1.0)
               
           except Exception as e:
               self.logger.error(f"Oväntat fel i schemaläggare: {str(e)}")
               self.logger.error(traceback.format_exc())
               
               # Kort paus för att undvika snabba loopar vid fel
               time.sleep(5.0)
       
       self.logger.workflow("Schemaläggare avslutar arbetsloop")
    
   def save_state(self, file_path: Union[str, Path]) -> bool:
       """
       Sparar schemaläggartillstånd till fil
       
       Args:
           file_path: Sökväg att spara till
           
       Returns:
           bool: True om lyckad, annars False
       """
       file_path = Path(file_path)
       
       try:
           with self.lock:
               # Skapa en kopia av schemalagda jobb med serializerbara jobb
               serialized_jobs = {job_id: job.to_dict() for job_id, job in self.scheduled_jobs.items()}
               
               # Skapa tillståndsobjekt
               state = {
                   "scheduled_jobs": serialized_jobs,
                   "recurring_jobs": self.recurring_jobs,
                   "timestamp": datetime.now().isoformat()
               }
               
               # Spara till fil
               with open(file_path, 'w', encoding='utf-8') as f:
                   json.dump(state, f, ensure_ascii=False, indent=2)
               
               self.logger.info(f"Sparade schemaläggartillstånd till {file_path}")
               return True
       except Exception as e:
           self.logger.error(f"Fel vid sparande av schemaläggartillstånd: {str(e)}")
           return False
   
   def load_state(self, file_path: Union[str, Path]) -> bool:
       """
       Laddar schemaläggartillstånd från fil
       
       Args:
           file_path: Sökväg att ladda från
           
       Returns:
           bool: True om lyckad, annars False
       """
       file_path = Path(file_path)
       
       if not file_path.exists():
           self.logger.error(f"Tillståndsfilen {file_path} existerar inte")
           return False
       
       try:
           # Läs tillstånd från fil
           with open(file_path, 'r', encoding='utf-8') as f:
               state = json.load(f)
           
           with self.lock:
               # Rensa nuvarande tillstånd
               self.scheduled_jobs = {}
               self.recurring_jobs = {}
               
               # Återskapa schemalagda jobb
               scheduled_jobs_data = state.get("scheduled_jobs", {})
               for job_id, job_data in scheduled_jobs_data.items():
                   self.scheduled_jobs[job_id] = Job.from_dict(job_data)
               
               # Återskapa återkommande jobb
               self.recurring_jobs = state.get("recurring_jobs", {})
               
               self.logger.info(
                   f"Laddade schemaläggartillstånd från {file_path}: "
                   f"{len(self.scheduled_jobs)} schemalagda jobb, "
                   f"{len(self.recurring_jobs)} återkommande jobb"
               )
               return True
       except Exception as e:
           self.logger.error(f"Fel vid laddning av schemaläggartillstånd: {str(e)}")
           return False







## ===================================
##   Batch-bearbetning
## ===================================

class BatchProcessor:
    """
    Klass för att hantera batch-bearbetning av produkter
    """
    
    def __init__(
        self, processing_queue: ProcessingQueue, config: Dict[str, Any], 
        logger: logging.Logger, output_dir: Union[str, Path]
    ):
        """
        Initierar batch-processorn
        
        Args:
            processing_queue: Kön att lägga till jobb i
            config: Konfiguration för batch-processorn
            logger: Logger för att logga meddelanden
            output_dir: Katalog att spara batchrapporter i
        """
        self.queue = processing_queue
        self.config = config
        self.logger = logger
        self.output_dir = Path(output_dir)
        
        # Skapa katalog för batchrapporter
        self.reports_dir = self.output_dir / "batch_reports"
        self.reports_dir.mkdir(exist_ok=True, parents=True)
        
        # Batch-register för att spåra batcher
        self.batch_registry = {}
        
        # Statistik
        self.batch_counter = 0
        self.stats = {
            "batches_processed": 0,
            "total_products": 0,
            "enqueued_products": 0,
            "skipped_products": 0,
            "errors": 0,
            "batches_completed": 0  # Nya för att spåra slutförda batcher
        }
    
    def process_batch(
       self, products: List[Tuple[str, Path]], batch_name: str = None, 
       priority: JobPriority = JobPriority.NORMAL, tags: List[str] = None
   ) -> Dict[str, Any]:
       """
       Bearbetar en batch med produkter
       
       Args:
           products: Lista med produkter (ID, filsökväg)
           batch_name: Namn på batchen (genereras automatiskt om None)
           priority: Prioritet för jobben
           tags: Taggar att applicera på alla jobb i batchen
           
       Returns:
           Dict[str, Any]: Batchrapport
       """
       # Generera batchnamn om inget anges
       if not batch_name:
           self.batch_counter += 1
           timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
           batch_name = f"batch_{self.batch_counter}_{timestamp}"
       
       self.logger.workflow(f"Startar bearbetning av batch {batch_name} med {len(products)} produkter")
       
       # Skapa batchrapport
       report = {
           "batch_name": batch_name,
           "batch_id": str(uuid.uuid4()),  # Unikt ID för batchen
           "timestamp": datetime.now().isoformat(),
           "total_products": len(products),
           "priority": priority.name,
           "tags": tags or [],
           "enqueued_products": 0,
           "skipped_products": 0,
           "errors": 0,
           "job_ids": [],  # Lista med ID för alla jobb i batchen
           "product_status": {}
       }
       
       # Samla batchtaggar
       batch_tags = (tags or []) + [f"batch:{batch_name}", f"batch_id:{report['batch_id']}"]
       
       # Bearbeta varje produkt
       for product_id, file_path in products:
           try:
               # Skapa ett jobb för produkten
               job = Job(
                   id="",  # Genereras automatiskt
                   product_id=product_id,
                   file_path=file_path,
                   priority=priority,
                   tags=batch_tags,
                   metadata={"batch_id": report["batch_id"], "batch_name": batch_name}
               )
               
               # Lägg till i kön
               success = self.queue.add_job(job)
               
               if success:
                   report["enqueued_products"] += 1
                   report["product_status"][product_id] = "enqueued"
                   report["job_ids"].append(job.id)
                   self.stats["enqueued_products"] += 1
               else:
                   report["skipped_products"] += 1
                   report["product_status"][product_id] = "skipped"
                   self.stats["skipped_products"] += 1
           
           except Exception as e:
               error_msg = f"Fel vid schemaläggning av produkt {product_id}: {str(e)}"
               self.logger.error(error_msg)
               
               report["errors"] += 1
               report["product_status"][product_id] = f"error: {str(e)}"
               self.stats["errors"] += 1
       
       # Uppdatera statistik
       self.stats["batches_processed"] += 1
       self.stats["total_products"] += len(products)
       
       # Spara batchen i registret
       self.batch_registry[report["batch_id"]] = {
           "batch_name": batch_name,
           "timestamp": datetime.now().isoformat(),
           "status": "in_progress",
           "total_products": len(products),
           "enqueued_products": report["enqueued_products"],
           "job_ids": report["job_ids"]
       }
       
       # Spara batchrapport
       report_file = self.reports_dir / f"{batch_name}_report.json"
       
       try:
           with open(report_file, 'w', encoding='utf-8') as f:
               json.dump(report, f, ensure_ascii=False, indent=2)
           
           self.logger.info(f"Sparade batchrapport till {report_file}")
       except Exception as e:
           self.logger.error(f"Fel vid sparande av batchrapport: {str(e)}")
       
       self.logger.workflow(
           f"Slutförde schemaläggning av batch {batch_name}: "
           f"{report['enqueued_products']}/{report['total_products']} produkter i kön"
       )
       
       return report
   
    def process_directory(
       self, directory: Union[str, Path], pattern: str = "*.md", 
       batch_size: int = 100, priority: JobPriority = JobPriority.NORMAL,
       recursive: bool = False, tags: List[str] = None
   ) -> List[Dict[str, Any]]:
       """
       Bearbetar alla filer i en katalog som matchar ett mönster
       
       Args:
           directory: Katalog att bearbeta
           pattern: Filnamnsmönster att matcha
           batch_size: Antal produkter per batch
           priority: Prioritet för jobben
           recursive: Om underkataloger ska inkluderas rekursivt
           tags: Taggar att applicera på alla jobb
           
       Returns:
           List[Dict[str, Any]]: Lista med batchrapporter
       """
       directory = Path(directory)
       
       if not directory.exists() or not directory.is_dir():
           self.logger.error(f"Katalogen {directory} existerar inte eller är inte en katalog")
           return []
       
       # Hitta alla filer som matchar mönstret
       self.logger.info(f"Söker efter filer med mönster {pattern} i {directory}")
       
       if recursive:
           files = list(directory.glob(f"**/{pattern}"))
       else:
           files = list(directory.glob(pattern))
       
       if not files:
           self.logger.warning(f"Inga filer hittades med mönster {pattern} i {directory}")
           return []
       
       self.logger.info(f"Hittade {len(files)} filer")
       
       # Gruppera filer i batcher
       batches = []
       current_batch = []
       
       for file_path in files:
           # Använd filnamnet utan ändelse som produkt-ID
           product_id = file_path.stem
           
           # Försök hitta artikel-ID i filnamnet med regex
           article_match = re.search(r'(\d{5,8}(?:-\w+)?)', file_path.stem)
           if article_match:
               product_id = article_match.group(1)
           
           current_batch.append((product_id, file_path))
           
           if len(current_batch) >= batch_size:
               batches.append(current_batch)
               current_batch = []
       
       # Lägg till den sista, eventuellt ofullständiga, batchen
       if current_batch:
           batches.append(current_batch)
       
       # Skapa ett set med katalogspecifika taggar
       dir_tags = (tags or []) + [f"directory:{directory.name}"]
       
       # Bearbeta varje batch
       batch_reports = []
       
       for i, batch in enumerate(batches):
           batch_name = f"dir_{directory.name}_batch_{i+1}"
           report = self.process_batch(batch, batch_name, priority, dir_tags)
           batch_reports.append(report)
       
       self.logger.workflow(f"Slutförde bearbetning av katalog {directory}: {len(batch_reports)} batcher")
       
       return batch_reports
   
    def process_csv(
       self, csv_file: Union[str, Path], product_id_column: str, file_path_column: str,
       batch_size: int = 100, priority: JobPriority = JobPriority.NORMAL, 
       encoding: str = 'utf-8', delimiter: str = ',', tags: List[str] = None
   ) -> List[Dict[str, Any]]:
       """
       Bearbetar produkter listade i en CSV-fil
       
       Args:
           csv_file: Sökväg till CSV-filen
           product_id_column: Kolumnnamn för produkt-ID
           file_path_column: Kolumnnamn för filsökväg
           batch_size: Antal produkter per batch
           priority: Prioritet för jobben
           encoding: Teckenkodning för CSV-filen
           delimiter: Avgränsare för CSV-filen
           tags: Taggar att applicera på alla jobb
           
       Returns:
           List[Dict[str, Any]]: Lista med batchrapporter
       """
       csv_file = Path(csv_file)
       
       if not csv_file.exists():
           self.logger.error(f"CSV-filen {csv_file} existerar inte")
           return []
       
       # Läs CSV-filen
       products = []
       
       try:
           with open(csv_file, 'r', encoding=encoding) as f:
               reader = csv.DictReader(f, delimiter=delimiter)
               
               if product_id_column not in reader.fieldnames or file_path_column not in reader.fieldnames:
                   self.logger.error(
                       f"CSV-filen saknar kolumnerna {product_id_column} och/eller {file_path_column}. "
                       f"Tillgängliga kolumner: {', '.join(reader.fieldnames)}"
                   )
                   return []
               
               for row in reader:
                   product_id = row.get(product_id_column, "").strip()
                   file_path = row.get(file_path_column, "").strip()
                   
                   if product_id and file_path:
                       products.append((product_id, Path(file_path)))
       
       except Exception as e:
           self.logger.error(f"Fel vid läsning av CSV-fil {csv_file}: {str(e)}")
           return []
       
       if not products:
           self.logger.warning(f"Inga produkter hittades i CSV-filen {csv_file}")
           return []
       
       self.logger.info(f"Läste {len(products)} produkter från CSV-filen {csv_file}")
       
       # Gruppera produkter i batcher
       batches = []
       current_batch = []
       
       for product in products:
           current_batch.append(product)
           
           if len(current_batch) >= batch_size:
               batches.append(current_batch)
               current_batch = []
       
       # Lägg till den sista, eventuellt ofullständiga, batchen
       if current_batch:
           batches.append(current_batch)
       
       # Skapa ett set med CSV-specifika taggar
       csv_tags = (tags or []) + [f"csv:{csv_file.stem}"]
       
       # Bearbeta varje batch
       batch_reports = []
       
       for i, batch in enumerate(batches):
           batch_name = f"csv_{csv_file.stem}_batch_{i+1}"
           report = self.process_batch(batch, batch_name, priority, csv_tags)
           batch_reports.append(report)
       
       self.logger.workflow(f"Slutförde bearbetning av CSV-fil {csv_file}: {len(batch_reports)} batcher")
       
       return batch_reports
    
    def check_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Kontrollerar status för en specifik batch
        
        Args:
            batch_id: ID för batchen att kontrollera
            
        Returns:
            Dict[str, Any]: Status för batchen
        """
        if batch_id not in self.batch_registry:
            return {"error": f"Batch med ID {batch_id} hittades inte"}
        
        batch_info = self.batch_registry[batch_id].copy()
        
        # Räkna jobb per status
        job_status_counts = {status.value: 0 for status in JobStatus}
        completed_jobs = 0
        failed_jobs = 0
        
        # Kontrollera status för varje jobb i batchen
        for job_id in batch_info["job_ids"]:
            job = self.queue.get_job(job_id)
            
            if job:
                job_status_counts[job.status.value] += 1
                
                if job.status == JobStatus.COMPLETED:
                    completed_jobs += 1
                elif job.status == JobStatus.FAILED:
                    failed_jobs += 1
        
        # Uppdatera batch-status
        if completed_jobs + failed_jobs == len(batch_info["job_ids"]):
            batch_info["status"] = "completed"
            
            # Uppdatera batch-registret om detta är första gången vi upptäcker att batchen är klar
            if self.batch_registry[batch_id]["status"] != "completed":
                self.batch_registry[batch_id]["status"] = "completed"
                self.batch_registry[batch_id]["completed_at"] = datetime.now().isoformat()
                self.stats["batches_completed"] += 1
        
        # Lägg till status-statistik
        batch_info["job_status_counts"] = job_status_counts
        batch_info["completed_jobs"] = completed_jobs
        batch_info["failed_jobs"] = failed_jobs
        batch_info["completion_percentage"] = (
            (completed_jobs + failed_jobs) / len(batch_info["job_ids"]) * 100 
            if batch_info["job_ids"] else 0
        )
        
        return batch_info
    
    def update_batch_registry(self) -> None:
        """Uppdaterar status för alla batcher i registret"""
        for batch_id in list(self.batch_registry.keys()):
            if self.batch_registry[batch_id]["status"] != "completed":
                self.check_batch_status(batch_id)
    
    def get_stats(self) -> Dict[str, Any]:
       """
       Hämtar statistik för batch-processorn
       
       Returns:
           Dict[str, Any]: Statistik för batch-processorn
       """
       # Uppdatera batch-status innan statistik returneras
       self.update_batch_registry()
       
       return {
           "batches_processed": self.stats["batches_processed"],
           "batches_completed": self.stats["batches_completed"],
           "completion_rate": (
               self.stats["batches_completed"] / self.stats["batches_processed"] * 100
               if self.stats["batches_processed"] > 0 else 0
           ),
           "total_products": self.stats["total_products"],
           "enqueued_products": self.stats["enqueued_products"],
           "skipped_products": self.stats["skipped_products"],
           "errors": self.stats["errors"],
           "active_batches": len([b for b in self.batch_registry.values() if b["status"] == "in_progress"])
       }
    
    def generate_summary_report(self) -> Dict[str, Any]:
       """
       Genererar en sammanfattande rapport över alla batcher
       
       Returns:
           Dict[str, Any]: Sammanfattande rapport
       """
       # Uppdatera batch-status
       self.update_batch_registry()
       
       report = {
           "timestamp": datetime.now().isoformat(),
           "stats": self.get_stats(),
           "batches": self.batch_registry,
           "queue_status": self.queue.get_queue_status()
       }
       
       # Spara rapporten
       timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       report_file = self.reports_dir / f"summary_report_{timestamp}.json"
       
       try:
           with open(report_file, 'w', encoding='utf-8') as f:
               json.dump(report, f, ensure_ascii=False, indent=2)
           
           self.logger.info(f"Sparade sammanfattande rapport till {report_file}")
       except Exception as e:
           self.logger.error(f"Fel vid sparande av sammanfattande rapport: {str(e)}")
       
       return report


## ===================================
##   WorkflowManager - Huvudklass
## ===================================

class WorkflowManager:
   """
   Huvudklass för att hantera hela arbetsflödet
   """
   
   def __init__(self, config_manager: ConfigManager, logger: logging.Logger, visualizer=None):
       """
       Initierar arbetsflödeshanteraren
       
       Args:
           config_manager: Konfigurationshanterare
           logger: Logger för att logga meddelanden
           visualizer: Visualiserare för att visa information i terminalen
       """
       self.config = config_manager
       self.logger = logger
       self.visualizer = visualizer
       
       # Konfigurera kataloger
       self.data_dir = Path(config_manager.get("general.data_dir", "./data"))
       self.output_dir = Path(config_manager.get("general.output_dir", "./output"))
       
       # Skapa kataloger
       self.data_dir.mkdir(exist_ok=True, parents=True)
       self.output_dir.mkdir(exist_ok=True, parents=True)
       
       # Skapa underkataloger i output
       (self.output_dir / "validated").mkdir(exist_ok=True, parents=True)
       (self.output_dir / "unvalidated").mkdir(exist_ok=True, parents=True)
       (self.output_dir / "corrected").mkdir(exist_ok=True, parents=True)  # Ny för korrigerade resultat
       (self.output_dir / "failed").mkdir(exist_ok=True, parents=True)
       (self.output_dir / "empty").mkdir(exist_ok=True, parents=True)  # Ny för resultat utan extraherad data
       (self.output_dir / "structured").mkdir(exist_ok=True, parents=True)
       (self.output_dir / "reports").mkdir(exist_ok=True, parents=True)
       (self.output_dir / "batch_reports").mkdir(exist_ok=True, parents=True)
       (self.output_dir / "prompts").mkdir(exist_ok=True, parents=True)
       
       # Skapa LLM-klient
       from client import LLMClient
       self.llm_config = config_manager.get("llm", {})
       self.llm_client = LLMClient(self.llm_config, logger, visualizer)
       
       # Skapa prompthanterare
       self.prompt_manager = PromptManager(
           storage_dir=self.output_dir / "prompts",
           logger=logger,
           visualizer=visualizer
       )
       
       # Konfigurera promptcaching om aktiverat
       if config_manager.get("extraction.use_prompt_cache", True):
           self.prompt_manager.setup_caching(
               cache_dir=self.output_dir / "prompt_cache",
               max_cache_size=config_manager.get("extraction.max_prompt_cache_size", 1000)
           )
       
       # Skapa produktprocessor med prompthanterare och den nya kombinerade extraktionstypen
       from Processor import ProductProcessor
       extraction_config = config_manager.get("extraction", {})
       
       # Uppdatera extraction_config för kombinerad extraktion
       combined_config = extraction_config.copy()
       combined_config["extraction_type"] = "combined"
       combined_config["combined"] = {
           "enabled": True,
           "threshold": extraction_config.get("threshold", 0.7),
           "include_product": extraction_config.get("include_product", True),
           "include_relations": extraction_config.get("compatibility", {}).get("enabled", True),
           "include_specifications": extraction_config.get("technical", {}).get("enabled", True),
           "include_data_tables": extraction_config.get("include_data_tables", True)
       }
       
       self.processor = ProductProcessor(
           combined_config,
           self.llm_client,
           logger,
           visualizer,
           prompt_manager=self.prompt_manager
       )
       
       # Skapa processeringskö
       self.processing_queue = ProcessingQueue(
           config_manager.get("workflow", {}),
           logger
       )
       
       # Skapa arbetare
       self.max_workers = config_manager.get("general.max_workers", 4)
       self.workers = []
       
       for i in range(self.max_workers):
           worker = Worker(
               i + 1,
               self.processing_queue,
               self.processor,
               config_manager.get("workflow", {}),
               logger,
               self.output_dir
           )
           self.workers.append(worker)
       
       # Skapa batch-processor
       self.batch_processor = BatchProcessor(
           self.processing_queue,
           config_manager.get("workflow", {}),
           logger,
           self.output_dir
       )
       
       # Skapa schemaläggare
       self.scheduler = JobScheduler(
           self.processing_queue,
           config_manager.get("workflow", {}),
           logger
       )
       
       # Sökmotorkomponent (initieras vid första användning)
       self._search_index = None
       self._search_index_last_updated = None
       
       # Kontrollvariabler
       self.running = False
       self.stop_event = threading.Event()
       self.pause_event = threading.Event()  # Ny flagga för paus
       
       # Register för slutförda och aktiva jobb (för återupptagning)
       self.job_registry = {}
       
       # Hantera avbrott
       signal.signal(signal.SIGINT, self._signal_handler)
       signal.signal(signal.SIGTERM, self._signal_handler)
   
   def register_prompt_callbacks(self) -> None:
       """Registrerar callbacks för prompthantering med processorn"""
       if hasattr(self.processor, 'register_prompt_callbacks'):
           self.processor.register_prompt_callbacks(
               self.prompt_manager.update_usage_statistics,
               self.prompt_manager.get_best_prompt
           )
           self.logger.debug("Registrerade promptcallbacks med processorn")
   
   def start(self) -> None:
       """Startar arbetsflödeshanteraren"""
       if not self.running:
           self.logger.workflow("Startar arbetsflödeshanterare")
           
           # Kontrollera anslutning till LLM-tjänsten
           if not self.llm_client.verify_connection():
               self.logger.error("Kunde inte ansluta till LLM-tjänsten, avbryter")
               return
           
           # Registrera promptcallbacks
           self.register_prompt_callbacks()
           
           # Starta schemaläggare
           self.scheduler.start()
           
           # Starta arbetare
           for worker in self.workers:
               worker.start()
           
           # Markera som startad
           self.running = True
           self.stop_event.clear()
           self.pause_event.clear()
           
           self.logger.workflow(f"Arbetsflödeshanterare startad med {len(self.workers)} arbetare")
           
           if self.visualizer:
               self.visualizer.display_markdown(
                   f"# Arbetsflödeshanterare startad\n\n"
                   f"- Antal arbetare: {len(self.workers)}\n"
                   f"- Data-katalog: {self.data_dir}\n"
                   f"- Utdata-katalog: {self.output_dir}\n"
               )
   
   def stop(self) -> None:
       """Stoppar arbetsflödeshanteraren"""
       if self.running:
           self.logger.workflow("Stoppar arbetsflödeshanterare...")
           
           # Signalera stopp
           self.stop_event.set()
           self.running = False
           
           # Stoppa schemaläggare
           self.scheduler.stop()
           
           # Stoppa arbetare
           for worker in self.workers:
               worker.stop()
           
           # Stoppa kön
           self.processing_queue.shutdown()
           
           # Spara tillstånd för återupptagning
           self._save_state()
           
           # Generera slutrapport
           self._generate_final_report()
           
           self.logger.workflow("Arbetsflödeshanterare stoppad")
   
   def pause(self) -> None:
       """Pausar arbetsflödeshanteraren"""
       if self.running and not self.pause_event.is_set():
           self.logger.workflow("Pausar arbetsflödeshanterare...")
           
           # Signalera paus
           self.pause_event.set()
           
           # Pausa kön
           self.processing_queue.pause_all()
           
           # Pausa arbetare
           for worker in self.workers:
               worker.pause()
           
           self.logger.workflow("Arbetsflödeshanterare pausad")
   
   def resume(self) -> None:
       """Återupptar arbetsflödeshanteraren efter paus"""
       if self.running and self.pause_event.is_set():
           self.logger.workflow("Återupptar arbetsflödeshanterare...")
           
           # Återställ pausflagga
           self.pause_event.clear()
           
           # Återuppta kön
           self.processing_queue.resume_all()
           
           # Återuppta arbetare
           for worker in self.workers:
               worker.resume()
           
           self.logger.workflow("Arbetsflödeshanterare återupptagen")
   
   def join(self, timeout: float = None) -> None:
       """
       Väntar på att alla arbetare ska avslutas
       
       Args:
           timeout: Tidsgräns per arbetare i sekunder, eller None för att vänta obegränsat
       """
       for worker in self.workers:
           worker.join(timeout)
       
       self.scheduler.join(timeout)
   
   def _signal_handler(self, signum, frame) -> None:
       """
       Hanterare för signaler (SIGINT, SIGTERM)
       
       Args:
           signum: Signalnummer
           frame: Aktuell stackram
       """
       self.logger.warning(f"Fick signal {signum}, stoppar arbetsflödeshanterare")
       self.stop()
   
   def _save_state(self) -> None:
       """Sparar tillstånd för arbetsflödeshanteraren"""
       # Skapa tillståndskatalog
       state_dir = self.output_dir / "state"
       state_dir.mkdir(exist_ok=True, parents=True)
       
       # Spara kötillstånd
       queue_state_file = state_dir / "queue_state.json"
       self.processing_queue.save_state(queue_state_file)
       
       # Spara schemaläggartillstånd
       scheduler_state_file = state_dir / "scheduler_state.json"
       self.scheduler.save_state(scheduler_state_file)
       
       # Spara jobbregister
       job_registry_file = state_dir / "job_registry.json"
       try:
           with open(job_registry_file, 'w', encoding='utf-8') as f:
               json.dump(self.job_registry, f, ensure_ascii=False, indent=2)
       except Exception as e:
           self.logger.error(f"Fel vid sparande av jobbregister: {str(e)}")
       
       self.logger.info(f"Sparade arbetsflödestillstånd till {state_dir}")
   
   def _load_state(self) -> bool:
       """
       Laddar tillstånd för arbetsflödeshanteraren
       
       Returns:
           bool: True om lyckad, annars False
       """
       state_dir = self.output_dir / "state"
       
       if not state_dir.exists():
           self.logger.warning("Ingen tillståndskatalog hittades, kan inte återuppta")
           return False
       
       # Ladda kötillstånd
       queue_state_file = state_dir / "queue_state.json"
       queue_loaded = False
       if queue_state_file.exists():
           queue_loaded = self.processing_queue.load_state(queue_state_file)
       
       # Ladda schemaläggartillstånd
       scheduler_state_file = state_dir / "scheduler_state.json"
       scheduler_loaded = False
       if scheduler_state_file.exists():
           scheduler_loaded = self.scheduler.load_state(scheduler_state_file)
       
       # Ladda jobbregister
       job_registry_file = state_dir / "job_registry.json"
       if job_registry_file.exists():
           try:
               with open(job_registry_file, 'r', encoding='utf-8') as f:
                   self.job_registry = json.load(f)
               self.logger.info(f"Laddade jobbregister med {len(self.job_registry)} jobb")
           except Exception as e:
               self.logger.error(f"Fel vid laddning av jobbregister: {str(e)}")
       
       self.logger.info(f"Laddade arbetsflödestillstånd från {state_dir}")
       return queue_loaded or scheduler_loaded
   
   def process_product(self, product_id: str, file_path: Union[str, Path]) -> ProductResult:
       """
       Bearbetar en enskild produkt direkt (utan kö)
       
       Args:
           product_id: ID för produkten
           file_path: Sökväg till filen
           
       Returns:
           ProductResult: Resultatet av bearbetningen
       """
       self.logger.workflow(f"Bearbetar produkt {product_id} direkt (utan kö)")
       result = self.processor.process_product(product_id, file_path)
       
       # Spara resultatet
       output_category = self._determine_output_category(result)
       output_dir = self.output_dir / output_category
       success, saved_path = self.processor.save_result(result, output_dir)
       
       if success:
           # Spara strukturerad data
           structured_dir = self.output_dir / "structured"
           saved_files = self.processor.save_structured_data(result, structured_dir)
           
           # Registrera jobbet som slutfört
           self.job_registry[product_id] = {
               "status": result.status.value,
               "timestamp": datetime.now().isoformat(),
               "result_file": str(saved_path),
               "structured_files": {k: str(v) for k, v in saved_files.items()} if saved_files else {}
           }
       
       return result
   
   def enqueue_product(
       self, product_id: str, file_path: Union[str, Path],
       priority: JobPriority = JobPriority.NORMAL, tags: List[str] = None
   ) -> str:
       """
       Lägger till en produkt i kön
       
       Args:
           product_id: ID för produkten
           file_path: Sökväg till filen
           priority: Prioritet för jobbet
           tags: Taggar för jobbet
           
       Returns:
           str: ID för det skapade jobbet
       """
       job = Job(
           id="",  # Genereras automatiskt
           product_id=product_id,
           file_path=file_path,
           priority=priority,
           tags=tags or []
       )
       
       if self.processing_queue.add_job(job):
           self.logger.workflow(f"Lade till produkt {product_id} i kön med prioritet {priority.name}")
           return job.id
       else:
           self.logger.error(f"Kunde inte lägga till produkt {product_id} i kön")
           return ""
   
   def schedule_product(
       self, product_id: str, file_path: Union[str, Path],
       scheduled_time: datetime, priority: JobPriority = JobPriority.NORMAL, 
       tags: List[str] = None
   ) -> str:
       """
       Schemalägger en produkt för framtida bearbetning
       
       Args:
           product_id: ID för produkten
           file_path: Sökväg till filen
           scheduled_time: Tidpunkt för schemaläggning
           priority: Prioritet för jobbet
           tags: Taggar för jobbet
           
       Returns:
           str: ID för det schemalagda jobbet
       """
       return self.scheduler.schedule_job(
           product_id=product_id,
           file_path=file_path,
           scheduled_time=scheduled_time,
           priority=priority,
           tags=tags
       )
   
   def schedule_recurring_product(
       self, product_id: str, file_path: Union[str, Path],
       interval_hours: float, priority: JobPriority = JobPriority.NORMAL,
       tags: List[str] = None, max_runs: int = None
   ) -> str:
       """
       Schemalägger en återkommande produkt med angivet intervall
       
       Args:
           product_id: ID för produkten
           file_path: Sökväg till filen
           interval_hours: Intervall i timmar mellan körningar
           priority: Prioritet för jobbet
           tags: Taggar för jobbet
           max_runs: Maximalt antal körningar (None = obegränsat)
           
       Returns:
           str: ID för det återkommande jobbet
       """
       return self.scheduler.schedule_recurring_job(
           product_id=product_id,
           file_path=file_path,
           interval_hours=interval_hours,
           priority=priority,
           tags=tags,
           max_runs=max_runs
       )
   
   def process_directory(
       self, directory: Union[str, Path], pattern: str = "*.md",
       batch_size: int = 100, priority: JobPriority = JobPriority.NORMAL,
       recursive: bool = False, tags: List[str] = None
   ) -> List[Dict[str, Any]]:
       """
       Bearbetar alla filer i en katalog som matchar ett mönster
       
       Args:
           directory: Katalog att bearbeta
           pattern: Filnamnsmönster att matcha
           batch_size: Antal produkter per batch
           priority: Prioritet för jobben
           recursive: Om underkataloger ska inkluderas rekursivt
           tags: Taggar att applicera på alla jobb
           
       Returns:
           List[Dict[str, Any]]: Lista med batchrapporter
       """
       return self.batch_processor.process_directory(
           directory=directory,
           pattern=pattern,
           batch_size=batch_size,
           priority=priority,
           recursive=recursive,
           tags=tags
       )
   
   def process_csv(
       self, csv_file: Union[str, Path], product_id_column: str, file_path_column: str,
       batch_size: int = 100, priority: JobPriority = JobPriority.NORMAL,
       encoding: str = 'utf-8', delimiter: str = ',', tags: List[str] = None
   ) -> List[Dict[str, Any]]:
       """
       Bearbetar produkter listade i en CSV-fil
       
       Args:
           csv_file: Sökväg till CSV-filen
           product_id_column: Kolumnnamn för produkt-ID
           file_path_column: Kolumnnamn för filsökväg
           batch_size: Antal produkter per batch
           priority: Prioritet för jobben
           encoding: Teckenkodning för CSV-filen
           delimiter: Avgränsare för CSV-filen
           tags: Taggar att applicera på alla jobb
           
       Returns:
           List[Dict[str, Any]]: Lista med batchrapporter
       """
       return self.batch_processor.process_csv(
           csv_file=csv_file,
           product_id_column=product_id_column,
           file_path_column=file_path_column,
           batch_size=batch_size,
           priority=priority,
           encoding=encoding,
           delimiter=delimiter,
           tags=tags
       )
   
   def get_status(self) -> Dict[str, Any]:
       """
       Hämtar status för arbetsflödeshanteraren
       
       Returns:
           Dict[str, Any]: Status för arbetsflödeshanteraren
       """
       status = {
           "running": self.running,
           "paused": self.pause_event.is_set(),
           "workers": [worker.get_stats() for worker in self.workers],
           "active_workers": sum(1 for w in self.workers if w.is_alive() and not w.is_paused()),
           "queue": self.processing_queue.get_queue_status(),
           "batch_processor": self.batch_processor.get_stats(),
           "scheduled_jobs": len(self.scheduler.get_scheduled_jobs()),
           "recurring_jobs": len(self.scheduler.get_recurring_jobs()),
           "processor_stats": self.processor.get_processing_statistics(),
           "timestamp": datetime.now().isoformat()
       }
       
       return status
   
   def get_detailed_worker_status(self) -> List[Dict[str, Any]]:
       """
       Hämtar detaljerad status för alla arbetare
       
       Returns:
           List[Dict[str, Any]]: Detaljerad status för varje arbetare
       """
       return [worker.get_stats() for worker in self.workers]
   
   def get_worker_by_id(self, worker_id: int) -> Optional[Worker]:
       """
       Hämtar en arbetare baserat på ID
       
       Args:
           worker_id: ID för arbetaren
           
       Returns:
           Optional[Worker]: Arbetaren eller None om den inte finns
       """
       for worker in self.workers:
           if worker.worker_id == worker_id:
               return worker
       return None
   
   def optimize_prompts(self, extraction_type: str = None) -> None:
       """
       Optimerar promptmallar för en specifik extraktionstyp
       
       Args:
           extraction_type: Typ av extraktion att optimera för, eller None för alla typer
       """
       if not hasattr(self, 'prompt_manager') or not self.prompt_manager:
           self.logger.error("Ingen prompthanterare tillgänglig för optimering")
           return
       
       # Bestäm vilka extraktionstyper som ska optimeras
       extraction_types = [extraction_type] if extraction_type else ["combined"]
       
       # Hämta exempel på produkter för testning
       sample_products = self._get_sample_products(5)
       
       if not sample_products:
           self.logger.warning("Kunde inte hitta några exempelprodukter för promptoptimering")
           return
       
       # Samla texter från exempelprodukterna
       sample_texts = []
       for product_id, file_path in sample_products:
           try:
               with open(file_path, 'r', encoding='utf-8') as f:
                   text = f.read()
                   sample_texts.append(text)
           except Exception as e:
               self.logger.error(f"Kunde inte läsa exempelprodukt {product_id}: {str(e)}")
       
       if not sample_texts:
           self.logger.warning("Kunde inte läsa några exempelprodukter för promptoptimering")
           return
       
       # Optimera varje extraktionstyp
       for ext_type in extraction_types:
           self.logger.workflow(f"Optimerar promptmallar för {ext_type}-extraktion")
           
           # Utför dynamisk optimering
           best_prompt = self.prompt_manager.dynamic_optimize(ext_type, sample_texts)
           
           if best_prompt:
               self.logger.workflow(f"Bästa promptmall för {ext_type}: {best_prompt.name}")
               
               # Visa resultatet i visualiseraren
               if self.visualizer:
                   self.visualizer.display_markdown(
                       f"# Promptoptimering för {ext_type}\n\n"
                       f"Bästa promptmall: **{best_prompt.name}**\n\n"
                       f"Framgångsfrekvens: {best_prompt.success_rate:.2f}\n"
                       f"Genomsnittlig svarstid: {best_prompt.average_latency_ms} ms\n"
                   )
           else:
               self.logger.warning(f"Kunde inte hitta någon lämplig promptmall för {ext_type}")
   
   def _get_sample_products(self, count: int = 5) -> List[Tuple[str, Path]]:
       """
       Hämtar exempelprodukter för testning
       
       Args:
           count: Antal produkter att hämta
           
       Returns:
           List[Tuple[str, Path]]: Lista med (product_id, file_path) par
       """
       # Försök först med tidigare bearbetade produkter
       processed_dir = self.output_dir / "validated"
       if processed_dir.exists():
           result_files = list(processed_dir.glob("*.json"))
           if result_files:
               # Läs in produktinformation från resultatfiler
               processed_products = []
               for result_file in result_files[:count*2]:  # Läs in fler än nödvändigt för att hantera fel
                   try:
                       with open(result_file, 'r', encoding='utf-8') as f:
                           result_data = json.load(f)
                       
                       product_id = result_data.get("product_id")
                       file_path = result_data.get("metadata", {}).get("file_path")
                       
                       if product_id and file_path and Path(file_path).exists():
                           processed_products.append((product_id, Path(file_path)))
                           
                           if len(processed_products) >= count:
                               break
                   except Exception as e:
                       self.logger.debug(f"Kunde inte läsa resultatfil {result_file}: {str(e)}")
               
               if len(processed_products) > 0:
                   return processed_products
       
       # Fallback till data-katalogen
       data_dir = self.data_dir
       if data_dir.exists():
           all_files = list(data_dir.glob("**/*.md"))
           if all_files:
               # Välj slumpmässiga filer
               import random
               random.shuffle(all_files)
               
               sample_products = []
               for file_path in all_files[:count]:
                   product_id = file_path.stem
                   sample_products.append((product_id, file_path))
               
               return sample_products
       
       # Ingen produkt hittades
       return []


## ===================================
##   Sökindexering och sökning
## ===================================

   def create_search_index(self) -> None:
       """
       Skapar ett sökindex för snabb åtkomst till produktdata
       """
       self.logger.workflow("Skapar sökindex för alla produkter...")
       
       # Initialisera index
       index = {
           "products": {},
           "title_index": {},
           "article_number_index": {},
           "ean_index": {},
           "relation_index": {},
           "metadata": {
               "created_at": datetime.now().isoformat(),
               "product_count": 0,
               "relations_count": 0,
               "specifications_count": 0,
               "data_tables_count": 0
           }
       }
       
       try:
           # Hitta alla index-filer i structured-katalogen
           structured_dir = self.output_dir / "structured"
           if not structured_dir.exists():
               self.logger.warning("Structured-katalogen finns inte, kan inte skapa sökindex")
               return
           
           index_files = list(structured_dir.glob("*/index.json"))
           if not index_files:
               self.logger.warning("Inga indexfiler hittades, kan inte skapa sökindex")
               return
           
           # Bearbeta varje indexfil
           for index_file in index_files:
               try:
                   with open(index_file, 'r', encoding='utf-8') as f:
                       product_index = json.load(f)
                   
                   product_id = product_index.get("product_id")
                   if not product_id:
                       continue
                   
                   # Lägg till i huvudindex
                   index["products"][product_id] = {
                       "product_id": product_id,
                       "title": product_index.get("product_title", ""),
                       "available_data": product_index.get("available_data", {}),
                       "file_paths": product_index.get("file_paths", {})
                   }
                   
                   # Öka räknaren
                   index["metadata"]["product_count"] += 1
                   
                   # Indexera efter titel
                   if product_index.get("product_title"):
                       title = product_index["product_title"].lower()
                       if title not in index["title_index"]:
                           index["title_index"][title] = []
                       index["title_index"][title].append(product_id)
                   
                   # Lägg till metadata om detta finns
                   if "product_info" in product_index.get("available_data", {}) and product_index["available_data"]["product_info"]:
                       # Läs produktinfo-filen för att hämta artikelnummer och EAN
                       product_info_path = structured_dir / product_index["file_paths"].get("product", "")
                       if product_info_path.exists():
                           try:
                               with open(product_info_path, 'r', encoding='utf-8') as f:
                                   product_info = json.load(f)
                               
                               # Indexera efter artikelnummer
                               if "article_number" in product_info:
                                   article_number = product_info["article_number"]
                                   if article_number not in index["article_number_index"]:
                                       index["article_number_index"][article_number] = []
                                   index["article_number_index"][article_number].append(product_id)
                               
                               # Indexera efter EAN
                               if "ean" in product_info:
                                   ean = product_info["ean"]
                                   if ean not in index["ean_index"]:
                                       index["ean_index"][ean] = []
                                   index["ean_index"][ean].append(product_id)
                           except Exception as e:
                               self.logger.warning(f"Kunde inte läsa produktinfo för {product_id}: {str(e)}")
                   
                   # Lägg till relationsindex
                   if "relations" in product_index.get("available_data", {}) and product_index["available_data"]["relations"]:
                       compatibility_path = structured_dir / product_index["file_paths"].get("compatibility", "")
                       if compatibility_path.exists():
                           try:
                               with open(compatibility_path, 'r', encoding='utf-8') as f:
                                   compatibility = json.load(f)
                               
                               if "relations" in compatibility:
                                   relations = compatibility["relations"]
                                   for relation in relations:
                                       if isinstance(relation, dict) and "related_product" in relation:
                                           related_product = relation["related_product"]
                                           
                                           if isinstance(related_product, dict):
                                               # Extrahera information om relaterad produkt
                                               related_name = related_product.get("name", "").lower()
                                               related_article = related_product.get("article_number", "")
                                               related_ean = related_product.get("ean", "")
                                               
                                               # Indexera efter artikelnummer
                                               if related_article:
                                                   if related_article not in index["relation_index"]:
                                                       index["relation_index"][related_article] = []
                                                   if product_id not in index["relation_index"][related_article]:
                                                       index["relation_index"][related_article].append(product_id)
                                               
                                               # Indexera efter EAN
                                               if related_ean:
                                                   if related_ean not in index["relation_index"]:
                                                       index["relation_index"][related_ean] = []
                                                   if product_id not in index["relation_index"][related_ean]:
                                                       index["relation_index"][related_ean].append(product_id)
                                           
                                       index["metadata"]["relations_count"] += 1
                           except Exception as e:
                               self.logger.warning(f"Kunde inte läsa kompatibilitetsinformation för {product_id}: {str(e)}")
                   
                   # Räkna specifikationer och datatabeller
                   if "specifications" in product_index.get("available_data", {}) and product_index["available_data"]["specifications"]:
                       specs_path = structured_dir / product_index["file_paths"].get("technical", "")
                       if specs_path.exists():
                           try:
                               with open(specs_path, 'r', encoding='utf-8') as f:
                                   specs = json.load(f)
                               
                               if "specifications" in specs:
                                   index["metadata"]["specifications_count"] += len(specs["specifications"])
                           except Exception as e:
                               self.logger.warning(f"Kunde inte läsa tekniska specifikationer för {product_id}: {str(e)}")
                   
                   if "data_tables" in product_index.get("available_data", {}) and product_index["available_data"]["data_tables"]:
                       tables_path = structured_dir / product_index["file_paths"].get("data_tables", "")
                       if tables_path.exists():
                           try:
                               with open(tables_path, 'r', encoding='utf-8') as f:
                                   tables = json.load(f)
                               
                               if "data_tables" in tables:
                                   index["metadata"]["data_tables_count"] += len(tables["data_tables"])
                           except Exception as e:
                               self.logger.warning(f"Kunde inte läsa datatabeller för {product_id}: {str(e)}")
               
               except Exception as e:
                   self.logger.warning(f"Kunde inte bearbeta indexfil {index_file}: {str(e)}")
           
           # Spara index
           index_path = self.output_dir / "product_search_index.json"
           with open(index_path, 'w', encoding='utf-8') as f:
               json.dump(index, f, ensure_ascii=False, indent=2)
           
           # Spara också sökindexet i minnet för snabbare sökningar
           self._search_index = index
           self._search_index_last_updated = datetime.now()
           
           self.logger.workflow(f"Skapade sökindex med {index['metadata']['product_count']} produkter och {index['metadata']['relations_count']} relationer")
           
           if self.visualizer:
               self.visualizer.display_markdown(
                   f"# Sökindex skapat\n\n"
                   f"- **Antal produkter:** {index['metadata']['product_count']}\n"
                   f"- **Antal relationer:** {index['metadata']['relations_count']}\n"
                   f"- **Antal specifikationer:** {index['metadata']['specifications_count']}\n"
                   f"- **Antal datatabeller:** {index['metadata']['data_tables_count']}\n"
                   f"- **Index sparat till:** {index_path}\n"
               )
       
       except Exception as e:
           self.logger.error(f"Fel vid skapande av sökindex: {str(e)}")
   
   def search_products(self, query: str, search_type: str = "all") -> Dict[str, Any]:
       """
       Söker efter produkter baserat på sökfråga och typ
       
       Args:
           query: Sökfrågan
           search_type: Typ av sökning (all, title, article, ean, relation)
           
       Returns:
           Dict[str, Any]: Sökresultat
       """
       self.logger.workflow(f"Söker efter '{query}' med söktyp '{search_type}'")
       
       # Initialisera resultat
       result = {
           "query": query,
           "search_type": search_type,
           "timestamp": datetime.now().isoformat(),
           "matches": [],
           "related_matches": [],
           "total_matches": 0
       }
       
       try:
           # Ladda sökindex om det inte finns eller är för gammalt
           if self._search_index is None or (
               self._search_index_last_updated is not None and 
               (datetime.now() - self._search_index_last_updated).total_seconds() > 3600  # Äldre än 1 timme
           ):
               self.logger.info("Sökindex saknas eller är för gammalt, laddar/skapar det nu...")
               self._load_or_create_search_index()
           
           if self._search_index is None:
               self.logger.error("Kunde inte ladda eller skapa sökindex")
               return result
           
           # Normalisera sökfrågan
           query = query.lower().strip()
           
           # Sök baserat på typ
           matches = set()
           
           if search_type in ["all", "title"]:
               # Sök i titelindex
               for title, product_ids in self._search_index["title_index"].items():
                   if query in title:
                       matches.update(product_ids)
           
           if search_type in ["all", "article"]:
               # Sök i artikelnummerindex
               if query in self._search_index["article_number_index"]:
                   matches.update(self._search_index["article_number_index"][query])
           
           if search_type in ["all", "ean"]:
               # Sök i EAN-index
               if query in self._search_index["ean_index"]:
                   matches.update(self._search_index["ean_index"][query])
           
           # Sök efter relaterade produkter
           related_matches = set()
           if search_type in ["all", "relation"]:
               # Sök i relationsindex
               if query in self._search_index["relation_index"]:
                   related_matches.update(self._search_index["relation_index"][query])
           
           # Bygg resultatet
           for product_id in matches:
               if product_id in self._search_index["products"]:
                   result["matches"].append(self._search_index["products"][product_id])
           
           for product_id in related_matches:
               if product_id in self._search_index["products"] and product_id not in matches:
                   result["related_matches"].append(self._search_index["products"][product_id])
           
           result["total_matches"] = len(result["matches"]) + len(result["related_matches"])
           
           self.logger.workflow(f"Hittade {result['total_matches']} träffar för '{query}'")
       
       except Exception as e:
           self.logger.error(f"Fel vid sökning: {str(e)}")
       
       return result
   
   def _load_or_create_search_index(self) -> None:
       """Laddar eller skapar sökindex om det inte finns"""
       index_path = self.output_dir / "product_search_index.json"
       
       if index_path.exists():
           try:
               with open(index_path, 'r', encoding='utf-8') as f:
                   self._search_index = json.load(f)
               self._search_index_last_updated = datetime.now()
               self.logger.info(f"Laddade sökindex från {index_path}")
               return
           except Exception as e:
               self.logger.error(f"Fel vid laddning av sökindex: {str(e)}")
       
       # Om index inte kunde laddas, skapa det
       self.create_search_index()
   
   def _determine_output_category(self, result: ProductResult) -> str:
       """
       Bestämmer i vilken kategori ett resultat ska sparas
       
       Args:
           result: Resultatet att kategorisera
           
       Returns:
           str: Kategorin för resultatet
       """
       # Kategorisera baserat på status och innehåll
       if result.status == ExtractionStatus.VALIDATED:
           return "validated"
       elif result.status == ExtractionStatus.CORRECTED:
           return "corrected"
       elif result.status in [ExtractionStatus.COMPLETED, ExtractionStatus.PARTIALLY_COMPLETED]:
           if result.get_compatibility_count() > 0 or result.get_technical_count() > 0 or result.product_info:
               return "unvalidated"
           else:
               return "empty"
       elif result.status == ExtractionStatus.FAILED:
           return "failed"
       else:
           return "other"


## ===================================
##   Rapportering och visualisering
## ===================================

   def _generate_extraction_stats(self) -> Dict[str, Any]:
       """
       Genererar statistik över extraktionsresultat
       
       Returns:
           Dict[str, Any]: Statistik över extraktionsresultat
       """
       # Initialisera statistik
       stats = {
           "products_with_info": 0,
           "products_with_relations": 0,
           "products_with_specs": 0,
           "products_with_tables": 0,
           "total_relations": 0,
           "total_specs": 0,
           "total_tables": 0,
           "total_products": 0,
           "info_percentage": 0,
           "relations_percentage": 0,
           "specs_percentage": 0,
           "tables_percentage": 0
       }
       
       try:
           # Hitta alla resultatfiler (i olika resultatkataloger)
           result_dirs = ["validated", "unvalidated", "corrected"]
           result_files = []
           
           for dir_name in result_dirs:
               dir_path = self.output_dir / dir_name
               if dir_path.exists():
                   result_files.extend(list(dir_path.glob("*.json")))
           
           if not result_files:
               return stats
           
           # Räkna totalt antal produkter
           stats["total_products"] = len(result_files)
           
           # Analysera varje resultatfil
           for file_path in result_files:
               try:
                   with open(file_path, 'r', encoding='utf-8') as f:
                       result = json.load(f)
                   
                   # Räkna produkter med olika typer av data
                   if "product_info" in result:
                       stats["products_with_info"] += 1
                   
                   if "relations" in result and isinstance(result["relations"], dict) and "relations" in result["relations"]:
                       relations = result["relations"]["relations"]
                       if relations and len(relations) > 0:
                           stats["products_with_relations"] += 1
                           stats["total_relations"] += len(relations)
                   
                   if "specifications" in result and isinstance(result["specifications"], dict) and "specifications" in result["specifications"]:
                       specs = result["specifications"]["specifications"]
                       if specs and len(specs) > 0:
                           stats["products_with_specs"] += 1
                           stats["total_specs"] += len(specs)
                   
                   if "data_tables" in result and isinstance(result["data_tables"], dict) and "data_tables" in result["data_tables"]:
                       tables = result["data_tables"]["data_tables"]
                       if tables and len(tables) > 0:
                           stats["products_with_tables"] += 1
                           stats["total_tables"] += len(tables)
               
               except Exception as e:
                   self.logger.warning(f"Kunde inte analysera resultatfil {file_path}: {str(e)}")
           
           # Beräkna procentandelar
           if stats["total_products"] > 0:
               stats["info_percentage"] = (stats["products_with_info"] / stats["total_products"]) * 100
               stats["relations_percentage"] = (stats["products_with_relations"] / stats["total_products"]) * 100
               stats["specs_percentage"] = (stats["products_with_specs"] / stats["total_products"]) * 100
               stats["tables_percentage"] = (stats["products_with_tables"] / stats["total_products"]) * 100
       
       except Exception as e:
           self.logger.error(f"Fel vid generering av extraktionsstatistik: {str(e)}")
       
       return stats

   def _generate_markdown_report(self, report: Dict[str, Any]) -> str:
       """
       Genererar en läsbar Markdown-rapport
       
       Args:
           report: Rapportdata
           
       Returns:
           str: Markdown-formaterad rapport
       """
       summary = report["summary"]
       
       md = [
           "# Slutrapport för LLM-baserad Produktinformationsextraktion",
           "",
           f"Tidpunkt: {report['timestamp']}",
           "",
           "## Sammanfattning",
           "",
           f"- **Totalt antal bearbetade jobb:** {summary['total_jobs_processed']}",
           f"- **Lyckade jobb:** {summary['total_jobs_succeeded']} ({summary['success_rate']:.2f}%)",
           f"- **Misslyckade jobb:** {summary['total_jobs_failed']}",
           f"- **Total bearbetningstid:** {summary['total_processing_time']:.2f} sekunder",
           f"- **Genomsnittlig bearbetningstid per jobb:** {summary['average_processing_time']:.2f} sekunder",
           f"- **Antal bearbetade batcher:** {summary['total_batches_processed']}",
           f"- **Totalt antal produkter i kö:** {summary['total_products_enqueued']}",
           "",
           "## Extraktionsstatistik",
           "",
       ]
       
       # Lägg till statistik för den nya strukturen
       if "extraction_stats" in report:
           extraction_stats = report.get("extraction_stats", {})
           md.extend([
               f"- **Produkter med produktinformation:** {extraction_stats.get('products_with_info', 0)} ({extraction_stats.get('info_percentage', 0):.1f}%)",
               f"- **Produkter med kompatibilitetsrelationer:** {extraction_stats.get('products_with_relations', 0)} ({extraction_stats.get('relations_percentage', 0):.1f}%)",
               f"- **Produkter med tekniska specifikationer:** {extraction_stats.get('products_with_specs', 0)} ({extraction_stats.get('specs_percentage', 0):.1f}%)",
               f"- **Produkter med datatabeller:** {extraction_stats.get('products_with_tables', 0)} ({extraction_stats.get('tables_percentage', 0):.1f}%)",
               f"- **Totalt antal extraherade relationer:** {extraction_stats.get('total_relations', 0)}",
               f"- **Totalt antal extraherade specifikationer:** {extraction_stats.get('total_specs', 0)}",
               f"- **Totalt antal extraherade datatabeller:** {extraction_stats.get('total_tables', 0)}",
               "",
           ])
       
       # Fortsätt med resten av rapporten 
       md.extend([
           "## Köstatus",
           "",
           f"- **Totalt antal jobb:** {report['queue']['total_jobs']}",
           f"- **Aktiva jobb:** {report['queue']['active_jobs']}",
           f"- **Slutförda jobb:** {report['queue']['completed_jobs']}",
           f"- **Misslyckade jobb:** {report['queue']['failed_jobs']}",
           f"- **Pausade jobb:** {report['queue']['paused_jobs']}",
           f"- **Väntande jobb:** {report['queue']['pending_jobs']}",
           "",
           "## Arbetarstatistik",
           ""
       ])
       
       # Lägg till arbetarstatistik
       for worker in report["workers"]:
           md.append(f"### Arbetare {worker['worker_id']}")
           md.append("")
           md.append(f"- **Status:** {'Pausad' if worker.get('paused', False) else 'Aktiv' if worker.get('alive', False) else 'Inaktiv'}")
           md.append(f"- **Bearbetade jobb:** {worker['jobs_processed']}")
           md.append(f"- **Lyckade jobb:** {worker['jobs_succeeded']}")
           md.append(f"- **Misslyckade jobb:** {worker['jobs_failed']}")
           md.append(f"- **Total bearbetningstid:** {worker['total_processing_time']:.2f} sekunder")
           
           if worker['jobs_processed'] > 0:
               avg_time = worker['total_processing_time'] / worker['jobs_processed']
               md.append(f"- **Genomsnittlig bearbetningstid per jobb:** {avg_time:.2f} sekunder")
           
           md.append("")
       
       # Lägg till batch-processor statistik
       md.append("## Batch-processor statistik")
       md.append("")
       md.append(f"- **Bearbetade batcher:** {report['batch_processor']['batches_processed']}")
       md.append(f"- **Slutförda batcher:** {report['batch_processor'].get('batches_completed', 0)}")
       md.append(f"- **Slutföringsgrad:** {report['batch_processor'].get('completion_rate', 0):.1f}%")
       md.append(f"- **Totalt antal produkter:** {report['batch_processor']['total_products']}")
       md.append(f"- **Produkter i kö:** {report['batch_processor']['enqueued_products']}")
       md.append(f"- **Överhoppade produkter:** {report['batch_processor']['skipped_products']}")
       md.append(f"- **Fel:** {report['batch_processor']['errors']}")
       md.append("")
       
       # Lägg till prompt-statistik om tillgänglig
       if "prompt_stats" in report and report["prompt_stats"]:
           prompt_stats = report["prompt_stats"]
           md.append("## Promptstatistik")
           md.append("")
           md.append(f"- **Totalt antal promptmallar:** {prompt_stats.get('total_prompts', 0)}")
           
           # Prompttyper
           if "by_type" in prompt_stats and prompt_stats["by_type"]:
               md.append("\n### Prompttyper")
               md.append("")
               for prompt_type, count in prompt_stats["by_type"].items():
                   md.append(f"- **{prompt_type}:** {count}")
               md.append("")
           
           # Populära taggar
           if "top_tags" in prompt_stats and prompt_stats["top_tags"]:
               md.append("### Populära taggar")
               md.append("")
               for tag_info in prompt_stats["top_tags"]:
                   md.append(f"- **{tag_info['tag']}:** {tag_info['count']}")
               md.append("")
           
           # Cachestatistik
           if "cache" in prompt_stats and prompt_stats["cache"].get("enabled", False):
               cache = prompt_stats["cache"]
               md.append("### Promptcachestatistik")
               md.append("")
               md.append(f"- **Cache-storlek:** {cache.get('cache_size', 0)}/{cache.get('max_cache_size', 0)}")
               md.append(f"- **Träffar:** {cache.get('hits', 0)}")
               md.append(f"- **Missar:** {cache.get('misses', 0)}")
               hit_rate = cache.get('hit_rate', 0)
               md.append(f"- **Träfffrekvens:** {hit_rate:.2f} ({hit_rate*100:.1f}%)")
               md.append("")
       
       return "\n".join(md)
   
   def _generate_final_report(self) -> None:
       """Genererar en slutrapport över hela bearbetningen"""
       timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       report_file = self.output_dir / "reports" / f"final_report_{timestamp}.json"
       
       # Samla statistik
       worker_stats = [worker.get_stats() for worker in self.workers]
       queue_status = self.processing_queue.get_queue_status()
       batch_stats = self.batch_processor.get_stats()
       
       # Generera extraktionsstatistik
       extraction_stats = self._generate_extraction_stats()
       
       # Hämta prompt-statistik om tillgänglig
       prompt_stats = self.prompt_manager.get_usage_statistics() if hasattr(self.prompt_manager, 'get_usage_statistics') else {}
       
       # Beräkna summor
       total_jobs_processed = sum(stats["jobs_processed"] for stats in worker_stats)
       total_jobs_succeeded = sum(stats["jobs_succeeded"] for stats in worker_stats)
       total_jobs_failed = sum(stats["jobs_failed"] for stats in worker_stats)
       total_processing_time = sum(stats["total_processing_time"] for stats in worker_stats)
       
       # Skapa rapport
       report = {
           "timestamp": datetime.now().isoformat(),
           "summary": {
               "total_jobs_processed": total_jobs_processed,
               "total_jobs_succeeded": total_jobs_succeeded,
               "total_jobs_failed": total_jobs_failed,
               "success_rate": (total_jobs_succeeded / total_jobs_processed * 100) if total_jobs_processed > 0 else 0,
               "total_processing_time": total_processing_time,
               "average_processing_time": (total_processing_time / total_jobs_processed) if total_jobs_processed > 0 else 0,
               "total_batches_processed": batch_stats["batches_processed"],
               "total_products_enqueued": batch_stats["enqueued_products"]
           },
           "extraction_stats": extraction_stats,
           "workers": worker_stats,
           "queue": queue_status,
           "batch_processor": batch_stats,
           "prompt_stats": prompt_stats
       }
       
       # Spara rapporten
       try:
           with open(report_file, 'w', encoding='utf-8') as f:
               json.dump(report, f, ensure_ascii=False, indent=2)
           
           self.logger.info(f"Sparade slutrapport till {report_file}")
           
           # Skapa även en läsbar version
           markdown_report = self._generate_markdown_report(report)
           md_file = self.output_dir / "reports" / f"final_report_{timestamp}.md"
           
           with open(md_file, 'w', encoding='utf-8') as f:
               f.write(markdown_report)
           
           self.logger.info(f"Sparade läsbar slutrapport till {md_file}")
           
           # Visa i visualizer om tillgänglig
           if self.visualizer:
               self.visualizer.display_markdown(markdown_report)
       
       except Exception as e:
           self.logger.error(f"Fel vid sparande av slutrapport: {str(e)}")

   def visualize_prompt_performance(self) -> None:
       """Visualiserar prestanda för promptmallar"""
       if hasattr(self.prompt_manager, 'visualize_prompt_performance') and self.visualizer:
           self.prompt_manager.visualize_prompt_performance(self.visualizer)
       else:
           self.logger.warning("Prompthanterare eller visualiserare saknas för prestandavisualisering")
   
   def generate_html_dashboard(self, output_path: Union[str, Path] = None) -> Path:
       """
       Genererar en interaktiv HTML-dashboard för att överblicka bearbetningsstatus
       
       Args:
           output_path: Sökväg att spara dashboarden till (default: reports/dashboard_{timestamp}.html)
           
       Returns:
           Path: Sökväg till den genererade dashboarden
       """
       if output_path is None:
           timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
           output_path = self.output_dir / "reports" / f"dashboard_{timestamp}.html"
       else:
           output_path = Path(output_path)
       
       # Samla statusdata för dashboard
       status_data = self.get_status()
       extraction_stats = self._generate_extraction_stats()
       
       try:
           # Skapa HTML-innehåll
           html_content = f"""
           <!DOCTYPE html>
           <html lang="sv">
           <head>
               <meta charset="UTF-8">
               <meta name="viewport" content="width=device-width, initial-scale=1.0">
               <title>Produktprocessor Dashboard</title>
               <style>
                   body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                   .dashboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
                   .card {{ background: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); padding: 20px; }}
                   .stat {{ font-size: 36px; font-weight: bold; margin-bottom: 10px; }}
                   .stat-label {{ color: #777; font-size: 14px; }}
                   .progress-bar {{ height: 10px; background: #e0e0e0; border-radius: 5px; margin-top: 15px; }}
                   .progress-value {{ height: 100%; border-radius: 5px; background: #4caf50; }}
                   .worker-card {{ margin-bottom: 15px; padding: 10px; border-left: 4px solid #2196f3; }}
                   .worker-active {{ border-left-color: #4caf50; }}
                   .worker-paused {{ border-left-color: #ffc107; }}
                   .worker-inactive {{ border-left-color: #f44336; }}
                   .section-title {{ margin-top: 30px; margin-bottom: 15px; color: #333; }}
                   table {{ width: 100%; border-collapse: collapse; }}
                   th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                   th {{ background-color: #f2f2f2; }}
               </style>
           </head>
           <body>
               <h1>LLM-baserad Produktinformationsextrahering - Dashboard</h1>
               <p>Genererad: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
               
               <div class="dashboard">
                   <div class="card">
                       <div class="stat">{status_data['processor_stats']['processed_count']}</div>
                       <div class="stat-label">Bearbetade produkter</div>
                       <div class="progress-bar">
                           <div class="progress-value" style="width: {status_data['processor_stats'].get('success_rate', 0)}%;"></div>
                       </div>
                       <div class="stat-label">{status_data['processor_stats'].get('success_rate', 0):.1f}% framgångsrika</div>
                   </div>
                   
                   <div class="card">
                       <div class="stat">{status_data['queue']['total_jobs']}</div>
                       <div class="stat-label">Totalt antal jobb</div>
                       <div class="stat-label">Aktiva: {status_data['queue']['active_jobs']}</div>
                       <div class="stat-label">Slutförda: {status_data['queue']['completed_jobs']}</div>
                       <div class="stat-label">Misslyckade: {status_data['queue']['failed_jobs']}</div>
                       <div class="stat-label">Pausade: {status_data['queue']['paused_jobs']}</div>
                       <div class="stat-label">Väntande: {status_data['queue']['pending_jobs']}</div>
                   </div>
                   
                   <div class="card">
                       <div class="stat">{status_data['batch_processor']['batches_processed']}</div>
                       <div class="stat-label">Bearbetade batcher</div>
                       <div class="progress-bar">
                           <div class="progress-value" style="width: {status_data['batch_processor'].get('completion_rate', 0)}%;"></div>
                       </div>
                       <div class="stat-label">{status_data['batch_processor'].get('completion_rate', 0):.1f}% slutförda</div>
                   </div>
                   
                   <div class="card">
                       <div class="stat">{extraction_stats['total_relations']}</div>
                       <div class="stat-label">Extraherade relationer</div>
                       <div class="stat-label">från {extraction_stats['products_with_relations']} produkter ({extraction_stats['relations_percentage']:.1f}%)</div>
                   </div>
                   
                   <div class="card">
                       <div class="stat">{extraction_stats['total_specs']}</div>
                       <div class="stat-label">Extraherade specifikationer</div>
                       <div class="stat-label">från {extraction_stats['products_with_specs']} produkter ({extraction_stats['specs_percentage']:.1f}%)</div>
                   </div>
                   
                   <div class="card">
                       <div class="stat">{extraction_stats['total_tables']}</div>
                       <div class="stat-label">Extraherade datatabeller</div>
                       <div class="stat-label">från {extraction_stats['products_with_tables']} produkter ({extraction_stats['tables_percentage']:.1f}%)</div>
                   </div>
               </div>
               
               <h2 class="section-title">Arbetarstatus</h2>
               <div>
           """
           
           # Lägg till arbetarkort
           for worker in status_data['workers']:
               worker_class = "worker-active"
               if worker.get('paused', False):
                   worker_class = "worker-paused"
               elif not worker.get('alive', False):
                   worker_class = "worker-inactive"
               
               html_content += f"""
                   <div class="worker-card {worker_class}">
                       <h3>Arbetare {worker['worker_id']}</h3>
                       <div>Status: {
                           'Pausad' if worker.get('paused', False) 
                           else 'Bearbetar' if worker.get('processing_job', False) 
                           else 'Väntar' if worker.get('alive', False) 
                           else 'Inaktiv'
                       }</div>
                       <div>Bearbetade: {worker['jobs_processed']} jobb</div>
                       <div>Lyckade: {worker['jobs_succeeded']} ({
                           (worker['jobs_succeeded'] / worker['jobs_processed'] * 100) if worker['jobs_processed'] > 0 else 0
                       :.1f}%)</div>
                       <div>Senast aktiv: {worker.get('last_active', 'N/A')}</div>
                   </div>
               """
           
           # Avsluta HTML
           html_content += """
               </div>
               
               <script>
                   // Auto-refresh var 30:e sekund
                   setTimeout(function() {
                       location.reload();
                   }, 30000);
               </script>
           </body>
           </html>
           """
           
           # Spara HTML-fil
           with open(output_path, 'w', encoding='utf-8') as f:
               f.write(html_content)
           
           self.logger.info(f"Genererade HTML-dashboard till {output_path}")
           return output_path
           
       except Exception as e:
           self.logger.error(f"Fel vid generering av HTML-dashboard: {str(e)}")
           return None

   def generate_data_report(self, output_format: str = "json") -> Path:
       """
       Genererar en datarapport över alla extraherade data
       
       Args:
           output_format: Formatet på rapporten ("json" eller "csv")
           
       Returns:
           Path: Sökväg till den genererade datarapporten
       """
       timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       
       if output_format.lower() == "json":
           output_path = self.output_dir / "reports" / f"data_report_{timestamp}.json"
       else:
           output_path = self.output_dir / "reports" / f"data_report_{timestamp}.csv"
       
       try:
           # Samla in strukturerad data
           structured_dir = self.output_dir / "structured"
           
           if not structured_dir.exists():
               self.logger.warning("Strukturerad datakatalog existerar inte")
               return None
           
           # Hitta alla indexfiler
           index_files = list(structured_dir.glob("*/index.json"))
           
           if not index_files:
               self.logger.warning("Inga indexfiler hittades i strukturerad datakatalog")
               return None
           
           # Samla data
           data_report = []
           
           for index_file in index_files:
               try:
                   with open(index_file, 'r', encoding='utf-8') as f:
                       index_data = json.load(f)
                   
                   product_id = index_data.get("product_id")
                   product_title = index_data.get("product_title", "")
                   available_data = index_data.get("available_data", {})
                   file_paths = index_data.get("file_paths", {})
                   
                   # Skapa en grundläggande datapost
                   product_data = {
                       "product_id": product_id,
                       "product_title": product_title,
                       "has_product_info": available_data.get("product_info", False),
                       "has_relations": available_data.get("relations", False),
                       "has_specifications": available_data.get("specifications", False),
                       "has_data_tables": available_data.get("data_tables", False)
                   }
                   
                   # Lägg till produktinfo om tillgänglig
                   if available_data.get("product_info", False) and "product" in file_paths:
                       product_info_path = structured_dir / file_paths["product"]
                       if product_info_path.exists():
                           try:
                               with open(product_info_path, 'r', encoding='utf-8') as f:
                                   product_info = json.load(f)
                               
                               # Lägg till viktig produktinfo
                               product_data["article_number"] = product_info.get("article_number", "")
                               product_data["ean"] = product_info.get("ean", "")
                           except Exception as e:
                               self.logger.debug(f"Kunde inte läsa produktinfo för {product_id}: {str(e)}")
                   
                   # Lägg till antal relationer, specifikationer och tabeller
                   if available_data.get("relations", False) and "compatibility" in file_paths:
                       compat_path = structured_dir / file_paths["compatibility"]
                       if compat_path.exists():
                           try:
                               with open(compat_path, 'r', encoding='utf-8') as f:
                                   compat_data = json.load(f)
                               
                               product_data["relations_count"] = len(compat_data.get("relations", []))
                           except Exception as e:
                               self.logger.debug(f"Kunde inte läsa relationer för {product_id}: {str(e)}")
                   else:
                       product_data["relations_count"] = 0
                   
                   if available_data.get("specifications", False) and "technical" in file_paths:
                       specs_path = structured_dir / file_paths["technical"]
                       if specs_path.exists():
                           try:
                               with open(specs_path, 'r', encoding='utf-8') as f:
                                   specs_data = json.load(f)
                               
                               product_data["specifications_count"] = len(specs_data.get("specifications", []))
                           except Exception as e:
                               self.logger.debug(f"Kunde inte läsa specifikationer för {product_id}: {str(e)}")
                   else:
                       product_data["specifications_count"] = 0
                   
                   if available_data.get("data_tables", False) and "data_tables" in file_paths:
                       tables_path = structured_dir / file_paths["data_tables"]
                       if tables_path.exists():
                           try:
                               with open(tables_path, 'r', encoding='utf-8') as f:
                                   tables_data = json.load(f)
                               
                               product_data["data_tables_count"] = len(tables_data.get("data_tables", []))
                           except Exception as e:
                               self.logger.debug(f"Kunde inte läsa datatabeller för {product_id}: {str(e)}")
                   else:
                       product_data["data_tables_count"] = 0
                   
                   # Lägg till i rapport
                   data_report.append(product_data)
               
               except Exception as e:
                   self.logger.warning(f"Kunde inte bearbeta indexfil {index_file}: {str(e)}")
           
           # Spara rapporten i önskat format
           if output_format.lower() == "json":
               with open(output_path, 'w', encoding='utf-8') as f:
                   json.dump(data_report, f, ensure_ascii=False, indent=2)
           else:
               # Skapa CSV
               if data_report:
                   with open(output_path, 'w', encoding='utf-8', newline='') as f:
                       writer = csv.DictWriter(f, fieldnames=data_report[0].keys())
                       writer.writeheader()
                       writer.writerows(data_report)
           
           self.logger.info(f"Genererade datarapport med {len(data_report)} produkter till {output_path}")
           return output_path
           
       except Exception as e:
           self.logger.error(f"Fel vid generering av datarapport: {str(e)}")
           return None

## ===================================
##   Divers hantering och kontroll
## ===================================

   def cleanup_output_dir(self, keep_days: int = 30, only_temp: bool = True) -> Dict[str, int]:
       """
       Rensar gamla filer från utdatakatalogen
       
       Args:
           keep_days: Antal dagar att behålla filer
           only_temp: Om endast temporära filer ska rensas
           
       Returns:
           Dict[str, int]: Antal borttagna filer per katalog
       """
       # Beräkna cut-off-datum
       cutoff_date = datetime.now() - timedelta(days=keep_days)
       
       # Initialisera resultaträknare
       removed_count = {
           "cache": 0,
           "reports": 0,
           "batch_reports": 0,
           "unvalidated": 0,
           "validated": 0,
           "corrected": 0,
           "failed": 0,
           "empty": 0,
           "state": 0,
           "total": 0
       }
       
       try:
           # Rensa cachekatalog (alltid temporär)
           cache_dir = self.output_dir / "cache"
           if cache_dir.exists():
               for cache_file in cache_dir.glob("*_cache.json"):
                   try:
                       file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                       if file_mtime < cutoff_date:
                           cache_file.unlink()
                           removed_count["cache"] += 1
                           removed_count["total"] += 1
                   except Exception as e:
                       self.logger.warning(f"Kunde inte ta bort cachefil {cache_file}: {str(e)}")
           
           # Hantera andra kataloger baserat på only_temp-flaggan
           if not only_temp:
               # Katalogmappning för icke-temp kataloger
               dirs_to_clean = {
                   "reports": self.output_dir / "reports",
                   "batch_reports": self.output_dir / "batch_reports",
                   "unvalidated": self.output_dir / "unvalidated", 
                   "validated": self.output_dir / "validated",
                   "corrected": self.output_dir / "corrected",
                   "failed": self.output_dir / "failed",
                   "empty": self.output_dir / "empty"
               }
               
               # Rensa varje katalog
               for dir_key, dir_path in dirs_to_clean.items():
                   if dir_path.exists():
                       for file in dir_path.glob("*.json"):
                           try:
                               file_mtime = datetime.fromtimestamp(file.stat().st_mtime)
                               if file_mtime < cutoff_date:
                                   file.unlink()
                                   removed_count[dir_key] += 1
                                   removed_count["total"] += 1
                           except Exception as e:
                               self.logger.warning(f"Kunde inte ta bort fil {file}: {str(e)}")
               
               # Hantera tillståndsfiler
               state_dir = self.output_dir / "state"
               if state_dir.exists():
                   for state_file in state_dir.glob("*.json"):
                       try:
                           file_mtime = datetime.fromtimestamp(state_file.stat().st_mtime)
                           if file_mtime < cutoff_date:
                               state_file.unlink()
                               removed_count["state"] += 1
                               removed_count["total"] += 1
                       except Exception as e:
                           self.logger.warning(f"Kunde inte ta bort tillståndsfil {state_file}: {str(e)}")
           
           self.logger.info(f"Rensade totalt {removed_count['total']} filer äldre än {keep_days} dagar")
           
       except Exception as e:
           self.logger.error(f"Fel vid rensning av utdatakatalog: {str(e)}")
       
       return removed_count
   
   def export_product_data(self, product_id: str, output_format: str = "json", 
                         output_path: Union[str, Path] = None) -> Optional[Path]:
       """
       Exporterar all data för en specifik produkt
       
       Args:
           product_id: ID för produkten att exportera
           output_format: Formatet för exporten ("json" eller "md")
           output_path: Sökväg att exportera till (valfritt)
           
       Returns:
           Optional[Path]: Sökväg till exporterad fil eller None vid fel
       """
       # Bestäm utdatasökväg
       if output_path is None:
           timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
           if output_format.lower() == "json":
               output_path = self.output_dir / "exports" / f"{product_id}_{timestamp}.json"
           else:
               output_path = self.output_dir / "exports" / f"{product_id}_{timestamp}.md"
       else:
           output_path = Path(output_path)
       
       # Skapa katalog om den inte finns
       output_path.parent.mkdir(exist_ok=True, parents=True)
       
       try:
           # Hitta produktdata i structured-katalogen
           structured_dir = self.output_dir / "structured" / product_id
           
           if not structured_dir.exists():
               self.logger.warning(f"Ingen strukturerad data hittades för produkt {product_id}")
               return None
           
           # Läs indexfilen
           index_path = structured_dir / "index.json"
           
           if not index_path.exists():
               self.logger.warning(f"Ingen indexfil hittades för produkt {product_id}")
               return None
           
           with open(index_path, 'r', encoding='utf-8') as f:
               index_data = json.load(f)
           
           # Samla all data
           product_data = {
               "product_id": product_id,
               "product_title": index_data.get("product_title", ""),
               "generated_at": datetime.now().isoformat(),
               "product_info": None,
               "relations": None,
               "specifications": None,
               "data_tables": None
           }
           
           # Läs produktinfo
           if index_data.get("available_data", {}).get("product_info", False):
               product_path = structured_dir / "product_info.json"
               if product_path.exists():
                   with open(product_path, 'r', encoding='utf-8') as f:
                       product_data["product_info"] = json.load(f)
           
           # Läs relations
           if index_data.get("available_data", {}).get("relations", False):
               compat_path = structured_dir / "compatibility.json"
               if compat_path.exists():
                   with open(compat_path, 'r', encoding='utf-8') as f:
                       product_data["relations"] = json.load(f)
           
           # Läs specifications
           if index_data.get("available_data", {}).get("specifications", False):
               specs_path = structured_dir / "technical_specs.json"
               if specs_path.exists():
                   with open(specs_path, 'r', encoding='utf-8') as f:
                       product_data["specifications"] = json.load(f)
           
           # Läs data_tables
           if index_data.get("available_data", {}).get("data_tables", False):
               tables_path = structured_dir / "data_tables.json"
               if tables_path.exists():
                   with open(tables_path, 'r', encoding='utf-8') as f:
                       product_data["data_tables"] = json.load(f)
           
           # Exportera i valt format
           if output_format.lower() == "json":
               with open(output_path, 'w', encoding='utf-8') as f:
                   json.dump(product_data, f, ensure_ascii=False, indent=2)
           else:
               # Skapa markdown-export
               markdown_content = self._generate_product_markdown(product_data)
               
               with open(output_path, 'w', encoding='utf-8') as f:
                   f.write(markdown_content)
           
           self.logger.info(f"Exporterade data för produkt {product_id} till {output_path}")
           return output_path
           
       except Exception as e:
           self.logger.error(f"Fel vid export av produkt {product_id}: {str(e)}")
           return None
   
   def _generate_product_markdown(self, product_data: Dict[str, Any]) -> str:
       """
       Genererar en läsbar markdown-version av produktdata
       
       Args:
           product_data: Produktdata att formatera
           
       Returns:
           str: Markdown-formaterad produktdata
       """
       lines = [
           f"# {product_data.get('product_title', 'Produkt ' + product_data['product_id'])}",
           "",
           f"Produkt-ID: {product_data['product_id']}  ",
           f"Genererad: {product_data['generated_at']}",
           ""
       ]
       
       # Lägg till produktinfo
       if product_data["product_info"]:
           lines.append("## Produktinformation")
           lines.append("")
           
           product_info = product_data["product_info"]
           
           # Skapa tabell med grundläggande attribut
           lines.append("| Egenskap | Värde |")
           lines.append("|----------|-------|")
           
           for key, value in {
               "Artikelnummer": product_info.get("article_number", ""),
               "EAN": product_info.get("ean", ""),
               "SKU": product_info.get("sku", ""),
               "Tillverkare": product_info.get("manufacturer", "")
           }.items():
               if value:
                   lines.append(f"| {key} | {value} |")
           
           lines.append("")
       
       # Lägg till relationer
       if product_data["relations"] and "relations" in product_data["relations"]:
           lines.append("## Kompatibilitetsrelationer")
           lines.append("")
           
           relations = product_data["relations"]["relations"]
           
           if not relations:
               lines.append("*Inga kompatibilitetsrelationer hittades.*")
               lines.append("")
           else:
               # Gruppera relationer efter typ
               relation_types = {}
               
               for relation in relations:
                   relation_type = relation.get("relation_type", "Okänd")
                   if relation_type not in relation_types:
                       relation_types[relation_type] = []
                   relation_types[relation_type].append(relation)
               
               # Skapa en sektion för varje relationstyp
               for relation_type, type_relations in relation_types.items():
                   lines.append(f"### {relation_type}")
                   lines.append("")
                   
                   for relation in type_relations:
                       # Formatera relaterad produktinformation
                       related_product = relation.get("related_product", {})
                       
                       if isinstance(related_product, dict):
                           name = related_product.get("name", "")
                           article = related_product.get("article_number", "")
                           ean = related_product.get("ean", "")
                           
                           related_info = f"**{name}**"
                           
                           if article:
                               related_info += f" (Art.nr: {article})"
                           if ean:
                               related_info += f" (EAN: {ean})"
                       else:
                           related_info = f"**{related_product}**"
                       
                       lines.append(f"- {related_info}")
                       
                       # Lägg till kontext om tillgängligt
                       if "context" in relation and relation["context"]:
                           lines.append(f"  *{relation['context']}*")
                       
                       lines.append("")
       
       # Lägg till specifikationer
       if product_data["specifications"] and "specifications" in product_data["specifications"]:
           lines.append("## Tekniska specifikationer")
           lines.append("")
           
           specifications = product_data["specifications"]["specifications"]
           
           if not specifications:
               lines.append("*Inga tekniska specifikationer hittades.*")
               lines.append("")
           else:
               # Gruppera specifikationer efter kategori
               categories = {}
               
               for spec in specifications:
                   category = spec.get("category", "Okänd")
                   if category not in categories:
                       categories[category] = []
                   categories[category].append(spec)
               
               # Skapa en sektion för varje kategori
               for category, category_specs in categories.items():
                   lines.append(f"### {category}")
                   lines.append("")
                   
                   # Tabell för specifikationer i denna kategori
                   lines.append("| Egenskap | Värde | Enhet |")
                   lines.append("|----------|-------|-------|")
                   
                   for spec in category_specs:
                       name = spec.get("name", "")
                       value = spec.get("raw_value", "")
                       unit = spec.get("unit", "")
                       
                       lines.append(f"| {name} | {value} | {unit} |")
                   
                   lines.append("")
       
       # Lägg till datatabeller
       if product_data["data_tables"] and "data_tables" in product_data["data_tables"]:
           lines.append("## Datatabeller")
           lines.append("")
           
           data_tables = product_data["data_tables"]["data_tables"]
           
           if not data_tables:
               lines.append("*Inga datatabeller hittades.*")
               lines.append("")
           else:
               for i, table in enumerate(data_tables):
                   title = table.get("title", f"Tabell {i+1}")
                   lines.append(f"### {title}")
                   lines.append("")
                   
                   # Lägg till beskrivning om tillgänglig
                   if "description" in table and table["description"]:
                       lines.append(f"*{table['description']}*")
                       lines.append("")
                   
                   # Lägg till tabellrader
                   if "rows" in table and table["rows"]:
                       lines.append("| Egenskap | Värde |")
                       lines.append("|----------|-------|")
                       
                       for row in table["rows"]:
                           if isinstance(row, dict) and "property" in row and "value" in row:
                               lines.append(f"| {row['property']} | {row['value']} |")
                       
                       lines.append("")
       
       return "\n".join(lines)
   
   def export_batch_data(self, batch_id: str, output_format: str = "zip") -> Optional[Path]:
       """
       Exporterar all data för en specifik batch
       
       Args:
           batch_id: ID för batchen att exportera
           output_format: Formatet för exporten ("zip" eller "dir")
           
       Returns:
           Optional[Path]: Sökväg till exporterad fil/katalog eller None vid fel
       """
       # Kontrollera om batchen finns
       if batch_id not in self.batch_processor.batch_registry:
           self.logger.warning(f"Ingen batch med ID {batch_id} hittades")
           return None
       
       batch_info = self.batch_processor.batch_registry[batch_id]
       batch_name = batch_info.get("batch_name", "unknown_batch")
       
       # Bestäm utdatasökväg
       timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       
       if output_format.lower() == "zip":
           output_path = self.output_dir / "exports" / f"{batch_name}_{timestamp}.zip"
       else:
           output_path = self.output_dir / "exports" / f"{batch_name}_{timestamp}"
       
       # Skapa katalog om den inte finns
       if output_format.lower() != "zip":
           output_path.mkdir(exist_ok=True, parents=True)
       else:
           output_path.parent.mkdir(exist_ok=True, parents=True)
       
       try:
           # Exportera varje produkt i batchen
           job_ids = batch_info.get("job_ids", [])
           exported_products = []
           
           for job_id in job_ids:
               job = self.processing_queue.get_job(job_id)
               
               if job:
                   product_id = job.product_id
                   
                   if output_format.lower() == "zip":
                       # För zip, exportera till temporär katalog
                       temp_dir = self.output_dir / "temp" / batch_name
                       temp_dir.mkdir(exist_ok=True, parents=True)
                       
                       # Exportera till temporär fil
                       temp_path = temp_dir / f"{product_id}.json"
                       result = self.export_product_data(product_id, "json", temp_path)
                       
                       if result:
                           exported_products.append(product_id)
                   else:
                       # Exportera direkt till utdatakatalogen
                       result = self.export_product_data(
                           product_id, "json", output_path / f"{product_id}.json"
                       )
                       
                       if result:
                           exported_products.append(product_id)
           
           # För zip, skapa zipfil och ta bort temporär katalog
           if output_format.lower() == "zip" and exported_products:
               import zipfile
               
               temp_dir = self.output_dir / "temp" / batch_name
               
               with zipfile.ZipFile(output_path, 'w') as zip_file:
                   for product_id in exported_products:
                       product_file = temp_dir / f"{product_id}.json"
                       if product_file.exists():
                           zip_file.write(product_file, product_file.name)
               
               # Ta bort temporära filer
               for product_id in exported_products:
                   product_file = temp_dir / f"{product_id}.json"
                   if product_file.exists():
                       product_file.unlink()
               
               # Försök ta bort temporär katalog
               try:
                   temp_dir.rmdir()
               except:
                   pass
           
           self.logger.info(
               f"Exporterade {len(exported_products)} produkter från batch {batch_name} till "
               f"{output_path} i {output_format}-format"
           )
           
           return output_path
           
       except Exception as e:
           self.logger.error(f"Fel vid export av batch {batch_id}: {str(e)}")
           return None
   
   def archive_project(self, path: Union[str, Path] = None, include_raw: bool = False) -> Optional[Path]:
       """
       Arkiverar hela projektet (eller viktiga delar) till en zipfil
       
       Args:
           path: Sökväg till arkivfilen (valfritt)
           include_raw: Om rådata ska inkluderas
           
       Returns:
           Optional[Path]: Sökväg till arkivfilen eller None vid fel
       """
       import zipfile
       
       # Bestäm utdatasökväg
       if path is None:
           timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
           path = self.output_dir.parent / f"project_archive_{timestamp}.zip"
       else:
           path = Path(path)
       
       try:
           # Skapa zipfil
           with zipfile.ZipFile(path, 'w') as zip_file:
               # Lägg till output-kataloger
               for subdir in ["structured", "reports", "batch_reports", "state"]:
                   dir_path = self.output_dir / subdir
                   if dir_path.exists():
                       # Arkivera alla filer i katalogen
                       for file_path in dir_path.glob("**/*"):
                           if file_path.is_file():
                               # Beräkna relativ sökväg för arkivet
                               rel_path = file_path.relative_to(self.output_dir.parent)
                               zip_file.write(file_path, rel_path)
               
               # Lägg till konfigurationsfiler
               config_dir = self.config.config_dir
               if config_dir and config_dir.exists():
                   for config_file in config_dir.glob("*.yaml"):
                       if config_file.is_file():
                           # Beräkna relativ sökväg för arkivet
                           rel_path = Path("config") / config_file.name
                           zip_file.write(config_file, rel_path)
               
               # Inkludera rådata om begärt
               if include_raw:
                   for raw_dir in ["validated", "unvalidated", "corrected"]:
                       dir_path = self.output_dir / raw_dir
                       if dir_path.exists():
                           # Arkivera alla filer i katalogen
                           for file_path in dir_path.glob("**/*"):
                               if file_path.is_file():
                                   # Beräkna relativ sökväg för arkivet
                                   rel_path = file_path.relative_to(self.output_dir.parent)
                                   zip_file.write(file_path, rel_path)
           
           self.logger.info(f"Arkiverade projektet till {path}")
           return path
           
       except Exception as e:
           self.logger.error(f"Fel vid arkivering av projekt: {str(e)}")
           return None


## ===================================
##   Inställningar och konfiguration
## ===================================

   def update_config(self, new_config: Dict[str, Any]) -> bool:
       """
       Uppdaterar konfiguration under körning
       
       Args:
           new_config: Ny konfiguration att applicera
           
       Returns:
           bool: True om uppdateringen lyckades, annars False
       """
       try:
           # Uppdatera global konfiguration
           self.config.update(new_config)
           
           # Uppdatera LLM-konfiguration om specificerad
           if "llm" in new_config:
               self.llm_client.update_config(new_config["llm"])
           
           # Uppdatera processorns konfiguration om specificerad
           if "extraction" in new_config:
               self.processor.update_config({"extraction": new_config["extraction"]})
           
           # Uppdatera arbetarnas konfiguration om specificerad
           if "workflow" in new_config:
               for worker in self.workers:
                   worker.config.update(new_config["workflow"])
           
           self.logger.info("Konfiguration uppdaterad under körning")
           return True
       except Exception as e:
           self.logger.error(f"Fel vid uppdatering av konfiguration: {str(e)}")
           return False
   
   def export_config(self, path: Union[str, Path] = None) -> Optional[Path]:
       """
       Exporterar nuvarande konfiguration till en YAML-fil
       
       Args:
           path: Sökväg att exportera till (valfritt)
           
       Returns:
           Optional[Path]: Sökväg till exporterad konfiguration eller None vid fel
       """
       try:
           import yaml
           
           # Bestäm utdatasökväg
           if path is None:
               timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
               path = self.output_dir / "config" / f"config_export_{timestamp}.yaml"
           else:
               path = Path(path)
           
           # Skapa katalog om den inte finns
           path.parent.mkdir(exist_ok=True, parents=True)
           
           # Hämta konfiguration
           config_export = self.config.get_all()
           
           # Exportera till YAML
           with open(path, 'w', encoding='utf-8') as f:
               yaml.dump(config_export, f, default_flow_style=False, sort_keys=False)
           
           self.logger.info(f"Exporterade konfiguration till {path}")
           return path
           
       except Exception as e:
           self.logger.error(f"Fel vid export av konfiguration: {str(e)}")
           return None
   
   def reload_config(self, path: Union[str, Path] = None) -> bool:
       """
       Laddar om konfiguration från fil
       
       Args:
           path: Sökväg att ladda från (valfritt, använder standardkonfigurationen annars)
           
       Returns:
           bool: True om omladdningen lyckades, annars False
       """
       try:
           if path is None:
               # Ladda standardkonfigurationen igen
               success = self.config.reload()
           else:
               # Ladda från angiven sökväg
               success = self.config.load_from_file(path)
           
           if success:
               # Uppdatera komponenter med den nya konfigurationen
               self.update_config(self.config.get_all())
               self.logger.info(f"Laddade om konfiguration {'från ' + str(path) if path else ''}")
           else:
               self.logger.error(f"Kunde inte ladda om konfiguration {'från ' + str(path) if path else ''}")
           
           return success
           
       except Exception as e:
           self.logger.error(f"Fel vid omladdning av konfiguration: {str(e)}")
           return False


## ===================================
##   Hjälpfunktioner och diverse
## ===================================

   def get_prompt_stats(self) -> Dict[str, Any]:
       """
       Hämtar statistik för prompthanteringen
       
       Returns:
           Dict[str, Any]: Promptstatistik
       """
       if not hasattr(self, 'prompt_manager') or not self.prompt_manager:
           return {"error": "Ingen prompthanterare tillgänglig"}
       
       if hasattr(self.prompt_manager, 'get_usage_statistics'):
           return self.prompt_manager.get_usage_statistics()
       
       # Samla grundläggande statistik om get_usage_statistics inte finns
       stats = {
           "total_prompts": len(getattr(self.prompt_manager, 'prompts', [])),
           "by_type": {},
           "top_tags": []
       }
       
       # Räkna mallar per typ om by_type finns
       if hasattr(self.prompt_manager, 'by_type'):
           for prompt_type, prompts in self.prompt_manager.by_type.items():
               stats["by_type"][prompt_type] = len(prompts)
       
       # Räkna mallar per tagg om by_tag finns
       if hasattr(self.prompt_manager, 'by_tag'):
           tag_counts = {}
           for tag, prompts in self.prompt_manager.by_tag.items():
               tag_counts[tag] = len(prompts)
           
           # Hitta de vanligaste taggarna
           top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
           stats["top_tags"] = [{"tag": tag, "count": count} for tag, count in top_tags]
       
       # Lägg till cache-statistik om tillgänglig
       if hasattr(self.prompt_manager, 'use_cache') and self.prompt_manager.use_cache:
           if hasattr(self.prompt_manager, 'get_cache_stats'):
               stats["cache"] = self.prompt_manager.get_cache_stats()
       
       return stats
   
   def run_command(self, command: str, *args, **kwargs) -> Any:
       """
       Kör ett kommando/funktion i arbetsflödeshanteraren
       
       Args:
           command: Kommandot att köra
           *args: Positionsargument till kommandot
           **kwargs: Nyckelordargument till kommandot
           
       Returns:
           Any: Resultatet av kommandot
       """
       if not hasattr(self, command):
           raise ValueError(f"Okänt kommando: {command}")
       
       command_func = getattr(self, command)
       
       if not callable(command_func):
           raise ValueError(f"'{command}' är inte ett körbart kommando")
       
       try:
           return command_func(*args, **kwargs)
       except Exception as e:
           self.logger.error(f"Fel vid körning av kommando '{command}': {str(e)}")
           raise
   
   def get_available_commands(self) -> Dict[str, Any]:
       """
       Returnerar information om tillgängliga kommandon
       
       Returns:
           Dict[str, Any]: Information om tillgängliga kommandon
       """
       commands = {}
       
       # Gå igenom alla attribut
       for attr_name in dir(self):
           # Ignorera privata attribut och icke-callable attribut
           if attr_name.startswith('_') or not callable(getattr(self, attr_name)):
               continue
           
           # Hämta funktionen
           func = getattr(self, attr_name)
           
           # Hämta docstring och parameter-info
           doc = func.__doc__ or "Ingen dokumentation tillgänglig"
           import inspect
           signature = inspect.signature(func)
           
           params = []
           for name, param in signature.parameters.items():
               if name != 'self':
                   param_info = {
                       "name": name,
                       "required": param.default == inspect.Parameter.empty,
                       "default": None if param.default == inspect.Parameter.empty else param.default,
                       "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "any"
                   }
                   params.append(param_info)
           
           commands[attr_name] = {
               "name": attr_name,
               "description": doc.split('\n')[0] if doc else "",
               "params": params,
               "return_type": str(signature.return_annotation) if signature.return_annotation != inspect.Parameter.empty else "any"
           }
       
       return commands
   
   def execute_script(self, script_path: Union[str, Path]) -> None:
       """
       Kör ett Python-skript i arbetsflödeshanterarens kontext
       
       Args:
           script_path: Sökväg till skriptet att köra
       """
       script_path = Path(script_path)
       
       if not script_path.exists():
           raise FileNotFoundError(f"Skriptet {script_path} hittades inte")
       
       self.logger.info(f"Kör skript: {script_path}")
       
       # Skapa variabler som ska vara tillgängliga i skriptet
       workflow_manager = self
       config = self.config
       logger = self.logger
       processor = self.processor
       queue = self.processing_queue
       batch_processor = self.batch_processor
       scheduler = self.scheduler
       workers = self.workers
       
       # Läs och kompilera skriptet
       with open(script_path, 'r', encoding='utf-8') as f:
           script_code = f.read()
       
       # Kör skriptet i den nuvarande kontexten
       exec(script_code, {
           "workflow_manager": workflow_manager,
           "config": config,
           "logger": logger,
           "processor": processor,
           "queue": queue,
           "batch_processor": batch_processor,
           "scheduler": scheduler,
           "workers": workers
       })
       
       self.logger.info(f"Skript slutfört: {script_path}")

## ===================================
##   Avancerad frågesökning för produkter
## ===================================

   def query_products_by_attribute(self, attribute: str, value: str, 
                                exact_match: bool = False) -> List[Dict[str, Any]]:
       """
       Söker efter produkter baserat på ett specifikt attributvärde
       
       Args:
           attribute: Attribut att söka på (t.ex. "color", "weight", "material")
           value: Värde att matcha
           exact_match: Om exakt matchning ska användas
           
       Returns:
           List[Dict[str, Any]]: Lista med matchande produkter
       """
       # Ladda sökindex om det inte finns
       if self._search_index is None:
           self._load_or_create_search_index()
       
       if self._search_index is None:
           self.logger.error("Kunde inte ladda eller skapa sökindex")
           return []
       
       matches = []
       
       try:
           # Genomsöker alla produkter i structured-katalogen
           structured_dir = self.output_dir / "structured"
           
           if not structured_dir.exists():
               self.logger.warning("Structured-katalogen finns inte, kan inte söka")
               return []
           
           # Normalisera sökvärde
           if not exact_match:
               search_value = value.lower()
           else:
               search_value = value
           
           # Sök igenom alla produkter
           for product_id, product_info in self._search_index["products"].items():
               product_dir = structured_dir / product_id
               
               if not product_dir.exists():
                   continue
               
               # Sök i produktinformation
               if product_info.get("available_data", {}).get("product_info", False):
                   product_file = product_dir / "product_info.json"
                   
                   if product_file.exists():
                       with open(product_file, 'r', encoding='utf-8') as f:
                           product_data = json.load(f)
                       
                       # Direkt matchning på produktattribut
                       if attribute in product_data:
                           attr_value = product_data[attribute]
                           
                           if (exact_match and attr_value == search_value) or \
                              (not exact_match and str(attr_value).lower().find(search_value) >= 0):
                               matches.append({
                                   "product_id": product_id,
                                   "title": product_info.get("title", ""),
                                   "match_type": "product_info",
                                   "attribute": attribute,
                                   "value": attr_value
                               })
                               continue
               
               # Sök i specifikationer
               if product_info.get("available_data", {}).get("specifications", False):
                   specs_file = product_dir / "technical_specs.json"
                   
                   if specs_file.exists():
                       with open(specs_file, 'r', encoding='utf-8') as f:
                           specs_data = json.load(f)
                       
                       # Iterera genom specifikationer
                       if "specifications" in specs_data and isinstance(specs_data["specifications"], list):
                           for spec in specs_data["specifications"]:
                               if "name" in spec and spec["name"].lower() == attribute.lower():
                                   spec_value = spec.get("raw_value", "")
                                   
                                   if (exact_match and spec_value == search_value) or \
                                      (not exact_match and str(spec_value).lower().find(search_value) >= 0):
                                       matches.append({
                                           "product_id": product_id,
                                           "title": product_info.get("title", ""),
                                           "match_type": "specification",
                                           "attribute": spec["name"],
                                           "category": spec.get("category", ""),
                                           "value": spec_value
                                       })
                                       break
           
           self.logger.info(f"Hittade {len(matches)} produkter med attribut {attribute}={value}")
           
       except Exception as e:
           self.logger.error(f"Fel vid sökning efter attribut: {str(e)}")
       
       return matches
   
   def query_products_with_relations(self, relation_type: str = None) -> List[Dict[str, Any]]:
       """
       Söker efter produkter med specifika relationstyper
       
       Args:
           relation_type: Typ av relation att söka efter (None = alla)
           
       Returns:
           List[Dict[str, Any]]: Lista med matchande produkter och deras relationer
       """
       # Ladda sökindex om det inte finns
       if self._search_index is None:
           self._load_or_create_search_index()
       
       if self._search_index is None:
           self.logger.error("Kunde inte ladda eller skapa sökindex")
           return []
       
       matches = []
       
       try:
           # Genomsöker alla produkter i structured-katalogen
           structured_dir = self.output_dir / "structured"
           
           if not structured_dir.exists():
               self.logger.warning("Structured-katalogen finns inte, kan inte söka")
               return []
           
           # Normalisera relationstyp
           if relation_type:
               relation_type = relation_type.lower()
           
           # Sök igenom alla produkter
           for product_id, product_info in self._search_index["products"].items():
               product_dir = structured_dir / product_id
               
               if not product_dir.exists():
                   continue
               
               # Sök i relationer
               if product_info.get("available_data", {}).get("relations", False):
                   relations_file = product_dir / "compatibility.json"
                   
                   if relations_file.exists():
                       with open(relations_file, 'r', encoding='utf-8') as f:
                           relations_data = json.load(f)
                       
                       matching_relations = []
                       
                       # Iterera genom relationer
                       if "relations" in relations_data and isinstance(relations_data["relations"], list):
                           for relation in relations_data["relations"]:
                               # Om ingen specifik relationstyp angivits eller om den matchar
                               if not relation_type or relation.get("relation_type", "").lower() == relation_type:
                                   matching_relations.append(relation)
                       
                       if matching_relations:
                           matches.append({
                               "product_id": product_id,
                               "title": product_info.get("title", ""),
                               "relations_count": len(matching_relations),
                               "relations": matching_relations
                           })
           
           self.logger.info(
               f"Hittade {len(matches)} produkter med "
               f"{relation_type + ' ' if relation_type else ''}relationer"
           )
           
       except Exception as e:
           self.logger.error(f"Fel vid sökning efter relationer: {str(e)}")
       
       return matches
   
   def find_related_products_graph(self, start_product_id: str, 
                               max_depth: int = 2) -> Dict[str, Any]:
       """
       Skapar en relationsgraf för att hitta alla produkter relaterade till en startprodukt
       
       Args:
           start_product_id: ID för produkten att utgå från
           max_depth: Maximalt djup för rekursionen
           
       Returns:
           Dict[str, Any]: Relationsgraf med alla relaterade produkter
       """
       # Ladda sökindex om det inte finns
       if self._search_index is None:
           self._load_or_create_search_index()
       
       if self._search_index is None:
           self.logger.error("Kunde inte ladda eller skapa sökindex")
           return {"error": "Inget sökindex tillgängligt"}
       
       if start_product_id not in self._search_index["products"]:
           self.logger.warning(f"Produkt {start_product_id} finns inte i sökindexet")
           return {"error": f"Produkt {start_product_id} hittades inte"}
       
       # Initialisera graf
       graph = {
           "nodes": [],
           "links": [],
           "root_id": start_product_id,
           "metadata": {
               "generated_at": datetime.now().isoformat(),
               "max_depth": max_depth
           }
       }
       
       # Skapa rotnode
       root_product = self._search_index["products"][start_product_id]
       graph["nodes"].append({
           "id": start_product_id,
           "title": root_product.get("title", ""),
           "depth": 0,
           "type": "root"
       })
       
       # Håll reda på besökta noder för att undvika cykler
       visited = {start_product_id}
       
       # Rekursivt sök efter relationer
       self._find_relations_recursive(start_product_id, 0, max_depth, graph, visited)
       
       self.logger.info(
           f"Genererade relationsgraf för {start_product_id} med "
           f"{len(graph['nodes'])} noder och {len(graph['links'])} länkar"
       )
       
       return graph
   
   def _find_relations_recursive(self, product_id: str, current_depth: int, 
                              max_depth: int, graph: Dict[str, Any], 
                              visited: Set[str]) -> None:
       """
       Rekursiv hjälpfunktion för att bygga relationsgraf
       
       Args:
           product_id: ID för aktuell produkt
           current_depth: Aktuellt djup i rekursionen
           max_depth: Maximalt djup för rekursionen
           graph: Graf som byggs upp
           visited: Set med redan besökta produkt-ID
       """
       # Baspunkt: om vi nått max djup
       if current_depth >= max_depth:
           return
       
       try:
           # Hitta produktens katalog
           structured_dir = self.output_dir / "structured"
           product_dir = structured_dir / product_id
           
           if not product_dir.exists():
               return
           
           # Läs relationsfil
           relations_file = product_dir / "compatibility.json"
           
           if not relations_file.exists():
               return
           
           with open(relations_file, 'r', encoding='utf-8') as f:
               relations_data = json.load(f)
           
           # Kontrollera att vi har relationer
           if "relations" not in relations_data or not isinstance(relations_data["relations"], list):
               return
           
           # Bearbeta varje relation
           for relation in relations_data["relations"]:
               # Extrahera information om relaterad produkt
               related_product = relation.get("related_product", {})
               
               if not isinstance(related_product, dict):
                   continue
               
               # Vi behöver ett sätt att identifiera den relaterade produkten
               related_article = related_product.get("article_number", "")
               related_ean = related_product.get("ean", "")
               related_name = related_product.get("name", "")
               
               # Försök hitta relaterad produkt i sökindexet
               related_id = None
               
               # Försök med artikelnummer
               if related_article and related_article in self._search_index["article_number_index"]:
                   related_ids = self._search_index["article_number_index"][related_article]
                   if related_ids:
                       related_id = related_ids[0]  # Använd första träffen
               
               # Försök med EAN om vi inte hittade med artikelnummer
               if not related_id and related_ean and related_ean in self._search_index["ean_index"]:
                   related_ids = self._search_index["ean_index"][related_ean]
                   if related_ids:
                       related_id = related_ids[0]  # Använd första träffen
               
               # Om vi inte kunde hitta produkten, skapa en "extern" nod
               if not related_id:
                   # Skapa en unik ID baserad på tillgänglig information
                   if related_article:
                       related_id = f"external_{related_article}"
                   elif related_ean:
                       related_id = f"external_{related_ean}"
                   else:
                       # Använd ett hash av namnet som ID om inget annat finns
                       import hashlib
                       name_hash = hashlib.md5(related_name.encode()).hexdigest()[:8]
                       related_id = f"external_{name_hash}"
                   
                   # Kontrollera om vi redan har lagt till denna externa nod
                   if related_id not in visited:
                       graph["nodes"].append({
                           "id": related_id,
                           "title": related_name,
                           "article_number": related_article,
                           "ean": related_ean,
                           "depth": current_depth + 1,
                           "type": "external"
                       })
                       visited.add(related_id)
               
               # Om vi inte har sett denna produkt förut, lägg till den i grafen
               elif related_id not in visited:
                   # Lägg till nod
                   related_product_info = self._search_index["products"][related_id]
                   graph["nodes"].append({
                       "id": related_id,
                       "title": related_product_info.get("title", related_name),
                       "depth": current_depth + 1,
                       "type": "internal"
                   })
                   visited.add(related_id)
                   
                   # Fortsätt rekursivt
                   self._find_relations_recursive(related_id, current_depth + 1, max_depth, graph, visited)
               
               # Lägg till länk oavsett om noden är ny eller redan existerar
               graph["links"].append({
                   "source": product_id,
                   "target": related_id,
                   "type": relation.get("relation_type", "unknown"),
                   "context": relation.get("context", "")
               })
               
       except Exception as e:
           self.logger.warning(f"Fel vid rekursiv relationssökning för {product_id}: {str(e)}")

   def export_relation_graph(self, graph: Dict[str, Any], 
                          output_format: str = "json", 
                          output_path: Union[str, Path] = None) -> Optional[Path]:
       """
       Exporterar en relationsgraf i önskat format
       
       Args:
           graph: Relationsgraf att exportera
           output_format: Format att exportera till ("json", "d3", "graphviz", "mermaid")
           output_path: Sökväg att exportera till (valfritt)
           
       Returns:
           Optional[Path]: Sökväg till exporterad fil eller None vid fel
       """
       # Bestäm utdatasökväg
       if output_path is None:
           timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
           root_id = graph.get("root_id", "graph")
           
           if output_format.lower() in ["json", "d3"]:
               output_path = self.output_dir / "exports" / f"{root_id}_graph_{timestamp}.json"
           elif output_format.lower() == "graphviz":
               output_path = self.output_dir / "exports" / f"{root_id}_graph_{timestamp}.dot"
           elif output_format.lower() == "mermaid":
               output_path = self.output_dir / "exports" / f"{root_id}_graph_{timestamp}.md"
           else:
               output_path = self.output_dir / "exports" / f"{root_id}_graph_{timestamp}.txt"
       else:
           output_path = Path(output_path)
       
       # Skapa katalog om den inte finns
       output_path.parent.mkdir(exist_ok=True, parents=True)
       
       try:
           if output_format.lower() in ["json", "d3"]:
               # För JSON och D3, spara grafen direkt
               with open(output_path, 'w', encoding='utf-8') as f:
                   json.dump(graph, f, ensure_ascii=False, indent=2)
           
           elif output_format.lower() == "graphviz":
               # Konvertera till Graphviz DOT-format
               dot_content = [
                   "digraph RelationGraph {",
                   "    rankdir=LR;",
                   "    node [shape=box, style=filled, fillcolor=lightblue];",
                   ""
               ]
               
               # Definiera noder
               for node in graph["nodes"]:
                   node_id = node["id"]
                   label = node["title"] or node["id"]
                   node_type = node.get("type", "unknown")
                   
                   if node_type == "root":
                       color = "lightgreen"
                   elif node_type == "external":
                       color = "lightyellow"
                   else:
                       color = "lightblue"
                   
                   dot_content.append(f'    "{node_id}" [label="{label}", fillcolor={color}];')
               
               dot_content.append("")
               
               # Definiera kanter
               for link in graph["links"]:
                   source = link["source"]
                   target = link["target"]
                   relation_type = link.get("type", "")
                   
                   dot_content.append(f'    "{source}" -> "{target}" [label="{relation_type}"];')
               
               dot_content.append("}")
               
               # Spara DOT-fil
               with open(output_path, 'w', encoding='utf-8') as f:
                   f.write("\n".join(dot_content))
           
           elif output_format.lower() == "mermaid":
               # Konvertera till Mermaid-format
               mermaid_content = [
                   "```mermaid",
                   "graph TD",
                   ""
               ]
               
               # Definiera noder
               for node in graph["nodes"]:
                   node_id = node["id"].replace("-", "_").replace(" ", "_")  # Mermaid har speciella krav på ID
                   label = node["title"] or node["id"]
                   node_type = node.get("type", "unknown")
                   
                   if node_type == "root":
                       style = "fill:#d5e8d4"
                   elif node_type == "external":
                       style = "fill:#fff2cc"
                   else:
                       style = "fill:#dae8fc"
                   
                   mermaid_content.append(f'    {node_id}["{label}"]:::{"root" if node_type == "root" else "normal"} style="{style}"')
               
               mermaid_content.append("")
               
               # Definiera kanter
               for link in graph["links"]:
                   source = link["source"].replace("-", "_").replace(" ", "_")
                   target = link["target"].replace("-", "_").replace(" ", "_")
                   relation_type = link.get("type", "")
                   
                   mermaid_content.append(f'    {source} -->|{relation_type}| {target}')
               
               mermaid_content.append("")
               
               # Definiera klasser
               mermaid_content.extend([
                   "    classDef root stroke:#82b366,stroke-width:2px;",
                   "    classDef normal stroke:#6c8ebf;",
                   "```"
               ])
               
               # Spara Mermaid-fil
               with open(output_path, 'w', encoding='utf-8') as f:
                   f.write("\n".join(mermaid_content))
           
           self.logger.info(f"Exporterade relationsgraf till {output_path} i {output_format}-format")
           return output_path
           
       except Exception as e:
           self.logger.error(f"Fel vid export av relationsgraf: {str(e)}")
           return None
   
   def generate_compatibility_report(self, output_path: Union[str, Path] = None) -> Optional[Path]:
       """
       Genererar en rapport över kompatibilitetsrelationer i hela produktdatabasen
       
       Args:
           output_path: Sökväg att exportera till (valfritt)
           
       Returns:
           Optional[Path]: Sökväg till exporterad fil eller None vid fel
       """
       # Bestäm utdatasökväg
       if output_path is None:
           timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
           output_path = self.output_dir / "reports" / f"compatibility_report_{timestamp}.md"
       else:
           output_path = Path(output_path)
       
       # Skapa katalog om den inte finns
       output_path.parent.mkdir(exist_ok=True, parents=True)
       
       try:
           # Hitta alla produkter med relationer
           products_with_relations = self.query_products_with_relations()
           
           if not products_with_relations:
               self.logger.warning("Inga produkter med relationer hittades")
               return None
           
           # Gruppera relationer efter typ
           relation_types = {}
           
           for product in products_with_relations:
               for relation in product["relations"]:
                   relation_type = relation.get("relation_type", "Okänd")
                   
                   if relation_type not in relation_types:
                       relation_types[relation_type] = []
                   
                   relation_types[relation_type].append({
                       "product_id": product["product_id"],
                       "product_title": product["title"],
                       "relation": relation
                   })
           
           # Skapa rapport
           report_lines = [
               "# Kompatibilitetsrapport för produktdatabasen",
               "",
               f"Genererad: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
               "",
               f"## Översikt",
               "",
               f"- **Totalt antal produkter med relationer:** {len(products_with_relations)}",
               f"- **Totalt antal relationstyper:** {len(relation_types)}",
               f"- **Totalt antal relationer:** {sum(len(relations) for relations in relation_types.values())}",
               "",
               "## Relationstyper",
               ""
           ]
           
           # Lägg till statistik per relationstyp
           for relation_type, relations in sorted(relation_types.items()):
               report_lines.extend([
                   f"### {relation_type}",
                   "",
                   f"- **Antal relationer:** {len(relations)}",
                   f"- **Antal produkter:** {len(set(r['product_id'] for r in relations))}",
                   "",
                   "#### Exempel på relationer:",
                   ""
               ])
               
               # Visa upp till 5 exempel
               for i, relation_data in enumerate(relations[:5]):
                   product_title = relation_data["product_title"] or relation_data["product_id"]
                   relation = relation_data["relation"]
                   
                   related_product = relation.get("related_product", {})
                   
                   if isinstance(related_product, dict):
                       related_name = related_product.get("name", "")
                       related_article = related_product.get("article_number", "")
                       related_info = f"**{related_name}**"
                       
                       if related_article:
                           related_info += f" (Art.nr: {related_article})"
                   else:
                       related_info = str(related_product)
                   
                   context = relation.get("context", "")
                   context_info = f"\n   *Kontext: {context}*" if context else ""
                   
                   report_lines.append(f"{i+1}. **{product_title}** → {related_info}{context_info}")
               
               report_lines.append("")
           
           # Spara rapporten
           with open(output_path, 'w', encoding='utf-8') as f:
               f.write("\n".join(report_lines))
           
           self.logger.info(f"Genererade kompatibilitetsrapport med {len(products_with_relations)} produkter till {output_path}")
           return output_path
           
       except Exception as e:
           self.logger.error(f"Fel vid generering av kompatibilitetsrapport: {str(e)}")
           return None



