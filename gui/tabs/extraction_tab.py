#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QLabel, QPushButton, QDoubleSpinBox, QSpinBox, 
    QCheckBox, QTabWidget, QLineEdit, QComboBox,
    QFormLayout, QScrollArea, QListWidget, QListWidgetItem,
    QTextEdit, QSplitter, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QFont, QIcon

class ExtractionTab(QWidget):
    """
    Tab for configuring extraction parameters
    """
    # Define signals
    extraction_config_changed = Signal(dict)  # All extraction settings
    
    def __init__(self):
        super().__init__()
        
        # Keep track of the current configuration
        self.current_config = {
            "compatibility": {
                "enabled": True,
                "threshold": 0.7,
                "max_context_length": 150
            },
            "technical": {
                "enabled": True,
                "threshold": 0.7,
                "max_context_length": 150
            },
            "faq": {
                "enabled": False
            },
            "chunk_size": 15000,
            "chunk_overlap": 2000,
            "max_file_size": 5000000
        }
        
        self.setup_ui()
        
        # Apply initial config to UI
        self.update_ui_from_config()
    
    def setup_ui(self):
        """Setup the extraction configuration UI"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # Create a splitter for left panel (controls) and right panel (preview)
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel with scrollable controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        # Create scroll area for controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        # Scroll content widget
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(15)
        
        # Main settings tabs
        self.settings_tabs = QTabWidget()
        
        # Compatibility tab
        compatibility_widget = QWidget()
        compatibility_layout = QVBoxLayout(compatibility_widget)
        
        # Basic settings
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout(basic_group)
        
        self.compatibility_enabled = QCheckBox("Enable Compatibility Extraction")
        self.compatibility_enabled.setChecked(True)
        self.compatibility_enabled.stateChanged.connect(self.on_config_changed)
        basic_layout.addRow("", self.compatibility_enabled)
        
        self.compatibility_threshold = QDoubleSpinBox()
        self.compatibility_threshold.setRange(0.1, 1.0)
        self.compatibility_threshold.setSingleStep(0.05)
        self.compatibility_threshold.setValue(0.7)
        self.compatibility_threshold.valueChanged.connect(self.on_config_changed)
        basic_layout.addRow("Confidence Threshold:", self.compatibility_threshold)
        
        self.compatibility_context_length = QSpinBox()
        self.compatibility_context_length.setRange(10, 500)
        self.compatibility_context_length.setSingleStep(10)
        self.compatibility_context_length.setValue(150)
        self.compatibility_context_length.valueChanged.connect(self.on_config_changed)
        basic_layout.addRow("Max Context Length:", self.compatibility_context_length)
        
        compatibility_layout.addWidget(basic_group)
        
        # Advanced settings
        advanced_group = QGroupBox("Required Fields")
        advanced_layout = QVBoxLayout(advanced_group)
        
        self.relation_type_required = QCheckBox("Relation Type")
        self.relation_type_required.setChecked(True)
        self.relation_type_required.setEnabled(False)  # Always required
        advanced_layout.addWidget(self.relation_type_required)
        
        self.related_product_required = QCheckBox("Related Product")
        self.related_product_required.setChecked(True)
        self.related_product_required.setEnabled(False)  # Always required
        advanced_layout.addWidget(self.related_product_required)
        
        self.context_required = QCheckBox("Context")
        self.context_required.setChecked(True)
        self.context_required.stateChanged.connect(self.on_config_changed)
        advanced_layout.addWidget(self.context_required)
        
        self.confidence_required = QCheckBox("Confidence Score")
        self.confidence_required.setChecked(True)
        self.confidence_required.stateChanged.connect(self.on_config_changed)
        advanced_layout.addWidget(self.confidence_required)
        
        compatibility_layout.addWidget(advanced_group)
        
        # Add extra context options
        extra_context_group = QGroupBox("Extra Context")
        extra_context_layout = QFormLayout(extra_context_group)
        
        self.extra_context_enabled = QCheckBox("Extract Extra Context")
        self.extra_context_enabled.setChecked(True)
        self.extra_context_enabled.stateChanged.connect(self.on_config_changed)
        extra_context_layout.addRow("", self.extra_context_enabled)
        
        self.extra_context_size = QSpinBox()
        self.extra_context_size.setRange(1, 10)
        self.extra_context_size.setValue(3)
        self.extra_context_size.valueChanged.connect(self.on_config_changed)
        extra_context_layout.addRow("Sentences Before/After:", self.extra_context_size)
        
        compatibility_layout.addWidget(extra_context_group)
        compatibility_layout.addStretch()
        
        self.settings_tabs.addTab(compatibility_widget, "Compatibility")
        
        # Technical tab
        technical_widget = QWidget()
        technical_layout = QVBoxLayout(technical_widget)
        
        # Basic settings for technical
        tech_basic_group = QGroupBox("Basic Settings")
        tech_basic_layout = QFormLayout(tech_basic_group)
        
        self.technical_enabled = QCheckBox("Enable Technical Specifications Extraction")
        self.technical_enabled.setChecked(True)
        self.technical_enabled.stateChanged.connect(self.on_config_changed)
        tech_basic_layout.addRow("", self.technical_enabled)
        
        self.technical_threshold = QDoubleSpinBox()
        self.technical_threshold.setRange(0.1, 1.0)
        self.technical_threshold.setSingleStep(0.05)
        self.technical_threshold.setValue(0.7)
        self.technical_threshold.valueChanged.connect(self.on_config_changed)
        tech_basic_layout.addRow("Confidence Threshold:", self.technical_threshold)
        
        self.technical_context_length = QSpinBox()
        self.technical_context_length.setRange(10, 500)
        self.technical_context_length.setSingleStep(10)
        self.technical_context_length.setValue(150)
        self.technical_context_length.valueChanged.connect(self.on_config_changed)
        tech_basic_layout.addRow("Max Context Length:", self.technical_context_length)
        
        technical_layout.addWidget(tech_basic_group)
        
        # Required fields for technical
        tech_fields_group = QGroupBox("Required Fields")
        tech_fields_layout = QVBoxLayout(tech_fields_group)
        
        self.category_required = QCheckBox("Category")
        self.category_required.setChecked(True)
        self.category_required.setEnabled(False)  # Always required
        tech_fields_layout.addWidget(self.category_required)
        
        self.name_required = QCheckBox("Name")
        self.name_required.setChecked(True)
        self.name_required.setEnabled(False)  # Always required
        tech_fields_layout.addWidget(self.name_required)
        
        self.raw_value_required = QCheckBox("Raw Value")
        self.raw_value_required.setChecked(True)
        self.raw_value_required.setEnabled(False)  # Always required
        tech_fields_layout.addWidget(self.raw_value_required)
        
        self.unit_normalization = QCheckBox("Unit Normalization")
        self.unit_normalization.setChecked(True)
        self.unit_normalization.stateChanged.connect(self.on_config_changed)
        tech_fields_layout.addWidget(self.unit_normalization)
        
        technical_layout.addWidget(tech_fields_group)
        technical_layout.addStretch()
        
        self.settings_tabs.addTab(technical_widget, "Technical")
        
        # FAQ tab
        faq_widget = QWidget()
        faq_layout = QVBoxLayout(faq_widget)
        
        # Basic settings for FAQ
        faq_basic_group = QGroupBox("Basic Settings")
        faq_basic_layout = QFormLayout(faq_basic_group)
        
        self.faq_enabled = QCheckBox("Enable FAQ Data Extraction")
        self.faq_enabled.setChecked(False)
        self.faq_enabled.stateChanged.connect(self.on_config_changed)
        faq_basic_layout.addRow("", self.faq_enabled)
        
        faq_layout.addWidget(faq_basic_group)
        
        # FAQ types
        faq_types_group = QGroupBox("FAQ Types")
        faq_types_layout = QVBoxLayout(faq_types_group)
        
        self.product_compatibility_faq = QCheckBox("Product Compatibility Questions")
        self.product_compatibility_faq.setChecked(True)
        self.product_compatibility_faq.stateChanged.connect(self.on_config_changed)
        faq_types_layout.addWidget(self.product_compatibility_faq)
        
        self.specifications_faq = QCheckBox("Specifications Questions")
        self.specifications_faq.setChecked(True)
        self.specifications_faq.stateChanged.connect(self.on_config_changed)
        faq_types_layout.addWidget(self.specifications_faq)
        
        self.installation_faq = QCheckBox("Installation & Setup Questions")
        self.installation_faq.setChecked(False)
        self.installation_faq.stateChanged.connect(self.on_config_changed)
        faq_types_layout.addWidget(self.installation_faq)
        
        self.troubleshooting_faq = QCheckBox("Troubleshooting Questions")
        self.troubleshooting_faq.setChecked(False)
        self.troubleshooting_faq.stateChanged.connect(self.on_config_changed)
        faq_types_layout.addWidget(self.troubleshooting_faq)
        
        faq_layout.addWidget(faq_types_group)
        faq_layout.addStretch()
        
        self.settings_tabs.addTab(faq_widget, "FAQ")
        
        # Chunking tab
        chunking_widget = QWidget()
        chunking_layout = QVBoxLayout(chunking_widget)
        
        # Chunking settings
        chunking_group = QGroupBox("Text Chunking Settings")
        chunking_form_layout = QFormLayout(chunking_group)
        
        self.chunk_size = QSpinBox()
        self.chunk_size.setRange(1000, 50000)
        self.chunk_size.setSingleStep(1000)
        self.chunk_size.setValue(15000)
        self.chunk_size.valueChanged.connect(self.on_config_changed)
        chunking_form_layout.addRow("Chunk Size (chars):", self.chunk_size)
        
        self.chunk_overlap = QSpinBox()
        self.chunk_overlap.setRange(0, 10000)
        self.chunk_overlap.setSingleStep(500)
        self.chunk_overlap.setValue(2000)
        self.chunk_overlap.valueChanged.connect(self.on_config_changed)
        chunking_form_layout.addRow("Chunk Overlap (chars):", self.chunk_overlap)
        
        self.max_file_size = QSpinBox()
        self.max_file_size.setRange(100000, 50000000)
        self.max_file_size.setSingleStep(1000000)
        self.max_file_size.setValue(5000000)
        self.max_file_size.setSuffix(" bytes")
        self.max_file_size.valueChanged.connect(self.on_config_changed)
        chunking_form_layout.addRow("Max File Size:", self.max_file_size)
        
        chunking_layout.addWidget(chunking_group)
        
        # Chunking strategies
        strategy_group = QGroupBox("Chunking Strategy")
        strategy_layout = QFormLayout(strategy_group)
        
        self.chunking_strategy = QComboBox()
        self.chunking_strategy.addItems([
            "Fixed Size with Overlap",
            "Sentence Boundaries",
            "Paragraph Boundaries"
        ])
        self.chunking_strategy.currentIndexChanged.connect(self.on_config_changed)
        strategy_layout.addRow("Strategy:", self.chunking_strategy)
        
        self.ensure_complete_sentences = QCheckBox("Ensure Complete Sentences")
        self.ensure_complete_sentences.setChecked(True)
        self.ensure_complete_sentences.stateChanged.connect(self.on_config_changed)
        strategy_layout.addRow("", self.ensure_complete_sentences)
        
        chunking_layout.addWidget(strategy_group)
        chunking_layout.addStretch()
        
        self.settings_tabs.addTab(chunking_widget, "Chunking")
        
        # Add settings tabs to scroll layout
        scroll_layout.addWidget(self.settings_tabs)
        
        # Add action buttons
        action_layout = QHBoxLayout()
        
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_to_defaults)
        action_layout.addWidget(self.reset_button)
        
        self.apply_button = QPushButton("Apply Changes")
        self.apply_button.setProperty("class", "primary")
        self.apply_button.clicked.connect(self.apply_changes)
        action_layout.addWidget(self.apply_button)
        
        scroll_layout.addLayout(action_layout)
        
        # Set scroll content and add to left layout
        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll)
        
        # Right panel with preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Preview area
        preview_group = QGroupBox("Configuration Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Config visualization
        self.config_preview = QTextEdit()
        self.config_preview.setReadOnly(True)
        self.config_preview.setProperty("monospace", True)  # Apply monospace style
        self.config_preview.setMinimumWidth(400)
        preview_layout.addWidget(self.config_preview)
        
        right_layout.addWidget(preview_group)
        
        # Add help/explainer
        help_group = QGroupBox("Extraction Types Explained")
        help_layout = QVBoxLayout(help_group)
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h3>Compatibility Extraction</h3>
        <p>Extracts information about which products are compatible with each other. 
        This includes relationships like "works with", "fits", "replaces", etc.</p>
        
        <h3>Technical Specifications</h3>
        <p>Extracts structured technical information about products, such as dimensions,
        materials, operating parameters, and other measurable attributes.</p>
        
        <h3>FAQ Data</h3>
        <p>Extracts frequently asked questions and answers from product documentation
        to create a knowledge base for customer support.</p>
        
        <h3>Text Chunking</h3>
        <p>Controls how large documents are split into smaller pieces for processing
        by the LLM. Proper chunking is essential for handling long documents.</p>
        """)
        help_layout.addWidget(help_text)
        
        right_layout.addWidget(help_group)
        
        # Add panels to splitter
        self.main_splitter.addWidget(left_widget)
        self.main_splitter.addWidget(right_widget)
        
        # Set initial splitter sizes (60% left, 40% right)
        self.main_splitter.setSizes([600, 400])
        
        # Add splitter to main layout
        layout.addWidget(self.main_splitter)
        
        # Update the preview with initial config
        self.update_config_preview()
    
    def update_ui_from_config(self):
        """Update UI elements based on current configuration"""
        # Compatibility
        self.compatibility_enabled.setChecked(self.current_config["compatibility"]["enabled"])
        self.compatibility_threshold.setValue(self.current_config["compatibility"]["threshold"])
        self.compatibility_context_length.setValue(self.current_config["compatibility"]["max_context_length"])
        
        # Technical
        self.technical_enabled.setChecked(self.current_config["technical"]["enabled"])
        self.technical_threshold.setValue(self.current_config["technical"]["threshold"])
        self.technical_context_length.setValue(self.current_config["technical"]["max_context_length"])
        
        # FAQ
        self.faq_enabled.setChecked(self.current_config["faq"]["enabled"])
        
        # Chunking
        self.chunk_size.setValue(self.current_config["chunk_size"])
        self.chunk_overlap.setValue(self.current_config["chunk_overlap"])
        self.max_file_size.setValue(self.current_config["max_file_size"])
        
        # Update the preview
        self.update_config_preview()
    
    def update_config_from_ui(self):
        """Update configuration based on UI elements"""
        # Compatibility
        self.current_config["compatibility"]["enabled"] = self.compatibility_enabled.isChecked()
        self.current_config["compatibility"]["threshold"] = self.compatibility_threshold.value()
        self.current_config["compatibility"]["max_context_length"] = self.compatibility_context_length.value()
        
        # Extra context
        self.current_config["compatibility"]["extra_context_enabled"] = self.extra_context_enabled.isChecked()
        self.current_config["compatibility"]["extra_context_size"] = self.extra_context_size.value()
        
        # Required fields
        required_fields = []
        if self.relation_type_required.isChecked():
            required_fields.append("relation_type")
        if self.related_product_required.isChecked():
            required_fields.append("related_product")
        if self.context_required.isChecked():
            required_fields.append("context")
        if self.confidence_required.isChecked():
            required_fields.append("confidence")
        
        self.current_config["compatibility"]["required_fields"] = required_fields
        
        # Technical
        self.current_config["technical"]["enabled"] = self.technical_enabled.isChecked()
        self.current_config["technical"]["threshold"] = self.technical_threshold.value()
        self.current_config["technical"]["max_context_length"] = self.technical_context_length.value()
        self.current_config["technical"]["unit_normalization"] = self.unit_normalization.isChecked()
        
        # Required fields for technical
        tech_required_fields = []
        if self.category_required.isChecked():
            tech_required_fields.append("category")
        if self.name_required.isChecked():
            tech_required_fields.append("name")
        if self.raw_value_required.isChecked():
            tech_required_fields.append("raw_value")
        
        self.current_config["technical"]["required_fields"] = tech_required_fields
        
        # FAQ
        self.current_config["faq"]["enabled"] = self.faq_enabled.isChecked()
        
        # FAQ types
        faq_types = []
        if self.product_compatibility_faq.isChecked():
            faq_types.append("product_compatibility")
        if self.specifications_faq.isChecked():
            faq_types.append("specifications")
        if self.installation_faq.isChecked():
            faq_types.append("installation")
        if self.troubleshooting_faq.isChecked():
            faq_types.append("troubleshooting")
        
        self.current_config["faq"]["types"] = faq_types
        
        # Chunking
        self.current_config["chunk_size"] = self.chunk_size.value()
        self.current_config["chunk_overlap"] = self.chunk_overlap.value()
        self.current_config["max_file_size"] = self.max_file_size.value()
        
        # Chunking strategy
        strategy_map = {
            0: "fixed_overlap",
            1: "sentence",
            2: "paragraph"
        }
        self.current_config["chunking_strategy"] = strategy_map[self.chunking_strategy.currentIndex()]
        self.current_config["ensure_complete_sentences"] = self.ensure_complete_sentences.isChecked()
        
        # Update the preview
        self.update_config_preview()
    
    def update_config_preview(self):
        """Update the configuration preview text"""
        import json
        
        # Format the configuration as JSON
        formatted_json = json.dumps(self.current_config, indent=4)
        
        # Set the preview text
        self.config_preview.setPlainText(formatted_json)
    
    def on_config_changed(self):
        """Handler for when any configuration option changes"""
        # Update the current config
        self.update_config_from_ui()
        
        # Enable the apply button
        self.apply_button.setEnabled(True)
    
    def reset_to_defaults(self):
        """Reset all settings to their default values"""
        # Reset to default config
        self.current_config = {
            "compatibility": {
                "enabled": True,
                "threshold": 0.7,
                "max_context_length": 150,
                "extra_context_enabled": True,
                "extra_context_size": 3,
                "required_fields": ["relation_type", "related_product", "context", "confidence"]
            },
            "technical": {
                "enabled": True,
                "threshold": 0.7,
                "max_context_length": 150,
                "unit_normalization": True,
                "required_fields": ["category", "name", "raw_value"]
            },
            "faq": {
                "enabled": False,
                "types": ["product_compatibility", "specifications"]
            },
            "chunk_size": 15000,
            "chunk_overlap": 2000,
            "max_file_size": 5000000,
            "chunking_strategy": "fixed_overlap",
            "ensure_complete_sentences": True
        }
        
        # Update UI from the config
        self.update_ui_from_config()
        
        # Enable the apply button
        self.apply_button.setEnabled(True)




    def apply_changes(self):
        """Apply the current configuration to the system"""
        # Make sure the config is up to date
        self.update_config_from_ui()
        
        # Emit the configuration changed signal
        self.extraction_config_changed.emit(self.current_config)
        
        # Update global config
        try:
            from config.ConfigManager import ConfigManager
            
            # Get the singleton instance
            config_manager = ConfigManager()
            
            # Update extraction config
            config_manager.set("extraction", self.current_config)
            
            # Show success in config preview
            current_preview = self.config_preview.toPlainText()
            self.config_preview.setPlainText(current_preview + "\n\n// Configuration successfully applied")
            
            # Disable apply button until next change
            self.apply_button.setEnabled(False)
            
        except Exception as e:
            # Show error in config preview
            current_preview = self.config_preview.toPlainText()
            self.config_preview.setPlainText(current_preview + f"\n\n// Error applying configuration: {str(e)}")
    
    def load_config(self, config=None):
        """
        Load configuration from ConfigManager or provided dict
        
        Args:
            config: Optional configuration dict to load
        """
        if config:
            # Load from provided dict
            self.current_config = config.copy()
        else:
            try:
                # Load from ConfigManager
                from config.ConfigManager import ConfigManager
                
                # Get the singleton instance
                config_manager = ConfigManager()
                
                # Get extraction config
                extraction_config = config_manager.get("extraction", {})
                
                if extraction_config:
                    self.current_config = extraction_config
            except Exception as e:
                # Show error in config preview
                self.config_preview.setPlainText(f"Error loading configuration: {str(e)}")
                return
        
        # Update UI from the loaded config
        self.update_ui_from_config()
        
        # Disable apply button since we just loaded
        self.apply_button.setEnabled(False)
    
    def run(self):
        """
        Run extraction with current configuration (called from main window)
        """
        # Make sure the config is up to date
        self.update_config_from_ui()
        
        # Ensure the configuration is applied
        self.apply_changes()
        
        # In a real implementation, this might perform a test extraction
        # or start a workflow with the current settings
        
        # For now, just show a confirmation
        self.config_preview.setPlainText(self.config_preview.toPlainText() + "\n\n// Ready to run extraction with these settings")

