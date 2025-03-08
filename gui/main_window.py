#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QSplitter, QWidget, QVBoxLayout, 
    QHBoxLayout, QStatusBar, QToolBar, QMenu, QDockWidget
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QKeySequence, QAction

# Import tab views
from gui.tabs.workflow_tab import WorkflowTab
from gui.tabs.extraction_tab import ExtractionTab
from gui.tabs.llm_config_tab import LLMConfigTab
from gui.tabs.prompt_editor_tab import PromptEditorTab
from gui.tabs.results_viewer_tab import ResultsViewerTab

# Import panels
from gui.panels.console_panel import ConsolePanel
from gui.panels.file_explorer_panel import FileExplorerPanel
from gui.panels.properties_panel import PropertiesPanel

class MainWindow(QMainWindow):
    """
    Main application window with docked panels and tab view
    """
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.setWindowTitle("LLM Product Information Extractor")
        self.setMinimumSize(1200, 800)
        
        # Create central widget with main splitter
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main vertical layout for central widget
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(2)
        
        # Create main splitter (horizontal split between panels and content)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.main_splitter)
        
        # Create vertical splitter for main content area
        self.content_splitter = QSplitter(Qt.Vertical)
        
        # Add tab widget to content splitter
        self.tab_widget = QTabWidget()
        self.setup_tabs()
        self.content_splitter.addWidget(self.tab_widget)
        
        # Create console panel and add to content splitter
        self.console = ConsolePanel()
        self.content_splitter.addWidget(self.console)
        
        # Set console splitter proportions (70% tabs, 30% console)
        self.content_splitter.setSizes([700, 300])
        
        # Add content splitter to main splitter
        self.main_splitter.addWidget(self.content_splitter)
        
        # Setup left panel dock widgets
        self.setup_dock_widgets()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Create toolbar and menus
        self.setup_toolbar()
        self.setup_menus()
        
        # Set main splitter proportions (20% file explorer, 80% content)
        self.main_splitter.setSizes([200, 800])
        
        # Connect signals and slots
        self.connect_signals()
        
    def setup_tabs(self):
        """Setup the main tab widget with all tab views"""
        # Workflow Management Tab
        self.workflow_tab = WorkflowTab()
        self.tab_widget.addTab(self.workflow_tab, "Workflow")
        
        # Extraction Configuration Tab
        self.extraction_tab = ExtractionTab()
        self.tab_widget.addTab(self.extraction_tab, "Extraction")
        
        # LLM Configuration Tab
        self.llm_config_tab = LLMConfigTab()
        self.tab_widget.addTab(self.llm_config_tab, "LLM Config")
        
        # Prompt Editor Tab
        self.prompt_editor_tab = PromptEditorTab()
        self.tab_widget.addTab(self.prompt_editor_tab, "Prompt Editor")
        
        # Results Viewer Tab
        self.results_viewer_tab = ResultsViewerTab()
        self.tab_widget.addTab(self.results_viewer_tab, "Results")
        
    def setup_dock_widgets(self):
        """Setup dock widgets for file browser and properties"""
        # File Explorer dock
        self.file_explorer_dock = QDockWidget("Files", self)
        self.file_explorer_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.file_explorer = FileExplorerPanel()
        self.file_explorer_dock.setWidget(self.file_explorer)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.file_explorer_dock)
        
        # Properties dock
        self.properties_dock = QDockWidget("Properties", self)
        self.properties_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.properties_panel = PropertiesPanel()
        self.properties_dock.setWidget(self.properties_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties_dock)
        
        # By default hide the properties panel
        self.properties_dock.setVisible(False)
        
    def setup_toolbar(self):
        """Setup main toolbar with actions"""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        
        # Run action
        self.action_run = QAction("Run", self)
        self.action_run.setShortcut(QKeySequence("F5"))
        self.action_run.triggered.connect(self.on_run_clicked)
        self.toolbar.addAction(self.action_run)
        
        # Process directory action
        self.action_process_dir = QAction("Process Directory", self)
        self.action_process_dir.triggered.connect(self.on_process_directory)
        self.toolbar.addAction(self.action_process_dir)
        
        # Process single file action
        self.action_process_file = QAction("Process File", self)
        self.action_process_file.triggered.connect(self.on_process_file)
        self.toolbar.addAction(self.action_process_file)
        
        # Separator
        self.toolbar.addSeparator()
        
        # Settings action
        self.action_settings = QAction("Settings", self)
        self.action_settings.triggered.connect(self.on_settings_clicked)
        self.toolbar.addAction(self.action_settings)
        
        # Help action
        self.action_help = QAction("Help", self)
        self.action_help.triggered.connect(self.on_help_clicked)
        self.toolbar.addAction(self.action_help)
        
    def setup_menus(self):
        """Setup application menus"""
        # Main menu bar
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        # Open configuration
        action_open_config = QAction("Open Configuration", self)
        action_open_config.setShortcut(QKeySequence.Open)
        action_open_config.triggered.connect(self.on_open_config)
        file_menu.addAction(action_open_config)
        
        # Save configuration
        action_save_config = QAction("Save Configuration", self)
        action_save_config.setShortcut(QKeySequence.Save)
        action_save_config.triggered.connect(self.on_save_config)
        file_menu.addAction(action_save_config)
        
        file_menu.addSeparator()
        
        # Exit action
        action_exit = QAction("Exit", self)
        action_exit.setShortcut(QKeySequence.Quit)
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)
        
        # View menu
        view_menu = menu_bar.addMenu("View")
        
        # Toggle file explorer
        self.action_toggle_file_explorer = QAction("File Explorer", self)
        self.action_toggle_file_explorer.setCheckable(True)
        self.action_toggle_file_explorer.setChecked(True)
        self.action_toggle_file_explorer.triggered.connect(self.toggle_file_explorer)
        view_menu.addAction(self.action_toggle_file_explorer)
        
        # Toggle properties panel
        self.action_toggle_properties = QAction("Properties Panel", self)
        self.action_toggle_properties.setCheckable(True)
        self.action_toggle_properties.setChecked(False)
        self.action_toggle_properties.triggered.connect(self.toggle_properties_panel)
        view_menu.addAction(self.action_toggle_properties)
        
        # Toggle console
        self.action_toggle_console = QAction("Console", self)
        self.action_toggle_console.setCheckable(True)
        self.action_toggle_console.setChecked(True)
        self.action_toggle_console.triggered.connect(self.toggle_console)
        view_menu.addAction(self.action_toggle_console)
        
        # Tools menu
        tools_menu = menu_bar.addMenu("Tools")
        
        # Test LLM connection
        action_test_connection = QAction("Test LLM Connection", self)
        action_test_connection.triggered.connect(self.on_test_connection)
        tools_menu.addAction(action_test_connection)
        
        # Generate report
        action_generate_report = QAction("Generate Report", self)
        action_generate_report.triggered.connect(self.on_generate_report)
        tools_menu.addAction(action_generate_report)
        
        # Export results
        action_export_results = QAction("Export Results", self)
        action_export_results.triggered.connect(self.on_export_results)
        tools_menu.addAction(action_export_results)
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        
        # About action
        action_about = QAction("About", self)
        action_about.triggered.connect(self.on_about)
        help_menu.addAction(action_about)
        
        # Documentation action
        action_docs = QAction("Documentation", self)
        action_docs.triggered.connect(self.on_documentation)
        help_menu.addAction(action_docs)
    
    def connect_signals(self):
        """Connect signals and slots between components"""
        # Connect file explorer signals to the appropriate handlers
        self.file_explorer.file_selected.connect(self.on_file_selected)
        
        # Connect console signals
        self.console.command_executed.connect(self.on_console_command)
        
        # Connect tab signals
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    # Slot handlers
    def on_run_clicked(self):
        """Handler for run button click"""
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, "run"):
            current_tab.run()
            self.status_bar.showMessage("Running process...")
        else:
            self.console.log_error("Current tab does not support run operation")
    
    def on_process_directory(self):
        """Handler for process directory action"""
        self.workflow_tab.process_directory()
        self.status_bar.showMessage("Processing directory...")
    
    def on_process_file(self):
        """Handler for process file action"""
        self.workflow_tab.process_file()
        self.status_bar.showMessage("Processing file...")
    
    def on_settings_clicked(self):
        """Handler for settings button click"""
        self.tab_widget.setCurrentWidget(self.llm_config_tab)
        self.status_bar.showMessage("Editing settings...")
    
    def on_help_clicked(self):
        """Handler for help button click"""
        self.console.log_info("Help documentation will be displayed here.")
        self.status_bar.showMessage("Showing help...")
    
    def on_open_config(self):
        """Handler for opening configuration"""
        self.llm_config_tab.load_config()
        self.status_bar.showMessage("Configuration loaded")
    
    def on_save_config(self):
        """Handler for saving configuration"""
        self.llm_config_tab.save_config()
        self.status_bar.showMessage("Configuration saved")
    
    def toggle_file_explorer(self, checked):
        """Toggle file explorer visibility"""
        self.file_explorer_dock.setVisible(checked)
    
    def toggle_properties_panel(self, checked):
        """Toggle properties panel visibility"""
        self.properties_dock.setVisible(checked)
    
    def toggle_console(self, checked):
        """Toggle console visibility"""
        if checked:
            # Show console
            self.console.setVisible(True)
            # Restore previous sizes
            self.content_splitter.setSizes([700, 300])
        else:
            # Hide console
            self.console.setVisible(False)
            # Give all space to the tab widget
            self.content_splitter.setSizes([1000, 0])
    
    def on_test_connection(self):
        """Handler for testing LLM connection"""
        self.llm_config_tab.test_connection()
        self.status_bar.showMessage("Testing LLM connection...")
    
    def on_generate_report(self):
        """Handler for generating report"""
        self.results_viewer_tab.generate_report()
        self.status_bar.showMessage("Generating report...")
    
    def on_export_results(self):
        """Handler for exporting results"""
        self.results_viewer_tab.export_results()
        self.status_bar.showMessage("Exporting results...")
    
    def on_about(self):
        """Handler for about action"""
        self.console.log_info("LLM Product Information Extractor - A tool for extracting structured data from product documentation.")
    
    def on_documentation(self):
        """Handler for documentation action"""
        self.console.log_info("Documentation will be opened in the default web browser.")
    
    def on_file_selected(self, file_path):
        """Handler for file selection in file explorer"""
        self.status_bar.showMessage(f"Selected file: {file_path}")
        
        # Update properties panel with file info
        self.properties_panel.update_properties(file_path)
        
        # If not visible, show properties panel
        if not self.properties_dock.isVisible():
            self.properties_dock.setVisible(True)
            self.action_toggle_properties.setChecked(True)
    
    def on_console_command(self, command):
        """Handler for console command execution"""
        self.status_bar.showMessage(f"Executed: {command}")
    
    def on_tab_changed(self, index):
        """Handler for tab change"""
        tab_name = self.tab_widget.tabText(index)
        self.status_bar.showMessage(f"Switched to {tab_name} tab")