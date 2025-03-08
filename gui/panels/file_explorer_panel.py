#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, 
    QPushButton, QFileSystemModel, QLineEdit, QComboBox,
    QMenu, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QDir, QModelIndex, QSize
from PySide6.QtGui import QAction, QKeySequence

class FileExplorerPanel(QWidget):
    """
    File explorer panel for browsing files and directories
    """
    # Define signals
    file_selected = Signal(str)
    directory_selected = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        # File system model
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        
        # File filters
        self.file_filters = [
            "All Files (*.*)",
            "Text Files (*.txt)",
            "Markdown Files (*.md)",
            "JSON Files (*.json)",
            "YAML Files (*.yaml *.yml)",
            "CSV Files (*.csv)"
        ]
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the file explorer UI"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # File path input and browse button
        path_layout = QHBoxLayout()
        path_layout.setContentsMargins(0, 0, 0, 0)
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Enter directory path...")
        self.path_input.returnPressed.connect(self.on_path_changed)
        path_layout.addWidget(self.path_input)
        
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_directory)
        path_layout.addWidget(self.browse_button)
        
        layout.addLayout(path_layout)
        
        # File filter
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(self.file_filters)
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)
        layout.addWidget(self.filter_combo)
        
        # File tree view
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)
        
        # Hide columns we don't need
        self.tree_view.setColumnHidden(1, True)  # Size
        self.tree_view.setColumnHidden(2, True)  # Type
        
        # Set the name column width
        self.tree_view.setColumnWidth(0, 300)
        
        # Enable dragging
        self.tree_view.setDragEnabled(True)
        
        # Connect signals
        self.tree_view.clicked.connect(self.on_item_clicked)
        self.tree_view.doubleClicked.connect(self.on_item_double_clicked)
        
        # Enable context menu
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.tree_view)
        
        # Buttons for common directories
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.home_button = QPushButton("Home")
        self.home_button.clicked.connect(self.go_to_home)
        button_layout.addWidget(self.home_button)
        
        self.documents_button = QPushButton("Documents")
        self.documents_button.clicked.connect(self.go_to_documents)
        button_layout.addWidget(self.documents_button)
        
        self.current_button = QPushButton("Current")
        self.current_button.clicked.connect(self.go_to_current_dir)
        button_layout.addWidget(self.current_button)
        
        layout.addLayout(button_layout)
        
        # Initialize with home directory
        self.go_to_home()
    
    def set_root_path(self, path):
        """Set the root path for the file system model"""
        index = self.model.setRootPath(path)
        self.tree_view.setRootIndex(index)
        self.path_input.setText(path)
    
    def on_path_changed(self):
        """Handle path input changes"""
        new_path = self.path_input.text()
        self.set_root_path(new_path)
    
    def browse_directory(self):
        """Open directory browser dialog"""
        from PySide6.QtWidgets import QFileDialog
        
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Directory", self.path_input.text()
        )
        
        if dir_path:
            self.set_root_path(dir_path)
    
    def apply_filter(self, index):
        """Apply file filter"""
        filter_text = self.filter_combo.currentText()
        
        # Extract file patterns from the filter text
        # Format is "Description (*.ext1 *.ext2)"
        if "(" in filter_text and ")" in filter_text:
            # Extract the patterns
            patterns = filter_text.split("(")[1].split(")")[0].strip()
            self.model.setNameFilters(patterns.split())
        else:
            # Clear filters
            self.model.setNameFilters([])
        
        # Don't hide files that don't match the filter
        self.model.setNameFilterDisables(False)
    
    def on_item_clicked(self, index):
        """Handle item click"""
        # Get file path of the clicked item
        file_path = self.model.filePath(index)
        
        # Check if it's a file or directory
        if self.model.isDir(index):
            self.directory_selected.emit(file_path)
        else:
            self.file_selected.emit(file_path)
    
    def on_item_double_clicked(self, index):
        """Handle item double click"""
        # Get file path of the double-clicked item
        file_path = self.model.filePath(index)
        
        # If it's a directory, expand/collapse it
        if self.model.isDir(index):
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
            else:
                self.tree_view.expand(index)
        else:
            # For files, emit file selected signal (could open file)
            self.file_selected.emit(file_path)
    
    def show_context_menu(self, position):
        """Show context menu"""
        index = self.tree_view.indexAt(position)
        
        if not index.isValid():
            return
        
        file_path = self.model.filePath(index)
        is_dir = self.model.isDir(index)
        
        # Create context menu
        context_menu = QMenu(self)
        
        # Add actions based on whether item is file or directory
        if is_dir:
            # Directory actions
            action_open = QAction("Open", self)
            action_open.triggered.connect(lambda: self.set_root_path(file_path))
            context_menu.addAction(action_open)
            
            action_process = QAction("Process Directory", self)
            action_process.triggered.connect(lambda: self.process_directory(file_path))
            context_menu.addAction(action_process)
        else:
            # File actions
            action_process = QAction("Process File", self)
            action_process.triggered.connect(lambda: self.process_file(file_path))
            context_menu.addAction(action_process)
            
            action_open = QAction("Open in Editor", self)
            action_open.triggered.connect(lambda: self.open_file(file_path))
            context_menu.addAction(action_open)
        
        # Show the context menu
        context_menu.exec(self.tree_view.viewport().mapToGlobal(position))
    
    def go_to_home(self):
        """Navigate to user's home directory"""
        home_dir = QDir.homePath()
        self.set_root_path(home_dir)
    
    def go_to_documents(self):
        """Navigate to user's documents directory"""
        docs_dir = QDir.homePath() + "/Documents"
        if not QDir(docs_dir).exists():
            docs_dir = QDir.homePath()
        self.set_root_path(docs_dir)
    
    def go_to_current_dir(self):
        """Navigate to the application's current directory"""
        import os
        current_dir = os.getcwd()
        self.set_root_path(current_dir)
    
    def process_directory(self, dir_path=None):
        """Process the selected directory"""
        if dir_path is None:
            # Get the selected directory
            indexes = self.tree_view.selectedIndexes()
            if not indexes:
                QMessageBox.warning(self, "Warning", "No directory selected.")
                return
            
            # Use the first column (name) index
            index = indexes[0]
            dir_path = self.model.filePath(index)
            
            # Check if it's actually a directory
            if not self.model.isDir(index):
                QMessageBox.warning(self, "Warning", "Selected item is not a directory.")
                return
        
        # Emit signal to process the directory
        self.directory_selected.emit(dir_path)
    
    def process_file(self, file_path=None):
        """Process the selected file"""
        if file_path is None:
            # Get the selected file
            indexes = self.tree_view.selectedIndexes()
            if not indexes:
                QMessageBox.warning(self, "Warning", "No file selected.")
                return
            
            # Use the first column (name) index
            index = indexes[0]
            file_path = self.model.filePath(index)
            
            # Check if it's actually a file
            if self.model.isDir(index):
                QMessageBox.warning(self, "Warning", "Selected item is a directory, not a file.")
                return
        
        # Emit signal to process the file
        self.file_selected.emit(file_path)
    
    def open_file(self, file_path):
        """Open the selected file in an editor"""
        # This is a placeholder for opening a file in an editor
        # For now, just emit the file selected signal
        self.file_selected.emit(file_path)
        
        # In a real implementation, this might use QDesktopServices to open the file
        # or integrate with an internal editor



