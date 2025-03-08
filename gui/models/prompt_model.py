#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# gui/models/prompt_model.py

"""
Data model for prompt templates.

This module provides classes for representing and managing prompt templates
in the GUI. It includes:
- PromptTemplate: Base dataclass for representing a prompt template
- PromptModel: A model for managing collections of prompt templates 
- PromptTableModel: A Qt table model for displaying prompt templates in views

These models provide a layer of abstraction between the GUI components and
the backend prompt management system, allowing for clean separation of concerns.
"""

import os
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QAbstractTableModel, QModelIndex, Qt, Signal, Slot, QSortFilterProxyModel
)


@dataclass
class PromptTemplate:
    """Data model for a prompt template"""
    name: str
    description: str = ""
    template: str = ""
    type: str = "extraction"  # extraction, validation, correction, combined
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stats: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default values if needed"""
        if not self.stats:
            self.stats = {
                "usage_count": 0,
                "success_count": 0,
                "avg_latency_ms": 0,
                "last_used": None
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptTemplate':
        """Create a template from a dictionary"""
        # Create a copy to avoid modifying the original
        data = data.copy()
        
        # Generate ID if missing
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        
        # Ensure created_at and updated_at exist
        if "created_at" not in data:
            data["created_at"] = datetime.now().isoformat()
        if "updated_at" not in data:
            data["updated_at"] = datetime.now().isoformat()
        
        # Create instance
        return cls(**data)
    
    def update(self, **kwargs) -> None:
        """Update template fields"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Update timestamp
        self.updated_at = datetime.now().isoformat()
    
    def format(self, **kwargs) -> str:
        """
        Format the template string with the provided arguments.
        
        Args:
            **kwargs: Arguments to format into the template
            
        Returns:
            str: Formatted template
            
        Raises:
            KeyError: If a required variable is missing
            ValueError: If formatting fails
        """
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise KeyError(f"Missing required template variable: {e}")
        except Exception as e:
            raise ValueError(f"Error formatting template: {e}")
    
    def record_usage(self, success: bool, latency_ms: int) -> None:
        """
        Record a usage of this template with performance metrics.
        
        Args:
            success: Whether the usage was successful
            latency_ms: Response latency in milliseconds
        """
        # Initialize stats if needed
        if not self.stats:
            self.stats = {
                "usage_count": 0,
                "success_count": 0,
                "avg_latency_ms": 0,
                "last_used": None
            }
        
        # Update counts
        self.stats["usage_count"] = self.stats.get("usage_count", 0) + 1
        if success:
            self.stats["success_count"] = self.stats.get("success_count", 0) + 1
        
        # Update latency (rolling average)
        current_avg = self.stats.get("avg_latency_ms", 0)
        usage_count = self.stats.get("usage_count", 0)
        
        if usage_count > 1:
            # Calculate new average
            self.stats["avg_latency_ms"] = ((current_avg * (usage_count - 1)) + latency_ms) / usage_count
        else:
            self.stats["avg_latency_ms"] = latency_ms
        
        # Update last used timestamp
        self.stats["last_used"] = datetime.now().isoformat()
        
        # Update template timestamp
        self.updated_at = datetime.now().isoformat()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage"""
        if not self.stats:
            return 0.0
        
        usage_count = self.stats.get("usage_count", 0)
        success_count = self.stats.get("success_count", 0)
        
        if usage_count == 0:
            return 0.0
        
        return (success_count / usage_count) * 100
    
    @property
    def efficiency_score(self) -> float:
        """
        Calculate an efficiency score based on success rate and usage count.
        Balances success rate with amount of usage (to avoid overvaluing templates with few uses).
        """
        if not self.stats:
            return 0.0
        
        usage_count = self.stats.get("usage_count", 0)
        success_rate = self.success_rate / 100  # Convert to decimal
        
        # Factor in usage count (caps at 10 for full value)
        usage_factor = min(1.0, usage_count / 10.0)
        
        return success_rate * usage_factor


class PromptModel:
    """Model for managing a collection of prompt templates"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the prompt model.
        
        Args:
            storage_path: Path to store templates (optional)
        """
        # Initialize storage
        self.storage_path = storage_path
        
        # Initialize collections
        self.templates: Dict[str, PromptTemplate] = {}  # id -> template
        self.by_name: Dict[str, str] = {}  # name -> id
        self.by_type: Dict[str, List[str]] = {}  # type -> [id]
        self.by_tag: Dict[str, List[str]] = {}  # tag -> [id]
        
        # Load default templates if no storage path
        if not storage_path:
            self._load_default_templates()
    
    def add_template(self, template: PromptTemplate) -> str:
        """
        Add a template to the collection.
        
        Args:
            template: The prompt template to add
            
        Returns:
            str: The template ID
            
        Raises:
            ValueError: If a template with the same name already exists
        """
        # Check if name already exists
        if template.name in self.by_name:
            raise ValueError(f"Template with name '{template.name}' already exists")
        
        # Add to collections
        self.templates[template.id] = template
        self.by_name[template.name] = template.id
        
        # Add to type index
        if template.type not in self.by_type:
            self.by_type[template.type] = []
        self.by_type[template.type].append(template.id)
        
        # Add to tag index
        for tag in template.tags:
            tag = tag.lower()  # Normalize tag
            if tag not in self.by_tag:
                self.by_tag[tag] = []
            self.by_tag[tag].append(template.id)
        
        return template.id
    
    def update_template(self, template_id: str, **kwargs) -> bool:
        """
        Update a template in the collection.
        
        Args:
            template_id: ID of the template to update
            **kwargs: Fields to update
            
        Returns:
            bool: True if successful, False if template not found
            
        Raises:
            ValueError: If trying to change name to one that already exists
        """
        if template_id not in self.templates:
            return False
        
        template = self.templates[template_id]
        
        # Check if name is changing and already exists
        if "name" in kwargs and kwargs["name"] != template.name and kwargs["name"] in self.by_name:
            raise ValueError(f"Template with name '{kwargs['name']}' already exists")
        
        # Handle type change
        if "type" in kwargs and kwargs["type"] != template.type:
            # Remove from old type index
            if template.type in self.by_type:
                self.by_type[template.type].remove(template_id)
            
            # Add to new type index
            new_type = kwargs["type"]
            if new_type not in self.by_type:
                self.by_type[new_type] = []
            self.by_type[new_type].append(template_id)
        
        # Handle tags change
        if "tags" in kwargs:
            old_tags = set(tag.lower() for tag in template.tags)
            new_tags = set(tag.lower() for tag in kwargs["tags"])
            
            # Remove from old tags
            for tag in old_tags - new_tags:
                if tag in self.by_tag and template_id in self.by_tag[tag]:
                    self.by_tag[tag].remove(template_id)
            
            # Add to new tags
            for tag in new_tags - old_tags:
                if tag not in self.by_tag:
                    self.by_tag[tag] = []
                self.by_tag[tag].append(template_id)
        
        # Handle name change
        if "name" in kwargs and kwargs["name"] != template.name:
            # Update by_name index
            del self.by_name[template.name]
            self.by_name[kwargs["name"]] = template_id
        
        # Update template
        template.update(**kwargs)
        
        return True
    
    def delete_template(self, template_id: str) -> bool:
        """
        Delete a template from the collection.
        
        Args:
            template_id: ID of the template to delete
            
        Returns:
            bool: True if successful, False if template not found
        """
        if template_id not in self.templates:
            return False
        
        template = self.templates[template_id]
        
        # Remove from collections
        del self.templates[template_id]
        del self.by_name[template.name]
        
        # Remove from type index
        if template.type in self.by_type and template_id in self.by_type[template.type]:
            self.by_type[template.type].remove(template_id)
        
        # Remove from tag index
        for tag in template.tags:
            tag = tag.lower()
            if tag in self.by_tag and template_id in self.by_tag[tag]:
                self.by_tag[tag].remove(template_id)
        
        return True
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """
        Get a template by ID.
        
        Args:
            template_id: ID of the template to get
            
        Returns:
            Optional[PromptTemplate]: The template, or None if not found
        """
        return self.templates.get(template_id)
    
    def get_template_by_name(self, name: str) -> Optional[PromptTemplate]:
        """
        Get a template by name.
        
        Args:
            name: Name of the template to get
            
        Returns:
            Optional[PromptTemplate]: The template, or None if not found
        """
        template_id = self.by_name.get(name)
        if template_id:
            return self.templates.get(template_id)
        return None
    
    def get_templates_by_type(self, template_type: str) -> List[PromptTemplate]:
        """
        Get templates by type.
        
        Args:
            template_type: Type of templates to get
            
        Returns:
            List[PromptTemplate]: List of templates of the specified type
        """
        template_ids = self.by_type.get(template_type, [])
        return [self.templates[tid] for tid in template_ids if tid in self.templates]
    
    def get_templates_by_tag(self, tag: str) -> List[PromptTemplate]:
        """
        Get templates by tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            List[PromptTemplate]: List of templates with the specified tag
        """
        tag = tag.lower()  # Normalize tag
        template_ids = self.by_tag.get(tag, [])
        return [self.templates[tid] for tid in template_ids if tid in self.templates]
    
    def get_all_templates(self) -> List[PromptTemplate]:
        """
        Get all templates.
        
        Returns:
            List[PromptTemplate]: All templates in the collection
        """
        return list(self.templates.values())
    
    def get_enabled_templates(self) -> List[PromptTemplate]:
        """
        Get all enabled templates.
        
        Returns:
            List[PromptTemplate]: All enabled templates in the collection
        """
        return [t for t in self.templates.values() if t.enabled]
    
    def get_best_template(self, 
                        template_type: str, 
                        tags: Optional[List[str]] = None, 
                        min_confidence: float = 0.0) -> Optional[PromptTemplate]:
        """
        Get the best template based on type, tags, and performance statistics.
        
        Args:
            template_type: The type of template to find
            tags: Optional list of tags to filter by
            min_confidence: Minimum confidence threshold
            
        Returns:
            Optional[PromptTemplate]: The best template, or None if no suitable template is found
        """
        # Get templates of the specified type
        candidates = self.get_templates_by_type(template_type)
        
        # Filter by enabled status
        candidates = [t for t in candidates if t.enabled]
        
        # Filter by tags if provided
        if tags:
            # A template must have at least one of the specified tags
            tagged_candidates = []
            for template in candidates:
                if any(tag.lower() in [t.lower() for t in template.tags] for tag in tags):
                    tagged_candidates.append(template)
            
            candidates = tagged_candidates
        
        if not candidates:
            return None
        
        # Sort candidates by efficiency score
        candidates.sort(key=lambda t: t.efficiency_score, reverse=True)
        
        # Return the best candidate
        return candidates[0] if candidates else None
    
    def load_templates(self, clear_existing: bool = True) -> int:
        """
        Load templates from storage.
        
        Args:
            clear_existing: Whether to clear existing templates before loading
            
        Returns:
            int: Number of templates loaded
            
        Raises:
            FileNotFoundError: If storage path doesn't exist
            ValueError: If storage path is not set
        """
        if not self.storage_path:
            raise ValueError("Storage path not set")
        
        if not self.storage_path.exists():
            raise FileNotFoundError(f"Storage path {self.storage_path} does not exist")
        
        # Clear existing templates if requested
        if clear_existing:
            self.templates = {}
            self.by_name = {}
            self.by_type = {}
            self.by_tag = {}
        
        templates_loaded = 0
        
        # Try to load from combined file first
        combined_file = self.storage_path / "templates.json"
        if combined_file.exists():
            with open(combined_file, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)
            
            for template_data in templates_data:
                try:
                    template = PromptTemplate.from_dict(template_data)
                    self.add_template(template)
                    templates_loaded += 1
                except Exception as e:
                    print(f"Error loading template: {e}")
        
        # If no combined file or no templates loaded, try individual files
        if templates_loaded == 0:
            for file_path in self.storage_path.glob("*.json"):
                if file_path.name == "templates.json":
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    
                    template = PromptTemplate.from_dict(template_data)
                    self.add_template(template)
                    templates_loaded += 1
                except Exception as e:
                    print(f"Error loading template from {file_path}: {e}")
        
        # Load default templates if none were loaded
        if templates_loaded == 0:
            self._load_default_templates()
            templates_loaded = len(self.templates)
        
        return templates_loaded
    
    def save_templates(self) -> bool:
        """
        Save templates to storage.
        
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If storage path is not set
        """
        if not self.storage_path:
            raise ValueError("Storage path not set")
        
        # Create directory if it doesn't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save all templates to a combined file
            combined_file = self.storage_path / "templates.json"
            
            templates_data = [template.to_dict() for template in self.templates.values()]
            
            with open(combined_file, 'w', encoding='utf-8') as f:
                json.dump(templates_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error saving templates: {e}")
            return False
    
    def import_templates(self, file_path: Path) -> int:
        """
        Import templates from a file.
        
        Args:
            file_path: Path to the file to import from
            
        Returns:
            int: Number of templates imported
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if it's an array of templates
            if not isinstance(data, list):
                raise ValueError("Invalid template file format: expected an array of templates")
            
            templates_imported = 0
            
            for template_data in data:
                try:
                    # Skip if not a dict
                    if not isinstance(template_data, dict):
                        continue
                    
                    # Check required fields
                    if "name" not in template_data or "template" not in template_data:
                        continue
                    
                    # Create template
                    template = PromptTemplate.from_dict(template_data)
                    
                    # If a template with this name already exists, make it unique
                    if template.name in self.by_name:
                        template.name = f"{template.name} (Imported)"
                        
                        # If still exists, add a number
                        counter = 1
                        while template.name in self.by_name:
                            template.name = f"{template.name.rsplit(' (', 1)[0]} ({counter})"
                            counter += 1
                    
                    # Add template
                    self.add_template(template)
                    templates_imported += 1
                except Exception as e:
                    print(f"Error importing template: {e}")
            
            return templates_imported
        except Exception as e:
            raise ValueError(f"Error importing templates: {e}")
    
    def export_templates(self, file_path: Path, 
                        template_ids: Optional[List[str]] = None, 
                        include_stats: bool = False) -> int:
        """
        Export templates to a file.
        
        Args:
            file_path: Path to the file to export to
            template_ids: Optional list of template IDs to export (None for all)
            include_stats: Whether to include usage statistics
            
        Returns:
            int: Number of templates exported
            
        Raises:
            ValueError: If no templates are found to export
        """
        templates_to_export = []
        
        # Get templates to export
        if template_ids:
            templates_to_export = [self.templates[tid] for tid in template_ids if tid in self.templates]
        else:
            templates_to_export = list(self.templates.values())
        
        if not templates_to_export:
            raise ValueError("No templates to export")
        
        try:
            # Convert templates to dictionaries
            templates_data = []
            
            for template in templates_to_export:
                template_dict = template.to_dict()
                
                # Remove sensitive or unnecessary fields
                if not include_stats and "stats" in template_dict:
                    del template_dict["stats"]
                
                templates_data.append(template_dict)
            
            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(templates_data, f, indent=2, ensure_ascii=False)
            
            return len(templates_data)
        except Exception as e:
            raise ValueError(f"Error exporting templates: {e}")
    
    def _load_default_templates(self) -> None:
        """Load default templates"""
        default_templates = [
            PromptTemplate(
                name="Default Compatibility Extraction",
                description="Standard template for extracting compatibility information",
                type="extraction",
                tags=["extraction", "compatibility"],
                template="""Analyze the following product documentation and extract compatibility information.

Product Documentation:
{text}

Extract all compatibility relationships between this product and other products.
For each relationship, identify:
1. The relation type (e.g., "works with", "compatible with", "fits", "replaces")
2. The related product (name, article number if available)
3. Any context that explains the compatibility relationship

Provide the results in the following JSON structure:
{
  "relations": [
    {
      "relation_type": "relation type",
      "related_product": "product name or ID",
      "context": "context about the compatibility",
      "confidence": 0.8
    }
  ]
}

Make sure to include a confidence score between 0 and 1 for each relation.
If no compatibility information is found, return an empty relations array.
"""
            ),
            PromptTemplate(
                name="Default Technical Specifications Extraction",
                description="Standard template for extracting technical specifications",
                type="extraction",
                tags=["extraction", "technical"],
                template="""Analyze the following product documentation and extract technical specifications.

Product Documentation:
{text}

Extract all technical specifications for this product.
For each specification, identify:
1. The category (e.g., "dimensions", "material", "electrical", "performance")
2. The name of the specification (e.g., "height", "weight", "input voltage")
3. The raw value as mentioned in the text
4. The unit if specified (e.g., "mm", "kg", "V")

Provide the results in the following JSON structure:
{
  "specifications": [
    {
      "category": "category name",
      "name": "specification name",
      "raw_value": "value as in text",
      "unit": "unit if any",
      "confidence": 0.8
    }
  ]
}

Make sure to include a confidence score between 0 and 1 for each specification.
If no technical specifications are found, return an empty specifications array.
"""
            ),
            PromptTemplate(
                name="Combined Extraction",
                description="Template for extracting combined information (product info, compatibility, technical)",
                type="combined",
                tags=["extraction", "combined", "compatibility", "technical"],
                template="""Analyze the following product documentation and extract structured information.

Product Documentation:
{text}

Extract the following types of information:
1. Basic product information (name, article number, description)
2. Compatibility relationships with other products
3. Technical specifications

Provide the results in the following JSON structure:
{
  "product_info": {
    "title": "product name",
    "article_number": "ID or SKU",
    "description": "brief description"
  },
  "relations": [
    {
      "relation_type": "relation type",
      "related_product": "product name or ID",
      "context": "context about the compatibility",
      "confidence": 0.8
    }
  ],
  "specifications": [
    {
      "category": "category name",
      "name": "specification name",
      "raw_value": "value as in text",
      "unit": "unit if any",
      "confidence": 0.8
    }
  ]
}

Make sure to include confidence scores between 0 and 1 for relations and specifications.
If any section has no information, return an empty array for that section.
"""
            )
        ]
        
        # Add default templates
        for template in default_templates:
            self.add_template(template)


