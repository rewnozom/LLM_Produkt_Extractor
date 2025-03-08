# gui/services/backend_service.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union

class BackendService:
    """
    Service for interfacing between the GUI and backend components
    """
    
    def __init__(self, config_path=None):
        """
        Initialize the backend service
        
        Args:
            config_path: Optional path to configuration file
        """
        self.logger = logging.getLogger("backend_service")
        self.config_manager = None
        self.workflow_manager = None
        self.llm_client = None
        self.processor = None
        self.prompt_manager = None
        
        # Event for shutdown coordination
        self.shutdown_event = threading.Event()
        
        # Status callbacks
        self.status_callbacks = []
        
        # Initialize backend components
        self.initialize_backend(config_path)
    
    def initialize_backend(self, config_path=None):
        """
        Initialize backend components
        
        Args:
            config_path: Optional path to configuration file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Import backend components
            from config.ConfigManager import ConfigManager
            from workflow.Arbetsflödeshantering import WorkflowManager
            from client.LLMClient import LLMClient
            from Processor.ProductProcessor import ProductProcessor
            from prompts import PromptManager
            
            # Initialize config manager
            self.config_manager = ConfigManager(config_path)
            
            # Initialize LLM client
            llm_config = self.config_manager.get("llm", {})
            self.llm_client = LLMClient(llm_config, self.logger, None)
            
            # Initialize prompt manager
            prompts_dir = Path("./prompts")
            if not prompts_dir.exists():
                prompts_dir.mkdir(parents=True, exist_ok=True)
            self.prompt_manager = PromptManager(storage_dir=prompts_dir, logger=self.logger)
            
            # Set prompt manager for LLM client
            if hasattr(self.llm_client, 'set_prompt_manager'):
                self.llm_client.set_prompt_manager(self.prompt_manager)
            
            # Initialize processor
            extraction_config = self.config_manager.get("extraction", {})
            self.processor = ProductProcessor(extraction_config, self.llm_client, self.logger, None, self.prompt_manager)
            
            # Initialize workflow manager
            self.workflow_manager = WorkflowManager(self.config_manager, self.logger, None)
            
            # Verify LLM connection
            connection_ok = self.llm_client.verify_connection()
            if not connection_ok:
                self.logger.warning("Could not connect to LLM service")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing backend components: {str(e)}")
            return False
    
    def shutdown(self):
        """Shutdown all backend components"""
        self.shutdown_event.set()
        
        # Stop workflow manager if running
        if self.workflow_manager:
            try:
                self.workflow_manager.stop()
                self.workflow_manager.join(timeout=5)
            except Exception as e:
                self.logger.error(f"Error stopping workflow manager: {str(e)}")
    
    def register_status_callback(self, callback: Callable[[str, str], None]):
        """
        Register a callback for status updates
        
        Args:
            callback: Callback function that takes (status_type, message)
        """
        self.status_callbacks.append(callback)
    
    def notify_status(self, status_type: str, message: str):
        """
        Notify all status callbacks
        
        Args:
            status_type: Type of status update (e.g., 'info', 'error', 'warning')
            message: Status message
        """
        for callback in self.status_callbacks:
            try:
                callback(status_type, message)
            except Exception as e:
                self.logger.error(f"Error in status callback: {str(e)}")
    
    # Methods for processor operations
    def process_product(self, product_id: str, file_path: Union[str, Path]):
        """
        Process a single product
        
        Args:
            product_id: Product ID
            file_path: Path to product file
            
        Returns:
            dict: Processing result
        """
        if not self.processor:
            self.notify_status("error", "Processor not initialized")
            return None
        
        try:
            self.notify_status("info", f"Processing product {product_id}")
            result = self.processor.process_product(product_id, file_path)
            
            if result:
                self.notify_status("info", f"Processed product {product_id}")
                return result.to_dict()
            else:
                self.notify_status("error", f"Failed to process product {product_id}")
                return None
                
        except Exception as e:
            self.notify_status("error", f"Error processing product {product_id}: {str(e)}")
            return None
    
    # Methods for workflow operations
    def start_workflow(self):
        """Start the workflow manager"""
        if not self.workflow_manager:
            self.notify_status("error", "Workflow manager not initialized")
            return False
        
        try:
            self.workflow_manager.start()
            self.notify_status("info", "Workflow manager started")
            return True
        except Exception as e:
            self.notify_status("error", f"Error starting workflow manager: {str(e)}")
            return False
    
    def stop_workflow(self):
        """Stop the workflow manager"""
        if not self.workflow_manager:
            self.notify_status("error", "Workflow manager not initialized")
            return False
        
        try:
            self.workflow_manager.stop()
            self.workflow_manager.join(timeout=5)
            self.notify_status("info", "Workflow manager stopped")
            return True
        except Exception as e:
            self.notify_status("error", f"Error stopping workflow manager: {str(e)}")
            return False
    
    def get_workflow_status(self):
        """Get current workflow status"""
        if not self.workflow_manager:
            return {
                "error": "Workflow manager not initialized"
            }
        
        try:
            return self.workflow_manager.get_status()
        except Exception as e:
            self.notify_status("error", f"Error getting workflow status: {str(e)}")
            return {"error": str(e)}
    
    def process_directory(self, directory: Union[str, Path], pattern: str, batch_size: int, 
                        priority: str, recursive: bool):
        """
        Process all files in a directory
        
        Args:
            directory: Directory path
            pattern: File pattern to match
            batch_size: Number of products per batch
            priority: Job priority
            recursive: Whether to search recursively
            
        Returns:
            list: Batch reports
        """
        if not self.workflow_manager:
            self.notify_status("error", "Workflow manager not initialized")
            return []
        
        try:
            # Make sure workflow manager is started
            if not self.workflow_manager.running:
                self.workflow_manager.start()
            
            # Get priority enum
            from workflow.Arbetsflödeshantering import JobPriority
            job_priority = JobPriority[priority]
            
            # Process directory
            self.notify_status("info", f"Processing directory {directory}")
            reports = self.workflow_manager.process_directory(
                directory, pattern, batch_size, job_priority, recursive
            )
            
            self.notify_status("info", f"Directory processing initiated with {len(reports)} batches")
            return reports
        except Exception as e:
            self.notify_status("error", f"Error processing directory: {str(e)}")
            return []
    
    # Methods for LLM operations
    def verify_llm_connection(self):
        """Verify connection to LLM service"""
        if not self.llm_client:
            self.notify_status("error", "LLM client not initialized")
            return False
        
        try:
            result = self.llm_client.verify_connection()
            if result:
                self.notify_status("info", "LLM connection verified")
            else:
                self.notify_status("warning", "Could not connect to LLM service")
            return result
        except Exception as e:
            self.notify_status("error", f"Error verifying LLM connection: {str(e)}")
            return False
    
    def test_llm_prompt(self, prompt: str):
        """
        Test a prompt with the LLM service
        
        Args:
            prompt: Prompt text
            
        Returns:
            str: LLM response
        """
        if not self.llm_client:
            self.notify_status("error", "LLM client not initialized")
            return None
        
        try:
            self.notify_status("info", "Sending test prompt to LLM")
            response = self.llm_client.get_completion(prompt)
            
            if response.successful:
                self.notify_status("info", f"Received LLM response ({response.total_tokens} tokens)")
                return response.text
            else:
                self.notify_status("error", f"LLM error: {response.error}")
                return None
        except Exception as e:
            self.notify_status("error", f"Error testing LLM prompt: {str(e)}")
            return None
    
    # Methods for prompt management
    def get_available_prompts(self, prompt_type=None):
        """
        Get list of available prompts
        
        Args:
            prompt_type: Optional type to filter by
            
        Returns:
            list: Available prompts
        """
        if not self.prompt_manager:
            self.notify_status("error", "Prompt manager not initialized")
            return []
        
        try:
            if prompt_type:
                return self.prompt_manager.get_prompts_by_type(prompt_type)
            else:
                return self.prompt_manager.get_all_prompts()
        except Exception as e:
            self.notify_status("error", f"Error getting prompts: {str(e)}")
            return []
    
    def get_prompt(self, prompt_name):
        """
        Get a specific prompt by name
        
        Args:
            prompt_name: Name of the prompt
            
        Returns:
            dict: Prompt data
        """
        if not self.prompt_manager:
            self.notify_status("error", "Prompt manager not initialized")
            return None
        
        try:
            return self.prompt_manager.get_prompt(prompt_name)
        except Exception as e:
            self.notify_status("error", f"Error getting prompt {prompt_name}: {str(e)}")
            return None
    
    def save_prompt(self, prompt_data):
        """
        Save a prompt
        
        Args:
            prompt_data: Prompt data
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.prompt_manager:
            self.notify_status("error", "Prompt manager not initialized")
            return False
        
        try:
            result = self.prompt_manager.add_or_update_prompt(prompt_data)
            self.notify_status("info", f"Saved prompt: {prompt_data.get('name')}")
            return result
        except Exception as e:
            self.notify_status("error", f"Error saving prompt: {str(e)}")
            return False
    
    # Methods for configuration
    def get_config(self, section=None, default=None):
        """
        Get configuration
        
        Args:
            section: Optional configuration section path
            default: Default value if section doesn't exist
            
        Returns:
            dict: Configuration data
        """
        if not self.config_manager:
            self.notify_status("error", "Config manager not initialized")
            return default
        
        try:
            if section:
                return self.config_manager.get(section, default)
            else:
                # Return complete config
                return self.config_manager.get_all()
        except Exception as e:
            self.notify_status("error", f"Error getting configuration: {str(e)}")
            return default
    
    def set_config(self, section, value):
        """
        Set configuration value
        
        Args:
            section: Configuration section path
            value: Value to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.config_manager:
            self.notify_status("error", "Config manager not initialized")
            return False
        
        try:
            self.config_manager.set(section, value)
            self.notify_status("info", f"Updated configuration: {section}")
            return True
        except Exception as e:
            self.notify_status("error", f"Error setting configuration: {str(e)}")
            return False
    
    def save_config(self, file_path=None):
        """
        Save configuration to file
        
        Args:
            file_path: Optional file path to save to
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.config_manager:
            self.notify_status("error", "Config manager not initialized")
            return False
        
        try:
            if file_path:
                result = self.config_manager.save_config(file_path)
            else:
                # Use default config path
                result = self.config_manager.save_config(self.config_manager.config_file or "config.yaml")
            
            if result:
                self.notify_status("info", "Configuration saved")
            else:
                self.notify_status("error", "Failed to save configuration")
            
            return result
        except Exception as e:
            self.notify_status("error", f"Error saving configuration: {str(e)}")
            return False