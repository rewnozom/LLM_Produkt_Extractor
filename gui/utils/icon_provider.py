#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# gui/utils/icon_provider.py

import os
import sys
from enum import Enum, auto
from pathlib import Path
from typing import Dict, Optional, Union

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter
from PySide6.QtSvg import QSvgRenderer


class IconType(Enum):
    """Enum for icon types"""
    # Application icons
    APP = auto()
    LOGO = auto()
    
    # File/document icons
    FILE = auto()
    FOLDER = auto()
    DOCUMENT = auto()
    PDF = auto()
    MARKDOWN = auto()
    JSON = auto()
    CSV = auto()
    
    # Action icons
    ADD = auto()
    REMOVE = auto()
    EDIT = auto()
    DELETE = auto()
    SAVE = auto()
    OPEN = auto()
    CLOSE = auto()
    REFRESH = auto()
    SEARCH = auto()
    SETTINGS = auto()
    
    # Navigation icons
    BACK = auto()
    FORWARD = auto()
    UP = auto()
    DOWN = auto()
    HOME = auto()
    
    # Status icons
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    SUCCESS = auto()
    ALERT = auto()
    
    # Control icons
    START = auto()
    STOP = auto()
    PAUSE = auto()
    RESUME = auto()
    CANCEL = auto()
    
    # UI element icons
    EXPAND = auto()
    COLLAPSE = auto()
    DROPDOWN = auto()
    CHECKBOX = auto()
    CHECKBOX_CHECKED = auto()
    RADIO = auto()
    RADIO_CHECKED = auto()
    
    # Misc icons
    USER = auto()
    CALENDAR = auto()
    CLOCK = auto()
    TAG = auto()
    LINK = auto()
    EXTERNAL_LINK = auto()
    CLIPBOARD = auto()
    DOWNLOAD = auto()
    UPLOAD = auto()
    CONSOLE = auto()
    PROMPT = auto()
    EXTRACTION = auto()
    WORKFLOW = auto()
    LLM = auto()
    PRODUCT = auto()
    VALIDATION = auto()
    
    # Tab icons
    TAB_WORKFLOW = auto()
    TAB_EXTRACTION = auto()
    TAB_RESULTS = auto()
    TAB_PROMPT = auto()
    TAB_LLM = auto()