class PromptTableModel(QAbstractTableModel):
    """Qt table model for displaying prompt templates in table views"""
    
    # Define column indices
    COL_NAME = 0
    COL_TYPE = 1
    COL_TAGS = 2
    COL_SUCCESS_RATE = 3
    COL_USAGE_COUNT = 4
    COL_ENABLED = 5
    
    # Define roles for data
    IdRole = Qt.UserRole + 1
    DescriptionRole = Qt.UserRole + 2
    TemplateTextRole = Qt.UserRole + 3
    TagsListRole = Qt.UserRole + 4
    StatsRole = Qt.UserRole + 5
    EnabledRole = Qt.UserRole + 6
    
    # Signals
    template_changed = Signal(str)  # template_id
    
    def __init__(self, prompt_model: PromptModel):
        """
        Initialize the table model.
        
        Args:
            prompt_model: The prompt model to display
        """
        super().__init__()
        
        self.prompt_model = prompt_model
        self.templates = []
        self.reload_templates()
    
    def reload_templates(self):
        """Reload templates from the model"""
        self.beginResetModel()
        self.templates = self.prompt_model.get_all_templates()
        self.endResetModel()
    
    def rowCount(self, parent=None):
        """Return the number of rows in the model"""
        return len(self.templates)
    
    def columnCount(self, parent=None):
        """Return the number of columns in the model"""
        return 6  # Name, Type, Tags, Success Rate, Usage Count, Enabled
    
    def data(self, index, role=Qt.DisplayRole):
        """Return data for the given role"""
        if not index.isValid() or index.row() >= len(self.templates):
            return None
        
        template = self.templates[index.row()]
        
        if role == Qt.DisplayRole:
            # Data for display
            col = index.column()
            if col == self.COL_NAME:
                return template.name
            elif col == self.COL_TYPE:
                return template.type.capitalize()
            elif col == self.COL_TAGS:
                return ", ".join(template.tags) if template.tags else ""
            elif col == self.COL_SUCCESS_RATE:
                return f"{template.success_rate:.1f}%"
            elif col == self.COL_USAGE_COUNT:
                return str(template.stats.get("usage_count", 0))
            elif col == self.COL_ENABLED:
                return "Yes" if template.enabled else "No"
        
        elif role == Qt.ToolTipRole:
            # Tooltip with description
            return template.description
        
        elif role == self.IdRole:
            # Template ID
            return template.id
        
        elif role == self.DescriptionRole:
            # Template description
            return template.description
        
        elif role == self.TemplateTextRole:
            # Template text
            return template.template
        
        elif role == self.TagsListRole:
            # Tags as a list
            return template.tags
        
        elif role == self.StatsRole:
            # Stats dictionary
            return template.stats
        
        elif role == self.EnabledRole:
            # Enabled status
            return template.enabled
        
        return None
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Return header data for the given role"""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            # Column headers
            headers = ["Name", "Type", "Tags", "Success Rate", "Usage", "Enabled"]
            return headers[section]
        
        return None
    
    def flags(self, index):
        """Return flags for the given index"""
        if not index.isValid():
            return Qt.NoItemFlags
        
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable
    
    def get_template_at_row(self, row):
        """
        Get the template at the specified row.
        
        Args:
            row: Row index
            
        Returns:
            Optional[PromptTemplate]: The template, or None if row is invalid
        """
        if 0 <= row < len(self.templates):
            return self.templates[row]
        return None
    
    def get_template_by_id(self, template_id):
        """
        Get the template with the specified ID.
        
        Args:
            template_id: ID of the template to find
            
        Returns:
            Optional[PromptTemplate]: The template, or None if not found
        """
        for template in self.templates:
            if template.id == template_id:
                return template
        return None
    
    def get_row_for_template_id(self, template_id):
        """
        Get the row index for the template with the specified ID.
        
        Args:
            template_id: ID of the template to find
            
        Returns:
            int: Row index, or -1 if not found
        """
        for i, template in enumerate(self.templates):
            if template.id == template_id:
                return i
        return -1
    
    def update_template(self, template_id, **kwargs):
        """
        Update a template in the model.
        
        Args:
            template_id: ID of the template to update
            **kwargs: Fields to update
            
        Returns:
            bool: True if successful, False if template not found
        """
        # Get the template row
        row = self.get_row_for_template_id(template_id)
        if row == -1:
            return False
        
        # Update in prompt model
        success = self.prompt_model.update_template(template_id, **kwargs)
        if not success:
            return False
        
        # Update in local list
        self.templates[row] = self.prompt_model.get_template(template_id)
        
        # Notify views
        self.dataChanged.emit(
            self.index(row, 0),
            self.index(row, self.columnCount() - 1)
        )
        
        # Emit custom signal
        self.template_changed.emit(template_id)
        
        return True
    
    def add_template(self, template: PromptTemplate):
        """
        Add a template to the model.
        
        Args:
            template: The template to add
            
        Returns:
            str: Template ID if successful, None otherwise
        """
        try:
            # Add to prompt model
            template_id = self.prompt_model.add_template(template)
            
            # Insert in local list
            self.beginInsertRows(QModelIndex(), len(self.templates), len(self.templates))
            self.templates.append(template)
            self.endInsertRows()
            
            return template_id
        except Exception as e:
            print(f"Error adding template: {e}")
            return None
    
    def delete_template(self, template_id: str):
        """
        Delete a template from the model.
        
        Args:
            template_id: ID of the template to delete
            
        Returns:
            bool: True if successful, False if template not found
        """
        # Get the template row
        row = self.get_row_for_template_id(template_id)
        if row == -1:
            return False
        
        # Delete from prompt model
        success = self.prompt_model.delete_template(template_id)
        if not success:
            return False
        
        # Remove from local list
        self.beginRemoveRows(QModelIndex(), row, row)
        self.templates.pop(row)
        self.endRemoveRows()
        
        return True
    
    def toggle_enabled(self, template_id: str):
        """
        Toggle the enabled state of a template.
        
        Args:
            template_id: ID of the template
            
        Returns:
            bool: New enabled state, or None if template not found
        """
        # Get the template
        template = self.get_template_by_id(template_id)
        if not template:
            return None
        
        # Toggle enabled state
        new_state = not template.enabled
        
        # Update template
        self.update_template(template_id, enabled=new_state)
        
        return new_state


class PromptFilterProxyModel(QSortFilterProxyModel):
    """Proxy model for filtering prompts by type, tags, name, etc."""
    
    def __init__(self, parent=None):
        """Initialize the filter proxy model"""
        super().__init__(parent)
        
        self.filter_text = ""
        self.filter_type = ""
        self.filter_tags = []
        self.show_disabled = True
    
    def set_filter_text(self, text: str):
        """Set text filter"""
        self.filter_text = text.lower()
        self.invalidateFilter()
    
    def set_filter_type(self, template_type: str):
        """Set type filter"""
        self.filter_type = template_type
        self.invalidateFilter()
    
    def set_filter_tags(self, tags: List[str]):
        """Set tags filter"""
        self.filter_tags = [tag.lower() for tag in tags]
        self.invalidateFilter()
    
    def set_show_disabled(self, show: bool):
        """Set whether to show disabled templates"""
        self.show_disabled = show
        self.invalidateFilter()
    
    def filterAcceptsRow(self, source_row, source_parent):
        """
        Determine if a row should be included in the filtered model.
        
        Args:
            source_row: Row in the source model
            source_parent: Parent index in the source model
            
        Returns:
            bool: True if the row should be included, False otherwise
        """
        source_model = self.sourceModel()
        
        # Get template data
        name_index = source_model.index(source_row, PromptTableModel.COL_NAME, source_parent)
        type_index = source_model.index(source_row, PromptTableModel.COL_TYPE, source_parent)
        tags_index = source_model.index(source_row, PromptTableModel.COL_TAGS, source_parent)
        
        # Get enabled status
        enabled = source_model.data(
            source_model.index(source_row, 0, source_parent),
            PromptTableModel.EnabledRole
        )
        
        # Filter by enabled status
        if not self.show_disabled and not enabled:
            return False
        
        # Filter by type
        if self.filter_type and self.filter_type != "all":
            template_type = source_model.data(type_index, Qt.DisplayRole).lower()
            if template_type != self.filter_type.lower():
                return False
        
        # Filter by tags
        if self.filter_tags:
            tags_list = source_model.data(
                source_model.index(source_row, 0, source_parent),
                PromptTableModel.TagsListRole
            )
            
            if not tags_list or not any(filter_tag in [tag.lower() for tag in tags_list] 
                                   for filter_tag in self.filter_tags):
                return False
        
        # Filter by text
        if self.filter_text:
            # Check name
            name = source_model.data(name_index, Qt.DisplayRole).lower()
            if self.filter_text in name:
                return True
            
            # Check tags
            tags = source_model.data(tags_index, Qt.DisplayRole).lower()
            if self.filter_text in tags:
                return True
            
            # Check description
            description = source_model.data(
                source_model.index(source_row, 0, source_parent),
                PromptTableModel.DescriptionRole
            ).lower()
            if self.filter_text in description:
                return True
            
            return False
        
        return True
    
    def lessThan(self, left, right):
        """
        Compare two items for sorting.
        
        Args:
            left: Left index to compare
            right: Right index to compare
            
        Returns:
            bool: True if left is less than right
        """
        source_model = self.sourceModel()
        
        left_data = source_model.data(left, Qt.DisplayRole)
        right_data = source_model.data(right, Qt.DisplayRole)
        
        # For success rate column, convert percentage string to float
        if left.column() == PromptTableModel.COL_SUCCESS_RATE:
            left_data = float(left_data.rstrip("%"))
            right_data = float(right_data.rstrip("%"))
        
        # For usage count column, convert string to int
        elif left.column() == PromptTableModel.COL_USAGE_COUNT:
            left_data = int(left_data)
            right_data = int(right_data)
        
        # Default string comparison
        return left_data < right_data