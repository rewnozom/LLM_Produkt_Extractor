#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# gui/components/json_viewer.py

import json
from typing import Dict, List, Any, Optional, Union

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, 
    QLabel, QPushButton, QFrame, QTextEdit, QSplitter, QToolBar,
    QComboBox, QLineEdit, QToolButton, QMenu, QAction
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QFont, QColor

class JsonViewer(QWidget):
    """
    Advanced JSON viewer component that provides:
    - Tree view for hierarchical visualization
    - Raw JSON text view with syntax highlighting
    - Search functionality
    - Collapsible sections
    - Copy/export functionality
    """
    
    # Signal emitted when a JSON item is selected
    item_selected = Signal(str, object)  # path, value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Data storage
        self.json_data = None
        self.current_path = ""
        self.expanded_paths = set()
        self.filter_text = ""
        
        # Configure widget
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar for controls
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))
        
        # Add expand/collapse actions
        expand_all = QAction("Expand All", self)
        expand_all.triggered.connect(self.expand_all_items)
        toolbar.addAction(expand_all)
        
        collapse_all = QAction("Collapse All", self)
        collapse_all.triggered.connect(self.collapse_all_items)
        toolbar.addAction(collapse_all)
        
        toolbar.addSeparator()
        
        # Search input
        search_label = QLabel("Search:")
        toolbar.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setMaximumWidth(200)
        self.search_input.setPlaceholderText("Search JSON...")
        self.search_input.textChanged.connect(self.filter_tree)
        toolbar.addWidget(self.search_input)
        
        toolbar.addSeparator()
        
        # View selection
        view_label = QLabel("View:")
        toolbar.addWidget(view_label)
        
        self.view_selector = QComboBox()
        self.view_selector.addItems(["Tree", "Text", "Split"])
        self.view_selector.currentIndexChanged.connect(self.change_view)
        toolbar.addWidget(self.view_selector)
        
        # Format dropdown
        format_button = QToolButton()
        format_button.setText("Format")
        format_button.setPopupMode(QToolButton.InstantPopup)
        
        format_menu = QMenu(format_button)
        
        compact_action = QAction("Compact", format_menu)
        compact_action.triggered.connect(lambda: self.format_json(compact=True))
        format_menu.addAction(compact_action)
        
        pretty_action = QAction("Pretty", format_menu)
        pretty_action.triggered.connect(lambda: self.format_json(compact=False))
        format_menu.addAction(pretty_action)
        
        format_button.setMenu(format_menu)
        toolbar.addWidget(format_button)
        
        # Copy button
        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self.copy_json)
        toolbar.addWidget(copy_button)
        
        layout.addWidget(toolbar)
        
        # Main content with splitter
        self.splitter = QSplitter(Qt.Vertical)
        
        # Tree view widget
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Key", "Value", "Type"])
        self.tree_widget.setColumnWidth(0, 200)
        self.tree_widget.setColumnWidth(1, 300)
        self.tree_widget.setColumnWidth(2, 100)
        self.tree_widget.setAlternatingRowColors(True)
        self.tree_widget.itemSelectionChanged.connect(self.on_item_selected)
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        # JSON text view with syntax highlighting
        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        monospace_font = QFont("Consolas", 10) if "Consolas" in QFont.families() else QFont("Monospace", 10)
        self.text_view.setFont(monospace_font)
        
        # Add to splitter
        self.splitter.addWidget(self.tree_widget)
        self.splitter.addWidget(self.text_view)
        
        # Set initial splitter sizes and state
        self.splitter.setSizes([200, 100])
        self.text_view.setVisible(False)  # Start with tree view only
        
        layout.addWidget(self.splitter)
        
        # Add status bar
        self.status_bar = QLabel("")
        layout.addWidget(self.status_bar)
    
    def set_json(self, json_data: Union[str, Dict, List]):
        """
        Set the JSON data to display
        
        Args:
            json_data: JSON data as string or Python object
        """
        try:
            # Convert string to object if needed
            if isinstance(json_data, str):
                self.json_data = json.loads(json_data)
            else:
                self.json_data = json_data
            
            # Clear current display
            self.tree_widget.clear()
            self.text_view.clear()
            
            # Update both views
            self.update_tree_view()
            self.update_text_view()
            
            # Update status
            if isinstance(self.json_data, dict):
                self.status_bar.setText(f"{len(self.json_data)} keys")
            elif isinstance(self.json_data, list):
                self.status_bar.setText(f"{len(self.json_data)} items")
            else:
                self.status_bar.setText("JSON loaded")
                
        except Exception as e:
            self.status_bar.setText(f"Error loading JSON: {str(e)}")
            self.text_view.setText(f"Error parsing JSON:\n{str(e)}")
    
    def update_tree_view(self):
        """Update the tree view with the current JSON data"""
        self.tree_widget.clear()
        
        # Skip if no data
        if self.json_data is None:
            return
        
        # Build tree from root
        root_items = []
        if isinstance(self.json_data, dict):
            for key, value in self.json_data.items():
                item = self.create_item(key, value)
                root_items.append(item)
        elif isinstance(self.json_data, list):
            for i, value in enumerate(self.json_data):
                item = self.create_item(str(i), value)
                root_items.append(item)
        else:
            # Simple value
            item = QTreeWidgetItem(["root", str(self.json_data), type(self.json_data).__name__])
            root_items.append(item)
        
        # Add all root items
        self.tree_widget.addTopLevelItems(root_items)
        
        # Expand previously expanded paths
        for path in self.expanded_paths:
            self.expand_path(path)
    
    def create_item(self, key, value, path="") -> QTreeWidgetItem:
        """
        Create a tree item for the given key-value pair
        
        Args:
            key: The JSON key
            value: The JSON value
            path: Current JSON path
            
        Returns:
            QTreeWidgetItem: The created tree item
        """
        # Build path
        current_path = f"{path}/{key}" if path else key
        
        # Special case for null/None value
        if value is None:
            item = QTreeWidgetItem([key, "null", "null"])
            item.setForeground(1, QColor("#999999"))
            item.setData(0, Qt.UserRole, current_path)
            return item
        
        # Handle different value types
        if isinstance(value, dict):
            # Dictionary
            item = QTreeWidgetItem([key, f"{{{len(value)} keys}}", "object"])
            item.setForeground(2, QColor("#7c3aed"))  # Purple for objects
            
            # Add child items
            for k, v in value.items():
                child = self.create_item(k, v, current_path)
                item.addChild(child)
                
        elif isinstance(value, list):
            # List
            item = QTreeWidgetItem([key, f"[{len(value)} items]", "array"])
            item.setForeground(2, QColor("#2563eb"))  # Blue for arrays
            
            # Add child items
            for i, v in enumerate(value):
                child = self.create_item(str(i), v, current_path)
                item.addChild(child)
                
        elif isinstance(value, bool):
            # Boolean
            item = QTreeWidgetItem([key, str(value).lower(), "boolean"])
            item.setForeground(1, QColor("#059669") if value else QColor("#dc2626"))
            
        elif isinstance(value, (int, float)):
            # Number
            item = QTreeWidgetItem([key, str(value), type(value).__name__])
            item.setForeground(1, QColor("#0284c7"))  # Blue for numbers
            
        elif isinstance(value, str):
            # String
            # Truncate very long strings
            display_value = value
            if len(display_value) > 100:
                display_value = f"{display_value[:100]}..."
                
            item = QTreeWidgetItem([key, f'"{display_value}"', "string"])
            item.setForeground(1, QColor("#65a30d"))  # Green for strings
            
        else:
            # Fallback for other types
            item = QTreeWidgetItem([key, str(value), type(value).__name__])
        
        # Store path for later reference
        item.setData(0, Qt.UserRole, current_path)
        
        return item
    
    def update_text_view(self):
        """Update the text view with formatted JSON"""
        if self.json_data is None:
            self.text_view.clear()
            return
        
        # Format as pretty JSON
        formatted = json.dumps(self.json_data, indent=2, sort_keys=False, ensure_ascii=False)
        
        # Apply syntax highlighting (basic approach)
        html = self._highlight_json(formatted)
        self.text_view.setHtml(html)
    
    def _highlight_json(self, json_str: str) -> str:
        """
        Apply syntax highlighting to JSON string
        
        Args:
            json_str: The JSON string to highlight
            
        Returns:
            str: HTML formatted string with syntax highlighting
        """
        # Convert to HTML with basic syntax highlighting
        html = ['<pre style="margin: 0; font-family: Consolas, monospace;">']
        
        # Simple token-based approach
        in_string = False
        in_key = False
        i = 0
        
        while i < len(json_str):
            char = json_str[i]
            
            # Handle string literals
            if char == '"':
                if not in_string:
                    # Starting a string
                    in_string = True
                    # Check if this is a key (followed by colon)
                    j = i + 1
                    while j < len(json_str) and json_str[j] != '"':
                        j += 1
                    if j < len(json_str):
                        j += 1  # Skip the closing quote
                        # Look for colon after the string
                        while j < len(json_str) and json_str[j].isspace():
                            j += 1
                        in_key = j < len(json_str) and json_str[j] == ':'
                    
                    if in_key:
                        html.append('<span style="color: #a16207;">')  # Brown for keys
                    else:
                        html.append('<span style="color: #65a30d;">')  # Green for strings
                    html.append(char)
                else:
                    # Ending a string
                    html.append(char)
                    html.append('</span>')
                    in_string = False
                    in_key = False
                i += 1
                continue
            
            # Skip escaped characters in strings
            if in_string and char == '\\' and i + 1 < len(json_str):
                html.append(char + json_str[i + 1])
                i += 2
                continue
                
            # Handle numbers
            if not in_string and (char.isdigit() or char == '-'):
                # Find the end of the number
                j = i + 1
                while j < len(json_str) and (json_str[j].isdigit() or json_str[j] in '.eE+-'):
                    j += 1
                num_str = json_str[i:j]
                html.append(f'<span style="color: #0284c7;">{num_str}</span>')  # Blue for numbers
                i = j
                continue
                
            # Handle special values (true, false, null)
            if not in_string:
                if json_str[i:i+4] == 'true':
                    html.append('<span style="color: #059669;">true</span>')  # Green for true
                    i += 4
                    continue
                elif json_str[i:i+5] == 'false':
                    html.append('<span style="color: #dc2626;">false</span>')  # Red for false
                    i += 5
                    continue
                elif json_str[i:i+4] == 'null':
                    html.append('<span style="color: #999999;">null</span>')  # Gray for null
                    i += 4
                    continue
            
            # Structural characters (braces, brackets, etc.)
            if not in_string and char in '{}[],:':
                html.append(f'<span style="color: #7c3aed;">{char}</span>')  # Purple for structure
            else:
                html.append(char)
            
            i += 1
            
        html.append('</pre>')
        return ''.join(html)
    
    def on_item_selected(self):
        """Handle selection of a tree item"""
        items = self.tree_widget.selectedItems()
        if not items:
            return
        
        # Get selected item
        item = items[0]
        
        # Get path to this item
        path = item.data(0, Qt.UserRole)
        if not path:
            return
        
        # Get value from path
        value = self.get_value_from_path(path)
        
        # Update current path
        self.current_path = path
        
        # Emit signal
        self.item_selected.emit(path, value)
    
    def get_value_from_path(self, path: str) -> Any:
        """
        Get the JSON value at the specified path
        
        Args:
            path: Path to the value (e.g., "person/address/city")
            
        Returns:
            Any: The value at the path or None if not found
        """
        if not path or not self.json_data:
            return None
        
        parts = path.split('/')
        current = self.json_data
        
        for part in parts:
            if not part:
                continue
                
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            else:
                return None
                
        return current
    
    def expand_path(self, path: str) -> bool:
        """
        Expand all items along the specified path
        
        Args:
            path: Path to expand (e.g., "person/address")
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not path:
            return False
            
        # Split path into components
        parts = path.split('/')
        
        # Start from root items
        items = [self.tree_widget.topLevelItem(i) for i in range(self.tree_widget.topLevelItemCount())]
        
        # Follow path components
        for i, part in enumerate(parts):
            # Skip empty parts
            if not part:
                continue
                
            # Search for matching item at this level
            found = False
            for item in items:
                if item.text(0) == part:
                    # Expand this item
                    item.setExpanded(True)
                    
                    # If more parts to process, get children for next iteration
                    if i < len(parts) - 1:
                        items = [item.child(j) for j in range(item.childCount())]
                    
                    found = True
                    break
            
            if not found:
                return False
                
        return True
    
    def expand_all_items(self):
        """Expand all items in the tree"""
        self.tree_widget.expandAll()
        
        # Record all expanded paths
        self.expanded_paths = set()
        self._collect_all_paths(None, "")
    
    def _collect_all_paths(self, item, path):
        """
        Recursively collect all paths in the tree
        
        Args:
            item: Current tree item (None for root)
            path: Current path
        """
        if item is None:
            # Start with top-level items
            for i in range(self.tree_widget.topLevelItemCount()):
                top_item = self.tree_widget.topLevelItem(i)
                self._collect_all_paths(top_item, top_item.text(0))
        else:
            # Add this path
            self.expanded_paths.add(path)
            
            # Process children
            for i in range(item.childCount()):
                child = item.child(i)
                child_path = f"{path}/{child.text(0)}"
                self._collect_all_paths(child, child_path)
    
    def collapse_all_items(self):
        """Collapse all items in the tree"""
        self.tree_widget.collapseAll()
        self.expanded_paths = set()
    
    def filter_tree(self):
        """Filter tree items based on search text"""
        self.filter_text = self.search_input.text().lower()
        
        # If empty, just restore normal view
        if not self.filter_text:
            self.update_tree_view()
            return
        
        # Helper function to check if item or its children match filter
        def matches_filter(item):
            # Check this item
            if (self.filter_text in item.text(0).lower() or 
                self.filter_text in item.text(1).lower()):
                return True
                
            # Check children
            for i in range(item.childCount()):
                if matches_filter(item.child(i)):
                    return True
                    
            return False
        
        # Hide non-matching items
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            item.setHidden(not matches_filter(item))
            
            # Expand items to show matches
            if matches_filter(item):
                self._expand_matching_items(item)
    
    def _expand_matching_items(self, item):
        """
        Recursively expand items that match the filter
        
        Args:
            item: The tree item to check
        """
        # Check if this item matches
        item_matches = (self.filter_text in item.text(0).lower() or 
                        self.filter_text in item.text(1).lower())
        
        # Check children
        has_matching_child = False
        for i in range(item.childCount()):
            child = item.child(i)
            child_matches = self._expand_matching_items(child)
            has_matching_child = has_matching_child or child_matches
        
        # Expand if this item matches or has matching children
        if item_matches or has_matching_child:
            item.setExpanded(True)
            
        # Don't hide matching items
        item.setHidden(False)
        
        return item_matches or has_matching_child
    
    def change_view(self, index):
        """
        Change the view mode
        
        Args:
            index: View mode index (0=Tree, 1=Text, 2=Split)
        """
        if index == 0:  # Tree
            self.tree_widget.setVisible(True)
            self.text_view.setVisible(False)
            self.splitter.setSizes([1, 0])
        elif index == 1:  # Text
            self.tree_widget.setVisible(False)
            self.text_view.setVisible(True)
            self.splitter.setSizes([0, 1])
        elif index == 2:  # Split
            self.tree_widget.setVisible(True)
            self.text_view.setVisible(True)
            self.splitter.setSizes([1, 1])
    
    def format_json(self, compact=False):
        """
        Format the JSON in the text view
        
        Args:
            compact: Whether to use compact formatting
        """
        if self.json_data is None:
            return
            
        # Format JSON
        indent = None if compact else 2
        formatted = json.dumps(self.json_data, indent=indent, sort_keys=False, ensure_ascii=False)
        
        # Apply highlighting and update
        html = self._highlight_json(formatted)
        self.text_view.setHtml(html)
    
    def copy_json(self):
        """Copy current JSON to clipboard"""
        if self.json_data is None:
            return
            
        # Format and copy to clipboard
        formatted = json.dumps(self.json_data, indent=2, sort_keys=False, ensure_ascii=False)
        from PySide6.QtGui import QClipboard
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(formatted)
        
        # Show message in status bar
        self.status_bar.setText("JSON copied to clipboard")
    
    def show_context_menu(self, position):
        """
        Show context menu for tree items
        
        Args:
            position: Position where menu should appear
        """
        item = self.tree_widget.itemAt(position)
        if not item:
            return
            
        # Create menu
        menu = QMenu(self)
        
        # Get value from the item
        path = item.data(0, Qt.UserRole)
        value = self.get_value_from_path(path)
        
        # Add copy action
        copy_value_action = QAction("Copy Value", self)
        copy_value_action.triggered.connect(lambda: self._copy_value(value))
        menu.addAction(copy_value_action)
        
        copy_path_action = QAction("Copy Path", self)
        copy_path_action.triggered.connect(lambda: self._copy_value(path))
        menu.addAction(copy_path_action)
        
        # Add expand/collapse actions for objects/arrays
        if item.childCount() > 0:
            menu.addSeparator()
            
            expand_action = QAction("Expand", self)
            expand_action.triggered.connect(lambda: item.setExpanded(True))
            menu.addAction(expand_action)
            
            collapse_action = QAction("Collapse", self)
            collapse_action.triggered.connect(lambda: item.setExpanded(False))
            menu.addAction(collapse_action)
        
        # Show menu
        menu.exec(self.tree_widget.viewport().mapToGlobal(position))
    
    def _copy_value(self, value):
        """
        Copy a value to clipboard
        
        Args:
            value: Value to copy
        """
        # Format and copy to clipboard
        if isinstance(value, (dict, list)):
            # JSON objects and arrays
            text = json.dumps(value, indent=2, ensure_ascii=False)
        else:
            # Simple values
            text = str(value)
            
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        
        # Show message in status bar
        self.status_bar.setText("Value copied to clipboard")