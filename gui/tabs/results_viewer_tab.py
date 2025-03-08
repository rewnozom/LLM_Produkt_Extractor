# gui/tabs/results_viewer_tab.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QLabel, QPushButton, QComboBox, 
    QLineEdit, QTextEdit, QGroupBox, QFormLayout, QTableWidget, 
    QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,
    QCheckBox, QFrame, QScrollArea, QMenu
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QIcon, QColor, QTextCursor, QAction

class ResultsViewerTab(QWidget):
    """
    Tab for viewing and analyzing extraction results
    """
    # Define signals
    result_selected = Signal(str, dict)  # product_id, result_data
    export_requested = Signal(str, str)  # product_id, format
    
    def __init__(self):
        super().__init__()
        
        # Keep track of loaded results
        self.result_files = []
        self.current_result = None
        self.filtered_results = []
        
        # Default output directory
        self.output_dir = Path("./output")
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the results viewer UI"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # Top controls for loading and filtering results
        controls_layout = QHBoxLayout()
        
        # Results source selection
        self.source_combo = QComboBox()
        self.source_combo.addItems([
            "Validated Results", 
            "Unvalidated Results", 
            "Failed Results",
            "All Results"
        ])
        self.source_combo.currentIndexChanged.connect(self.load_results)
        controls_layout.addWidget(QLabel("Source:"))
        controls_layout.addWidget(self.source_combo)
        
        # Filter input
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter by product ID or content...")
        self.filter_input.textChanged.connect(self.apply_filter)
        controls_layout.addWidget(QLabel("Filter:"))
        controls_layout.addWidget(self.filter_input)
        
        # Load button
        self.load_button = QPushButton("Load Results")
        self.load_button.clicked.connect(self.load_results)
        controls_layout.addWidget(self.load_button)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_results)
        controls_layout.addWidget(self.refresh_button)
        
        layout.addLayout(controls_layout)
        
        # Main content splitter
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Results list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Results list
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Product ID", "Status", "Date", "Relations", "Specs"])
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setSortingEnabled(True)
        self.results_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_tree.customContextMenuRequested.connect(self.show_result_context_menu)
        self.results_tree.itemSelectionChanged.connect(self.on_result_selected)
        
        # Set column widths
        self.results_tree.setColumnWidth(0, 150)  # Product ID
        self.results_tree.setColumnWidth(1, 100)  # Status
        self.results_tree.setColumnWidth(2, 150)  # Date
        self.results_tree.setColumnWidth(3, 80)   # Relations
        self.results_tree.setColumnWidth(4, 80)   # Specs
        
        left_layout.addWidget(self.results_tree)
        
        # Results stats
        self.stats_label = QLabel("Results: 0 total, 0 shown")
        left_layout.addWidget(self.stats_label)
        
        # Right side - Result details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tabs for different views of the current result
        self.detail_tabs = QTabWidget()
        
        # Overview tab
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        
        # Basic info group
        info_group = QGroupBox("Product Information")
        info_form = QFormLayout(info_group)
        
        self.product_id_label = QLabel("")
        info_form.addRow("Product ID:", self.product_id_label)
        
        self.status_label = QLabel("")
        info_form.addRow("Status:", self.status_label)
        
        self.date_label = QLabel("")
        info_form.addRow("Date:", self.date_label)
        
        self.processing_time_label = QLabel("")
        info_form.addRow("Processing Time:", self.processing_time_label)
        
        overview_layout.addWidget(info_group)
        
        # Extraction summary
        summary_group = QGroupBox("Extraction Summary")
        summary_layout = QFormLayout(summary_group)
        
        self.relations_count_label = QLabel("0")
        summary_layout.addRow("Compatibility Relations:", self.relations_count_label)
        
        self.specs_count_label = QLabel("0")
        summary_layout.addRow("Technical Specifications:", self.specs_count_label)
        
        self.errors_count_label = QLabel("0")
        summary_layout.addRow("Errors:", self.errors_count_label)
        
        self.warnings_count_label = QLabel("0")
        summary_layout.addRow("Warnings:", self.warnings_count_label)
        
        overview_layout.addWidget(summary_group)
        
        # Error list (if any)
        self.errors_group = QGroupBox("Errors")
        errors_layout = QVBoxLayout(self.errors_group)
        
        self.errors_text = QTextEdit()
        self.errors_text.setReadOnly(True)
        errors_layout.addWidget(self.errors_text)
        
        overview_layout.addWidget(self.errors_group)
        self.errors_group.setVisible(False)
        
        # Add to tabs
        self.detail_tabs.addTab(overview_tab, "Overview")
        
        # Compatibility tab
        compatibility_tab = QWidget()
        compatibility_layout = QVBoxLayout(compatibility_tab)
        
        self.relations_table = QTableWidget()
        self.relations_table.setColumnCount(4)
        self.relations_table.setHorizontalHeaderLabels([
            "Relation Type", "Related Product", "Confidence", "Context"
        ])
        self.relations_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        
        compatibility_layout.addWidget(self.relations_table)
        
        # Add to tabs
        self.detail_tabs.addTab(compatibility_tab, "Compatibility")
        
        # Technical Specifications tab
        specs_tab = QWidget()
        specs_layout = QVBoxLayout(specs_tab)
        
        self.specs_table = QTableWidget()
        self.specs_table.setColumnCount(5)
        self.specs_table.setHorizontalHeaderLabels([
            "Category", "Name", "Value", "Unit", "Confidence"
        ])
        self.specs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        
        specs_layout.addWidget(self.specs_table)
        
        # Add to tabs
        self.detail_tabs.addTab(specs_tab, "Specifications")
        
        # Raw JSON tab
        json_tab = QWidget()
        json_layout = QVBoxLayout(json_tab)
        
        self.json_viewer = QTextEdit()
        self.json_viewer.setReadOnly(True)
        self.json_viewer.setProperty("monospace", True)  # Apply monospace style
        
        json_layout.addWidget(self.json_viewer)
        
        # Add to tabs
        self.detail_tabs.addTab(json_tab, "Raw JSON")
        
        # Add tabs to right layout
        right_layout.addWidget(self.detail_tabs)
        
        # Export buttons
        export_layout = QHBoxLayout()
        
        self.export_csv_button = QPushButton("Export as CSV")
        self.export_csv_button.clicked.connect(lambda: self.export_current_result("csv"))
        export_layout.addWidget(self.export_csv_button)
        
        self.export_json_button = QPushButton("Export as JSON")
        self.export_json_button.clicked.connect(lambda: self.export_current_result("json"))
        export_layout.addWidget(self.export_json_button)
        
        self.export_markdown_button = QPushButton("Export as Markdown")
        self.export_markdown_button.clicked.connect(lambda: self.export_current_result("markdown"))
        export_layout.addWidget(self.export_markdown_button)
        
        right_layout.addLayout(export_layout)
        
        # Add widgets to splitter
        self.main_splitter.addWidget(left_widget)
        self.main_splitter.addWidget(right_widget)
        
        # Set initial splitter sizes (40% left, 60% right)
        self.main_splitter.setSizes([400, 600])
        
        # Add splitter to main layout
        layout.addWidget(self.main_splitter)
        
        # Initialize with disabled detail view
        self.enable_detail_view(False)
        
        # Try to load results from default locations
        self.try_load_default_results()
    
    def try_load_default_results(self):
        """Try to load results from standard output directories"""
        # Try to find the output directory
        possible_paths = [
            Path("./output"),
            Path("../output"),
            Path(os.path.expanduser("~")) / "product_extractor/output"
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                self.output_dir = path
                break
        
        # Load results
        self.load_results()
    
    def load_results(self):
        """Load results based on selected source"""
        source_index = self.source_combo.currentIndex()
        
        # Clear existing results
        self.results_tree.clear()
        self.result_files = []
        
        # Determine which directories to search based on source
        if source_index == 0:  # Validated
            dirs = [self.output_dir / "validated"]
        elif source_index == 1:  # Unvalidated
            dirs = [self.output_dir / "unvalidated"]
        elif source_index == 2:  # Failed
            dirs = [self.output_dir / "failed"]
        else:  # All
            dirs = [
                self.output_dir / "validated",
                self.output_dir / "unvalidated",
                self.output_dir / "failed",
                self.output_dir / "corrected"
            ]
        
        # Load results from each directory
        for dir_path in dirs:
            if not dir_path.exists() or not dir_path.is_dir():
                continue
            
            # Find all JSON files
            json_files = list(dir_path.glob("*.json"))
            
            for file_path in json_files:
                try:
                    # Load the result file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        result_data = json.load(f)
                    
                    # Check if it has the expected structure
                    if "product_id" not in result_data or "status" not in result_data:
                        continue
                    
                    # Add to our list of results
                    self.result_files.append({
                        "file_path": file_path,
                        "data": result_data,
                        "directory": dir_path.name
                    })
                except Exception as e:
                    print(f"Error loading result file {file_path}: {str(e)}")
        
        # Apply any filter
        self.apply_filter()
    
    def apply_filter(self):
        """Apply filter to results"""
        filter_text = self.filter_input.text().lower()
        
        # Clear the tree
        self.results_tree.clear()
        self.filtered_results = []
        
        # Apply filter and add matching results to tree
        for result in self.result_files:
            data = result["data"]
            product_id = data.get("product_id", "")
            status = data.get("status", "")
            
            # Check if matches filter
            if filter_text and filter_text not in product_id.lower() and filter_text not in status.lower():
                # Also search in compatibility relations and specifications
                found_in_relations = False
                if "compatibility" in data and "relations" in data["compatibility"]:
                    for relation in data["compatibility"]["relations"]:
                        if isinstance(relation, dict):
                            related_product = relation.get("related_product", "")
                            if isinstance(related_product, str) and filter_text in related_product.lower():
                                found_in_relations = True
                                break
                
                found_in_specs = False
                if "technical" in data and "specifications" in data["technical"]:
                    for spec in data["technical"]["specifications"]:
                        if isinstance(spec, dict):
                            name = spec.get("name", "")
                            value = spec.get("raw_value", "")
                            if (filter_text in name.lower() or 
                                (isinstance(value, str) and filter_text in value.lower())):
                                found_in_specs = True
                                break
                
                if not found_in_relations and not found_in_specs:
                    continue
            
            # Add to filtered results
            self.filtered_results.append(result)
            
            # Create tree item
            item = QTreeWidgetItem([
                product_id,
                status,
                self.format_date(data.get("metadata", {}).get("created_at", "")),
                str(len(data.get("compatibility", {}).get("relations", []))),
                str(len(data.get("technical", {}).get("specifications", [])))
            ])
            
            # Set color based on status
            if status.lower() == "validated":
                item.setForeground(1, QColor("#10b981"))  # Green
            elif status.lower() == "failed":
                item.setForeground(1, QColor("#f43f5e"))  # Red
            elif status.lower() == "partially_completed":
                item.setForeground(1, QColor("#f59e0b"))  # Amber
            
            # Store the index in user data
            item.setData(0, Qt.UserRole, len(self.filtered_results) - 1)
            
            # Add to tree
            self.results_tree.addItem(item)
        
        # Update stats
        self.stats_label.setText(f"Results: {len(self.filtered_results)} shown, {len(self.result_files)} total")
        
        # Clear current result
        self.current_result = None
        self.enable_detail_view(False)
    
    def refresh_results(self):
        """Refresh results by reloading from disk"""
        self.load_results()
    
    def on_result_selected(self):
        """Handler for result selection in tree"""
        selected_items = self.results_tree.selectedItems()
        if not selected_items:
            self.enable_detail_view(False)
            return
        
        # Get the selected result
        item = selected_items[0]
        index = item.data(0, Qt.UserRole)
        
        if index is None or index < 0 or index >= len(self.filtered_results):
            self.enable_detail_view(False)
            return
        
        # Get the result data
        self.current_result = self.filtered_results[index]
        result_data = self.current_result["data"]
        
        # Update the detail view
        self.update_detail_view(result_data)
        
        # Enable the detail view
        self.enable_detail_view(True)
        
        # Emit the result selected signal
        self.result_selected.emit(result_data.get("product_id", ""), result_data)
    
    def update_detail_view(self, result_data):
        """Update the detail view with the selected result"""
        # Update overview tab
        self.product_id_label.setText(result_data.get("product_id", ""))
        self.status_label.setText(result_data.get("status", ""))
        
        # Apply status color
        status = result_data.get("status", "").lower()
        if status == "validated":
            self.status_label.setStyleSheet("color: #10b981;")  # Green
        elif status == "failed":
            self.status_label.setStyleSheet("color: #f43f5e;")  # Red
        elif status == "partially_completed":
            self.status_label.setStyleSheet("color: #f59e0b;")  # Amber
        else:
            self.status_label.setStyleSheet("")
        
        # Metadata
        metadata = result_data.get("metadata", {})
        self.date_label.setText(self.format_date(metadata.get("created_at", "")))
        
        processing_time = metadata.get("processing_time_ms", 0)
        if processing_time > 1000:
            self.processing_time_label.setText(f"{processing_time/1000:.2f} seconds")
        else:
            self.processing_time_label.setText(f"{processing_time} ms")
        
        # Compatibility relations
        relations = result_data.get("compatibility", {}).get("relations", [])
        relation_count = len(relations)
        self.relations_count_label.setText(str(relation_count))
        
        # Technical specifications
        specs = result_data.get("technical", {}).get("specifications", [])
        specs_count = len(specs)
        self.specs_count_label.setText(str(specs_count))
        
        # Errors and warnings
        errors = result_data.get("errors", [])
        warnings = result_data.get("warnings", [])
        self.errors_count_label.setText(str(len(errors)))
        self.warnings_count_label.setText(str(len(warnings)))
        
        # Show/hide errors group
        if errors:
            self.errors_group.setVisible(True)
            self.errors_text.clear()
            for error in errors:
                self.errors_text.append(f"• {error}")
        else:
            self.errors_group.setVisible(False)
        
        # Update compatibility tab
        self.relations_table.setRowCount(0)
        for i, relation in enumerate(relations):
            if not isinstance(relation, dict):
                continue
                
            self.relations_table.insertRow(i)
            
            # Relation type
            relation_type = relation.get("relation_type", "")
            self.relations_table.setItem(i, 0, QTableWidgetItem(relation_type))
            
            # Related product
            related_product = relation.get("related_product", "")
            if isinstance(related_product, dict):
                # Handle structured product info
                name = related_product.get("name", "")
                article = related_product.get("article_number", "")
                
                if article:
                    product_text = f"{name} ({article})"
                else:
                    product_text = name
            else:
                product_text = str(related_product)
                
            self.relations_table.setItem(i, 1, QTableWidgetItem(product_text))
            
            # Confidence
            confidence = relation.get("confidence", 0)
            confidence_item = QTableWidgetItem(f"{confidence:.2f}" if isinstance(confidence, (int, float)) else str(confidence))
            self.relations_table.setItem(i, 2, confidence_item)
            
            # Context
            context = relation.get("context", "")
            self.relations_table.setItem(i, 3, QTableWidgetItem(context))
        
        # Update technical specifications tab
        self.specs_table.setRowCount(0)
        for i, spec in enumerate(specs):
            if not isinstance(spec, dict):
                continue
                
            self.specs_table.insertRow(i)
            
            # Category
            category = spec.get("category", "")
            self.specs_table.setItem(i, 0, QTableWidgetItem(category))
            
            # Name
            name = spec.get("name", "")
            self.specs_table.setItem(i, 1, QTableWidgetItem(name))
            
            # Value
            value = spec.get("raw_value", "")
            self.specs_table.setItem(i, 2, QTableWidgetItem(str(value)))
            
            # Unit
            unit = spec.get("unit", "")
            self.specs_table.setItem(i, 3, QTableWidgetItem(unit))
            
            # Confidence
            confidence = spec.get("confidence", 0)
            confidence_item = QTableWidgetItem(f"{confidence:.2f}" if isinstance(confidence, (int, float)) else str(confidence))
            self.specs_table.setItem(i, 4, confidence_item)
        
        # Update raw JSON tab with pretty-printed JSON
        try:
            pretty_json = json.dumps(result_data, indent=2, ensure_ascii=False)
            self.json_viewer.setText(pretty_json)
        except Exception as e:
            self.json_viewer.setText(f"Error formatting JSON: {str(e)}")
    
    def enable_detail_view(self, enable):
        """Enable or disable the detail view"""
        self.detail_tabs.setEnabled(enable)
        self.export_csv_button.setEnabled(enable)
        self.export_json_button.setEnabled(enable)
        self.export_markdown_button.setEnabled(enable)
    
    def show_result_context_menu(self, position):
        """Show context menu for results tree"""
        # Get selected item
        item = self.results_tree.itemAt(position)
        if not item:
            return
        
        # Get the selected result
        index = item.data(0, Qt.UserRole)
        if index is None or index < 0 or index >= len(self.filtered_results):
            return
        
        # Create context menu
        menu = QMenu(self)
        
        view_action = menu.addAction("View Details")
        view_action.triggered.connect(self.on_result_selected)
        
        menu.addSeparator()
        
        export_menu = menu.addMenu("Export As")
        csv_action = export_menu.addAction("CSV")
        csv_action.triggered.connect(lambda: self.export_current_result("csv"))
        
        json_action = export_menu.addAction("JSON")
        json_action.triggered.connect(lambda: self.export_current_result("json"))
        
        markdown_action = export_menu.addAction("Markdown")
        markdown_action.triggered.connect(lambda: self.export_current_result("markdown"))
        
        menu.addSeparator()
        
        open_file_action = menu.addAction("Open Result File")
        open_file_action.triggered.connect(lambda: self.open_result_file(index))
        
        # Show menu
        menu.exec(self.results_tree.viewport().mapToGlobal(position))
    
    def open_result_file(self, index):
        """Open the result file in system editor"""
        if index < 0 or index >= len(self.filtered_results):
            return
        
        result = self.filtered_results[index]
        file_path = result["file_path"]
        
        # Use system default application to open the file
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))
    
    def export_current_result(self, format_type):
        """Export the current result in the specified format"""
        if not self.current_result:
            return
        
        # Get result data
        result_data = self.current_result["data"]
        product_id = result_data.get("product_id", "unknown")
        
        # Default filename based on format
        default_name = f"{product_id}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if format_type == "csv":
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export as CSV", default_name + ".csv", "CSV Files (*.csv)"
            )
            
            if file_path:
                self.export_to_csv(result_data, file_path)
                
        elif format_type == "json":
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export as JSON", default_name + ".json", "JSON Files (*.json)"
            )
            
            if file_path:
                self.export_to_json(result_data, file_path)
                
        elif format_type == "markdown":
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export as Markdown", default_name + ".md", "Markdown Files (*.md)"
            )
            
            if file_path:
                self.export_to_markdown(result_data, file_path)
        
        # Emit signal that export was requested
        self.export_requested.emit(product_id, format_type)
    
    def export_to_csv(self, result_data, file_path):
        """Export result data to CSV format"""
        try:
            import csv
            
            # First export compatibility relations
            relations = result_data.get("compatibility", {}).get("relations", [])
            if relations:
                relations_file = Path(file_path).with_stem(Path(file_path).stem + "_relations")
                
                with open(relations_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Write header
                    writer.writerow(['Relation Type', 'Related Product', 'Confidence', 'Context'])
                    
                    # Write data
                    for relation in relations:
                        if not isinstance(relation, dict):
                            continue
                        
                        # Format related product
                        related_product = relation.get("related_product", "")
                        if isinstance(related_product, dict):
                            name = related_product.get("name", "")
                            article = related_product.get("article_number", "")
                            
                            if article:
                                product_text = f"{name} ({article})"
                            else:
                                product_text = name
                        else:
                            product_text = str(related_product)
                        
                        writer.writerow([
                            relation.get("relation_type", ""),
                            product_text,
                            relation.get("confidence", ""),
                            relation.get("context", "")
                        ])
            
            # Then export technical specifications
            specs = result_data.get("technical", {}).get("specifications", [])
            if specs:
                specs_file = Path(file_path).with_stem(Path(file_path).stem + "_specs")
                
                with open(specs_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Write header
                    writer.writerow(['Category', 'Name', 'Value', 'Unit', 'Confidence'])
                    
                    # Write data
                    for spec in specs:
                        if not isinstance(spec, dict):
                            continue
                        
                        writer.writerow([
                            spec.get("category", ""),
                            spec.get("name", ""),
                            spec.get("raw_value", ""),
                            spec.get("unit", ""),
                            spec.get("confidence", "")
                        ])
            
            # Create a summary file
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(['Property', 'Value'])
                
                # Write summary data
                writer.writerow(['Product ID', result_data.get("product_id", "")])
                writer.writerow(['Status', result_data.get("status", "")])
                writer.writerow(['Created At', result_data.get("metadata", {}).get("created_at", "")])
                writer.writerow(['Processing Time (ms)', result_data.get("metadata", {}).get("processing_time_ms", "")])
                writer.writerow(['Relations Count', len(relations)])
                writer.writerow(['Specifications Count', len(specs)])
                writer.writerow(['Errors Count', len(result_data.get("errors", []))])
                writer.writerow(['Warnings Count', len(result_data.get("warnings", []))])
            
            QMessageBox.information(self, "Export Successful", f"Exported data to {file_path}")
            
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to export to CSV: {str(e)}")
    
    def export_to_json(self, result_data, file_path):
        """Export result data to JSON format"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "Export Successful", f"Exported data to {file_path}")
            
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to export to JSON: {str(e)}")
    
    def export_to_markdown(self, result_data, file_path):
        """Export result data to Markdown format"""
        try:
            # Generate Markdown content
            product_id = result_data.get("product_id", "unknown")
            status = result_data.get("status", "")
            metadata = result_data.get("metadata", {})
            
            md_lines = [
                f"# Product Analysis: {product_id}",
                "",
                f"**Status:** {status}",
                f"**Date:** {self.format_date(metadata.get('created_at', ''))}",
                f"**Processing Time:** {metadata.get('processing_time_ms', 0)} ms",
                ""
            ]
            
            # Add errors if any
            errors = result_data.get("errors", [])
            if errors:
                md_lines.extend([
                    "## Errors",
                    ""
                ])
                for error in errors:
                    md_lines.append(f"* {error}")
                md_lines.append("")
            
            # Add compatibility relations
            relations = result_data.get("compatibility", {}).get("relations", [])
            if relations:
                md_lines.extend([
                    "## Compatibility Relations",
                    "",
                    "| Relation Type | Related Product | Confidence | Context |",
                    "|---------------|----------------|------------|---------|"
                ])
                
                for relation in relations:
                    if not isinstance(relation, dict):
                        continue
                    
                    # Format related product
                    related_product = relation.get("related_product", "")
                    if isinstance(related_product, dict):
                        name = related_product.get("name", "")
                        article = related_product.get("article_number", "")
                        
                        if article:
                            product_text = f"{name} ({article})"
                        else:
                            product_text = name
                    else:
                        product_text = str(related_product)
                    
                    # Format confidence
                    confidence = relation.get("confidence", 0)
                    if isinstance(confidence, (int, float)):
                        confidence_text = f"{confidence:.2f}"
                    else:
                        confidence_text = str(confidence)
                    
                    # Escape pipe characters in fields
                    relation_type = relation.get("relation_type", "").replace("|", "\\|")
                    product_text = product_text.replace("|", "\\|")
                    context = relation.get("context", "").replace("|", "\\|")
                    
                    md_lines.append(
                        f"| {relation_type} | {product_text} | {confidence_text} | {context} |"
                    )
                
                md_lines.append("")
            
            # Add technical specifications
            specs = result_data.get("technical", {}).get("specifications", [])
            if specs:
                md_lines.extend([
                    "## Technical Specifications",
                    ""
                ])
                
                # Group specs by category
                spec_categories = {}
                for spec in specs:
                    if not isinstance(spec, dict):
                        continue
                    
                    category = spec.get("category", "Other")
                    if category not in spec_categories:
                        spec_categories[category] = []
                    
                    spec_categories[category].append(spec)
                
                # Add each category
                for category, category_specs in spec_categories.items():
                    md_lines.extend([
                        f"### {category}",
                        "",
                        "| Name | Value | Unit | Confidence |",
                        "|------|-------|------|------------|"
                    ])
                    
                    for spec in category_specs:
                        # Format confidence
                        confidence = spec.get("confidence", 0)
                        if isinstance(confidence, (int, float)):
                            confidence_text = f"{confidence:.2f}"
                        else:
                            confidence_text = str(confidence)
                        
                        # Escape pipe characters in fields
                        name = spec.get("name", "").replace("|", "\\|")
                        value = str(spec.get("raw_value", "")).replace("|", "\\|")
                        unit = spec.get("unit", "").replace("|", "\\|")
                        
                        md_lines.append(
                            f"| {name} | {value} | {unit} | {confidence_text} |"
                        )
                    
                    md_lines.append("")
            
            # Add metadata section
            md_lines.extend([
                "## Metadata",
                "",
                "| Property | Value |",
                "|----------|-------|"
            ])
            
            for key, value in metadata.items():
                # Skip complex metadata
                if isinstance(value, (dict, list)):
                    continue
                
                md_lines.append(f"| {key} | {value} |")
            
            md_lines.append("")
            
            # Write markdown to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(md_lines))
            
            QMessageBox.information(self, "Export Successful", f"Exported data to {file_path}")
            
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to export to Markdown: {str(e)}")

    def format_date(self, date_str):
        """Format date string for display"""
        if not date_str:
            return ""
        
        try:
            # Try to parse ISO format date
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Return original if parsing fails
            return date_str

    def set_output_directory(self, directory):
        """Set the output directory for results"""
        path = Path(directory)
        if path.exists() and path.is_dir():
            self.output_dir = path
            self.load_results()
            return True
        return False

    def run(self):
        """
        Run the results viewer (called from main window)
        """
        # In a real implementation, this might ask for a directory to load from
        # or perform other initialization
        self.refresh_results()

