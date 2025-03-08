#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# gui/utils/logger_adapter.py

import os
import sys
import logging
import datetime
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Callable
from PySide6.QtCore import QObject, Signal, Qt


class LogRecord:
    """Simple data class to represent a log record"""
    def __init__(self, level: int, level_name: str, message: str, timestamp: float, 
                module: str = "", function: str = "", extra: Dict[str, Any] = None):
        self.level = level
        self.level_name = level_name
        self.message = message
        self.timestamp = timestamp
        self.module = module
        self.function = function
        self.extra = extra or {}
        self.datetime = datetime.datetime.fromtimestamp(timestamp)
        
    def __repr__(self):
        return f"LogRecord({self.level_name}, {self.message}, {self.datetime})"
    
    def get_formatted_time(self, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Get formatted timestamp"""
        return self.datetime.strftime(format_str)


class GUILogHandler(logging.Handler):
    """
    Custom logging handler that emits signals for log messages.
    This allows integration of Python's logging with Qt's signal/slot system.
    """
    def __init__(self, callback: Callable[[LogRecord], None]):
        """
        Initialize the handler.
        
        Args:
            callback: Function to call with each log record
        """
        super().__init__()
        self.callback = callback
    
    def emit(self, record):
        """
        Emit a log record by calling the callback.
        
        Args:
            record: The log record to emit
        """
        try:
            # Extract info from the record
            log_record = LogRecord(
                level=record.levelno,
                level_name=record.levelname,
                message=self.format(record),
                timestamp=record.created,
                module=record.module,
                function=record.funcName,
                extra=getattr(record, 'extra', None)
            )
            
            # Call the callback with the record
            self.callback(log_record)
        except Exception:
            self.handleError(record)


class LoggerAdapter(QObject):
    """
    Adapter class to bridge Python's logging with Qt GUI.
    
    This class:
    1. Sets up Python's logging system
    2. Emits Qt signals for log events
    3. Provides convenience methods for logging
    4. Optionally logs to file
    
    Usage:
        logger_adapter = LoggerAdapter()
        logger_adapter.log_received.connect(my_console_widget.add_log)
        logger_adapter.info("Application started")
    """
    
    # Signal emitted when a log record is received
    log_received = Signal(object)  # Emits LogRecord objects
    
    # Signals for specific log levels
    info_logged = Signal(str)
    warning_logged = Signal(str)
    error_logged = Signal(str)
    debug_logged = Signal(str)
    
    def __init__(self, 
                app_name: str = "product_extractor",
                log_level: int = logging.INFO,
                log_to_file: bool = False,
                log_file: Optional[str] = None,
                max_logs_in_memory: int = 1000):
        """
        Initialize the logger adapter.
        
        Args:
            app_name: Name of the application (used for logger name)
            log_level: Initial logging level
            log_to_file: Whether to log to a file
            log_file: Path to log file (default: ./logs/{app_name}.log)
            max_logs_in_memory: Maximum number of logs to keep in memory
        """
        super().__init__()
        
        self.app_name = app_name
        self.log_to_file = log_to_file
        self.log_file = log_file or f"./logs/{app_name}.log"
        self.max_logs_in_memory = max_logs_in_memory
        
        # List to store recent log records in memory
        self.log_records = []
        
        # Set up logging
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(log_level)
        
        # Remove existing handlers to avoid duplicates when reconfiguring
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        ))
        self.logger.addHandler(console_handler)
        
        # Add GUI handler
        self.gui_handler = GUILogHandler(self._on_log_record)
        self.gui_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(self.gui_handler)
        
        # Add file handler if enabled
        if log_to_file:
            self.setup_file_logging(self.log_file)
        
        # Log startup
        self.info(f"{app_name} logging initialized")
    
    def _on_log_record(self, record: LogRecord) -> None:
        """
        Handle a new log record.
        
        Args:
            record: The log record to handle
        """
        # Add to in-memory log storage
        self.log_records.append(record)
        
        # Trim if we have too many
        if len(self.log_records) > self.max_logs_in_memory:
            self.log_records = self.log_records[-self.max_logs_in_memory:]
        
        # Emit signals
        self.log_received.emit(record)
        
        # Emit specific level signals
        message = record.message
        if record.level == logging.INFO:
            self.info_logged.emit(message)
        elif record.level == logging.WARNING:
            self.warning_logged.emit(message)
        elif record.level == logging.ERROR:
            self.error_logged.emit(message)
        elif record.level == logging.DEBUG:
            self.debug_logged.emit(message)
    
    def setup_file_logging(self, log_file: str) -> None:
        """
        Set up logging to a file.
        
        Args:
            log_file: Path to the log file
        """
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            # Create file handler
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s (%(module)s.%(funcName)s): %(message)s'
            ))
            
            # Add to logger
            self.logger.addHandler(file_handler)
            self.log_file = log_file
            self.log_to_file = True
            
            self.debug(f"File logging enabled: {log_file}")
        except Exception as e:
            self.error(f"Failed to set up file logging: {str(e)}")
    
    def disable_file_logging(self) -> None:
        """Disable logging to file"""
        # Remove file handlers
        for handler in self.logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                self.logger.removeHandler(handler)
        
        self.log_to_file = False
        self.debug("File logging disabled")
    
    def set_level(self, level: Union[int, str]) -> None:
        """
        Set the logging level.
        
        Args:
            level: Logging level (can be a string like 'INFO' or a logging constant)
        """
        # Convert string to level if needed
        if isinstance(level, str):
            level_map = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
                'CRITICAL': logging.CRITICAL
            }
            numeric_level = level_map.get(level.upper(), logging.INFO)
        else:
            numeric_level = level
        
        # Set the level
        self.logger.setLevel(numeric_level)
        self.debug(f"Log level set to {logging.getLevelName(numeric_level)}")
    
    def get_recent_logs(self, count: int = None, level: int = None,
                       start_time: float = None, end_time: float = None) -> List[LogRecord]:
        """
        Get recent log records, optionally filtered.
        
        Args:
            count: Maximum number of logs to return
            level: Minimum log level to include
            start_time: Start time (timestamp) to filter logs
            end_time: End time (timestamp) to filter logs
            
        Returns:
            List of filtered LogRecord objects
        """
        # Start with all logs
        logs = self.log_records
        
        # Apply filters
        if level is not None:
            logs = [log for log in logs if log.level >= level]
        
        if start_time is not None:
            logs = [log for log in logs if log.timestamp >= start_time]
        
        if end_time is not None:
            logs = [log for log in logs if log.timestamp <= end_time]
        
        # Limit count
        if count is not None:
            logs = logs[-count:]
        
        return logs
    
    def clear_logs(self) -> None:
        """Clear all in-memory logs"""
        self.log_records = []
        self.debug("In-memory logs cleared")
    
    def export_logs(self, file_path: str, format_type: str = "txt") -> bool:
        """
        Export logs to a file.
        
        Args:
            file_path: Path to save the logs
            format_type: Format type ('txt', 'csv', or 'json')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if format_type.lower() == 'csv':
                    # CSV format
                    import csv
                    writer = csv.writer(f)
                    writer.writerow(['Timestamp', 'Level', 'Message', 'Module', 'Function'])
                    
                    for record in self.log_records:
                        writer.writerow([
                            record.get_formatted_time(),
                            record.level_name,
                            record.message,
                            record.module,
                            record.function
                        ])
                
                elif format_type.lower() == 'json':
                    # JSON format
                    import json
                    json_logs = []
                    
                    for record in self.log_records:
                        json_logs.append({
                            'timestamp': record.timestamp,
                            'formatted_time': record.get_formatted_time(),
                            'level': record.level,
                            'level_name': record.level_name,
                            'message': record.message,
                            'module': record.module,
                            'function': record.function,
                            'extra': record.extra
                        })
                    
                    json.dump(json_logs, f, indent=2)
                
                else:
                    # Plain text format
                    for record in self.log_records:
                        f.write(f"{record.get_formatted_time()} [{record.level_name}] {record.message}\n")
            
            self.info(f"Logs exported to {file_path}")
            return True
            
        except Exception as e:
            self.error(f"Failed to export logs: {str(e)}")
            return False
    
    # Convenience logging methods
    def debug(self, message: str, **kwargs) -> None:
        """Log a debug message"""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log an info message"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log a warning message"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log an error message"""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log a critical message"""
        self.logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """Log an exception message with traceback"""
        self.logger.exception(message, **kwargs)
    
    # Additional specialized logging methods
    def workflow(self, message: str) -> None:
        """Log a workflow-related message"""
        self.logger.info(message, extra={'category': 'workflow'})
    
    def extraction(self, message: str) -> None:
        """Log an extraction-related message"""
        self.logger.info(message, extra={'category': 'extraction'})
    
    def llm(self, message: str) -> None:
        """Log an LLM-related message"""
        self.logger.info(message, extra={'category': 'llm'})
    
    def gui(self, message: str) -> None:
        """Log a GUI-related message"""
        self.logger.info(message, extra={'category': 'gui'})
    
    def config(self, message: str) -> None:
        """Log a configuration-related message"""
        self.logger.info(message, extra={'category': 'config'})


