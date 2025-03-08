# File: gui/services/extraction_service.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from PySide6.QtCore import QObject, Signal, QThread, Slot


class ExtractionStatus(Enum):
    """Extraction status codes"""
    NOT_STARTED = "not_started"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    PROCESSING_CHUNKS = "processing_chunks"
    MERGING_RESULTS = "merging_results"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"


@dataclass
class ExtractionResult:
    """Data class for extraction results"""
    product_id: str
    status: ExtractionStatus = ExtractionStatus.NOT_STARTED
    compatibility: Dict[str, Any] = None
    technical: Dict[str, Any] = None
    faq_data: Dict[str, Any] = None
    errors: List[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize empty collections if not provided"""
        if self.compatibility is None:
            self.compatibility = {}
        if self.technical is None:
            self.technical = {}
        if self.faq_data is None:
            self.faq_data = {}
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "processing_time_ms": 0,
                "file_size": 0,
                "chunked": False,
                "chunks_count": 0
            }
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update a metadata field"""
        self.metadata[key] = value
        self.metadata["updated_at"] = datetime.now().isoformat()
    
    def add_error(self, error: str) -> None:
        """Add an error message"""
        self.errors.append(error)
        if self.status not in [ExtractionStatus.FAILED, ExtractionStatus.PARTIALLY_COMPLETED]:
            self.status = ExtractionStatus.FAILED
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message"""
        self.warnings.append(warning)
    
    def get_compatibility_count(self) -> int:
        """Get the number of compatibility relations"""
        return len(self.compatibility.get("relations", []))
    
    def get_technical_count(self) -> int:
        """Get the number of technical specifications"""
        return len(self.technical.get("specifications", []))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary"""
        return {
            "product_id": self.product_id,
            "status": self.status.value,
            "compatibility": self.compatibility,
            "technical": self.technical,
            "faq_data": self.faq_data,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractionResult':
        """Create from a dictionary"""
        result = cls(
            product_id=data.get("product_id", ""),
            status=ExtractionStatus(data.get("status", "not_started")),
            compatibility=data.get("compatibility", {}),
            technical=data.get("technical", {}),
            faq_data=data.get("faq_data", {}),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            metadata=data.get("metadata", {})
        )
        return result


class ExtractionWorker(QThread):
    """Worker thread for extraction tasks"""
    
    # Define signals
    progress = Signal(str, ExtractionStatus, int, str)  # task_id, status, progress percentage, message
    result = Signal(str, ExtractionResult)  # task_id, result
    error = Signal(str, str)  # task_id, error message
    
    def __init__(self, 
                task_id: str, 
                product_id: str, 
                file_path: str, 
                config: Dict[str, Any],
                processor = None):
        """
        Initialize extraction worker
        
        Args:
            task_id: Unique ID for this extraction task
            product_id: ID of the product to extract
            file_path: Path to the file to process
            config: Extraction configuration
            processor: Optional product processor instance
        """
        super().__init__()
        
        self.task_id = task_id
        self.product_id = product_id
        self.file_path = file_path
        self.config = config
        self.processor = processor
        self.should_stop = False
        
        # Configure logger
        self.logger = logging.getLogger(f"extraction_worker_{task_id}")
    
    def run(self):
        """Run the extraction task"""
        try:
            # Update status
            self.progress.emit(self.task_id, ExtractionStatus.IN_PROGRESS, 0, 
                            f"Starting extraction for {self.product_id}")
            
            # Check if file exists
            file_path = Path(self.file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File does not exist: {self.file_path}")
            
            # If processor wasn't provided, create one
            if not self.processor:
                # Need to import here to avoid circular imports
                from Processor.ProductProcessor import ProductProcessor
                from client.LLMClient import LLMClient
                from config.ConfigManager import ConfigManager
                
                # Load configuration
                config_manager = ConfigManager()
                
                # Set extraction configuration if provided
                if self.config:
                    config_manager.set("extraction", self.config)
                
                # Create LLM client
                llm_config = config_manager.get("llm", {})
                llm_client = LLMClient(llm_config, self.logger)
                
                # Create processor
                extraction_config = config_manager.get("extraction", {})
                self.processor = ProductProcessor(extraction_config, llm_client, self.logger)
            
            # Update progress
            self.progress.emit(self.task_id, ExtractionStatus.IN_PROGRESS, 10, 
                            "Reading file content...")
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update file metadata
            file_size = file_path.stat().st_size
            
            # Create result object
            result = ExtractionResult(
                product_id=self.product_id,
                status=ExtractionStatus.IN_PROGRESS,
                metadata={
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "file_path": str(file_path),
                    "file_size": file_size,
                    "processing_time_ms": 0
                }
            )
            
            # Process the file in chunks if needed
            start_time = time.time()
            
            # Check if file should be chunked
            if self.processor.chunk_manager.should_chunk(content):
                result.update_metadata("chunked", True)
                chunks = self.processor.chunk_manager.chunk_text(content)
                result.update_metadata("chunks_count", len(chunks))
                
                self.progress.emit(self.task_id, ExtractionStatus.PROCESSING_CHUNKS, 20, 
                                f"Processing file in {len(chunks)} chunks...")
                
                # Process each chunk
                compatibility_results = []
                technical_results = []
                faq_results = []
                
                for i, chunk in enumerate(chunks):
                    # Check if we should stop
                    if self.should_stop:
                        raise InterruptedError("Extraction task was cancelled")
                    
                    # Update progress
                    progress = 20 + int(60 * (i / len(chunks)))
                    self.progress.emit(self.task_id, ExtractionStatus.PROCESSING_CHUNKS, progress, 
                                    f"Processing chunk {i+1}/{len(chunks)}...")
                    
                    # Extract from this chunk
                    chunk_result = self._process_content(chunk)
                    
                    # Collect results
                    if "compatibility" in self.config and self.config["compatibility"].get("enabled", False):
                        if chunk_result.compatibility:
                            compatibility_results.append(chunk_result.compatibility)
                    
                    if "technical" in self.config and self.config["technical"].get("enabled", False):
                        if chunk_result.technical:
                            technical_results.append(chunk_result.technical)
                    
                    if "faq" in self.config and self.config["faq"].get("enabled", False):
                        if chunk_result.faq_data:
                            faq_results.append(chunk_result.faq_data)
                    
                    # Collect errors and warnings
                    result.errors.extend([f"Chunk {i+1}: {error}" for error in chunk_result.errors])