class IconProvider:
    """
    Provider class for application icons.
    
    This class:
    1. Manages loading and caching of icons
    2. Supports both raster and SVG icons
    3. Provides theme-aware icons (light/dark)
    4. Generates dynamic icons based on templates
    
    Usage:
        icon_provider = IconProvider()
        add_button.setIcon(icon_provider.get_icon(IconType.ADD))
    """
    
    def __init__(self, icon_dir: Optional[str] = None):
        """
        Initialize the icon provider.
        
        Args:
            icon_dir: Directory containing icon files (default: ./assets/icons)
        """
        # Set icon directory
        if icon_dir:
            self.icon_dir = Path(icon_dir)
        else:
            # Try to find icons directory
            app_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            self.icon_dir = app_dir / "assets" / "icons"
            
            # If not found, use a fallback
            if not self.icon_dir.exists():
                self.icon_dir = app_dir / "gui" / "assets" / "icons"
                
                # Create directory if it doesn't exist
                if not self.icon_dir.exists():
                    self.icon_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for loaded icons
        self._icon_cache: Dict[IconType, QIcon] = {}
        
        # Initialize icon mapping
        self._init_icon_mapping()
        
        # Current theme (light or dark)
        self._is_dark_theme = False
    
    def _init_icon_mapping(self) -> None:
        """Initialize the mapping between IconType and filenames"""
        self._icon_files = {
            # App icons
            IconType.APP: "app.svg",
            IconType.LOGO: "logo.svg",
            
            # File/document icons
            IconType.FILE: "file.svg",
            IconType.FOLDER: "folder.svg",
            IconType.DOCUMENT: "document.svg",
            IconType.PDF: "pdf.svg",
            IconType.MARKDOWN: "markdown.svg",
            IconType.JSON: "json.svg",
            IconType.CSV: "csv.svg",
            
            # Action icons
            IconType.ADD: "add.svg",
            IconType.REMOVE: "remove.svg",
            IconType.EDIT: "edit.svg",
            IconType.DELETE: "delete.svg",
            IconType.SAVE: "save.svg",
            IconType.OPEN: "open.svg",
            IconType.CLOSE: "close.svg",
            IconType.REFRESH: "refresh.svg",
            IconType.SEARCH: "search.svg",
            IconType.SETTINGS: "settings.svg",
            
            # Navigation icons
            IconType.BACK: "back.svg",
            IconType.FORWARD: "forward.svg",
            IconType.UP: "up.svg",
            IconType.DOWN: "down.svg",
            IconType.HOME: "home.svg",
            
            # Status icons
            IconType.INFO: "info.svg",
            IconType.WARNING: "warning.svg",
            IconType.ERROR: "error.svg",
            IconType.SUCCESS: "success.svg",
            IconType.ALERT: "alert.svg",
            
            # Control icons
            IconType.START: "start.svg",
            IconType.STOP: "stop.svg",
            IconType.PAUSE: "pause.svg",
            IconType.RESUME: "resume.svg",
            IconType.CANCEL: "cancel.svg",
            
            # UI element icons
            IconType.EXPAND: "expand.svg",
            IconType.COLLAPSE: "collapse.svg",
            IconType.DROPDOWN: "dropdown.svg",
            IconType.CHECKBOX: "checkbox.svg",
            IconType.CHECKBOX_CHECKED: "checkbox-checked.svg",
            IconType.RADIO: "radio.svg",
            IconType.RADIO_CHECKED: "radio-checked.svg",
            
            # Misc icons
            IconType.USER: "user.svg",
            IconType.CALENDAR: "calendar.svg",
            IconType.CLOCK: "clock.svg",
            IconType.TAG: "tag.svg",
            IconType.LINK: "link.svg",
            IconType.EXTERNAL_LINK: "external-link.svg",
            IconType.CLIPBOARD: "clipboard.svg",
            IconType.DOWNLOAD: "download.svg",
            IconType.UPLOAD: "upload.svg",
            IconType.CONSOLE: "console.svg",
            IconType.PROMPT: "prompt.svg",
            IconType.EXTRACTION: "extraction.svg",
            IconType.WORKFLOW: "workflow.svg",
            IconType.LLM: "llm.svg",
            IconType.PRODUCT: "product.svg",
            IconType.VALIDATION: "validation.svg",
            
            # Tab icons
            IconType.TAB_WORKFLOW: "tab-workflow.svg",
            IconType.TAB_EXTRACTION: "tab-extraction.svg",
            IconType.TAB_RESULTS: "tab-results.svg",
            IconType.TAB_PROMPT: "tab-prompt.svg",
            IconType.TAB_LLM: "tab-llm.svg",
        }
    
    def set_theme(self, is_dark: bool) -> None:
        """
        Set the current theme.
        
        Args:
            is_dark: True for dark theme, False for light theme
        """
        if self._is_dark_theme != is_dark:
            self._is_dark_theme = is_dark
            # Clear the cache to reload icons with correct theme
            self._icon_cache.clear()
    
    def get_icon(self, icon_type: IconType, size: QSize = None) -> QIcon:
        """
        Get an icon by type.
        
        Args:
            icon_type: Type of icon to get
            size: Optional specific size for the icon
            
        Returns:
            QIcon for the requested type
        """
        # Check if icon is in cache
        if icon_type in self._icon_cache:
            icon = self._icon_cache[icon_type]
            
            # If specific size requested, ensure icon has that size
            if size and not icon.availableSizes():
                return self._resize_icon(icon, size)
            
            return icon
        
        # Get icon filename
        filename = self._icon_files.get(icon_type)
        if not filename:
            # Return fallback icon
            return self._create_fallback_icon(icon_type, size)
        
        # Try to load icon
        icon = self._load_icon(filename, icon_type, size)
        
        # Cache the icon
        self._icon_cache[icon_type] = icon
        
        return icon
    
    def get_colored_icon(self, icon_type: IconType, color: Union[QColor, str], 
                        size: QSize = None) -> QIcon:
        """
        Get an icon with a specific color.
        
        Args:
            icon_type: Type of icon to get
            color: Color to apply to the icon
            size: Optional specific size for the icon
            
        Returns:
            Colored QIcon for the requested type
        """
        # Get base icon
        icon = self.get_icon(icon_type, size)
        
        # Convert string color to QColor if needed
        if isinstance(color, str):
            color = QColor(color)
        
        # Create colored version
        return self._apply_color_to_icon(icon, color, size)
    
    def get_icon_pixmap(self, icon_type: IconType, size: QSize = None) -> QPixmap:
        """
        Get an icon as a pixmap.
        
        Args:
            icon_type: Type of icon to get
            size: Size for the pixmap
            
        Returns:
            QPixmap for the requested icon
        """
        icon = self.get_icon(icon_type)
        
        # Set default size if not specified
        if not size:
            size = QSize(16, 16)
        
        return icon.pixmap(size)
    
    def clear_cache(self) -> None:
        """Clear the icon cache"""
        self._icon_cache.clear()
    
    def _load_icon(self, filename: str, icon_type: IconType, size: QSize = None) -> QIcon:
        """
        Load an icon from file.
        
        Args:
            filename: Filename of the icon
            icon_type: Type of icon (for fallback)
            size: Optional specific size
            
        Returns:
            Loaded QIcon or fallback
        """
        # Check if theme-specific icon exists
        if self._is_dark_theme:
            theme_path = self.icon_dir / "dark" / filename
            if theme_path.exists():
                return self._load_icon_from_file(theme_path, size)
        else:
            theme_path = self.icon_dir / "light" / filename
            if theme_path.exists():
                return self._load_icon_from_file(theme_path, size)
        
        # Check for non-theme-specific icon
        regular_path = self.icon_dir / filename
        if regular_path.exists():
            return self._load_icon_from_file(regular_path, size)
        
        # Try alternative directories
        alt_paths = [
            self.icon_dir / "common" / filename,
            Path(f":/icons/{filename}")  # Qt resource path
        ]
        
        for path in alt_paths:
            try:
                if Path(str(path)).exists():
                    return self._load_icon_from_file(path, size)
            except:
                pass
        
        # Return fallback icon
        return self._create_fallback_icon(icon_type, size)
    
    def _load_icon_from_file(self, file_path: Path, size: QSize = None) -> QIcon:
        """
        Load an icon from a specific file.
        
        Args:
            file_path: Path to the icon file
            size: Optional specific size
            
        Returns:
            Loaded QIcon
        """
        # Handle SVG icons
        if str(file_path).lower().endswith('.svg'):
            return self._load_svg_icon(file_path, size)
        
        # Handle raster icons
        icon = QIcon(str(file_path))
        
        # Resize if needed
        if size and not icon.availableSizes():
            icon = self._resize_icon(icon, size)
        
        return icon
    
    def _load_svg_icon(self, file_path: Path, size: QSize = None) -> QIcon:
        """
        Load an SVG icon.
        
        Args:
            file_path: Path to the SVG file
            size: Optional specific size
            
        Returns:
            Loaded QIcon
        """
        try:
            # Default size if not specified
            if not size:
                size = QSize(16, 16)
            
            # Use QSvgRenderer to render the SVG to a pixmap
            renderer = QSvgRenderer(str(file_path))
            
            if not renderer.isValid():
                raise ValueError(f"Invalid SVG file: {file_path}")
            
            pixmap = QPixmap(size)
            pixmap.fill(Qt.transparent)
            
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            
            return QIcon(pixmap)
            
        except Exception as e:
            print(f"Error loading SVG icon: {str(e)}")
            
            # Return an empty icon
            return QIcon()
    
    def _create_fallback_icon(self, icon_type: IconType, size: QSize = None) -> QIcon:
        """
        Create a fallback icon when the requested icon is not found.
        
        Args:
            icon_type: Type of icon to create
            size: Size for the icon
            
        Returns:
            Generated fallback QIcon
        """
        # Default size if not specified
        if not size:
            size = QSize(16, 16)
        
        # Create a blank pixmap
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)
        
        # Create painter for the pixmap
        painter = QPainter(pixmap)
        
        # Set up painter
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw based on icon type
        if icon_type in [IconType.WARNING, IconType.ERROR, IconType.ALERT]:
            # Warning triangle
            painter.setPen(Qt.red)
            painter.setBrush(QColor(255, 200, 200))
            
            # Draw a triangle
            points = [
                QSize(size.width() // 2, 2),
                QSize(size.width() - 2, size.height() - 2),
                QSize(2, size.height() - 2)
            ]
            
            painter.drawPolygon(points)
            
            # Draw exclamation mark
            painter.setPen(Qt.black)
            painter.drawLine(
                size.width() // 2, size.height() // 3,
                size.width() // 2, size.height() * 2 // 3
            )
            painter.drawPoint(size.width() // 2, size.height() * 3 // 4)
            
        elif icon_type in [IconType.INFO, IconType.SUCCESS]:
            # Info circle
            painter.setPen(Qt.blue)
            painter.setBrush(QColor(200, 200, 255))
            
            # Draw a circle
            painter.drawEllipse(2, 2, size.width() - 4, size.height() - 4)
            
            # Draw 'i'
            painter.setPen(Qt.black)
            painter.drawLine(
                size.width() // 2, size.height() // 3,
                size.width() // 2, size.height() * 2 // 3
            )
            painter.drawPoint(size.width() // 2, size.height() // 4)
            
        else:
            # Generic icon (box with icon type initial)
            painter.setPen(Qt.black)
            painter.setBrush(QColor(240, 240, 240))
            
            # Draw a rounded rect
            painter.drawRoundedRect(2, 2, size.width() - 4, size.height() - 4, 2, 2)
            
            # Draw text
            painter.setPen(Qt.black)
            name = icon_type.name
            text = name[0] if name else "?"
            
            painter.drawText(
                2, 2, size.width() - 4, size.height() - 4,
                Qt.AlignCenter, text
            )
        
        painter.end()
        
        return QIcon(pixmap)
    
    def _resize_icon(self, icon: QIcon, size: QSize)