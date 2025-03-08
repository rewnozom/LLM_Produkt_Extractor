#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QLabel, QPushButton, QSplitter, QListWidget, 
    QTextEdit, QLineEdit, QComboBox, QCheckBox,
    QDialog, QDialogButtonBox, QFormLayout, QTabWidget,
    QFileDialog, QMessageBox, QListWidgetItem, QMenu,
    QToolBar, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QIcon, QFont, QTextCursor, QColor, QAction

class PromptTagsDialog(QDialog):
    """Dialog for managing prompt tags"""
    
    def __init__(self, current_tags=None, parent=None):
        super().__init__(parent)
        
        self.current_tags = current_tags or []
        
        self.setWindowTitle("Manage Prompt Tags")
        self.setMinimumSize(400, 300)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Tags list
        self.tags_list = QListWidget()
        self.tags_list.setSelectionMode(QListWidget.MultiSelection)
        
        # Populate with common tags
        common_tags = [
            "extraction", "compatibility", "technical", "faq", 
            "validation", "correction", "combined", "optimized"
        ]
        
        for tag in common_tags:
            item = QListWidgetItem(tag)
            self.tags_list.addItem(item)
            
            # Check currently selected tags
            if tag in self.current_tags:
                item.setSelected(True)
        
        layout.addWidget(QLabel("Select tags for this prompt:"))
        layout.addWidget(self.tags_list)
        
        # Custom tag
        custom_layout = QHBoxLayout()
        self.custom_tag = QLineEdit()
        self.custom_tag.setPlaceholderText("Add custom tag...")
        custom_layout.addWidget(self.custom_tag)
        
        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add_custom_tag)
        custom_layout.addWidget(add_button)
        
        layout.addLayout(custom_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def add_custom_tag(self):
        """Add a custom tag to the list"""
        tag = self.custom_tag.text().strip().lower()
        
        if not tag:
            return
        
        # Check if already exists
        for i in range(self.tags_list.count()):
            if self.tags_list.item(i).text().lower() == tag:
                # Select it
                self.tags_list.item(i).setSelected(True)
                self.custom_tag.clear()
                return
        
        # Add new tag
        item = QListWidgetItem(tag)
        item.setSelected(True)
        self.tags_list.addItem(item)
        self.custom_tag.clear()
    
    def get_selected_tags(self):
        """Get the list of selected tags"""
        tags = []
        
        for i in range(self.tags_list.count()):
            item = self.tags_list.item(i)
            if item.isSelected():
                tags.append(item.text())
        
        return tags

class PromptTemplateEditor(QDialog):
    """Dialog for creating/editing prompt templates"""
    
    def __init__(self, template=None, parent=None):
        super().__init__(parent)
        
        self.template = template or {
            "name": "",
            "description": "",
            "type": "extraction",
            "tags": [],
            "template": "Analyze the following text and extract information:\n\n{text}\n\nProvide the result in JSON format.",
            "enabled": True
        }
        
        self.setWindowTitle("Edit Prompt Template" if template else "New Prompt Template")
        self.setMinimumSize(800, 600)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Template metadata
        metadata_group = QGroupBox("Template Metadata")
        metadata_layout = QFormLayout(metadata_group)
        
        self.name_input = QLineEdit(self.template.get("name", ""))
        metadata_layout.addRow("Name:", self.name_input)
        
        self.description_input = QLineEdit(self.template.get("description", ""))
        metadata_layout.addRow("Description:", self.description_input)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "extraction", "validation", "correction", "combined"
        ])
        self.type_combo.setCurrentText(self.template.get("type", "extraction"))
        metadata_layout.addRow("Type:", self.type_combo)
        
        # Tags display and edit button
        tags_layout = QHBoxLayout()
        self.tags_label = QLabel(", ".join(self.template.get("tags", [])) or "No tags")
        tags_layout.addWidget(self.tags_label)
        
        self.edit_tags_button = QPushButton("Edit Tags...")
        self.edit_tags_button.clicked.connect(self.edit_tags)
        tags_layout.addWidget(self.edit_tags_button)
        
        metadata_layout.addRow("Tags:", tags_layout)
        
        # Enabled checkbox
        self.enabled_checkbox = QCheckBox("Enabled")
        self.enabled_checkbox.setChecked(self.template.get("enabled", True))
        metadata_layout.addRow("", self.enabled_checkbox)
        
        layout.addWidget(metadata_group)
        
        # Template editor
        editor_group = QGroupBox("Template Content")
        editor_layout = QVBoxLayout(editor_group)
        
        self.template_editor = QTextEdit(self.template.get("template", ""))
        self.template_editor.setProperty("monospace", True)  # Apply monospace style
        self.template_editor.setMinimumHeight(300)
        editor_layout.addWidget(self.template_editor)
        
        # Template variables hint
        variables_label = QLabel(
            "Available variables: {text} - The content to analyze"
        )
        variables_label.setStyleSheet("color: #a3a3a3;")
        editor_layout.addWidget(variables_label)
        
        layout.addWidget(editor_group)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def edit_tags(self):
        """Open the tags dialog"""
        dialog = PromptTagsDialog(self.template.get("tags", []), self)
        if dialog.exec():
            tags = dialog.get_selected_tags()
            self.template["tags"] = tags
            self.tags_label.setText(", ".join(tags) or "No tags")
    
    def accept(self):
        """Override accept to validate inputs"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Template name is required")
            return
        
        template_text = self.template_editor.toPlainText().strip()
        if not template_text:
            QMessageBox.warning(self, "Validation Error", "Template content is required")
            return
        
        # Check that template contains the {text} variable
        if "{text}" not in template_text:
            QMessageBox.warning(self, "Validation Error", "Template must include the {text} variable")
            return
        
        # Update template
        self.template["name"] = name
        self.template["description"] = self.description_input.text().strip()
        self.template["type"] = self.type_combo.currentText()
        self.template["template"] = template_text
        self.template["enabled"] = self.enabled_checkbox.isChecked()
        
        # Call parent accept
        super().accept()
    
    def get_template(self):
        """Get the updated template"""
        return self.template


class PromptEditorTab(QWidget):
    """
    Tab for editing and managing prompt templates
    """
    # Define signals
    prompt_saved = Signal(dict)  # Emitted when a prompt is saved
    
    def __init__(self):
        super().__init__()
        
        # Keep track of loaded templates
        self.templates = []
        self.current_template = None
        
        self.setup_ui()
        
        # Load templates
        self.load_templates()
    
    def setup_ui(self):
        """Setup the prompt editor UI"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # Create a splitter for left panel (template list) and right panel (editor)
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Template List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        # Template list label
        left_layout.addWidget(QLabel("Prompt Templates"))
        
        # Filter input
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter templates...")
        self.filter_input.textChanged.connect(self.filter_templates)
        left_layout.addWidget(self.filter_input)
        
        # Template type filter
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "Extraction", "Validation", "Correction", "Combined"])
        self.type_filter.currentIndexChanged.connect(self.filter_templates)
        left_layout.addWidget(self.type_filter)
        
        # Template list
        self.template_list = QListWidget()
        self.template_list.setSelectionMode(QListWidget.SingleSelection)
        self.template_list.itemSelectionChanged.connect(self.on_template_selected)
        self.template_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.template_list.customContextMenuRequested.connect(self.show_template_context_menu)
        left_layout.addWidget(self.template_list)
        
        # Template actions
        template_actions = QHBoxLayout()
        
        self.new_template_button = QPushButton("New")
        self.new_template_button.clicked.connect(self.create_new_template)
        template_actions.addWidget(self.new_template_button)
        
        self.import_button = QPushButton("Import")
        self.import_button.clicked.connect(self.import_templates)
        template_actions.addWidget(self.import_button)
        
        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self.export_templates)
        template_actions.addWidget(self.export_button)
        
        left_layout.addLayout(template_actions)
        
        # Right panel - Template editor
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        
        # Editor tabs
        self.editor_tabs = QTabWidget()
        
        # Template details tab
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        
        # Template details form
        details_form = QFormLayout()
        
        self.name_label = QLabel("")
        details_form.addRow("Name:", self.name_label)
        
        self.description_label = QLabel("")
        details_form.addRow("Description:", self.description_label)
        
        self.type_label = QLabel("")
        details_form.addRow("Type:", self.type_label)
        
        self.tags_label = QLabel("")
        details_form.addRow("Tags:", self.tags_label)
        
        self.status_label = QLabel("")
        details_form.addRow("Status:", self.status_label)
        
        details_layout.addLayout(details_form)
        details_layout.addStretch()
        
        # Content preview
        content_group = QGroupBox("Template Content")
        content_layout = QVBoxLayout(content_group)
        
        self.template_preview = QTextEdit()
        self.template_preview.setReadOnly(True)
        self.template_preview.setProperty("monospace", True)  # Apply monospace style
        content_layout.addWidget(self.template_preview)
        
        details_layout.addWidget(content_group)
        
        self.editor_tabs.addTab(details_tab, "Details")
        
        # Performance tab
        performance_tab = QWidget()
        performance_layout = QVBoxLayout(performance_tab)
        
        # Performance stats
        stats_group = QGroupBox("Performance Statistics")
        stats_layout = QFormLayout(stats_group)
        
        self.usage_count_label = QLabel("0")
        stats_layout.addRow("Usage Count:", self.usage_count_label)
        
        self.success_rate_label = QLabel("0%")
        stats_layout.addRow("Success Rate:", self.success_rate_label)
        
        self.avg_latency_label = QLabel("0 ms")
        stats_layout.addRow("Avg. Latency:", self.avg_latency_label)
        
        self.last_used_label = QLabel("Never")
        stats_layout.addRow("Last Used:", self.last_used_label)
        
        performance_layout.addWidget(stats_group)
        
        # Performance chart placeholder
        chart_group = QGroupBox("Performance Over Time")
        chart_layout = QVBoxLayout(chart_group)
        
        chart_placeholder = QLabel("Performance chart will be displayed here")
        chart_placeholder.setAlignment(Qt.AlignCenter)
        chart_placeholder.setStyleSheet("color: #a3a3a3;")
        chart_layout.addWidget(chart_placeholder)
        
        performance_layout.addWidget(chart_group)
        performance_layout.addStretch()
        
        self.editor_tabs.addTab(performance_tab, "Performance")
        
        # Test tab
        test_tab = QWidget()
        test_layout = QVBoxLayout(test_tab)
        
        test_input_group = QGroupBox("Test Input")
        test_input_layout = QVBoxLayout(test_input_group)
        
        self.test_input = QTextEdit()
        self.test_input.setPlaceholderText("Enter test text here...")
        test_input_layout.addWidget(self.test_input)
        
        test_layout.addWidget(test_input_group)
        
        test_output_group = QGroupBox("Test Output")
        test_output_layout = QVBoxLayout(test_output_group)
        
        self.test_output = QTextEdit()
        self.test_output.setReadOnly(True)
        self.test_output.setPlaceholderText("Test output will appear here...")
        test_output_layout.addWidget(self.test_output)
        
        test_layout.addWidget(test_output_group)
        
        test_button_layout = QHBoxLayout()
        
        self.run_test_button = QPushButton("Run Test")
        self.run_test_button.setProperty("class", "primary")
        self.run_test_button.clicked.connect(self.run_template_test)
        test_button_layout.addWidget(self.run_test_button)
        
        test_layout.addLayout(test_button_layout)
        
        self.editor_tabs.addTab(test_tab, "Test")
        
        right_layout.addWidget(self.editor_tabs)
        
        # Edit controls
        edit_controls = QHBoxLayout()
        
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_current_template)
        edit_controls.addWidget(self.edit_button)
        
        self.duplicate_button = QPushButton("Duplicate")
        self.duplicate_button.clicked.connect(self.duplicate_current_template)
        edit_controls.addWidget(self.duplicate_button)
        
        self.delete_button = QPushButton("Delete")
        self.delete_button.setProperty("class", "destructive")
        self.delete_button.clicked.connect(self.delete_current_template)
        edit_controls.addWidget(self.delete_button)
        
        right_layout.addLayout(edit_controls)
        
        # Add panels to main splitter
        self.main_splitter.addWidget(left_widget)
        self.main_splitter.addWidget(right_widget)
        
        # Set initial splitter sizes (30% left, 70% right)
        self.main_splitter.setSizes([300, 700])
        
        # Add splitter to main layout
        layout.addWidget(self.main_splitter)
        
        # Initially disable edit controls
        self.edit_button.setEnabled(False)
        self.duplicate_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.run_test_button.setEnabled(False)
    
    def load_templates(self):

        """Load prompt templates from storage"""
        try:
            # Try to import the prompt manager to get templates
            from prompts.PromptTemplate import PromptTemplate
            import os
            import json
            
            # First check if we can get templates from PromptManager
            try:
                from prompts import PromptManager
                template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "prompts")
                manager = PromptManager(template_dir, None)
                self.templates = manager.get_all_prompts()
            except (ImportError, AttributeError):
                # Fall back to loading default templates
                default_templates = [
                    {
                        "name": "Default Compatibility Extraction",
                        "description": "Standard template for extracting compatibility information",
                        "type": "extraction",
                        "tags": ["extraction", "compatibility"],
                        "template": """Analyze the following product documentation and extract compatibility information.

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
                        "enabled": True,
                        "stats": {
                            "usage_count": 0,
                            "success_count": 0,
                            "avg_latency_ms": 0,
                            "last_used": None
                        }
                    },
                    {
                        "name": "Default Technical Specifications Extraction",
                        "description": "Standard template for extracting technical specifications",
                        "type": "extraction",
                        "tags": ["extraction", "technical"],
                        "template": """Analyze the following product documentation and extract technical specifications.

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
                        "enabled": True,
                        "stats": {
                            "usage_count": 0,
                            "success_count": 0,
                            "avg_latency_ms": 0,
                            "last_used": None
                        }
                    },
                    {
                        "name": "Combined Extraction",
                        "description": "Template for extracting combined information (product info, compatibility, technical)",
                        "type": "combined",
                        "tags": ["extraction", "combined", "compatibility", "technical"],
                        "template": """Analyze the following product documentation and extract structured information.

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
                        "enabled": True,
                        "stats": {
                            "usage_count": 0,
                            "success_count": 0,
                            "avg_latency_ms": 0,
                            "last_used": None
                        }
                    }
                ]
                
                self.templates = default_templates
            
            # Populate template list
            self.update_template_list()
            
        except Exception as e:
            # Show error
            QMessageBox.warning(self, "Error", f"Failed to load templates: {str(e)}")
    
    def update_template_list(self):
        """Update the template list with current templates"""
        # Clear the list
        self.template_list.clear()
        
        # Get current filter text
        filter_text = self.filter_input.text().lower()
        
        # Get type filter
        type_filter = self.type_filter.currentText().lower()
        if type_filter == "all types":
            type_filter = ""
        
        # Add templates that match filters
        for template in self.templates:
            name = template.get("name", "")
            template_type = template.get("type", "").lower()
            
            # Apply filters
            if filter_text and filter_text not in name.lower():
                continue
                
            if type_filter and type_filter != template_type:
                continue
            
            # Create list item
            item = QListWidgetItem(name)
            
            # Set data for the item
            item.setData(Qt.UserRole, template)
            
            # Add to list
            self.template_list.addItem(item)
    
    def filter_templates(self):
        """Filter the template list based on current filters"""
        self.update_template_list()
    
    def on_template_selected(self):
        """Handler for template selection changed"""
        selected_items = self.template_list.selectedItems()
        
        if not selected_items:
            # Clear details and disable buttons
            self.clear_template_details()
            self.edit_button.setEnabled(False)
            self.duplicate_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.run_test_button.setEnabled(False)
            return
        
        # Get the selected template
        self.current_template = selected_items[0].data(Qt.UserRole)
        
        # Update details
        self.update_template_details()
        
        # Enable buttons
        self.edit_button.setEnabled(True)
        self.duplicate_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.run_test_button.setEnabled(True)
    
    def clear_template_details(self):
        """Clear template details in the UI"""
        self.name_label.setText("")
        self.description_label.setText("")
        self.type_label.setText("")
        self.tags_label.setText("")
        self.status_label.setText("")
        self.template_preview.setText("")
        self.usage_count_label.setText("0")
        self.success_rate_label.setText("0%")
        self.avg_latency_label.setText("0 ms")
        self.last_used_label.setText("Never")
    
    def update_template_details(self):
        """Update UI with details of the current template"""
        if not self.current_template:
            self.clear_template_details()
            return
        
        # Update basic details
        self.name_label.setText(self.current_template.get("name", ""))
        self.description_label.setText(self.current_template.get("description", ""))
        self.type_label.setText(self.current_template.get("type", "").capitalize())
        self.tags_label.setText(", ".join(self.current_template.get("tags", [])) or "None")
        
        # Status
        status = "Enabled" if self.current_template.get("enabled", True) else "Disabled"
        status_color = "#10b981" if status == "Enabled" else "#f43f5e"
        self.status_label.setText(f"<span style='color:{status_color};'>{status}</span>")
        
        # Template content
        self.template_preview.setText(self.current_template.get("template", ""))
        
        # Stats
        stats = self.current_template.get("stats", {})
        self.usage_count_label.setText(str(stats.get("usage_count", 0)))
        
        success_count = stats.get("success_count", 0)
        usage_count = stats.get("usage_count", 0)
        
        if usage_count > 0:
            success_rate = (success_count / usage_count) * 100
            self.success_rate_label.setText(f"{success_rate:.1f}%")
        else:
            self.success_rate_label.setText("N/A")
        
        self.avg_latency_label.setText(f"{stats.get('avg_latency_ms', 0):.0f} ms")
        
        last_used = stats.get("last_used")
        self.last_used_label.setText(last_used if last_used else "Never")
    
    def create_new_template(self):
        """Create a new prompt template"""
        dialog = PromptTemplateEditor(None, self)
        if dialog.exec():
            template = dialog.get_template()
            
            # Add stats
            template["stats"] = {
                "usage_count": 0,
                "success_count": 0,
                "avg_latency_ms": 0,
                "last_used": None
            }
            
            # Add to templates
            self.templates.append(template)
            
            # Update list
            self.update_template_list()
            
            # Select the new template
            for i in range(self.template_list.count()):
                if self.template_list.item(i).text() == template["name"]:
                    self.template_list.setCurrentRow(i)
                    break
            
            # Save templates
            self.save_templates()
    
    def edit_current_template(self):
        """Edit the current template"""
        if not self.current_template:
            return
        
        # Create a copy to edit
        template_copy = self.current_template.copy()
        
        dialog = PromptTemplateEditor(template_copy, self)
        if dialog.exec():
            updated_template = dialog.get_template()
            
            # Update the template
            for key, value in updated_template.items():
                if key != "stats":  # Preserve stats
                    self.current_template[key] = value
            
            # Update list and details
            self.update_template_list()
            self.update_template_details()
            
            # Save templates
            self.save_templates()
    
    def duplicate_current_template(self):
        """Duplicate the current template"""
        if not self.current_template:
            return
        
        # Create a copy
        template_copy = self.current_template.copy()
        
        # Update name
        template_copy["name"] = f"{template_copy['name']} (Copy)"
        
        # Reset stats
        template_copy["stats"] = {
            "usage_count": 0,
            "success_count": 0,
            "avg_latency_ms": 0,
            "last_used": None
        }
        
        # Add to templates
        self.templates.append(template_copy)
        
        # Update list
        self.update_template_list()
        
        # Select the new template
        for i in range(self.template_list.count()):
            if self.template_list.item(i).text() == template_copy["name"]:
                self.template_list.setCurrentRow(i)
                break
        
        # Save templates
        self.save_templates()
    
    def delete_current_template(self):
        """Delete the current template"""
        if not self.current_template:
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Delete Template", 
            f"Are you sure you want to delete the template '{self.current_template['name']}'?",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Remove from templates
        self.templates.remove(self.current_template)
        
        # Clear current template
        self.current_template = None
        
        # Update list and details
        self.update_template_list()
        self.clear_template_details()
        
        # Save templates
        self.save_templates()
    
    def save_templates(self):
        """Save templates to storage"""
        try:
            import os
            import json
            
            # Create output directory if it doesn't exist
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "prompts")
            os.makedirs(output_dir, exist_ok=True)
            
            # Save templates to file
            templates_file = os.path.join(output_dir, "templates.json")
            with open(templates_file, 'w', encoding='utf-8') as f:
                json.dump(self.templates, f, indent=2)
            
            # Try to update PromptManager if available
            try:
                from prompts import PromptManager
                template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "prompts")
                manager = PromptManager(template_dir, None)
                manager.reload_prompts()
            except (ImportError, AttributeError):
                pass
            
        except Exception as e:
            # Show error
            QMessageBox.warning(self, "Error", f"Failed to save templates: {str(e)}")
    
    def import_templates(self):
        """Import templates from a file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Templates", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            import json
            
            # Read templates from file
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_templates = json.load(f)
            
            # Validate templates
            if not isinstance(imported_templates, list):
                raise ValueError("Invalid template file format")
            
            # Count valid templates
            valid_count = 0
            
            for template in imported_templates:
                if not isinstance(template, dict):
                    continue
                
                # Check required fields
                if "name" not in template or "template" not in template:
                    continue
                
                # Add template to our list
                self.templates.append(template)
                valid_count += 1
            
            # Update list
            self.update_template_list()
            
            # Save templates
            self.save_templates()
            
            # Show success message
            QMessageBox.information(
                self, "Import Successful", 
                f"Successfully imported {valid_count} templates."
            )
            
        except Exception as e:
            # Show error
            QMessageBox.warning(self, "Import Error", f"Failed to import templates: {str(e)}")
    
    def export_templates(self):
        """Export templates to a file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Templates", "", "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            import json
            
            # Write templates to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.templates, f, indent=2)
            
            # Show success message
            QMessageBox.information(
                self, "Export Successful", 
                f"Successfully exported {len(self.templates)} templates."
            )
            
        except Exception as e:
            # Show error
            QMessageBox.warning(self, "Export Error", f"Failed to export templates: {str(e)}")
    
    def show_template_context_menu(self, position):
        """Show context menu for template list"""
        # Get selected item
        item = self.template_list.itemAt(position)
        if not item:
            return
        
        # Get template
        template = item.data(Qt.UserRole)
        
        # Create context menu
        menu = QMenu(self)
        
        # Add actions
        edit_action = menu.addAction("Edit")
        edit_action.triggered.connect(self.edit_current_template)
        
        duplicate_action = menu.addAction("Duplicate")
        duplicate_action.triggered.connect(self.duplicate_current_template)
        
        # Toggle enabled/disabled
        if template.get("enabled", True):
            enable_action = menu.addAction("Disable")
            enable_action.triggered.connect(lambda: self.toggle_template_enabled(False))
        else:
            enable_action = menu.addAction("Enable")
            enable_action.triggered.connect(lambda: self.toggle_template_enabled(True))
        
        menu.addSeparator()
        
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(self.delete_current_template)
        
        # Show menu
        menu.exec(self.template_list.mapToGlobal(position))
    
    def toggle_template_enabled(self, enabled):
        """Toggle the enabled state of the current template"""
        if not self.current_template:
            return
        
        # Update template
        self.current_template["enabled"] = enabled
        
        # Update details
        self.update_template_details()
        
        # Save templates
        self.save_templates()
    
    def run_template_test(self):
        """Run a test with the current template"""
        if not self.current_template:
            return
        
        # Get test input
        test_input = self.test_input.toPlainText().strip()
        if not test_input:
            QMessageBox.warning(self, "Test Error", "Please enter test input text")
            return
        
        # Clear test output
        self.test_output.clear()
        self.test_output.append("Running test...")
        
        # Format the template
        template_text = self.current_template.get("template", "")
        formatted_text = template_text.format(text=test_input)
        
        # Start test in a background thread
        from PySide6.QtCore import QThread, Signal
        
        class TemplateTestRunner(QThread):
            result_ready = Signal(bool, str, int)
            
            def __init__(self, template, input_text, formatted_text):
                super().__init__()
                self.template = template
                self.input_text = input_text
                self.formatted_text = formatted_text
            
            def run(self):
                try:
                    # Import required modules
                    from client.LLMClient import LLMClient
                    import logging
                    
                    # Create a basic logger
                    logger = logging.getLogger("template_test")
                    handler = logging.StreamHandler()
                    logger.addHandler(handler)
                    
                    # Create LLM client with default config
                    from config.ConfigManager import ConfigManager
                    config_manager = ConfigManager()
                    llm_config = config_manager.get("llm", {})
                    
                    llm_client = LLMClient(llm_config, logger)
                    
                    # Send the prompt
                    start_time = time.time()
                    response = llm_client.get_completion(self.formatted_text)
                    latency_ms = int((time.time() - start_time) * 1000)
                    
                    if response.successful:
                        self.result_ready.emit(True, response.text, latency_ms)
                    else:
                        self.result_ready.emit(False, f"Error: {response.error}", latency_ms)
                except Exception as e:
                    self.result_ready.emit(False, f"Error: {str(e)}", 0)
        
        # Create and start the test runner
        self.test_runner = TemplateTestRunner(self.current_template, test_input, formatted_text)
        self.test_runner.result_ready.connect(self.on_test_result)
        self.test_runner.start()
    
    def on_test_result(self, success, result_text, latency_ms):
        """Handler for test results"""
        # Clear previous output
        self.test_output.clear()
        
        # Add heading
        if success:
            self.test_output.append("<h3 style='color: #10b981;'>Test Successful</h3>")
        else:
            self.test_output.append("<h3 style='color: #f43f5e;'>Test Failed</h3>")
        
        # Add latency
        self.test_output.append(f"<p>Latency: {latency_ms} ms</p>")
        
        # Add result
        self.test_output.append("<h4>Response:</h4>")
        
        # Format JSON if the response looks like JSON
        if result_text.strip().startswith("{") and result_text.strip().endswith("}"):
            try:
                import json
                formatted_json = json.dumps(json.loads(result_text), indent=2)
                self.test_output.append(f"<pre>{formatted_json}</pre>")
            except:
                # Just show as plain text if JSON parsing fails
                self.test_output.append(f"<pre>{result_text}</pre>")
        else:
            # Show as plain text
            self.test_output.append(f"<pre>{result_text}</pre>")
        
        # Update template stats
        if "stats" not in self.current_template:
            self.current_template["stats"] = {
                "usage_count": 0,
                "success_count": 0,
                "avg_latency_ms": 0,
                "last_used": None
            }
        
        stats = self.current_template["stats"]
        
        # Update usage count
        stats["usage_count"] = stats.get("usage_count", 0) + 1
        
        # Update success count if successful
        if success:
            stats["success_count"] = stats.get("success_count", 0) + 1
        
        # Update average latency
        avg_latency = stats.get("avg_latency_ms", 0)
        usage_count = stats.get("usage_count", 0)
        
        if usage_count > 1:
            # Calculate new average
            stats["avg_latency_ms"] = ((avg_latency * (usage_count - 1)) + latency_ms) / usage_count
        else:
            stats["avg_latency_ms"] = latency_ms
        
        # Update last used
        from datetime import datetime
        stats["last_used"] = datetime.now().isoformat()
        
        # Update UI
        self.update_template_details()
        
        # Save templates
        self.save_templates()
    
    def run(self):
        """
        Run the prompt editor (called from main window)
        """
        # In a real implementation, this might show a prompt test dialog
        if self.current_template:
            self.edit_current_template()
        else:
            self.create_new_template()

