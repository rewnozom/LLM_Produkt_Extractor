#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QFormLayout, QPushButton,
    QFrame
)
from PySide6.QtCore import Qt, Signal

class PropertiesPanel(QWidget):
    """
    Properties panel for displaying details about selected files and objects
    """
    # Define signals
    property_updated = Signal(str, object)  # (property_name, value)
    
    def __init__(self):
        super().__init__()
        
        self.current_file_path = None
        self.current_object = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the properties panel UI"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Title label
        self.title_label = QLabel("Properties")
        self.title_label.setProperty("heading", True)  # Apply heading style
        layout.addWidget(self.title_label)
        
        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # Create a widget for the scroll area
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)
        
        # Create a form layout for properties
        self.form_layout = QFormLayout()
        self.form_layout.setLabelAlignment(Qt.AlignLeft)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.form_layout.setSpacing(8)
        
        scroll_layout.addLayout(self.form_layout)
        
        # Spacer to push everything to the top
        scroll_layout.addStretch()
        
        # Set the scroll content
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # Buttons for actions
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_properties)
        button_layout.addWidget(self.edit_button)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_properties)
        button_layout.addWidget(self.refresh_button)
        
        layout.addLayout(button_layout)
        
        # Initialize with empty properties
        self.clear_properties()
    
    def clear_properties(self):
        """Clear all properties"""
        # Clear the form layout
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)
        
        self.current_file_path = None
        self.current_object = None
        
        # Add a placeholder message
        self.form_layout.addRow(QLabel("No item selected"))
    
    def update_properties(self, file_path=None, obj=None):
        """
        Update properties based on file path or object
        
        Args:
            file_path: Path to file or directory
            obj: Object with properties
        """
        # Clear existing properties
        self.clear_properties()
        
        if file_path:
            self.update_file_properties(file_path)
        elif obj:
            self.update_object_properties(obj)
    
    def update_file_properties(self, file_path):
        """
        Update properties based on file path
        
        Args:
            file_path: Path to file or directory
        """
        self.current_file_path = file_path
        
        # Get file information
        path = Path(file_path)
        
        if not path.exists():
            self.form_layout.addRow("Error:", QLabel("File does not exist"))
            return
        
        # Update title
        self.title_label.setText(f"Properties: {path.name}")
        
        # Basic properties
        self.form_layout.addRow("Name:", QLabel(path.name))
        self.form_layout.addRow("Path:", QLabel(str(path.parent)))
        
        # File vs directory specific properties
        if path.is_dir():
            # Directory properties
            self.form_layout.addRow("Type:", QLabel("Directory"))
            
            # Count files and subdirectories
            try:
                num_files = len([f for f in path.glob('*') if f.is_file()])
                num_dirs = len([f for f in path.glob('*') if f.is_dir()])
                
                self.form_layout.addRow("Files:", QLabel(str(num_files)))
                self.form_layout.addRow("Subdirectories:", QLabel(str(num_dirs)))
            except Exception as e:
                self.form_layout.addRow("Error:", QLabel(f"Could not read directory: {str(e)}"))
        else:
            # File properties
            self.form_layout.addRow("Type:", QLabel(path.suffix[1:].upper() if path.suffix else "Unknown"))
            
            # Size
            try:
                size = path.stat().st_size
                # Format size in appropriate units
                if size < 1024:
                    size_str = f"{size} bytes"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.2f} KB"
                elif size < 1024 * 1024 * 1024:
                    size_str = f"{size/(1024*1024):.2f} MB"
                else:
                    size_str = f"{size/(1024*1024*1024):.2f} GB"
                
                self.form_layout.addRow("Size:", QLabel(size_str))
            except Exception:
                self.form_layout.addRow("Size:", QLabel("Unknown"))
        
        # Common metadata
        try:
            stat = path.stat()
            # Format dates
            created = datetime.datetime.fromtimestamp(stat.st_ctime)
            modified = datetime.datetime.fromtimestamp(stat.st_mtime)
            accessed = datetime.datetime.fromtimestamp(stat.st_atime)
            
            date_format = "%Y-%m-%d %H:%M:%S"
            self.form_layout.addRow("Created:", QLabel(created.strftime(date_format)))
            self.form_layout.addRow("Modified:", QLabel(modified.strftime(date_format)))
            self.form_layout.addRow("Accessed:", QLabel(accessed.strftime(date_format)))
        except Exception:
            self.form_layout.addRow("Timestamps:", QLabel("Could not read timestamps"))
        
        # File content preview for supported files
        if path.is_file() and path.suffix.lower() in ['.txt', '.md', '.json', '.yml', '.yaml', '.csv']:
            self.add_file_preview(path)
    
    def add_file_preview(self, path):
        """
        Add a preview of the file content
        
        Args:
            path: Path object for the file
        """
        try:
            # Read the first few lines of the file
            with open(path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines()[:10]]
            
            if lines:
                # Create preview text
                preview = "\n".join(lines)
                if len(lines) >= 10:
                    preview += "\n..."
                
                # Create a label with preview
                preview_label = QLabel(preview)
                preview_label.setWordWrap(True)
                preview_label.setStyleSheet("background-color: rgba(38, 38, 38, 0.6); padding: 8px; border-radius: 4px;")
                
                self.form_layout.addRow("Preview:", preview_label)
            else:
                self.form_layout.addRow("Preview:", QLabel("(Empty file)"))
        except Exception as e:
            self.form_layout.addRow("Preview:", QLabel(f"Could not read file: {str(e)}"))
    
    def update_object_properties(self, obj):
        """
        Update properties based on object
        
        Args:
            obj: Object with properties
        """
        self.current_object = obj
        
        # Update title
        obj_type = type(obj).__name__
        self.title_label.setText(f"Properties: {obj_type}")
        
        # Add type
        self.form_layout.addRow("Type:", QLabel(obj_type))
        
        # Add all attributes
        for attr_name in dir(obj):
            # Skip private attributes and methods
            if attr_name.startswith('_') or callable(getattr(obj, attr_name)):
                continue
            
            try:
                value = getattr(obj, attr_name)
                # Convert value to string representation
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:100] + "..."
                
                self.form_layout.addRow(f"{attr_name}:", QLabel(value_str))
            except Exception:
                # Skip attributes that can't be accessed/converted
                pass
    
    def edit_properties(self):
        """Edit the selected properties (currently a placeholder)"""
        # This would open a dialog to edit properties, but for now it's just a placeholder
        if self.current_file_path:
            # Show a message that this feature is not implemented
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "Edit Properties", 
                f"Editing properties for {self.current_file_path} is not implemented yet."
            )
    
    def refresh_properties(self):
        """Refresh the current properties"""
        if self.current_file_path:
            self.update_file_properties(self.current_file_path)
        elif self.current_object:
            self.update_object_properties(self.current_object)