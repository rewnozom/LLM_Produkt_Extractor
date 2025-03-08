#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# gui/dialogs/progress_dialog.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QProgressBar, 
    QLabel, QPushButton, QTextEdit, QFrame, 
    QDialogButtonBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QThread
from PySide6.QtGui import QIcon, QFont, QTextCursor

class ProgressWorker(QThread):
    """Worker thread for long-running operations"""
    
    # Signals
    progress_updated = Signal(int, int)  # current, total
    status_updated = Signal(str)  # status message
    operation_completed = Signal(bool, object)  # success, result
    log_message = Signal(str, str)  # message, type (info, warning, error)
    
    def __init__(self, operation_func, *args, **kwargs):
        """
        Initialize the worker thread.
        
        Args:
            operation_func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        """
        super().__init__()
        
        self.operation_func = operation_func
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self.success = False
        self.should_cancel = False
    
    def run(self):
        """Execute the function in the thread"""
        try:
            # Add callback functions to kwargs
            self.kwargs["progress_callback"] = self.progress_updated.emit
            self.kwargs["status_callback"] = self.status_updated.emit
            self.kwargs["log_callback"] = self.log_message.emit
            self.kwargs["cancel_check"] = lambda: self.should_cancel
            
            # Run the operation
            self.result = self.operation_func(*self.args, **self.kwargs)
            self.success = True
            
            # Emit completion signal
            self.operation_completed.emit(True, self.result)
            
        except Exception as e:
            # Log the error
            import traceback
            error_text = f"Error: {str(e)}\n{traceback.format_exc()}"
            self.log_message.emit(error_text, "error")
            
            # Emit completion signal with failure
            self.operation_completed.emit(False, None)
            self.success = False
    
    def cancel(self):
        """Signal that the operation should be cancelled"""
        self.should_cancel = True


class ProgressDialog(QDialog):
    """
    Dialog for showing progress of long-running operations.
    
    Features:
    - Progress bar with percentage and text
    - Detailed log of operations
    - Ability to cancel operation
    - Option to run in background
    """
    
    # Signal emitted when operation is completed
    operation_completed = Signal(bool, object)  # success, result
    
    def __init__(self, title, description, parent=None, can_cancel=True, can_background=True):
        """
        Initialize the progress dialog.
        
        Args:
            title: Dialog title
            description: Operation description
            parent: Parent widget
            can_cancel: Whether the operation can be cancelled
            can_background: Whether the operation can be run in background
        """
        super().__init__(parent)
        
        self.setWindowTitle(title)
        self.description = description
        self.can_cancel = can_cancel
        self.can_background = can_background
        self.is_completed = False
        self.is_successful = False
        self.result = None
        self.worker = None
        self.auto_close = True
        
        # Ensure dialog is deleted when closed
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        
        # Set size
        self.setMinimumSize(500, 400)
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI components"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Description label
        self.description_label = QLabel(self.description)
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)
        
        # Progress section
        progress_frame = QFrame()
        progress_frame.setFrameShape(QFrame.StyledPanel)
        progress_layout = QVBoxLayout(progress_frame)
        
        # Status label
        self.status_label = QLabel("Preparing...")
        self.status_label.setWordWrap(True)
        progress_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(progress_frame)
        
        # Log section
        log_layout = QVBoxLayout()
        log_label = QLabel("Operation Log:")
        log_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setProperty("monospace", True)  # Apply monospace style
        self.log_text.setMinimumHeight(150)
        log_layout.addWidget(self.log_text)
        
        layout.addLayout(log_layout)
        
        # Auto-close checkbox
        self.auto_close_checkbox = QCheckBox("Close automatically when completed")
        self.auto_close_checkbox.setChecked(self.auto_close)
        self.auto_close_checkbox.toggled.connect(self.set_auto_close)
        layout.addWidget(self.auto_close_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Background button (if enabled)
        if self.can_background:
            self.background_button = QPushButton("Run in Background")
            self.background_button.clicked.connect(self.run_in_background)
            button_layout.addWidget(self.background_button)
        
        # Spacer
        button_layout.addStretch()
        
        # Cancel/Close button
        self.cancel_button = QPushButton("Cancel" if self.can_cancel else "Close")
        self.cancel_button.clicked.connect(self.handle_cancel)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def run_operation(self, operation_func, *args, **kwargs):
        """
        Run the operation in a separate thread.
        
        Args:
            operation_func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            ProgressWorker: The worker thread
        """
        # Create worker thread
        self.worker = ProgressWorker(operation_func, *args, **kwargs)
        
        # Connect signals
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.status_updated.connect(self.update_status)
        self.worker.log_message.connect(self.add_log_message)
        self.worker.operation_completed.connect(self.handle_completion)
        
        # Start the worker
        self.worker.start()
        
        # Log operation start
        self.add_log_message("Operation started...", "info")
        
        return self.worker
    
    def update_progress(self, current, total):
        """
        Update the progress bar.
        
        Args:
            current: Current progress
            total: Total progress value
        """
        if total <= 0:
            # Show busy indicator if total is not known
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            
            # Calculate percentage
            percentage = int((current / total) * 100)
            self.progress_bar.setFormat(f"{percentage}% ({current}/{total})")
    
    def update_status(self, status):
        """
        Update the status message.
        
        Args:
            status: New status message
        """
        self.status_label.setText(status)
        
        # Also add to log
        self.add_log_message(status, "info")
    
    def add_log_message(self, message, message_type="info"):
        """
        Add a message to the log.
        
        Args:
            message: Message text
            message_type: Type of message (info, warning, error)
        """
        # Get timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color based on message type
        if message_type == "error":
            color = "#f43f5e"  # Red
        elif message_type == "warning":
            color = "#f59e0b"  # Amber
        else:
            color = "#3b82f6"  # Blue
        
        # Add formatted message to log
        self.log_text.append(f'<span style="color:{color}">[{timestamp}]</span> {message}')
        
        # Auto-scroll to bottom
        self.log_text.moveCursor(QTextCursor.End)
    
    def handle_completion(self, success, result):
        """
        Handle operation completion.
        
        Args:
            success: Whether the operation was successful
            result: Operation result
        """
        self.is_completed = True
        self.is_successful = success
        self.result = result
        
        # Log completion
        if success:
            self.add_log_message("Operation completed successfully.", "info")
        else:
            self.add_log_message("Operation failed.", "error")
        
        # Update UI
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100 if success else 0)
        
        self.status_label.setText("Completed" if success else "Failed")
        
        # Update buttons
        if self.can_background:
            self.background_button.setEnabled(False)
        
        self.cancel_button.setText("Close")
        self.cancel_button.setEnabled(True)
        
        # Emit completion signal
        self.operation_completed.emit(success, result)
        
        # Auto-close if enabled and successful
        if self.auto_close and success:
            self.accept()
    
    def handle_cancel(self):
        """Handle cancel button click"""
        if self.is_completed:
            # If completed, just close
            self.accept() if self.is_successful else self.reject()
        else:
            # Cancel in progress operation
            if self.worker and self.can_cancel:
                self.add_log_message("Cancelling operation...", "warning")
                self.worker.cancel()
                
                # Update UI
                self.cancel_button.setEnabled(False)
                self.cancel_button.setText("Cancelling...")
                
                # Add a timer to check for completion
                QTimer.singleShot(500, self.check_cancelled)
            else:
                # Just close
                self.reject()
    
    def check_cancelled(self):
        """Check if the worker has been cancelled and stopped"""
        if self.worker and self.worker.isRunning():
            # Still running, check again later
            QTimer.singleShot(500, self.check_cancelled)
        else:
            # Worker stopped, close dialog
            self.reject()
    
    def run_in_background(self):
        """Run the operation in background (minimize dialog)"""
        if self.parent():
            # Just hide, don't destroy
            self.hide()
            
            # Show status in parent's status bar if available
            if hasattr(self.parent(), "statusBar"):
                parent_status_bar = self.parent().statusBar()
                if parent_status_bar:
                    parent_status_bar.showMessage(f"Background operation: {self.description}")
    
    def set_auto_close(self, auto_close):
        """Set whether to auto-close when completed"""
        self.auto_close = auto_close
    
    def closeEvent(self, event):
        """Handle window close event"""
        if not self.is_completed and self.worker and self.worker.isRunning():
            # Operation is still running
            if self.can_cancel:
                # Cancel the operation
                self.worker.cancel()
                event.accept()
            else:
                # Cannot cancel, reject close
                event.ignore()
        else:
            # Allow close
            event.accept()

    @staticmethod
    def run_with_progress(title, description, operation_func, parent=None, 
                         can_cancel=True, can_background=True, *args, **kwargs):
        """
        Static method to create and show a progress dialog for an operation.
        
        Args:
            title: Dialog title
            description: Operation description
            operation_func: Function to execute
            parent: Parent widget
            can_cancel: Whether the operation can be cancelled
            can_background: Whether the operation can be run in background
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            tuple: (success, result)
        """
        # Create progress dialog
        dialog = ProgressDialog(title, description, parent, can_cancel, can_background)
        
        # Run the operation
        dialog.run_operation(operation_func, *args, **kwargs)
        
        # Show the dialog
        dialog.exec()
        
        # Return the result
        return dialog.is_successful, dialog.result


