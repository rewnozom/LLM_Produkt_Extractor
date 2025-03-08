#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QLabel, QPushButton, QProgressBar, QTableWidget,
    QTableWidgetItem, QComboBox, QSpinBox, QLineEdit,
    QFileDialog, QFormLayout, QTabWidget, QTextEdit,
    QCheckBox, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, Signal, Slot, QThreadPool, QRunnable
from PySide6.QtGui import QColor

# Import backend modules
from workflow.Arbetsflödeshantering import (
    WorkflowManager, JobPriority, JobStatus, Job
)

class WorkerRunner(QRunnable):
    """Worker thread for running workflow tasks"""
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        """Execute the function with provided arguments"""
        try:
            self.func(*self.args, **self.kwargs)
        except Exception as e:
            print(f"Worker error: {str(e)}")


class WorkflowTab(QWidget):
    """
    Tab for managing workflow processes
    """
    # Define signals
    workflow_started = Signal(str)  # workflow_id
    workflow_completed = Signal(str, bool)  # workflow_id, success
    workflow_progress = Signal(str, int, int)  # workflow_id, current, total
    workflow_status = Signal(str, str)  # workflow_id, status_message
    
    def __init__(self):
        super().__init__()
        
        # Initialize thread pool for background tasks
        self.thread_pool = QThreadPool()
        
        # Initialize backend workflow manager
        self.workflow_manager = None
        
        # Store currently running workflows
        self.active_workflows = {}
        
        self.setup_ui()
        
        # Initialize backend components once UI is ready
        self.initialize_backend()
    
    def setup_ui(self):
        """Setup the workflow tab UI"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # Create a splitter for top controls and bottom results
        self.main_splitter = QSplitter(Qt.Vertical)
        
        # Top section widget with controls
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Control tabs (Single Product, Directory, CSV, Batch)
        self.control_tabs = QTabWidget()
        
        # Single Product tab
        single_product_widget = QWidget()
        single_layout = QVBoxLayout(single_product_widget)
        
        # File selection group
        file_group = QGroupBox("Product File")
        file_layout = QFormLayout(file_group)
        
        self.product_id_input = QLineEdit()
        file_layout.addRow("Product ID:", self.product_id_input)
        
        file_select_layout = QHBoxLayout()
        self.file_path_input = QLineEdit()
        file_select_layout.addWidget(self.file_path_input)
        
        self.file_browse_button = QPushButton("Browse...")
        self.file_browse_button.clicked.connect(self.browse_product_file)
        file_select_layout.addWidget(self.file_browse_button)
        
        file_layout.addRow("File Path:", file_select_layout)
        
        single_layout.addWidget(file_group)
        
        # Extraction options
        extraction_group = QGroupBox("Extraction Options")
        extraction_layout = QFormLayout(extraction_group)
        
        self.extract_compatibility = QCheckBox("Extract Compatibility Information")
        self.extract_compatibility.setChecked(True)
        extraction_layout.addRow("", self.extract_compatibility)
        
        self.extract_technical = QCheckBox("Extract Technical Specifications")
        self.extract_technical.setChecked(True)
        extraction_layout.addRow("", self.extract_technical)
        
        self.extract_faq = QCheckBox("Extract FAQ Data")
        extraction_layout.addRow("", self.extract_faq)
        
        single_layout.addWidget(extraction_group)
        
        # Action buttons
        single_buttons_layout = QHBoxLayout()
        
        self.process_button = QPushButton("Process Product")
        self.process_button.setProperty("class", "primary")
        self.process_button.clicked.connect(self.process_single_product)
        single_buttons_layout.addWidget(self.process_button)
        
        single_layout.addLayout(single_buttons_layout)
        single_layout.addStretch()
        
        self.control_tabs.addTab(single_product_widget, "Single Product")
        
        # Directory tab
        directory_widget = QWidget()
        dir_layout = QVBoxLayout(directory_widget)
        
        # Directory selection group
        dir_group = QGroupBox("Directory")
        dir_form_layout = QFormLayout(dir_group)
        
        dir_select_layout = QHBoxLayout()
        self.dir_path_input = QLineEdit()
        dir_select_layout.addWidget(self.dir_path_input)
        
        self.dir_browse_button = QPushButton("Browse...")
        self.dir_browse_button.clicked.connect(self.browse_directory)
        dir_select_layout.addWidget(self.dir_browse_button)
        
        dir_form_layout.addRow("Directory:", dir_select_layout)
        
        self.file_pattern_input = QLineEdit("*.md")
        dir_form_layout.addRow("File Pattern:", self.file_pattern_input)
        
        self.recursive_checkbox = QCheckBox("Search recursively in subdirectories")
        dir_form_layout.addRow("", self.recursive_checkbox)
        
        dir_layout.addWidget(dir_group)
        
        # Batch options
        batch_group = QGroupBox("Batch Options")
        batch_layout = QFormLayout(batch_group)
        
        self.batch_size_input = QSpinBox()
        self.batch_size_input.setRange(1, 100)
        self.batch_size_input.setValue(10)
        batch_layout.addRow("Batch Size:", self.batch_size_input)
        
        self.workers_input = QSpinBox()
        self.workers_input.setRange(1, 16)
        self.workers_input.setValue(4)
        batch_layout.addRow("Workers:", self.workers_input)
        
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["LOW", "NORMAL", "HIGH", "CRITICAL"])
        self.priority_combo.setCurrentIndex(1)  # NORMAL
        batch_layout.addRow("Priority:", self.priority_combo)
        
        dir_layout.addWidget(batch_group)
        
        # Action buttons
        dir_buttons_layout = QHBoxLayout()
        
        self.process_dir_button = QPushButton("Process Directory")
        self.process_dir_button.setProperty("class", "primary")
        self.process_dir_button.clicked.connect(self.process_directory)
        dir_buttons_layout.addWidget(self.process_dir_button)
        
        dir_layout.addLayout(dir_buttons_layout)
        dir_layout.addStretch()
        
        self.control_tabs.addTab(directory_widget, "Directory")
        
        # CSV tab
        csv_widget = QWidget()
        csv_layout = QVBoxLayout(csv_widget)
        
        # CSV file selection
        csv_group = QGroupBox("CSV File")
        csv_form_layout = QFormLayout(csv_group)
        
        csv_select_layout = QHBoxLayout()
        self.csv_path_input = QLineEdit()
        csv_select_layout.addWidget(self.csv_path_input)
        
        self.csv_browse_button = QPushButton("Browse...")
        self.csv_browse_button.clicked.connect(self.browse_csv_file)
        csv_select_layout.addWidget(self.csv_browse_button)
        
        csv_form_layout.addRow("CSV File:", csv_select_layout)
        
        self.id_column_input = QLineEdit("product_id")
        csv_form_layout.addRow("ID Column:", self.id_column_input)
        
        self.path_column_input = QLineEdit("file_path")
        csv_form_layout.addRow("Path Column:", self.path_column_input)
        
        self.encoding_input = QLineEdit("utf-8")
        csv_form_layout.addRow("Encoding:", self.encoding_input)
        
        self.delimiter_input = QLineEdit(",")
        csv_form_layout.addRow("Delimiter:", self.delimiter_input)
        
        csv_layout.addWidget(csv_group)
        
        # CSV batch options (reuse batch group from directory tab)
        batch_group_csv = QGroupBox("Batch Options")
        batch_layout_csv = QFormLayout(batch_group_csv)
        
        self.batch_size_csv_input = QSpinBox()
        self.batch_size_csv_input.setRange(1, 100)
        self.batch_size_csv_input.setValue(10)
        batch_layout_csv.addRow("Batch Size:", self.batch_size_csv_input)
        
        self.workers_csv_input = QSpinBox()
        self.workers_csv_input.setRange(1, 16)
        self.workers_csv_input.setValue(4)
        batch_layout_csv.addRow("Workers:", self.workers_csv_input)
        
        self.priority_csv_combo = QComboBox()
        self.priority_csv_combo.addItems(["LOW", "NORMAL", "HIGH", "CRITICAL"])
        self.priority_csv_combo.setCurrentIndex(1)  # NORMAL
        batch_layout_csv.addRow("Priority:", self.priority_csv_combo)
        
        csv_layout.addWidget(batch_group_csv)
        
        # Action buttons
        csv_buttons_layout = QHBoxLayout()
        
        self.process_csv_button = QPushButton("Process CSV")
        self.process_csv_button.setProperty("class", "primary")
        self.process_csv_button.clicked.connect(self.process_csv)
        csv_buttons_layout.addWidget(self.process_csv_button)
        
        csv_layout.addLayout(csv_buttons_layout)
        csv_layout.addStretch()
        
        self.control_tabs.addTab(csv_widget, "CSV")
        
        # Continuous tab
        continuous_widget = QWidget()
        continuous_layout = QVBoxLayout(continuous_widget)
        
        # Continuous mode options
        continuous_group = QGroupBox("Continuous Mode Settings")
        continuous_form_layout = QFormLayout(continuous_group)
        
        self.queue_dir_layout = QHBoxLayout()
        self.queue_dir_input = QLineEdit()
        self.queue_dir_layout.addWidget(self.queue_dir_input)
        
        self.queue_dir_button = QPushButton("Browse...")
        self.queue_dir_button.clicked.connect(self.browse_queue_dir)
        self.queue_dir_layout.addWidget(self.queue_dir_button)
        
        continuous_form_layout.addRow("Queue Directory:", self.queue_dir_layout)
        
        self.queue_interval_input = QSpinBox()
        self.queue_interval_input.setRange(1, 60)
        self.queue_interval_input.setValue(5)
        continuous_form_layout.addRow("Check Interval (seconds):", self.queue_interval_input)
        
        self.workers_continuous_input = QSpinBox()
        self.workers_continuous_input.setRange(1, 16)
        self.workers_continuous_input.setValue(4)
        continuous_form_layout.addRow("Workers:", self.workers_continuous_input)
        
        continuous_layout.addWidget(continuous_group)
        
        # Status display
        status_group = QGroupBox("Workflow Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setPlaceholderText("Workflow status will be displayed here...")
        status_layout.addWidget(self.status_text)
        
        continuous_layout.addWidget(status_group)
        
        # Action buttons
        continuous_buttons_layout = QHBoxLayout()
        
        self.start_workflow_button = QPushButton("Start Workflow")
        self.start_workflow_button.setProperty("class", "primary")
        self.start_workflow_button.clicked.connect(self.start_continuous_workflow)
        continuous_buttons_layout.addWidget(self.start_workflow_button)
        
        self.stop_workflow_button = QPushButton("Stop Workflow")
        self.stop_workflow_button.setProperty("class", "destructive")
        self.stop_workflow_button.clicked.connect(self.stop_continuous_workflow)
        self.stop_workflow_button.setEnabled(False)
        continuous_buttons_layout.addWidget(self.stop_workflow_button)
        
        continuous_layout.addLayout(continuous_buttons_layout)
        
        self.control_tabs.addTab(continuous_widget, "Continuous")
        
        top_layout.addWidget(self.control_tabs)
        
        # Add top widget to main splitter
        self.main_splitter.addWidget(top_widget)
        
        # Bottom section with results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "ID", "Product ID", "Status", "Progress", "Results", "Actions"
        ])
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.verticalHeader().setVisible(False)
        
        # Adjust column widths
        self.results_table.setColumnWidth(0, 80)   # ID
        self.results_table.setColumnWidth(1, 150)  # Product ID
        self.results_table.setColumnWidth(2, 120)  # Status
        self.results_table.setColumnWidth(3, 150)  # Progress
        self.results_table.setColumnWidth(4, 200)  # Results
        
        # Add results table to main splitter
        self.main_splitter.addWidget(self.results_table)
        
        # Set initial splitter sizes
        self.main_splitter.setSizes([500, 300])
        
        layout.addWidget(self.main_splitter)
        
        # Add status bar at bottom
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)





# Set initial splitter sizes
        self.main_splitter.setSizes([500, 300])
        
        layout.addWidget(self.main_splitter)
        
        # Add status bar at bottom
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        
        self.global_progress = QProgressBar()
        self.global_progress.setTextVisible(True)
        self.global_progress.setRange(0, 100)
        self.global_progress.setValue(0)
        status_layout.addWidget(self.global_progress)
        
        layout.addLayout(status_layout)
        
        # Connect signals
        self.workflow_started.connect(self.on_workflow_started)
        self.workflow_completed.connect(self.on_workflow_completed)
        self.workflow_progress.connect(self.on_workflow_progress)
        self.workflow_status.connect(self.on_workflow_status)
    
    def initialize_backend(self):
        """Initialize backend workflow components"""
        try:
            # Import required backend components
            from config.ConfigManager import ConfigManager
            import logging
            
            # Setup basic logging
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger("workflow_gui")
            
            # Load config (empty for now, will use defaults)
            config_manager = ConfigManager()
            
            # Initialize workflow manager
            from workflow.Arbetsflödeshantering import WorkflowManager
            self.workflow_manager = WorkflowManager(config_manager, logger, None)
            
            # Add a success message to the status text
            self.status_text.append("<span style='color:#10b981;'>✓ Backend components initialized successfully</span>")
            self.status_label.setText("Backend initialized")
        except Exception as e:
            # Display error in status text
            error_message = f"<span style='color:#f43f5e;'>✗ Error initializing backend: {str(e)}</span>"
            self.status_text.append(error_message)
            self.status_label.setText("Backend initialization failed")
            
            # Disable main action buttons
            self.process_button.setEnabled(False)
            self.process_dir_button.setEnabled(False)
            self.process_csv_button.setEnabled(False)
            self.start_workflow_button.setEnabled(False)
    
    # Button event handlers
    def browse_product_file(self):
        """Browse for a product file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Product File", "", "All Files (*);;Markdown Files (*.md);;Text Files (*.txt)"
        )
        
        if file_path:
            self.file_path_input.setText(file_path)
            
            # Auto-fill product ID from filename if empty
            if not self.product_id_input.text():
                file_name = Path(file_path).stem
                self.product_id_input.setText(file_name)
    
    def browse_directory(self):
        """Browse for a directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Directory", ""
        )
        
        if dir_path:
            self.dir_path_input.setText(dir_path)
    
    def browse_csv_file(self):
        """Browse for a CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.csv_path_input.setText(file_path)
    
    def browse_queue_dir(self):
        """Browse for a queue directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Queue Directory", ""
        )
        
        if dir_path:
            self.queue_dir_input.setText(dir_path)
    
    def process_single_product(self):
        """Process a single product"""
        # Validate inputs
        product_id = self.product_id_input.text().strip()
        file_path = self.file_path_input.text().strip()
        
        if not product_id:
            QMessageBox.warning(self, "Input Error", "Product ID is required.")
            return
        
        if not file_path:
            QMessageBox.warning(self, "Input Error", "File path is required.")
            return
        
        if not Path(file_path).exists():
            QMessageBox.warning(self, "Input Error", f"File does not exist: {file_path}")
            return
        
        # Create a unique workflow ID
        import uuid
        workflow_id = f"single_{uuid.uuid4().hex[:8]}"
        
        # Add entry to results table
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # Set up table cells
        self.results_table.setItem(row, 0, QTableWidgetItem(workflow_id))
        self.results_table.setItem(row, 1, QTableWidgetItem(product_id))
        self.results_table.setItem(row, 2, QTableWidgetItem("Queued"))
        
        # Progress bar cell
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        self.results_table.setCellWidget(row, 3, progress_bar)
        
        # Results cell placeholder
        self.results_table.setItem(row, 4, QTableWidgetItem("Pending..."))
        
        # Create action button cell
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(2, 2, 2, 2)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(lambda: self.cancel_workflow(workflow_id))
        action_layout.addWidget(cancel_button)
        
        self.results_table.setCellWidget(row, 5, action_widget)
        
        # Store workflow info
        self.active_workflows[workflow_id] = {
            "type": "single",
            "product_id": product_id,
            "file_path": file_path,
            "row": row,
            "extract_compatibility": self.extract_compatibility.isChecked(),
            "extract_technical": self.extract_technical.isChecked(),
            "extract_faq": self.extract_faq.isChecked()
        }
        
        # Start the workflow in a background thread
        self.workflow_started.emit(workflow_id)
        
        worker = WorkerRunner(
            self._run_single_product_workflow,
            workflow_id,
            product_id,
            file_path,
            self.extract_compatibility.isChecked(),
            self.extract_technical.isChecked(),
            self.extract_faq.isChecked()
        )
        self.thread_pool.start(worker)
    
    def process_directory(self):
        """Process a directory of products"""
        # Validate inputs
        dir_path = self.dir_path_input.text().strip()
        pattern = self.file_pattern_input.text().strip()
        
        if not dir_path:
            QMessageBox.warning(self, "Input Error", "Directory path is required.")
            return
        
        if not Path(dir_path).exists() or not Path(dir_path).is_dir():
            QMessageBox.warning(self, "Input Error", f"Directory does not exist: {dir_path}")
            return
        
        if not pattern:
            QMessageBox.warning(self, "Input Error", "File pattern is required.")
            return
        
        # Get batch options
        batch_size = self.batch_size_input.value()
        workers = self.workers_input.value()
        priority = self.priority_combo.currentText()
        recursive = self.recursive_checkbox.isChecked()
        
        # Create a unique workflow ID
        import uuid
        workflow_id = f"dir_{uuid.uuid4().hex[:8]}"
        
        # Add entry to results table
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # Set up table cells
        self.results_table.setItem(row, 0, QTableWidgetItem(workflow_id))
        self.results_table.setItem(row, 1, QTableWidgetItem(f"Directory: {Path(dir_path).name}"))
        self.results_table.setItem(row, 2, QTableWidgetItem("Queued"))
        
        # Progress bar cell
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        self.results_table.setCellWidget(row, 3, progress_bar)
        
        # Results cell placeholder
        self.results_table.setItem(row, 4, QTableWidgetItem("Preparing..."))
        
        # Create action button cell
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(2, 2, 2, 2)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(lambda: self.cancel_workflow(workflow_id))
        action_layout.addWidget(cancel_button)
        
        self.results_table.setCellWidget(row, 5, action_widget)
        
        # Store workflow info
        self.active_workflows[workflow_id] = {
            "type": "directory",
            "dir_path": dir_path,
            "pattern": pattern,
            "batch_size": batch_size,
            "workers": workers,
            "priority": priority,
            "recursive": recursive,
            "row": row
        }
        
        # Start the workflow in a background thread
        self.workflow_started.emit(workflow_id)
        
        worker = WorkerRunner(
            self._run_directory_workflow,
            workflow_id,
            dir_path,
            pattern,
            batch_size,
            workers,
            priority,
            recursive
        )
        self.thread_pool.start(worker)
    
    def process_csv(self):
        """Process products from a CSV file"""
        # Validate inputs
        csv_path = self.csv_path_input.text().strip()
        id_column = self.id_column_input.text().strip()
        path_column = self.path_column_input.text().strip()
        encoding = self.encoding_input.text().strip()
        delimiter = self.delimiter_input.text().strip()
        
        if not csv_path:
            QMessageBox.warning(self, "Input Error", "CSV file path is required.")
            return
        
        if not Path(csv_path).exists():
            QMessageBox.warning(self, "Input Error", f"CSV file does not exist: {csv_path}")
            return
        
        if not id_column:
            QMessageBox.warning(self, "Input Error", "ID column name is required.")
            return
        
        if not path_column:
            QMessageBox.warning(self, "Input Error", "Path column name is required.")
            return
        
        # Get batch options
        batch_size = self.batch_size_csv_input.value()
        workers = self.workers_csv_input.value()
        priority = self.priority_csv_combo.currentText()
        
        # Create a unique workflow ID
        import uuid
        workflow_id = f"csv_{uuid.uuid4().hex[:8]}"
        
        # Add entry to results table
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # Set up table cells
        self.results_table.setItem(row, 0, QTableWidgetItem(workflow_id))
        self.results_table.setItem(row, 1, QTableWidgetItem(f"CSV: {Path(csv_path).name}"))
        self.results_table.setItem(row, 2, QTableWidgetItem("Queued"))
        
        # Progress bar cell
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        self.results_table.setCellWidget(row, 3, progress_bar)
        
        # Results cell placeholder
        self.results_table.setItem(row, 4, QTableWidgetItem("Preparing..."))
        
        # Create action button cell
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(2, 2, 2, 2)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(lambda: self.cancel_workflow(workflow_id))
        action_layout.addWidget(cancel_button)
        
        self.results_table.setCellWidget(row, 5, action_widget)
        
        # Store workflow info
        self.active_workflows[workflow_id] = {
            "type": "csv",
            "csv_path": csv_path,
            "id_column": id_column,
            "path_column": path_column,
            "encoding": encoding,
            "delimiter": delimiter,
            "batch_size": batch_size,
            "workers": workers,
            "priority": priority,
            "row": row
        }
        
        # Start the workflow in a background thread
        self.workflow_started.emit(workflow_id)
        
        worker = WorkerRunner(
            self._run_csv_workflow,
            workflow_id,
            csv_path,
            id_column,
            path_column,
            batch_size,
            workers,
            priority,
            encoding,
            delimiter
        )
        self.thread_pool.start(worker)
    
    def start_continuous_workflow(self):
        """Start continuous workflow"""
        # Validate inputs
        queue_dir = self.queue_dir_input.text().strip()
        queue_interval = self.queue_interval_input.value()
        workers = self.workers_continuous_input.value()
        
        if not queue_dir:
            QMessageBox.warning(self, "Input Error", "Queue directory is required.")
            return
        
        queue_path = Path(queue_dir)
        if not queue_path.exists():
            # Ask to create
            reply = QMessageBox.question(
                self, "Create Directory?", 
                f"Directory does not exist: {queue_dir}\nDo you want to create it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                try:
                    queue_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Could not create directory: {str(e)}")
                    return
            else:
                return
        
        # Create a unique workflow ID
        import uuid
        workflow_id = f"continuous_{uuid.uuid4().hex[:8]}"
        
        # Add entry to results table
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # Set up table cells
        self.results_table.setItem(row, 0, QTableWidgetItem(workflow_id))
        self.results_table.setItem(row, 1, QTableWidgetItem("Continuous workflow"))
        self.results_table.setItem(row, 2, QTableWidgetItem("Running"))
        
        # Progress cell (no progress bar for continuous)
        self.results_table.setItem(row, 3, QTableWidgetItem("Continuous"))
        
        # Results cell
        self.results_table.setItem(row, 4, QTableWidgetItem("Monitoring queue..."))
        
        # Create action button cell
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(2, 2, 2, 2)
        
        stop_button = QPushButton("Stop")
        stop_button.setProperty("class", "destructive")
        stop_button.clicked.connect(lambda: self.stop_continuous_workflow())
        action_layout.addWidget(stop_button)
        
        self.results_table.setCellWidget(row, 5, action_widget)
        
        # Store workflow info
        self.active_workflows[workflow_id] = {
            "type": "continuous",
            "queue_dir": queue_dir,
            "queue_interval": queue_interval,
            "workers": workers,
            "row": row,
            "running": True
        }
        
        # Update UI
        self.start_workflow_button.setEnabled(False)
        self.stop_workflow_button.setEnabled(True)
        self.control_tabs.setTabEnabled(0, False)  # Disable single product tab
        self.control_tabs.setTabEnabled(1, False)  # Disable directory tab
        self.control_tabs.setTabEnabled(2, False)  # Disable CSV tab
        
        # Start the workflow in a background thread
        self.workflow_started.emit(workflow_id)
        
        worker = WorkerRunner(
            self._run_continuous_workflow,
            workflow_id,
            queue_dir,
            queue_interval,
            workers
        )
        self.thread_pool.start(worker)
    
    def stop_continuous_workflow(self):
        """Stop the continuous workflow"""
        # Find the active continuous workflow
        continuous_workflow = None
        for wf_id, wf_info in self.active_workflows.items():
            if wf_info["type"] == "continuous" and wf_info.get("running", False):
                continuous_workflow = (wf_id, wf_info)
                break
        
        if not continuous_workflow:
            return
        
        wf_id, wf_info = continuous_workflow
        
        # Update the workflow info
        wf_info["running"] = False
        
        # Update UI
        row = wf_info["row"]
        self.results_table.item(row, 2).setText("Stopping...")
        self.results_table.item(row, 4).setText("Waiting for workflow to stop...")
        
        # Signal that we're stopping
        self.workflow_status.emit(wf_id, "Stopping continuous workflow...")
        
        # The workflow thread should detect the running flag and stop
        # Update UI state
        self.stop_workflow_button.setEnabled(False)
    
    def cancel_workflow(self, workflow_id):
        """Cancel a workflow"""
        if workflow_id not in self.active_workflows:
            return
        
        wf_info = self.active_workflows[workflow_id]
        
        # Update UI
        row = wf_info["row"]
        self.results_table.item(row, 2).setText("Cancelling...")
        
        # Signal that we're cancelling
        self.workflow_status.emit(workflow_id, "Cancelling workflow...")
        
        # In a real implementation, we would signal the backend to cancel
        # For now, we'll just mark it as completed with failure
        self.workflow_completed.emit(workflow_id, False)
    
    # Backend runner methods
    def _run_single_product_workflow(self, workflow_id, product_id, file_path, 
                                    extract_compatibility, extract_technical, extract_faq):
        """Run workflow for a single product"""
        try:
            # Update status
            self.workflow_status.emit(workflow_id, "Processing product...")
            
            # Initialize the backend if needed
            if not self.workflow_manager:
                self.workflow_status.emit(workflow_id, "Error: Backend not initialized")
                self.workflow_completed.emit(workflow_id, False)
                return
            
            # Set extraction options
            extraction_config = {}
            if extract_compatibility:
                extraction_config["compatibility"] = {"enabled": True}
            if extract_technical:
                extraction_config["technical"] = {"enabled": True}
            if extract_faq:
                extraction_config["faq"] = {"enabled": True}
            
            self.workflow_manager.config.set("extraction", extraction_config)
            
            # Process the product
            self.workflow_status.emit(workflow_id, "Starting processing...")
            result = self.workflow_manager.process_product(product_id, file_path)
            
            # Update progress
            self.workflow_progress.emit(workflow_id, 100, 100)
            
            # Check result
            if result.status.name in ["COMPLETED", "VALIDATED"]:
                self.workflow_status.emit(
                    workflow_id, 
                    f"Completed successfully. Extracted {result.get_compatibility_count()} compatibility relations, "
                    f"{result.get_technical_count()} technical specifications."
                )
                self.workflow_completed.emit(workflow_id, True)
            else:
                self.workflow_status.emit(
                    workflow_id, 
                    f"Completed with status: {result.status.name}. {len(result.errors)} errors."
                )
                self.workflow_completed.emit(workflow_id, False)
                
        except Exception as e:
            # Handle exceptions
            self.workflow_status.emit(workflow_id, f"Error: {str(e)}")
            self.workflow_completed.emit(workflow_id, False)
    
    def _run_directory_workflow(self, workflow_id, dir_path, pattern, 
                              batch_size, num_workers, priority, recursive):
        """Run workflow for a directory"""
        try:
            # Update status
            self.workflow_status.emit(workflow_id, "Preparing directory processing...")
            
            # Initialize the backend if needed
            if not self.workflow_manager:
                self.workflow_status.emit(workflow_id, "Error: Backend not initialized")
                self.workflow_completed.emit(workflow_id, False)
                return
            
            # Configure the workflow manager
            self.workflow_manager.config.set("general.max_workers", num_workers)
            self.workflow_manager.config.set("workflow.batch_size", batch_size)
            
            # Convert priority string to enum
            job_priority = JobPriority[priority]
            
            # Start the workflow manager
            self.workflow_manager.start()
            
            try:
                # Process the directory
                self.workflow_status.emit(workflow_id, "Processing directory...")
                reports = self.workflow_manager.process_directory(
                    dir_path, pattern, batch_size, job_priority, recursive
                )
                
                # Parse results
                total_products = sum(report["total_products"] for report in reports)
                enqueued_products = sum(report["enqueued_products"] for report in reports)
                
                if enqueued_products == 0:
                    self.workflow_status.emit(
                        workflow_id,
                        f"No products found matching pattern '{pattern}' in directory."
                    )
                    self.workflow_completed.emit(workflow_id, False)
                    return
                
                # Monitor progress
                self.workflow_status.emit(
                    workflow_id,
                    f"Enqueued {enqueued_products}/{total_products} products. Processing..."
                )
                
                # Check status periodically
                completed = 0
                while True:
                    # Get current status
                    status = self.workflow_manager.get_status()
                    queue_status = status["queue"]
                    
                    completed_jobs = queue_status["completed_jobs"]
                    active_jobs = queue_status["active_jobs"]
                    failed_jobs = queue_status["failed_jobs"]
                    pending_jobs = queue_status["pending_jobs"]
                    
                    # Calculate progress
                    total_jobs = completed_jobs + active_jobs + failed_jobs + pending_jobs
                    progress = (completed_jobs + failed_jobs) / max(1, enqueued_products) * 100
                    
                    # Update progress
                    self.workflow_progress.emit(workflow_id, int(progress), 100)
                    
                    # Update status
                    self.workflow_status.emit(
                        workflow_id,
                        f"Progress: {completed_jobs}/{enqueued_products} completed, "
                        f"{active_jobs} active, {failed_jobs} failed, {pending_jobs} pending"
                    )
                    
                    # Check if all done
                    if completed_jobs + failed_jobs >= enqueued_products or (completed_jobs + failed_jobs == total_jobs and total_jobs > 0):
                        break
                    
                    # Wait before next check
                    import time
                    time.sleep(1)
                
                # All done
                self.workflow_status.emit(
                    workflow_id,
                    f"Directory processing complete. {completed_jobs}/{enqueued_products} products processed successfully."
                )
                self.workflow_completed.emit(workflow_id, failed_jobs == 0)
                
            finally:
                # Stop the workflow manager
                self.workflow_manager.stop()
                self.workflow_manager.join(timeout=5)
                
        except Exception as e:
            # Handle exceptions
            self.workflow_status.emit(workflow_id, f"Error: {str(e)}")
            self.workflow_completed.emit(workflow_id, False)
    
    def _run_csv_workflow(self, workflow_id, csv_path, id_column, path_column, 
                        batch_size, num_workers, priority, encoding, delimiter):
        """Run workflow for a CSV file"""
        try:
            # Update status
            self.workflow_status.emit(workflow_id, "Preparing CSV processing...")
            
            # Initialize the backend if needed
            if not self.workflow_manager:
                self.workflow_status.emit(workflow_id, "Error: Backend not initialized")
                self.workflow_completed.emit(workflow_id, False)
                return
            
            # Configure the workflow manager
            self.workflow_manager.config.set("general.max_workers", num_workers)
            self.workflow_manager.config.set("workflow.batch_size", batch_size)
            
            # Convert priority string to enum
            job_priority = JobPriority[priority]
            
            # Start the workflow manager
            self.workflow_manager.start()
            
            try:
                # Process the CSV file
                self.workflow_status.emit(workflow_id, "Processing CSV file...")
                reports = self.workflow_manager.process_csv(
                    csv_path, id_column, path_column, batch_size, job_priority, encoding, delimiter
                )
                
                # Parse results
                if not reports:
                    self.workflow_status.emit(workflow_id, "No valid data found in CSV file.")
                    self.workflow_completed.emit(workflow_id, False)
                    return
                
                total_products = sum(report["total_products"] for report in reports)
                enqueued_products = sum(report["enqueued_products"] for report in reports)
                
                if enqueued_products == 0:
                    self.workflow_status.emit(workflow_id, "No products could be enqueued from CSV.")
                    self.workflow_completed.emit(workflow_id, False)
                    return
                
                # Monitor progress (same as directory workflow)
                self.workflow_status.emit(
                    workflow_id,
                    f"Enqueued {enqueued_products}/{total_products} products. Processing..."
                )
                
                # Check status periodically
                completed = 0
                while True:
                    # Get current status
                    status = self.workflow_manager.get_status()
                    queue_status = status["queue"]
                    
                    completed_jobs = queue_status["completed_jobs"]
                    active_jobs = queue_status["active_jobs"]
                    failed_jobs = queue_status["failed_jobs"]
                    pending_jobs = queue_status["pending_jobs"]
                    
                    # Calculate progress
                    total_jobs = completed_jobs + active_jobs + failed_jobs + pending_jobs
                    progress = (completed_jobs + failed_jobs) / max(1, enqueued_products) * 100
                    
                    # Update progress
                    self.workflow_progress.emit(workflow_id, int(progress), 100)
                    
                    # Update status
                    self.workflow_status.emit(
                        workflow_id,
                        f"Progress: {completed_jobs}/{enqueued_products} completed, "
                        f"{active_jobs} active, {failed_jobs} failed, {pending_jobs} pending"
                    )
                    
                    # Check if all done
                    if completed_jobs + failed_jobs >= enqueued_products or (completed_jobs + failed_jobs == total_jobs and total_jobs > 0):
                        break
                    
                    # Wait before next check
                    import time
                    time.sleep(1)
                
                # All done
                self.workflow_status.emit(
                    workflow_id,
                    f"CSV processing complete. {completed_jobs}/{enqueued_products} products processed successfully."
                )
                self.workflow_completed.emit(workflow_id, failed_jobs == 0)
                
            finally:
                # Stop the workflow manager
                self.workflow_manager.stop()
                self.workflow_manager.join(timeout=5)
                
        except Exception as e:
            # Handle exceptions
            self.workflow_status.emit(workflow_id, f"Error: {str(e)}")
            self.workflow_completed.emit(workflow_id, False)
    
    def _run_continuous_workflow(self, workflow_id, queue_dir, queue_interval, num_workers):
        """Run continuous workflow"""
        try:
            # Update status
            self.workflow_status.emit(workflow_id, "Preparing continuous workflow...")
            
            # Initialize the backend if needed
            if not self.workflow_manager:
                self.workflow_status.emit(workflow_id, "Error: Backend not initialized")
                self.workflow_completed.emit(workflow_id, False)
                return
            
            # Configure the workflow manager
            self.workflow_manager.config.set("general.max_workers", num_workers)
            
            # Start the workflow manager
            self.workflow_manager.start()
            
            try:
                # Create Queue directory if it doesn't exist
                Path(queue_dir).mkdir(parents=True, exist_ok=True)
                
                # Start continuous monitoring
                self.workflow_status.emit(
                    workflow_id, 
                    f"Continuous workflow started. Monitoring directory: {queue_dir}"
                )
                
                wf_info = self.active_workflows[workflow_id]
                
                # Main monitoring loop
                while wf_info.get("running", False):
                    # Get current status
                    status = self.workflow_manager.get_status()
                    queue_status = status["queue"]
                    
                    # Update status message
                    status_msg = (
                        f"Queue status: {queue_status['completed_jobs']} completed, "
                        f"{queue_status['active_jobs']} active, "
                        f"{queue_status['failed_jobs']} failed"
                    )
                    self.workflow_status.emit(workflow_id, status_msg)
                    
                    # Wait before next check
                    import time
                    time.sleep(queue_interval)
                
                # Stopping requested
                self.workflow_status.emit(workflow_id, "Continuous workflow stopping...")
                
            finally:
                # Stop the workflow manager
                self.workflow_manager.stop()
                self.workflow_manager.join(timeout=5)
                
                # Re-enable UI elements
                self.workflow_status.emit(workflow_id, "Continuous workflow stopped")
                
                # Update UI in main thread
                from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    self, "_on_continuous_workflow_stopped", 
                    Qt.QueuedConnection, 
                    Q_ARG(str, workflow_id)
                )
                
        except Exception as e:
            # Handle exceptions
            self.workflow_status.emit(workflow_id, f"Error: {str(e)}")
            self.workflow_completed.emit(workflow_id, False)
    
    def _on_continuous_workflow_stopped(self, workflow_id):
        """Handler for when continuous workflow is stopped (called in main thread)"""
        self.start_workflow_button.setEnabled(True)
        self.stop_workflow_button.setEnabled(False)
        self.control_tabs.setTabEnabled(0, True)  # Enable single product tab
        self.control_tabs.setTabEnabled(1, True)  # Enable directory tab
        self.control_tabs.setTabEnabled(2, True)  # Enable CSV tab
        
        # Update the workflow info
        if workflow_id in self.active_workflows:
            wf_info = self.active_workflows[workflow_id]
            row = wf_info["row"]
            self.results_table.item(row, 2).setText("Stopped")
            self.results_table.item(row, 4).setText("Workflow stopped")
        
        self.workflow_completed.emit(workflow_id, True)
    
    # Workflow event handlers
    def on_workflow_started(self, workflow_id):
        """Handler for workflow started signal"""
        if workflow_id not in self.active_workflows:
            return
        
        # Get workflow info
        wf_info = self.active_workflows[workflow_id]
        row = wf_info["row"]
        
        # Update UI
        self.results_table.item(row, 2).setText("Running")
        
        # Update global status
        self.global_progress.setValue(0)
        self.status_label.setText(f"Running workflow: {workflow_id}")
    
    def on_workflow_completed(self, workflow_id, success):
        """Handler for workflow completed signal"""
        if workflow_id not in self.active_workflows:
            return
        
        # Get workflow info
        wf_info = self.active_workflows[workflow_id]
        row = wf_info["row"]
        
        # Update UI
        self.results_table.item(row, 2).setText("Completed" if success else "Failed")
        
        # Update progress bar
        progress_widget = self.results_table.cellWidget(row, 3)
        if isinstance(progress_widget, QProgressBar):
            progress_widget.setValue(100)
            progress_widget.setStyleSheet(
                "QProgressBar::chunk { background-color: #10b981; }" if success else
                "QProgressBar::chunk { background-color: #f43f5e; }"
            )
        
        # Update global status
        self.global_progress.setValue(100)
        self.status_label.setText(f"Workflow {workflow_id} completed" + ("" if success else " with errors"))
        
        # Update action buttons
        action_widget = self.results_table.cellWidget(row, 5)
        if action_widget:
            # Clear existing layout
            for i in reversed(range(action_widget.layout().count())): 
                action_widget.layout().itemAt(i).widget().setParent(None)
            
            # Add view results button
            view_button = QPushButton("View Results")
            view_button.clicked.connect(lambda: self.view_workflow_results(workflow_id))
            action_widget.layout().addWidget(view_button)
        
        # Remove from active workflows if it's not a continuous workflow
        if wf_info["type"] != "continuous":
            # Don't actually remove, just mark as inactive
            wf_info["active"] = False
    
    def on_workflow_progress(self, workflow_id, current, total):
        """Handler for workflow progress signal"""
        if workflow_id not in self.active_workflows:
            return
        
        # Get workflow info
        wf_info = self.active_workflows[workflow_id]
        row = wf_info["row"]
        
        # Calculate percentage
        percentage = int(current / max(1, total) * 100)
        
        # Update progress bar in table
        progress_widget = self.results_table.cellWidget(row, 3)
        if isinstance(progress_widget, QProgressBar):
            progress_widget.setValue(percentage)
        
        # Update global progress bar
        self.global_progress.setValue(percentage)
    
    def on_workflow_status(self, workflow_id, status_message):
        """Handler for workflow status signal"""
        if workflow_id not in self.active_workflows:
            return
        
        # Get workflow info
        wf_info = self.active_workflows[workflow_id]
        row = wf_info["row"]
        
        # Update results cell with status
        self.results_table.item(row, 4).setText(status_message)
        
        # For continuous workflow, also update the status text
        if wf_info["type"] == "continuous":
            # Add timestamp to the status message
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Append to status text
            self.status_text.append(f"[{timestamp}] {status_message}")
            
            # Make sure the latest message is visible
            scrollbar = self.status_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def view_workflow_results(self, workflow_id):
        """Handler for viewing workflow results"""
        if workflow_id not in self.active_workflows:
            return
        
        # Get workflow info
        wf_info = self.active_workflows[workflow_id]
        
        # TODO: Implement this to open the results viewer tab
        # For now, just show a message
        QMessageBox.information(
            self, "View Results", 
            f"Results for workflow {workflow_id} would be shown in the Results tab.\n\n"
            f"Workflow type: {wf_info['type']}"
        )


