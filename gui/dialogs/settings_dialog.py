#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# gui/dialogs/settings_dialog.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
    QWidget, QFormLayout, QLabel, QLineEdit, 
    QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, 
    QPushButton, QFileDialog, QGroupBox, QMessageBox,
    QFontComboBox, QColorDialog, QFrame, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, QSettings, QSize
from PySide6.QtGui import QFont, QColor, QIcon

class SettingsDialog(QDialog):
    """
    Dialog for application settings management.
    Organizes settings in tabs for different categories:
    - General: Basic app settings
    - Appearance: Theme, fonts, colors
    - Backend: API endpoints, credentials
    - Advanced: Performance, caching, debugging
    """
    
    # Signal emitted when settings are applied
    settings_changed = Signal(dict)
    
    def __init__(self, parent=None, config=None):
        """
        Initialize the settings dialog.
        
        Args:
            parent: Parent widget
            config: Current configuration dictionary (optional)
        """
        super().__init__(parent)
        
        # Store the current configuration
        self.config = config or {}
        self.initial_config = self.config.copy()
        
        # Settings object for storing/retrieving user preferences
        self.settings = QSettings("ProductExtractor", "LLMProductTool")
        
        # Initialize UI
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 450)
        self.setup_ui()
        
        # Apply current config to UI
        self.update_ui_from_config()
    
    def setup_ui(self):
        """Set up the dialog UI components"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Create tabs widget
        self.tabs = QTabWidget()
        
        # Add tabs for different setting categories
        self.setup_general_tab()
        self.setup_appearance_tab()
        self.setup_backend_tab()
        self.setup_advanced_tab()
        
        layout.addWidget(self.tabs)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        # Reset button
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(self.reset_button)
        
        # Spacer
        button_layout.addStretch()
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
    
    def setup_general_tab(self):
        """Set up the General settings tab"""
        general_tab = QWidget()
        layout = QVBoxLayout(general_tab)
        
        # General options group
        general_group = QGroupBox("General Options")
        form_layout = QFormLayout(general_group)
        
        # Default output directory
        dir_layout = QHBoxLayout()
        self.output_dir_input = QLineEdit()
        dir_layout.addWidget(self.output_dir_input)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_output_dir)
        dir_layout.addWidget(browse_button)
        
        form_layout.addRow("Output Directory:", dir_layout)
        
        # File extension filter
        self.file_filter_input = QLineEdit()
        form_layout.addRow("File Extensions:", self.file_filter_input)
        
        # Auto-save
        self.auto_save_check = QCheckBox("Enable Auto-Save")
        form_layout.addRow("", self.auto_save_check)
        
        # Auto-save interval
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(1, 60)
        self.auto_save_interval.setValue(5)
        self.auto_save_interval.setSuffix(" minutes")
        form_layout.addRow("Auto-Save Interval:", self.auto_save_interval)
        
        layout.addWidget(general_group)
        
        # Startup behavior
        startup_group = QGroupBox("Startup Behavior")
        startup_layout = QFormLayout(startup_group)
        
        self.load_last_project = QCheckBox("Load last project on startup")
        startup_layout.addRow("", self.load_last_project)
        
        self.check_updates = QCheckBox("Check for updates on startup")
        startup_layout.addRow("", self.check_updates)
        
        self.startup_tab = QComboBox()
        self.startup_tab.addItems(["Workflow", "Extraction", "Prompts", "Results", "LLM Config"])
        startup_layout.addRow("Default Tab:", self.startup_tab)
        
        layout.addWidget(startup_group)
        layout.addStretch()
        
        self.tabs.addTab(general_tab, "General")
    
    def setup_appearance_tab(self):
        """Set up the Appearance settings tab"""
        appearance_tab = QWidget()
        layout = QVBoxLayout(appearance_tab)
        
        # Theme group
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout(theme_group)
        
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["Light", "Dark", "System"])
        theme_layout.addRow("Application Theme:", self.theme_selector)
        
        self.accent_color_button = QPushButton("Select...")
        self.accent_color_button.clicked.connect(self.select_accent_color)
        self.accent_color_preview = QFrame()
        self.accent_color_preview.setFixedSize(24, 24)
        self.accent_color_preview.setFrameShape(QFrame.Box)
        self.accent_color_preview.setStyleSheet("background-color: #3b82f6;")
        
        accent_layout = QHBoxLayout()
        accent_layout.addWidget(self.accent_color_preview)
        accent_layout.addWidget(self.accent_color_button)
        
        theme_layout.addRow("Accent Color:", accent_layout)
        
        layout.addWidget(theme_group)
        
        # Font group
        font_group = QGroupBox("Fonts")
        font_layout = QFormLayout(font_group)
        
        self.ui_font = QFontComboBox()
        self.ui_font.setEditable(False)
        font_layout.addRow("UI Font:", self.ui_font)
        
        self.code_font = QFontComboBox()
        self.code_font.setEditable(False)
        # Filter to only show monospaced fonts
        self.code_font.setFontFilters(QFontComboBox.MonospacedFonts)
        font_layout.addRow("Code Font:", self.code_font)
        
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 24)
        self.font_size.setValue(11)
        font_layout.addRow("Font Size:", self.font_size)
        
        layout.addWidget(font_group)
        
        # Editor group
        editor_group = QGroupBox("Editor Preferences")
        editor_layout = QFormLayout(editor_group)
        
        self.line_numbers = QCheckBox("Show Line Numbers")
        editor_layout.addRow("", self.line_numbers)
        
        self.syntax_highlighting = QCheckBox("Enable Syntax Highlighting")
        editor_layout.addRow("", self.syntax_highlighting)
        
        self.word_wrap = QCheckBox("Enable Word Wrap")
        editor_layout.addRow("", self.word_wrap)
        
        layout.addWidget(editor_group)
        layout.addStretch()
        
        self.tabs.addTab(appearance_tab, "Appearance")
    
    def setup_backend_tab(self):
        """Set up the Backend settings tab"""
        backend_tab = QWidget()
        layout = QVBoxLayout(backend_tab)
        
        # LLM Endpoints group
        llm_group = QGroupBox("LLM Service Configuration")
        llm_layout = QFormLayout(llm_group)
        
        self.primary_endpoint = QLineEdit()
        llm_layout.addRow("Primary Endpoint:", self.primary_endpoint)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(self.api_key_input)
        
        toggle_visibility = QPushButton("Show")
        toggle_visibility.setCheckable(True)
        toggle_visibility.toggled.connect(self.toggle_api_key_visibility)
        api_key_layout.addWidget(toggle_visibility)
        
        llm_layout.addRow("API Key:", api_key_layout)
        
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(5, 300)
        self.timeout_input.setValue(60)
        self.timeout_input.setSuffix(" seconds")
        llm_layout.addRow("Request Timeout:", self.timeout_input)
        
        layout.addWidget(llm_group)
        
        # Cache settings
        cache_group = QGroupBox("Cache Settings")
        cache_layout = QFormLayout(cache_group)
        
        self.enable_cache = QCheckBox("Enable Result Caching")
        cache_layout.addRow("", self.enable_cache)
        
        self.cache_dir_input = QLineEdit()
        cache_dir_layout = QHBoxLayout()
        cache_dir_layout.addWidget(self.cache_dir_input)
        
        cache_browse_button = QPushButton("Browse...")
        cache_browse_button.clicked.connect(self.browse_cache_dir)
        cache_dir_layout.addWidget(cache_browse_button)
        
        cache_layout.addRow("Cache Directory:", cache_dir_layout)
        
        self.cache_max_size = QSpinBox()
        self.cache_max_size.setRange(100, 10000)
        self.cache_max_size.setValue(1000)
        self.cache_max_size.setSuffix(" MB")
        cache_layout.addRow("Max Cache Size:", self.cache_max_size)
        
        self.cache_expiry = QSpinBox()
        self.cache_expiry.setRange(1, 365)
        self.cache_expiry.setValue(30)
        self.cache_expiry.setSuffix(" days")
        cache_layout.addRow("Cache Expiry:", self.cache_expiry)
        
        layout.addWidget(cache_group)
        layout.addStretch()
        
        self.tabs.addTab(backend_tab, "Backend")
    
    def setup_advanced_tab(self):
        """Set up the Advanced settings tab"""
        advanced_tab = QWidget()
        layout = QVBoxLayout(advanced_tab)
        
        # Performance group
        performance_group = QGroupBox("Performance")
        performance_layout = QFormLayout(performance_group)
        
        self.max_threads = QSpinBox()
        self.max_threads.setRange(1, 16)
        self.max_threads.setValue(4)
        performance_layout.addRow("Max Worker Threads:", self.max_threads)
        
        self.chunk_size = QSpinBox()
        self.chunk_size.setRange(1000, 50000)
        self.chunk_size.setValue(8000)
        self.chunk_size.setSuffix(" chars")
        performance_layout.addRow("Text Chunk Size:", self.chunk_size)
        
        self.batch_size = QSpinBox()
        self.batch_size.setRange(1, 100)
        self.batch_size.setValue(10)
        self.batch_size.setSuffix(" files")
        performance_layout.addRow("Batch Processing Size:", self.batch_size)
        
        layout.addWidget(performance_group)
        
        # Logging group
        logging_group = QGroupBox("Logging")
        logging_layout = QFormLayout(logging_group)
        
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level.setCurrentIndex(1)  # INFO by default
        logging_layout.addRow("Log Level:", self.log_level)
        
        self.log_to_file = QCheckBox("Save Logs to File")
        logging_layout.addRow("", self.log_to_file)
        
        self.log_file_path = QLineEdit()
        log_file_layout = QHBoxLayout()
        log_file_layout.addWidget(self.log_file_path)
        
        log_browse_button = QPushButton("Browse...")
        log_browse_button.clicked.connect(self.browse_log_file)
        log_file_layout.addWidget(log_browse_button)
        
        logging_layout.addRow("Log File:", log_file_layout)
        
        layout.addWidget(logging_group)
        
        # Debug options
        debug_group = QGroupBox("Debug Options")
        debug_layout = QFormLayout(debug_group)
        
        self.debug_mode = QCheckBox("Enable Debug Mode")
        debug_layout.addRow("", self.debug_mode)
        
        self.debug_console = QCheckBox("Show Debug Console")
        debug_layout.addRow("", self.debug_console)
        
        self.save_raw_responses = QCheckBox("Save Raw LLM Responses")
        debug_layout.addRow("", self.save_raw_responses)
        
        layout.addWidget(debug_group)
        layout.addStretch()
        
        self.tabs.addTab(advanced_tab, "Advanced")
    
    def update_ui_from_config(self):
        """Update UI elements with values from the configuration"""
        # General tab
        self.output_dir_input.setText(self.config.get("general", {}).get("output_dir", "./output"))
        self.file_filter_input.setText(self.config.get("general", {}).get("file_filter", "*.md;*.txt"))
        self.auto_save_check.setChecked(self.config.get("general", {}).get("auto_save", True))
        self.auto_save_interval.setValue(self.config.get("general", {}).get("auto_save_interval", 5))
        self.load_last_project.setChecked(self.config.get("general", {}).get("load_last_project", True))
        self.check_updates.setChecked(self.config.get("general", {}).get("check_updates", True))
        
        # Startup tab
        startup_tab = self.config.get("general", {}).get("startup_tab", "Workflow")
        tab_index = self.startup_tab.findText(startup_tab)
        if tab_index >= 0:
            self.startup_tab.setCurrentIndex(tab_index)
        
        # Appearance tab
        theme = self.config.get("appearance", {}).get("theme", "System")
        theme_index = self.theme_selector.findText(theme)
        if theme_index >= 0:
            self.theme_selector.setCurrentIndex(theme_index)
        
        accent_color = self.config.get("appearance", {}).get("accent_color", "#3b82f6")
        self.accent_color_preview.setStyleSheet(f"background-color: {accent_color};")
        
        ui_font = self.config.get("appearance", {}).get("ui_font", "")
        if ui_font:
            font_index = self.ui_font.findText(ui_font)
            if font_index >= 0:
                self.ui_font.setCurrentIndex(font_index)
        
        code_font = self.config.get("appearance", {}).get("code_font", "Consolas")
        font_index = self.code_font.findText(code_font)
        if font_index >= 0:
            self.code_font.setCurrentIndex(font_index)
        
        self.font_size.setValue(self.config.get("appearance", {}).get("font_size", 11))
        self.line_numbers.setChecked(self.config.get("appearance", {}).get("line_numbers", True))
        self.syntax_highlighting.setChecked(self.config.get("appearance", {}).get("syntax_highlighting", True))
        self.word_wrap.setChecked(self.config.get("appearance", {}).get("word_wrap", True))
        
        # Backend tab
        self.primary_endpoint.setText(self.config.get("llm", {}).get("base_url", ""))
        self.api_key_input.setText(self.config.get("llm", {}).get("api_key", ""))
        self.timeout_input.setValue(self.config.get("llm", {}).get("timeout", 60))
        
        self.enable_cache.setChecked(self.config.get("cache", {}).get("enabled", True))
        self.cache_dir_input.setText(self.config.get("cache", {}).get("directory", "./cache"))
        self.cache_max_size.setValue(self.config.get("cache", {}).get("max_size", 1000))
        self.cache_expiry.setValue(self.config.get("cache", {}).get("expiry_days", 30))
        
        # Advanced tab
        self.max_threads.setValue(self.config.get("performance", {}).get("max_threads", 4))
        self.chunk_size.setValue(self.config.get("extraction", {}).get("chunk_size", 8000))
        self.batch_size.setValue(self.config.get("workflow", {}).get("batch_size", 10))
        
        log_level = self.config.get("logging", {}).get("level", "INFO")
        level_index = self.log_level.findText(log_level)
        if level_index >= 0:
            self.log_level.setCurrentIndex(level_index)
        
        self.log_to_file.setChecked(self.config.get("logging", {}).get("log_to_file", False))
        self.log_file_path.setText(self.config.get("logging", {}).get("log_file", "./logs/app.log"))
        
        self.debug_mode.setChecked(self.config.get("debug", {}).get("enabled", False))
        self.debug_console.setChecked(self.config.get("debug", {}).get("console", False))
        self.save_raw_responses.setChecked(self.config.get("debug", {}).get("save_raw_responses", False))
    
    def update_config_from_ui(self):
        """Update configuration with values from UI elements"""
        # Create a new config dictionary
        config = {}
        
        # General settings
        config["general"] = {
            "output_dir": self.output_dir_input.text(),
            "file_filter": self.file_filter_input.text(),
            "auto_save": self.auto_save_check.isChecked(),
            "auto_save_interval": self.auto_save_interval.value(),
            "load_last_project": self.load_last_project.isChecked(),
            "check_updates": self.check_updates.isChecked(),
            "startup_tab": self.startup_tab.currentText()
        }
        
        # Appearance settings
        config["appearance"] = {
            "theme": self.theme_selector.currentText(),
            "accent_color": self.accent_color_preview.styleSheet().split(":")[1].strip().strip(";"),
            "ui_font": self.ui_font.currentText(),
            "code_font": self.code_font.currentText(),
            "font_size": self.font_size.value(),
            "line_numbers": self.line_numbers.isChecked(),
            "syntax_highlighting": self.syntax_highlighting.isChecked(),
            "word_wrap": self.word_wrap.isChecked()
        }
        
        # Backend settings
        config["llm"] = {
            "base_url": self.primary_endpoint.text(),
            "api_key": self.api_key_input.text(),
            "timeout": self.timeout_input.value()
        }
        
        config["cache"] = {
            "enabled": self.enable_cache.isChecked(),
            "directory": self.cache_dir_input.text(),
            "max_size": self.cache_max_size.value(),
            "expiry_days": self.cache_expiry.value()
        }
        
        # Advanced settings
        config["performance"] = {
            "max_threads": self.max_threads.value()
        }
        
        config["extraction"] = {
            "chunk_size": self.chunk_size.value()
        }
        
        config["workflow"] = {
            "batch_size": self.batch_size.value()
        }
        
        config["logging"] = {
            "level": self.log_level.currentText(),
            "log_to_file": self.log_to_file.isChecked(),
            "log_file": self.log_file_path.text()
        }
        
        config["debug"] = {
            "enabled": self.debug_mode.isChecked(),
            "console": self.debug_console.isChecked(),
            "save_raw_responses": self.save_raw_responses.isChecked()
        }
        
        # Update the config
        self.config = config
        
        return config
    
    def accept(self):
        """Handle dialog acceptance (OK button)"""
        # Update config from UI
        self.update_config_from_ui()
        
        # Apply settings
        self.apply_settings()
        
        # Close dialog
        super().accept()
    
    def apply_settings(self):
        """Apply the current settings"""
        # Save settings to QSettings
        self.save_settings_to_qsettings()
        
        # Emit signal with new config
        self.settings_changed.emit(self.config)
    
    def save_settings_to_qsettings(self):
        """Save current settings to QSettings storage"""
        # General settings
        self.settings.beginGroup("General")
        for key, value in self.config.get("general", {}).items():
            self.settings.setValue(key, value)
        self.settings.endGroup()
        
        # Appearance settings
        self.settings.beginGroup("Appearance")
        for key, value in self.config.get("appearance", {}).items():
            self.settings.setValue(key, value)
        self.settings.endGroup()
        
        # Backend settings
        self.settings.beginGroup("Backend")
        # Don't save API key directly, save if it's been modified
        api_key = self.config.get("llm", {}).get("api_key", "")
        if api_key:
            # In a real app, consider encrypting the API key
            self.settings.setValue("api_key", api_key)
        
        self.settings.setValue("primary_endpoint", self.config.get("llm", {}).get("base_url", ""))
        self.settings.setValue("timeout", self.config.get("llm", {}).get("timeout", 60))
        self.settings.endGroup()
        
        # Cache settings
        self.settings.beginGroup("Cache")
        for key, value in self.config.get("cache", {}).items():
            self.settings.setValue(key, value)
        self.settings.endGroup()
        
        # Advanced settings
        self.settings.beginGroup("Advanced")
        self.settings.setValue("max_threads", self.config.get("performance", {}).get("max_threads", 4))
        self.settings.setValue("chunk_size", self.config.get("extraction", {}).get("chunk_size", 8000))
        self.settings.setValue("batch_size", self.config.get("workflow", {}).get("batch_size", 10))
        self.settings.endGroup()
        
        # Logging settings
        self.settings.beginGroup("Logging")
        for key, value in self.config.get("logging", {}).items():
            self.settings.setValue(key, value)
        self.settings.endGroup()
        
        # Debug settings
        self.settings.beginGroup("Debug")
        for key, value in self.config.get("debug", {}).items():
            self.settings.setValue(key, value)
        self.settings.endGroup()
        
        # Sync settings to disk
        self.settings.sync()
    
    def load_settings_from_qsettings(self):
        """Load settings from QSettings storage"""
        config = {}
        
        # General settings
        config["general"] = {}
        self.settings.beginGroup("General")
        for key in self.settings.childKeys():
            config["general"][key] = self.settings.value(key)
        self.settings.endGroup()
        
        # Appearance settings
        config["appearance"] = {}
        self.settings.beginGroup("Appearance")
        for key in self.settings.childKeys():
            config["appearance"][key] = self.settings.value(key)
        self.settings.endGroup()
        
        # Backend settings
        config["llm"] = {}
        self.settings.beginGroup("Backend")
        config["llm"]["api_key"] = self.settings.value("api_key", "")
        config["llm"]["base_url"] = self.settings.value("primary_endpoint", "")
        config["llm"]["timeout"] = self.settings.value("timeout", 60, int)
        self.settings.endGroup()
        
        # Cache settings
        config["cache"] = {}
        self.settings.beginGroup("Cache")
        for key in self.settings.childKeys():
            config["cache"][key] = self.settings.value(key)
        self.settings.endGroup()
        
        # Advanced settings
        config["performance"] = {}
        config["extraction"] = {}
        config["workflow"] = {}
        
        self.settings.beginGroup("Advanced")
        config["performance"]["max_threads"] = self.settings.value("max_threads", 4, int)
        config["extraction"]["chunk_size"] = self.settings.value("chunk_size", 8000, int)
        config["workflow"]["batch_size"] = self.settings.value("batch_size", 10, int)
        self.settings.endGroup()
        
        # Logging settings
        config["logging"] = {}
        self.settings.beginGroup("Logging")
        for key in self.settings.childKeys():
            config["logging"][key] = self.settings.value(key)
        self.settings.endGroup()
        
        # Debug settings
        config["debug"] = {}
        self.settings.beginGroup("Debug")
        for key in self.settings.childKeys():
            config["debug"][key] = self.settings.value(key)
        self.settings.endGroup()
        
        return config
    
    def reset_to_defaults(self):
        """Reset all settings to default values"""
        # Ask for confirmation
        reply = QMessageBox.question(
            self, "Reset to Defaults", 
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Default settings
        default_config = {
            "general": {
                "output_dir": "./output",
                "file_filter": "*.md;*.txt",
                "auto_save": True,
                "auto_save_interval": 5,
                "load_last_project": True,
                "check_updates": True,
                "startup_tab": "Workflow"
            },
            "appearance": {
                "theme": "System",
                "accent_color": "#3b82f6",
                "ui_font": "",
                "code_font": "Consolas",
                "font_size": 11,
                "line_numbers": True,
                "syntax_highlighting": True,
                "word_wrap": True
            },
            "llm": {
                "base_url": "",
                "api_key": "",
                "timeout": 60
            },
            "cache": {
                "enabled": True,
                "directory": "./cache",
                "max_size": 1000,
                "expiry_days": 30
            },
            "performance": {
                "max_threads": 4
            },
            "extraction": {
                "chunk_size": 8000
            },
            "workflow": {
                "batch_size": 10
            },
            "logging": {
                "level": "INFO",
                "log_to_file": False,
                "log_file": "./logs/app.log"
            },
            "debug": {
                "enabled": False,
                "console": False,
                "save_raw_responses": False
            }
        }
        
        # Update config and UI
        self.config = default_config
        self.update_ui_from_config()
    
    def browse_output_dir(self):
        """Open dialog to browse for output directory"""
        current_dir = self.output_dir_input.text() or "./"
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", current_dir
        )
        
        if dir_path:
            self.output_dir_input.setText(dir_path)
    
    def browse_cache_dir(self):
        """Open dialog to browse for cache directory"""
        current_dir = self.cache_dir_input.text() or "./"
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Cache Directory", current_dir
        )
        
        if dir_path:
            self.cache_dir_input.setText(dir_path)
    
    def browse_log_file(self):
        """Open dialog to browse for log file"""
        current_file = self.log_file_path.text() or "./logs/app.log"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Select Log File", current_file, "Log Files (*.log);;All Files (*)"
        )
        
        if file_path:
            self.log_file_path.setText(file_path)
    
    def select_accent_color(self):
        """Open color dialog to select accent color"""
        # Get current color
        current_style = self.accent_color_preview.styleSheet()
        current_color = current_style.split(":")[1].strip().strip(";")
        
        # Open color dialog
        color = QColorDialog.getColor(QColor(current_color), self, "Select Accent Color")
        
        # If a valid color was selected
        if color.isValid():
            # Update the preview
            self.accent_color_preview.setStyleSheet(f"background-color: {color.name()};")
    
    def toggle_api_key_visibility(self, checked):
        """Toggle API key visibility"""
        if checked:
            self.api_key_input.setEchoMode(QLineEdit.Normal)
            self.sender().setText("Hide")
        else:
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.sender().setText("Show")
    
    def get_config(self):
        """Get the current configuration"""
        return self.config
    
    @staticmethod
    def get_settings(parent=None):
        """
        Static method to create and show the settings dialog.
        
        Args:
            parent: Parent widget
            
        Returns:
            tuple: (accepted, config) where accepted is True if OK was clicked
        """
        # Create a settings instance
        dialog = SettingsDialog(parent)
        
        # Load settings from QSettings
        config = dialog.load_settings_from_qsettings()
        dialog.config = config
        dialog.update_ui_from_config()
        
        # Show the dialog and get result
        result = dialog.exec()
        
        # Return the result and config
        return result == QDialog.Accepted, dialog.config