# Example usage
if __name__ == "__main__":
    import sys
    import time
    from PySide6.QtWidgets import QApplication
    
    # Example operation function
    def example_operation(steps=10, delay=0.5, 
                        progress_callback=None, 
                        status_callback=None, 
                        log_callback=None,
                        cancel_check=None):
        """Example long-running operation"""
        # Initialize
        if status_callback:
            status_callback("Starting operation...")
        
        # Process each step
        for i in range(steps):
            # Check for cancellation
            if cancel_check and cancel_check():
                if log_callback:
                    log_callback("Operation was cancelled", "warning")
                return None
            
            # Update progress
            if progress_callback:
                progress_callback(i, steps)
            
            # Update status
            if status_callback:
                status_callback(f"Processing step {i+1}/{steps}...")
            
            # Log step
            if log_callback:
                log_callback(f"Completed step {i+1}/{steps}", "info")
                
                # Add random warnings or errors
                import random
                if random.random() < 0.3:
                    log_callback(f"Warning in step {i+1}: This is a test warning", "warning")
                
                if random.random() < 0.1:
                    log_callback(f"Non-fatal error in step {i+1}: This is a test error", "error")
            
            # Simulate work
            time.sleep(delay)
        
        # Final update
        if progress_callback:
            progress_callback(steps, steps)
        
        if status_callback:
            status_callback("Operation completed successfully.")
        
        # Return a result
        return {"processed_steps": steps, "success": True}
    
    # Create application
    app = QApplication(sys.argv)
    
    # Run the operation with a progress dialog
    success, result = ProgressDialog.run_with_progress(
        "Example Operation",
        "This is an example long-running operation with progress reporting.",
        example_operation,
        None,  # No parent
        True,  # Can cancel
        True,  # Can run in background
        steps=20,  # Operation args
        delay=0.3
    )
    
    # Print result
    print(f"Operation {'succeeded' if success else 'failed'}")
    if success:
        print(f"Result: {result}")
    
    # Exit
    sys.exit(0)