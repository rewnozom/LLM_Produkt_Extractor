# gui/models/extraction_model.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data model for extraction results.

This module provides classes for representing and managing extraction results
in the GUI. It includes:
- ExtractionModel: A data model for extraction results
- CompatibilityRelation: A model for compatibility relations
- TechnicalSpecification: A model for technical specifications
- ProductInfo: A model for basic product information
- ExtractionStatus: Enum for extraction status values

These models provide a layer of abstraction between the GUI components and
the backend extraction systems, allowing for more maintainable and testable code.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union, Set
from datetime import datetime
from pathlib import Path
import json

from PySide6.QtCore import QObject, Signal, Slot, Qt, QAbstractTableModel, QModelIndex


class ExtractionStatus(Enum):
    """Enum for extraction status values"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"
    CORRECTED = "corrected"
    
    def __str__(self):
        return self.value
    
    @classmethod
    def from_string(cls, status_str: str) -> 'ExtractionStatus':
        """Convert a string to an ExtractionStatus enum value"""
        try:
            return cls(status_str.lower())
        except ValueError:
            # If not found, try to map common values
            mapping = {
                "complete": cls.COMPLETED,
                "partial": cls.PARTIALLY_COMPLETED,
                "fail": cls.FAILED,
                "error": cls.FAILED,
                "validate": cls.VALIDATED,
                "validated": cls.VALIDATED,
                "validation_error": cls.VALIDATION_FAILED,
                "correct": cls.CORRECTED,
                "corrected": cls.CORRECTED
            }
            
            for key, value in mapping.items():
                if key in status_str.lower():
                    return value
            
            return cls.NOT_STARTED
    
    def is_successful(self) -> bool:
        """Check if the status indicates successful extraction"""
        return self in [self.COMPLETED, self.PARTIALLY_COMPLETED, self.VALIDATED, self.CORRECTED]


@dataclass
class ProductInfo:
    """Model for basic product information"""
    title: str = ""
    article_number: str = ""
    ean: str = ""
    sku: str = ""
    manufacturer: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization"""
        return {
            "title": self.title,
            "article_number": self.article_number,
            "ean": self.ean,
            "sku": self.sku,
            "manufacturer": self.manufacturer,
            "description": self.description,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProductInfo':
        """Create a ProductInfo from a dictionary"""
        return cls(
            title=data.get("title", ""),
            article_number=data.get("article_number", ""),
            ean=data.get("ean", ""),
            sku=data.get("sku", ""),
            manufacturer=data.get("manufacturer", ""),
            description=data.get("description", ""),
            metadata=data.get("metadata", {})
        )


@dataclass
class RelatedProduct:
    """Model for a related product reference"""
    name: str = ""
    article_number: str = ""
    ean: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization"""
        return {
            "name": self.name,
            "article_number": self.article_number,
            "ean": self.ean,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RelatedProduct':
        """Create a RelatedProduct from a dictionary"""
        if isinstance(data, dict):
            return cls(
                name=data.get("name", ""),
                article_number=data.get("article_number", ""),
                ean=data.get("ean", ""),
                metadata=data.get("metadata", {})
            )
        else:
            # Handle case where related_product is just a string
            return cls(name=str(data))
    
    def __str__(self) -> str:
        """String representation"""
        if self.article_number:
            return f"{self.name} ({self.article_number})"
        else:
            return self.name


@dataclass
class CompatibilityRelation:
    """Model for a compatibility relation"""
    relation_type: str
    related_product: Union[RelatedProduct, str]
    context: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Convert related_product to RelatedProduct if it's a dict or string"""
        if isinstance(self.related_product, dict):
            self.related_product = RelatedProduct.from_dict(self.related_product)
        elif isinstance(self.related_product, str):
            self.related_product = RelatedProduct(name=self.related_product)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization"""
        if isinstance(self.related_product, RelatedProduct):
            related_product_dict = self.related_product.to_dict()
        else:
            related_product_dict = str(self.related_product)
            
        return {
            "relation_type": self.relation_type,
            "related_product": related_product_dict,
            "context": self.context,
            "confidence": self.