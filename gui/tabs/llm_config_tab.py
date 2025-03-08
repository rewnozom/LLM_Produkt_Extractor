#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QLabel, QPushButton, QDoubleSpinBox, QSpinBox, 
    QCheckBox, QTabWidget, QLineEdit, QComboBox,
    QFormLayout, QScrollArea, QTextEdit, QSplitter,
    QFrame, QFileDialog, QMessageBox, QToolButton,
    QDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QFont, QIcon

class ProviderSettingsDialog(QDialog):
    """Dialog for editing provider-specific settings"""
    
    def __init__(self, provider_name, provider_config, parent=None):
        super().__init__(parent)
        
        self.provider_name = provider_name
        self.provider_config = provider_config.copy()
        
        self.setWindowTitle(f"Settings for {provider_name}")
        self.setMinimumSize(500, 400)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Provider Settings Form
        form_group = QGroupBox("Provider Settings")
        form_layout = QFormLayout(form_group)
        
        # Base URL
        self.base_url_input = QLineEdit(self.provider_config.get("base_url", ""))
        form_layout.addRow("Base URL:", self.base_url_input)
        
        # API Key (if applicable)
        self.api_key_input = QLineEdit(self.provider_config.get("api_key", ""))
        self.api_key_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("API Key:", self.api_key_input)
        
        # Models
        self.models_input = QLineEdit(", ".join(self.provider_config.get("models", [])))
        form_layout.addRow("Available Models:", self.models_input)
        
        # Additional parameters
        self.params_text = QTextEdit()
        if "api_parameters" in self.provider_config:
            # Format as key: value pairs, one per line
            params_text = "\n".join([f"{k}: {v}" for k, v in self.provider_config["api_parameters"].items()])
            self.params_text.setPlainText(params_text)
        form_layout.addRow("API Parameters:", self.params_text)
        
        layout.addWidget(form_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        self.save_button.setProperty("class", "primary")
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
    
    def get_updated_config(self):
        """Get the updated provider configuration"""
        # Update the config with values from UI
        self.provider_config["base_url"] = self.base_url_input.text().strip()
        self.provider_config["api_key"] = self.api_key_input.text().strip()
        
        # Parse models as comma-separated list
        models_text = self.models_input.text().strip()
        if models_text:
            self.provider_config["models"] = [model.strip() for model in models_text.split(",")]
        else:
            self.provider_config["models"] = []
        
        # Parse API parameters as key-value pairs, one per line
        params_text = self.params_text.toPlainText().strip()
        if params_text:
            api_parameters = {}
            for line in params_text.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    api_parameters[key.strip()] = value.strip()
            self.provider_config["api_parameters"] = api_parameters
        
        return self.provider_config

class LLMConfigTab(QWidget):
    """
    Tab for configuring LLM providers and settings
    """
    # Define signals
    llm_config_changed = Signal(dict)  # All LLM settings
    
    def __init__(self):
        super().__init__()
        
        # Define possible providers
        self.available_providers = [
            "ollama",
            "lmstudio",
            "oobabooga",
            "openai",
            "claude",
            "openrouter",
            "custom"
        ]
        
        # Keep track of the current configuration
        self.current_config = {
            "provider": "ollama",
            "base_url": "http://localhost:11434/api",
            "model": "llama3",
            "max_tokens": 2048,
            "temperature": 0.1,
            "timeout": 60,
            "max_retries": 3,
            "retry_delay": 2,
            "context_size": 20000,
            "fallback_provider": "lmstudio",
            "fallback_base_url": "http://localhost:1234/v1",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434/api",
                    "models": ["llama3", "mistral", "vicuna"],
                    "api_parameters": {
                        "generate_endpoint": "/generate",
                        "response_key": "response"
                    }
                },
                "lmstudio": {
                    "base_url": "http://localhost:1234/v1",
                    "models": ["local-model"],
                    "api_parameters": {
                        "generate_endpoint": "/completions",
                        "response_key": "choices[0].text"
                    }
                },
                "oobabooga": {
                    "base_url": "http://localhost:5000/v1",
                    "models": ["local-model"],
                    "api_parameters": {
                        "generate_endpoint": "/completions",
                        "response_key": "choices[0].text"
                    }
                }
            }
        }
        
        self.setup_ui()
        
        # Apply initial config to UI
        self.update_ui_from_config()
    
    def setup_ui(self):
        """Setup the LLM configuration UI"""
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
        
        # Primary Provider Group
        provider_group = QGroupBox("Primary LLM Provider")
        provider_layout = QFormLayout(provider_group)
        
        # Provider selection
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(self.available_providers)
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        provider_layout.addRow("Provider:", self.provider_combo)
        
        # Base URL
        self.base_url_input = QLineEdit()
        provider_layout.addRow("Base URL:", self.base_url_input)
        
        # Model selection
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        provider_layout.addRow("Model:", self.model_combo)
        
        # Provider settings button
        provider_settings_layout = QHBoxLayout()
        self.test_connection_button = QPushButton("Test Connection")
        self.test_connection_button.clicked.connect(self.test_connection)
        provider_settings_layout.addWidget(self.test_connection_button)
        
        self.provider_settings_button = QPushButton("Provider Settings...")
        self.provider_settings_button.clicked.connect(self.edit_provider_settings)
        provider_settings_layout.addWidget(self.provider_settings_button)
        
        provider_layout.addRow("", provider_settings_layout)
        
        scroll_layout.addWidget(provider_group)
        
        # Inference Parameters Group
        inference_group = QGroupBox("Inference Parameters")
        inference_layout = QFormLayout(inference_group)
        
        # Max Tokens
        self.max_tokens_input = QSpinBox()
        self.max_tokens_input.setRange(50, 16384)
        self.max_tokens_input.setSingleStep(256)
        self.max_tokens_input.setValue(2048)
        self.max_tokens_input.valueChanged.connect(self.on_config_changed)
        inference_layout.addRow("Max Tokens:", self.max_tokens_input)
        
        # Temperature
        self.temperature_input = QDoubleSpinBox()
        self.temperature_input.setRange(0.0, 1.0)
        self.temperature_input.setSingleStep(0.05)
        self.temperature_input.setValue(0.1)
        self.temperature_input.valueChanged.connect(self.on_config_changed)
        inference_layout.addRow("Temperature:", self.temperature_input)
        
        # Context Size
        self.context_size_input = QSpinBox()
        self.context_size_input.setRange(1000, 100000)
        self.context_size_input.setSingleStep(1000)
        self.context_size_input.setValue(20000)
        self.context_size_input.valueChanged.connect(self.on_config_changed)
        inference_layout.addRow("Context Size:", self.context_size_input)
        
        scroll_layout.addWidget(inference_group)
        
        # Network Settings Group
        network_group = QGroupBox("Network Settings")
        network_layout = QFormLayout(network_group)
        
        # Timeout
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(10, 300)
        self.timeout_input.setSingleStep(10)
        self.timeout_input.setValue(60)
        self.timeout_input.setSuffix(" seconds")
        self.timeout_input.valueChanged.connect(self.on_config_changed)
        network_layout.addRow("Timeout:", self.timeout_input)
        
        # Max Retries
        self.max_retries_input = QSpinBox()
        self.max_retries_input.setRange(0, 10)
        self.max_retries_input.setValue(3)
        self.max_retries_input.valueChanged.connect(self.on_config_changed)
        network_layout.addRow("Max Retries:", self.max_retries_input)
        
        # Retry Delay
        self.retry_delay_input = QSpinBox()
        self.retry_delay_input.setRange(1, 30)
        self.retry_delay_input.setValue(2)
        self.retry_delay_input.setSuffix(" seconds")
        self.retry_delay_input.valueChanged.connect(self.on_config_changed)
        network_layout.addRow("Retry Delay:", self.retry_delay_input)
        
        # Throttling
        throttling_layout = QHBoxLayout()
        self.throttling_enabled = QCheckBox("Enable Throttling")
        self.throttling_enabled.stateChanged.connect(self.on_config_changed)
        throttling_layout.addWidget(self.throttling_enabled)
        
        self.requests_per_minute = QSpinBox()
        self.requests_per_minute.setRange(1, 120)
        self.requests_per_minute.setValue(30)
        self.requests_per_minute.valueChanged.connect(self.on_config_changed)
        throttling_layout.addWidget(self.requests_per_minute)
        throttling_layout.addWidget(QLabel("requests per minute"))
        
        network_layout.addRow("", throttling_layout)
        
        scroll_layout.addWidget(network_group)
        
        # Fallback Provider Group
        fallback_group = QGroupBox("Fallback Provider")
        fallback_layout = QFormLayout(fallback_group)
        
        # Enable Fallback
        self.fallback_enabled = QCheckBox("Enable Fallback Provider")
        self.fallback_enabled.stateChanged.connect(self.toggle_fallback_settings)
        fallback_layout.addRow("", self.fallback_enabled)
        
        # Fallback Provider
        self.fallback_provider_combo = QComboBox()
        self.fallback_provider_combo.addItems(self.available_providers)
        self.fallback_provider_combo.currentIndexChanged.connect(self.on_fallback_provider_changed)
        fallback_layout.addRow("Fallback Provider:", self.fallback_provider_combo)
        
        # Fallback Base URL
        self.fallback_base_url_input = QLineEdit()
        fallback_layout.addRow("Fallback Base URL:", self.fallback_base_url_input)
        
        # Fallback Model
        self.fallback_model_combo = QComboBox()
        self.fallback_model_combo.setEditable(True)
        fallback_layout.addRow("Fallback Model:", self.fallback_model_combo)
        
        # Fallback provider settings button
        fallback_settings_layout = QHBoxLayout()
        self.test_fallback_button = QPushButton("Test Fallback")
        self.test_fallback_button.clicked.connect(self.test_fallback_connection)
        fallback_settings_layout.addWidget(self.test_fallback_button)
        
        self.fallback_settings_button = QPushButton("Fallback Settings...")
        self.fallback_settings_button.clicked.connect(self.edit_fallback_settings)
        fallback_settings_layout.addWidget(self.fallback_settings_button)
        
        fallback_layout.addRow("", fallback_settings_layout)
        
        scroll_layout.addWidget(fallback_group)
        
        # Add buttons to the bottom
        buttons_layout = QHBoxLayout()
        
        self.load_config_button = QPushButton("Load Config")
        self.load_config_button.clicked.connect(self.load_config_from_file)
        buttons_layout.addWidget(self.load_config_button)
        
        self.save_config_button = QPushButton("Save Config")
        self.save_config_button.clicked.connect(self.save_config_to_file)
        buttons_layout.addWidget(self.save_config_button)
        
        self.reset_config_button = QPushButton("Reset to Defaults")
        self.reset_config_button.clicked.connect(self.reset_to_defaults)
        buttons_layout.addWidget(self.reset_config_button)
        
        self.apply_config_button = QPushButton("Apply Changes")
        self.apply_config_button.setProperty("class", "primary")
        self.apply_config_button.clicked.connect(self.apply_changes)
        buttons_layout.addWidget(self.apply_config_button)
        
        scroll_layout.addLayout(buttons_layout)
        
        # Set scroll content and add to left layout
        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll)
        
        # Right panel with preview and test results
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Configuration preview
        preview_group = QGroupBox("Configuration Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.config_preview = QTextEdit()
        self.config_preview.setReadOnly(True)
        self.config_preview.setProperty("monospace", True)  # Apply monospace style
        preview_layout.addWidget(self.config_preview)
        
        right_layout.addWidget(preview_group)
        
        # Test output
        test_group = QGroupBox("Test Results")
        test_layout = QVBoxLayout(test_group)
        
        self.test_output = QTextEdit()
        self.test_output.setReadOnly(True)
        test_layout.addWidget(self.test_output)
        
        right_layout.addWidget(test_group)
        
        # Add panels to splitter
        self.main_splitter.addWidget(left_widget)
        self.main_splitter.addWidget(right_widget)
        
        # Set initial splitter sizes (60% left, 40% right)
        self.main_splitter.setSizes([600, 400])
        
        # Add splitter to main layout
        layout.addWidget(self.main_splitter)
        
        # Connect additional signals
        self.base_url_input.textChanged.connect(self.on_config_changed)
        self.model_combo.currentTextChanged.connect(self.on_config_changed)
        self.fallback_base_url_input.textChanged.connect(self.on_config_changed)
        self.fallback_model_combo.currentTextChanged.connect(self.on_config_changed)
        
        # Update the preview with initial config
        self.update_config_preview()
    
    def update_ui_from_config(self):
        """Update UI elements based on current configuration"""
        # Primary provider settings
        provider_index = self.available_providers.index(self.current_config["provider"]) if self.current_config["provider"] in self.available_providers else 0
        self.provider_combo.setCurrentIndex(provider_index)
        self.base_url_input.setText(self.current_config["base_url"])
        
        # Update model list
        self.update_model_list()
        
        # Set current model
        self.model_combo.setCurrentText(self.current_config["model"])
        
        # Inference parameters
        self.max_tokens_input.setValue(self.current_config["max_tokens"])
        self.temperature_input.setValue(self.current_config["temperature"])
        self.context_size_input.setValue(self.current_config["context_size"])
        
        # Network settings
        self.timeout_input.setValue(self.current_config["timeout"])
        self.max_retries_input.setValue(self.current_config["max_retries"])
        self.retry_delay_input.setValue(self.current_config["retry_delay"])
        
        # Throttling
        throttling_enabled = "throttling" in self.current_config and self.current_config["throttling"].get("enabled", False)
        self.throttling_enabled.setChecked(throttling_enabled)
        
        requests_per_minute = self.current_config.get("throttling", {}).get("requests_per_minute", 30)
        self.requests_per_minute.setValue(requests_per_minute)
        
        # Fallback provider
        fallback_enabled = "fallback_provider" in self.current_config and self.current_config["fallback_provider"]
        self.fallback_enabled.setChecked(fallback_enabled)
        
        if fallback_enabled:
            fallback_provider = self.current_config["fallback_provider"]
            fallback_index = self.available_providers.index(fallback_provider) if fallback_provider in self.available_providers else 0
            self.fallback_provider_combo.setCurrentIndex(fallback_index)
            self.fallback_base_url_input.setText(self.current_config.get("fallback_base_url", ""))
            
            # Update fallback model list
            self.update_fallback_model_list()
            
            # Set current fallback model
            fallback_model = self.current_config.get("fallback_model", "")
            if fallback_model:
                self.fallback_model_combo.setCurrentText(fallback_model)
        
        # Toggle fallback settings based on enabled state
        self.toggle_fallback_settings()
        
        # Update the preview
        self.update_config_preview()
    
    def update_config_from_ui(self):
        """Update configuration based on UI elements"""
        # Primary provider settings
        self.current_config["provider"] = self.available_providers[self.provider_combo.currentIndex()]
        self.current_config["base_url"] = self.base_url_input.text().strip()
        self.current_config["model"] = self.model_combo.currentText().strip()
        
        # Inference parameters
        self.current_config["max_tokens"] = self.max_tokens_input.value()
        self.current_config["temperature"] = self.temperature_input.value()
        self.current_config["context_size"] = self.context_size_input.value()
        
        # Network settings
        self.current_config["timeout"] = self.timeout_input.value()
        self.current_config["max_retries"] = self.max_retries_input.value()
        self.current_config["retry_delay"] = self.retry_delay_input.value()
        
        # Throttling
        self.current_config["throttling"] = {
            "enabled": self.throttling_enabled.isChecked(),
            "requests_per_minute": self.requests_per_minute.value()
        }
        
        # Fallback provider
        if self.fallback_enabled.isChecked():
            self.current_config["fallback_provider"] = self.available_providers[self.fallback_provider_combo.currentIndex()]
            self.current_config["fallback_base_url"] = self.fallback_base_url_input.text().strip()
            self.current_config["fallback_model"] = self.fallback_model_combo.currentText().strip()
        else:
            # Remove fallback provider if disabled
            if "fallback_provider" in self.current_config:
                del self.current_config["fallback_provider"]
            if "fallback_base_url" in self.current_config:
                del self.current_config["fallback_base_url"]
            if "fallback_model" in self.current_config:
                del self.current_config["fallback_model"]
        
        # Update the preview
        self.update_config_preview()
    
    def update_config_preview(self):
        """Update the configuration preview text"""
        import json
        
        # Format the configuration as JSON
        formatted_json = json.dumps(self.current_config, indent=4)
        
        # Set the preview text
        self.config_preview.setPlainText(formatted_json)
    
    def update_model_list(self):
        """Update the model list based on selected provider"""
        provider = self.available_providers[self.provider_combo.currentIndex()]
        
        # Clear the current list
        self.model_combo.clear()
        
        # Get models for this provider
        models = []
        if provider in self.current_config["providers"]:
            models = self.current_config["providers"][provider].get("models", [])
        
        # Add models to combo box
        self.model_combo.addItems(models)
    
    def update_fallback_model_list(self):
        """Update the fallback model list based on selected provider"""
        if not self.fallback_enabled.isChecked():
            return
        
        provider = self.available_providers[self.fallback_provider_combo.currentIndex()]
        
        # Clear the current list
        self.fallback_model_combo.clear()
        
        # Get models for this provider
        models = []
        if provider in self.current_config["providers"]:
            models = self.current_config["providers"][provider].get("models", [])
        
        # Add models to combo box
        self.fallback_model_combo.addItems(models)
    
    def toggle_fallback_settings(self):
        """Enable/disable fallback settings based on checkbox"""
        enabled = self.fallback_enabled.isChecked()
        
        self.fallback_provider_combo.setEnabled(enabled)
        self.fallback_base_url_input.setEnabled(enabled)
        self.fallback_model_combo.setEnabled(enabled)
        self.test_fallback_button.setEnabled(enabled)
        self.fallback_settings_button.setEnabled(enabled)
        
        # Update config
        self.on_config_changed()
    
    def on_provider_changed(self, index):
        """Handler for when primary provider changes"""
        provider = self.available_providers[index]
        
        # Update the base URL field
        if provider in self.current_config["providers"]:
            self.base_url_input.setText(self.current_config["providers"][provider].get("base_url", ""))
        else:
            self.base_url_input.setText("")
        
        # Update model list
        self.update_model_list()
        
        # Update config
        self.on_config_changed()
    
    def on_fallback_provider_changed(self, index):
        """Handler for when fallback provider changes"""
        if not self.fallback_enabled.isChecked():
            return
        
        provider = self.available_providers[index]
        
        # Update the base URL field
        if provider in self.current_config["providers"]:
            self.fallback_base_url_input.setText(self.current_config["providers"][provider].get("base_url", ""))
        else:
            self.fallback_base_url_input.setText("")
        
        # Update model list
        self.update_fallback_model_list()
        
        # Update config
        self.on_config_changed()
    
    def on_config_changed(self):
        """Handler for when any configuration option changes"""
        # Update the current config
        self.update_config_from_ui()
        
        # Enable the apply button
        self.apply_config_button.setEnabled(True)
    
    def edit_provider_settings(self):
        """Edit detailed settings for the primary provider"""
        provider = self.available_providers[self.provider_combo.currentIndex()]
        
        # Get current provider config
        provider_config = {}
        if provider in self.current_config["providers"]:
            provider_config = self.current_config["providers"][provider].copy()
        else:
            # Create minimal default config
            provider_config = {
                "base_url": self.base_url_input.text().strip(),
                "models": []
            }
        
        # Open settings dialog
        dialog = ProviderSettingsDialog(provider, provider_config, self)
        if dialog.exec():
            # Update provider config
            updated_config = dialog.get_updated_config()
            
            # Ensure providers dict exists
            if "providers" not in self.current_config:
                self.current_config["providers"] = {}
            
            # Update config
            self.current_config["providers"][provider] = updated_config
            
            # Update UI
            self.base_url_input.setText(updated_config.get("base_url", ""))
            self.update_model_list()
            
            # Update preview
            self.update_config_preview()
    
    def edit_fallback_settings(self):
        """Edit detailed settings for the fallback provider"""
        if not self.fallback_enabled.isChecked():
            return
        
        provider = self.available_providers[self.fallback_provider_combo.currentIndex()]
        
        # Get current provider config
        provider_config = {}
        if provider in self.current_config["providers"]:
            provider_config = self.current_config["providers"][provider].copy()
        else:
            # Create minimal default config
            provider_config = {
                "base_url": self.fallback_base_url_input.text().strip(),
                "models": []
            }
        
        # Open settings dialog
        dialog = ProviderSettingsDialog(provider, provider_config, self)
        if dialog.exec():
            # Update provider config
            updated_config = dialog.get_updated_config()
            
            # Ensure providers dict exists
            if "providers" not in self.current_config:
                self.current_config["providers"] = {}
            
            # Update config
            self.current_config["providers"][provider] = updated_config
            
            # Update UI
            self.fallback_base_url_input.setText(updated_config.get("base_url", ""))
            self.update_fallback_model_list()
            
            # Update preview
            self.update_config_preview()
    
    def test_connection(self):
        """Test connection to the primary provider"""
        # Clear previous results
        self.test_output.clear()
        self.test_output.append("Testing connection to primary provider...")
        
        # Make sure we have the latest config
        self.update_config_from_ui()
        
        # Start test in a background thread
        from PySide6.QtCore import QThread, Signal
        
        class ConnectionTester(QThread):
            result_ready = Signal(bool, str)
            
            def __init__(self, config):
                super().__init__()
                self.config = config
            
            def run(self):
                try:
                    # Import required modules
                    from client.LLMClient import LLMClient
                    import logging
                    
                    # Create a basic logger
                    logger = logging.getLogger("connection_test")
                    handler = logging.StreamHandler()
                    logger.addHandler(handler)
                    
                    # Create LLM client
                    llm_client = LLMClient(self.config, logger)
                    
                    # Test connection
                    success, message = llm_client.verify_connection()
                    
                    self.result_ready.emit(success, message)
                except Exception as e:
                    self.result_ready.emit(False, f"Error: {str(e)}")
        
        # Create and start the tester
        self.tester = ConnectionTester(self.current_config)
        self.tester.result_ready.connect(self.on_connection_test_result)
        self.tester.start()
    
    def on_connection_test_result(self, success, message):
        """Handler for connection test results"""
        if success:
            self.test_output.append(f"<span style='color: #10b981;'>✓ Connection successful: {message}</span>")
        else:
            self.test_output.append(f"<span style='color: #f43f5e;'>✗ Connection failed: {message}</span>")
    
    def test_fallback_connection(self):
        """Test connection to the fallback provider"""
        if not self.fallback_enabled.isChecked():
            return
        
        # Clear previous results
        self.test_output.clear()
        self.test_output.append("Testing connection to fallback provider...")
        
        # Make sure we have the latest config
        self.update_config_from_ui()
        
        # Create a test config with fallback as primary
        test_config = self.current_config.copy()
        test_config["provider"] = test_config.get("fallback_provider", "")
        test_config["base_url"] = test_config.get("fallback_base_url", "")
        if "fallback_model" in test_config:
            test_config["model"] = test_config["fallback_model"]
        
        # Start test in a background thread
        from PySide6.QtCore import QThread, Signal
        
        class ConnectionTester(QThread):
            result_ready = Signal(bool, str)
            
            def __init__(self, config):
                super().__init__()
                self.config = config
            
            def run(self):
                try:
                    # Import required modules
                    from client.LLMClient import LLMClient
                    import logging
                    
                    # Create a basic logger
                    logger = logging.getLogger("connection_test")
                    handler = logging.StreamHandler()
                    logger.addHandler(handler)
                    
                    # Create LLM client
                    llm_client = LLMClient(self.config, logger)
                    
                    # Test connection
                    success, message = llm_client.verify_connection()
                    
                    self.result_ready.emit(success, message)
                except Exception as e:
                    self.result_ready.emit(False, f"Error: {str(e)}")
        
        # Create and start the tester
        self.tester = ConnectionTester(test_config)
        self.tester.result_ready.connect(self.on_fallback_test_result)
        self.tester.start()
    
    def on_fallback_test_result(self, success, message):
        """Handler for fallback connection test results"""
        if success:
            self.test_output.append(f"<span style='color: #10b981;'>✓ Fallback connection successful: {message}</span>")
        else:
            self.test_output.append(f"<span style='color: #f43f5e;'>✗ Fallback connection failed: {message}</span>")
    
    def reset_to_defaults(self):
        """Reset all settings to their default values"""
        # Ask for confirmation
        reply = QMessageBox.question(
            self, "Reset Configuration", 
            "Are you sure you want to reset all LLM settings to default values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Reset to default config
        self.current_config = {
            "provider": "ollama",
            "base_url": "http://localhost:11434/api",
            "model": "llama3",
            "max_tokens": 2048,
            "temperature": 0.1,
            "timeout": 60,
            "max_retries": 3,
            "retry_delay": 2,
            "context_size": 20000,
            "fallback_provider": "lmstudio",
            "fallback_base_url": "http://localhost:1234/v1",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434/api",
                    "models": ["llama3", "mistral", "vicuna"],
                    "api_parameters": {
                        "generate_endpoint": "/generate",
                        "response_key": "response"
                    }
                },
                "lmstudio": {
                    "base_url": "http://localhost:1234/v1",
                    "models": ["local-model"],
                    "api_parameters": {
                        "generate_endpoint": "/completions",
                        "response_key": "choices[0].text"
                    }
                },
                "oobabooga": {
                    "base_url": "http://localhost:5000/v1",
                    "models": ["local-model"],
                    "api_parameters": {
                        "generate_endpoint": "/completions",
                        "response_key": "choices[0].text"
                    }
                }
            }
        }
        
        # Update UI from the config
        self.update_ui_from_config()
        
        # Enable the apply button
        self.apply_config_button.setEnabled(True)
        
        # Show confirmation
        self.test_output.clear()
        self.test_output.append("<span style='color: #10b981;'>✓ Configuration reset to defaults</span>")
    
    def apply_changes(self):
        """Apply the current configuration to the system"""
        # Make sure the config is up to date
        self.update_config_from_ui()
        
        # Emit the configuration changed signal
        self.llm_config_changed.emit(self.current_config)
        
        # Update global config
        try:
            from config.ConfigManager import ConfigManager
            
            # Get the singleton instance
            config_manager = ConfigManager()
            
            # Update LLM config
            config_manager.set("llm", self.current_config)
            
            # Show success in test output
            self.test_output.append("<span style='color: #10b981;'>✓ Configuration successfully applied</span>")
            
            # Disable apply button until next change
            self.apply_config_button.setEnabled(False)
            
        except Exception as e:
            # Show error in test output
            self.test_output.append(f"<span style='color: #f43f5e;'>✗ Error applying configuration: {str(e)}</span>")
    
    def load_config_from_file(self):
        """Load configuration from a file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration", "", "YAML Files (*.yaml *.yml);;JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            # Load the config
            from config.ConfigManager import ConfigManager
            temp_config = ConfigManager(file_path)
            
            # Get the LLM config
            llm_config = temp_config.get("llm", {})
            
            if not llm_config:
                raise ValueError("No LLM configuration found in file")
            
            # Update the current config
            self.current_config = llm_config
            
            # Update UI
            self.update_ui_from_config()
            
            # Show success message
            self.test_output.clear()
            self.test_output.append(f"<span style='color: #10b981;'>✓ Loaded configuration from {file_path}</span>")
            
            # Enable apply button
            self.apply_config_button.setEnabled(True)
            
        except Exception as e:
            # Show error
            self.test_output.clear()
            self.test_output.append(f"<span style='color: #f43f5e;'>✗ Error loading configuration: {str(e)}</span>")
    
    def save_config_to_file(self):
        """Save configuration to a file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration", "", "YAML Files (*.yaml);;JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            # Make sure the config is up to date
            self.update_config_from_ui()
            
            # Create a temporary config manager
            from config.ConfigManager import ConfigManager
            temp_config = ConfigManager()
            
            # Update with our LLM config
            temp_config.set("llm", self.current_config)
            
            # Save the config
            success = temp_config.save_config(file_path)
            
            if success:
                # Show success message
                self.test_output.clear()
                self.test_output.append(f"<span style='color: #10b981;'>✓ Saved configuration to {file_path}</span>")
            else:
                raise ValueError("Failed to save configuration")
            
        except Exception as e:
            # Show error
            self.test_output.clear()
            self.test_output.append(f"<span style='color: #f43f5e;'>✗ Error saving configuration: {str(e)}</span>")
    
    def run(self):
        """
        Run LLM with current configuration (called from main window)
        """
        # Make sure the config is up to date
        self.update_config_from_ui()
        
        # Ensure the configuration is applied
        self.apply_changes()
        
        # In a real implementation, this might initiate a test extraction
        # For now, just test the connection
        self.test_connection()


