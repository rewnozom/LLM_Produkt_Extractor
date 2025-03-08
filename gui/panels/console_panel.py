#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, 
    QLineEdit, QPushButton, QComboBox, QLabel
)
from PySide6.QtCore import Qt, Signal, QDateTime
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor

class ConsolePanel(QWidget):
    """
    Console panel for displaying logs and executing commands
    """
    # Define signals
    command_executed = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        # Color settings for different log types
        self.log_colors = {
            'info': QColor("#3b82f6"),     # Blue
            'workflow': QColor("#10b981"), # Green
            'error': QColor("#f43f5e"),    # Red
            'warning': QColor("#f59e0b"),  # Amber
            'command': QColor("#8b5cf6"),  # Purple
            'response': QColor("#d1cccc")  # Default text color
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the console panel UI"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Console output area
        self.console_output = QPlainTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setProperty("monospace", True)  # Apply monospace styling
        self.console_output.setMaximumBlockCount(5000)  # Limit to prevent memory issues
        layout.addWidget(self.console_output)
        
        # Command input area
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        # Log level filter
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["All", "Info", "Workflow", "Warning", "Error"])
        self.log_level_combo.setCurrentIndex(0)
        self.log_level_combo.currentIndexChanged.connect(self.filter_logs)
        input_layout.addWidget(QLabel("Filter:"))
        input_layout.addWidget(self.log_level_combo)
        
        # Command input
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command...")
        self.command_input.returnPressed.connect(self.execute_command)
        input_layout.addWidget(self.command_input)
        
        # Execute button
        self.execute_button = QPushButton("Execute")
        self.execute_button.clicked.connect(self.execute_command)
        input_layout.addWidget(self.execute_button)
        
        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_console)
        input_layout.addWidget(self.clear_button)
        
        layout.addLayout(input_layout)
        
        # Initialize console with welcome message
        self.log_info("Console initialized. Type commands here or see application logs.")
    
    def execute_command(self):
        """Execute the command entered in the input field"""
        command = self.command_input.text().strip()
        if not command:
            return
        
        # Log the command
        self.log_message(f"$ {command}", 'command')
        
        # Emit signal with command
        self.command_executed.emit(command)
        
        # Clear the input field
        self.command_input.clear()
    
    def log_message(self, message, message_type='info'):
        """
        Log a message to the console with appropriate formatting
        
        Args:
            message: Message to log
            message_type: Type of message ('info', 'workflow', 'error', 'warning', 'command', 'response')
        """
        # Get current time
        timestamp = QDateTime.currentDateTime().toString("HH:mm:ss")
        
        # Create formatted message
        formatted_message = f"[{timestamp}] "
        
        # Create text format for this message type
        text_format = QTextCharFormat()
        text_format.setForeground(self.log_colors.get(message_type, QColor("#d1cccc")))
        
        # Get cursor and preserve position state
        cursor = self.console_output.textCursor()
        scrollbar_position = self.console_output.verticalScrollBar().value()
        was_at_bottom = scrollbar_position == self.console_output.verticalScrollBar().maximum()
        
        # Move cursor to end
        cursor.movePosition(QTextCursor.End)
        
        # Insert timestamp with default formatting
        cursor.insertText(formatted_message)
        
        # Insert message with type-specific formatting
        cursor.setCharFormat(text_format)
        cursor.insertText(f"{message}\n")
        
        # Auto-scroll if was previously at bottom
        if was_at_bottom:
            self.console_output.verticalScrollBar().setValue(
                self.console_output.verticalScrollBar().maximum()
            )
    
    def log_info(self, message):
        """Log an informational message"""
        self.log_message(message, 'info')
    
    def log_workflow(self, message):
        """Log a workflow-related message"""
        self.log_message(message, 'workflow')
    
    def log_error(self, message):
        """Log an error message"""
        self.log_message(message, 'error')
    
    def log_warning(self, message):
        """Log a warning message"""
        self.log_message(message, 'warning')
    
    def log_response(self, message):
        """Log a response from the LLM"""
        self.log_message(message, 'response')
    
    def clear_console(self):
        """Clear the console output"""
        self.console_output.clear()
        self.log_info("Console cleared")
    
    def filter_logs(self, index):
        """
        Filter logs by level
        
        Args:
            index: Index of the selected filter in the combo box
        """
        # This would ideally filter the existing log entries, but for simplicity
        # we'll just log that filtering was changed
        filter_type = self.log_level_combo.currentText()
        self.log_info(f"Log filtering set to: {filter_type}")