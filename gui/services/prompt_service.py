# File: gui/services/prompt_service.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QObject, Signal


@dataclass
class PromptTemplate:
    """Data class representing a prompt template"""
    name: str
    description: str
    template: str
    type: str
    tags: List[str]
    enabled: bool = True
    stats: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize stats if not provided"""
        if self.stats is None:
            self.stats = {
                "usage_count": 0,
                "success_count": 0,
                "avg_latency_ms": 0,
                "last_used": None
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the template to a dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "type": self.type,
            "tags": self.tags,
            "enabled": self.enabled,
            "stats": self.stats
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptTemplate':
        """Create a template from a dictionary"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            template=data.get("template", ""),
            type=data.get("type", "extraction"),
            tags=data.get("tags", []),
            enabled=data.get("enabled", True),
            stats=data.get("stats", None)
        )
    
    def format(self, **kwargs) -> str:
        """Format the template with the provided arguments"""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required template variable: {e}")
        except Exception as e:
            raise ValueError(f"Error formatting template: {e}")


class PromptService(QObject):
    """Service for managing prompt templates"""
    
    # Define signals
    templates_loaded = Signal(list)  # list of PromptTemplates
    template_saved = Signal(object)  # PromptTemplate
    template_deleted = Signal(str)   # template name
    template_used = Signal(str, bool, int)  # template name, success, latency_ms
    
    def __init__(self, storage_dir: str = None):
        super().__init__()
        
        # Configure logger
        self.logger = logging.getLogger("prompt_service")
        
        # Set storage directory
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            # Default to prompts directory in the application root
            self.storage_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "prompts"
        
        # Create directory if it doesn't exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Templates cache
        self.templates: List[PromptTemplate] = []
        
        # Template lookup maps
        self.templates_by_name: Dict[str, PromptTemplate] = {}
        self.templates_by_type: Dict[str, List[PromptTemplate]] = {}
        self.templates_by_tag: Dict[str, List[PromptTemplate]] = {}
        
        # Cache for prompt responses
        self.response_cache: Dict[str, Any] = {}
        self.cache_enabled = True
        self.max_cache_size = 100
        
        # Load templates
        self.load_templates()
    
    def load_templates(self) -> List[PromptTemplate]:
        """Load templates from storage directory"""
        try:
            # Clear existing templates
            self.templates = []
            self.templates_by_name = {}
            self.templates_by_type = {}
            self.templates_by_tag = {}
            
            # First try to load from templates.json (combined file)
            templates_file = self.storage_dir / "templates.json"
            
            if templates_file.exists():
                with open(templates_file, 'r', encoding='utf-8') as f:
                    templates_data = json.load(f)
                
                for template_data in templates_data:
                    template = PromptTemplate.from_dict(template_data)
                    self.templates.append(template)
            else:
                # If combined file doesn't exist, load individual template files
                template_files = list(self.storage_dir.glob("*.json"))
                
                for file_path in template_files:
                    if file_path.name == "templates.json":
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            template_data = json.load(f)
                        
                        template = PromptTemplate.from_dict(template_data)
                        self.templates.append(template)
                    except Exception as e:
                        self.logger.error(f"Error loading template {file_path}: {e}")
            
            # If no templates found, load default templates
            if not self.templates:
                self._load_default_templates()
            
            # Index templates
            self._index_templates()
            
            # Emit signal
            self.templates_loaded.emit(self.templates)
            
            self.logger.info(f"Loaded {len(self.templates)} prompt templates")
            return self.templates
            
        except Exception as e:
            self.logger.error(f"Error loading prompt templates: {e}")
            
            # Load defaults if loading fails
            if not self.templates:
                self._load_default_templates()
                self._index_templates()
                self.templates_loaded.emit(self.templates)
            
            return self.templates
    
    def save_templates(self) -> bool:
        """Save all templates to storage directory"""
        try:
            # Save to combined file
            templates_file = self.storage_dir / "templates.json"
            
            templates_data = [template.to_dict() for template in self.templates]
            
            with open(templates_file, 'w', encoding='utf-8') as f:
                json.dump(templates_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(self.templates)} prompt templates")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving prompt templates: {e}")
            return False
    
    def save_template(self, template: PromptTemplate) -> bool:
        """Save a single template"""
        # Check if template already exists
        if template.name in self.templates_by_name:
            # Update existing template
            for i, existing in enumerate(self.templates):
                if existing.name == template.name:
                    self.templates[i] = template
                    break
        else:
            # Add new template
            self.templates.append(template)
        
        # Update index
        self._index_templates()
        
        # Save all templates
        result = self.save_templates()
        
        # Emit signal if save was successful
        if result:
            self.template_saved.emit(template)
        
        return result
    
    def delete_template(self, template_name: str) -> bool:
        """Delete a template by name"""
        # Check if template exists
        if template_name not in self.templates_by_name:
            return False
        
        # Remove template from list
        self.templates = [t for t in self.templates if t.name != template_name]
        
        # Update index
        self._index_templates()
        
        # Save all templates
        result = self.save_templates()
        
        # Emit signal if save was successful
        if result:
            self.template_deleted.emit(template_name)
        
        return result
    
    def get_template(self, template_name: str) -> Optional[PromptTemplate]:
        """Get a template by name"""
        return self.templates_by_name.get(template_name)
    
    def get_templates_by_type(self, template_type: str) -> List[PromptTemplate]:
        """Get templates by type"""
        return self.templates_by_type.get(template_type, [])
    
    def get_templates_by_tag(self, tag: str) -> List[PromptTemplate]:
        """Get templates by tag"""
        return self.templates_by_tag.get(tag.lower(), [])
    
    def get_all_templates(self) -> List[PromptTemplate]:
        """Get all templates"""
        return self.templates
    
    def get_enabled_templates(self) -> List[PromptTemplate]:
        """Get all enabled templates"""
        return [t for t in self.templates if t.enabled]
    
    def get_best_template(self, 
                        template_type: str, 
                        tags: List[str] = None, 
                        min_confidence: float = 0.0) -> Optional[PromptTemplate]:
        """
        Get the best template based on type, tags, and performance statistics
        
        Args:
            template_type: The type of template to find
            tags: Optional list of tags to filter by
            min_confidence: Minimum confidence threshold
            
        Returns:
            The best template or None if no suitable template is found
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
                if any(tag in template.tags for tag in tags):
                    tagged_candidates.append(template)
            
            candidates = tagged_candidates
        
        if not candidates:
            return None
        
        # Sort candidates by success rate and usage count
        # We prioritize templates with high success rates and more usage
        def template_score(template: PromptTemplate) -> float:
            stats = template.stats
            usage_count = stats.get("usage_count", 0)
            success_count = stats.get("success_count", 0)
            
            if usage_count == 0:
                return 0.0
            
            success_rate = success_count / usage_count
            
            # We want templates with both high success rates and enough usage
            # This helps prevent a template with 1/1 success from outranking
            # a template with 90/100 successes
            usage_factor = min(1.0, usage_count / 10.0)  # Caps at 10 usages
            
            return success_rate * usage_factor
        
        candidates.sort(key=template_score, reverse=True)
        
        # Return the best candidate
        return candidates[0] if candidates else None
    
    def record_template_usage(self, template_name: str, success: bool, latency_ms: int) -> None:
        """
        Record usage statistics for a template
        
        Args:
            template_name: The name of the template
            success: Whether the usage was successful
            latency_ms: Response latency in milliseconds
        """
        template = self.get_template(template_name)
        if not template:
            return
        
        # Update stats
        if "stats" not in template.stats:
            template.stats = {
                "usage_count": 0,
                "success_count": 0,
                "avg_latency_ms": 0,
                "last_used": None
            }
        
        stats = template.stats
        
        # Update counts
        stats["usage_count"] = stats.get("usage_count", 0) + 1
        if success:
            stats["success_count"] = stats.get("success_count", 0) + 1
        
        # Update latency (rolling average)
        current_avg = stats.get("avg_latency_ms", 0)
        usage_count = stats.get("usage_count", 0)
        
        if usage_count > 1:
            # Calculate new average
            stats["avg_latency_ms"] = ((current_avg * (usage_count - 1)) + latency_ms) / usage_count
        else:
            stats["avg_latency_ms"] = latency_ms
        
        # Update last used timestamp
        stats["last_used"] = datetime.now().isoformat()
        
        # Save templates
        self.save_templates()
        
        # Emit signal
        self.template_used.emit(template_name, success, latency_ms)
    
    def format_template(self, template_name: str, **kwargs) -> str:
        """
        Format a template with the provided arguments
        
        Args:
            template_name: The name of the template
            **kwargs: The arguments to format the template with
            
        Returns:
            The formatted template
            
        Raises:
            ValueError: If the template is not found or the formatting fails
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        return template.format(**kwargs)
    
    def cache_response(self, prompt: str, response: Any) -> None:
        """
        Cache a prompt response
        
        Args:
            prompt: The prompt that was sent
            response: The response that was received
        """
        if not self.cache_enabled:
            return
        
        # Generate a hash key for the prompt
        import hashlib
        key = hashlib.md5(prompt.encode()).hexdigest()
        
        # Add to cache
        self.response_cache[key] = response
        
        # Trim cache if needed
        if len(self.response_cache) > self.max_cache_size:
            # Remove the oldest entries
            excess = len(self.response_cache) - self.max_cache_size
            keys_to_remove = list(self.response_cache.keys())[:excess]
            
            for key in keys_to_remove:
                del self.response_cache[key]
    
    def get_cached_response(self, prompt: str) -> Optional[Any]:
        """
        Get a cached response for a prompt
        
        Args:
            prompt: The prompt to look up
            
        Returns:
            The cached response or None if not found
        """
        if not self.cache_enabled:
            return None
        
        # Generate a hash key for the prompt
        import hashlib
        key = hashlib.md5(prompt.encode()).hexdigest()
        
        # Return cached response if found
        return self.response_cache.get(key)
    
    def clear_cache(self) -> None:
        """Clear the response cache"""
        self.response_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "enabled": self.cache_enabled,
            "cache_size": len(self.response_cache),
            "max_cache_size": self.max_cache_size
        }
    
    def setup_caching(self, cache_enabled: bool = True, max_cache_size: int = 100) -> None:
        """Configure the response cache"""
        self.cache_enabled = cache_enabled
        self.max_cache_size = max_cache_size
        
        if not cache_enabled:
            self.clear_cache()
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage statistics for all templates"""
        stats = {
            "total_prompts": len(self.templates),
            "by_type": {},
            "top_tags": [],
            "cache": self.get_cache_stats()
        }
        
        # Count templates by type
        for template_type, templates in self.templates_by_type.items():
            stats["by_type"][template_type] = len(templates)
        
        # Get top tags
        tag_counts = {}
        for tag, templates in self.templates_by_tag.items():
            tag_counts[tag] = len(templates)
        
        # Get the top 10 tags
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        stats["top_tags"] = [{"tag": tag, "count": count} for tag, count in top_tags]
        
        return stats
    
    def _index_templates(self) -> None:
        """Index templates for quick lookup"""
        # Clear existing indexes
        self.templates_by_name = {}
        self.templates_by_type = {}
        self.templates_by_tag = {}
        
        # Index templates
        for template in self.templates:
            # By name
            self.templates_by_name[template.name] = template
            
            # By type
            if template.type not in self.templates_by_type:
                self.templates_by_type[template.type] = []
            self.templates_by_type[template.type].append(template)
            
            # By tag
            for tag in template.tags:
                tag = tag.lower()  # Case-insensitive tags
                if tag not in self.templates_by_tag:
                    self.templates_by_tag[tag] = []
                self.templates_by_tag[tag].append(template)
    
    def _load_default_templates(self) -> None:
        """Load default templates"""
        self.templates = [
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
""",
                enabled=True,
                stats={
                    "usage_count": 0,
                    "success_count": 0,
                    "avg_latency_ms": 0,
                    "last_used": None
                }
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
""",
                enabled=True,
                stats={
                    "usage_count": 0,
                    "success_count": 0,
                    "avg_latency_ms": 0,
                    "last_used": None
                }
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
  "product": {
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
""",
                enabled=True,
                stats={
                    "usage_count": 0,
                    "success_count": 0,
                    "avg_latency_ms": 0,
                    "last_used": None
                }
            )
        ]
        
        self.logger.info("Loaded default templates")

