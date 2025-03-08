#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# gui/components/status_indicator.py

from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, 
    QSizePolicy, QFrame
)
from PySide6.QtCore import Qt, QSize, Signal, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPaintEvent, QFontMetrics

class StatusIndicator(QWidget):
    """
    A customizable indicator widget that shows system or component status
    with color-coded visual feedback and optional text label.
    
    Features:
    - Color-coded status indicator (success, warning, error, info, offline)
    - Optional text label describing the status
    - Pulsing animation for active states
    - Customizable size and appearance
    """
    
    # Status types
    STATUS_SUCCESS = "success"
    STATUS_WARNING = "warning"
    STATUS_ERROR = "error"
    STATUS_INFO = "info"
    STATUS_OFFLINE = "offline"
    STATUS_ACTIVE = "active"
    
    # Signals
    clicked = Signal()
    
    def __init__(self, parent=None, status=None, text=None, size=16):
        """
        Initialize the status indicator widget
        
        Args:
            parent: Parent widget
            status: Initial status (success, warning, error, info, offline, active)
            text: Optional text label to display next to indicator
            size: Size of the indicator in pixels
        """
        super().__init__(parent)
        
        # Status settings
        self._status = status or self.STATUS_OFFLINE
        self._text = text
        self._size = size
        self._pulsing = False
        
        # Status colors
        self._colors = {
            self.STATUS_SUCCESS: QColor(16, 185, 129),    # Green
            self.STATUS_WARNING: QColor(245, 158, 11),    # Amber
            self.STATUS_ERROR: QColor(244, 63, 94),       # Red
            self.STATUS_INFO: QColor(59, 130, 246),       # Blue
            self.STATUS_OFFLINE: QColor(156, 163, 175),   # Grey
            self.STATUS_ACTIVE: QColor(139, 92, 246)      # Purple
        }
        
        # Animation properties
        self._opacity = 1.0
        self._animation = QPropertyAnimation(self, b"opacity")
        self._animation.setDuration(1500)
        self._animation.setStartValue(1.0)
        self._animation.setEndValue(0.4)
        self._animation.setLoopCount(-1)  # Loop indefinitely
        self._animation.setEasingCurve(QEasingCurve.InOutSine)
        
        # Setup UI
        self._setup_ui()
        
        # Start animation if needed
        self._update_animation()
    
    def _setup_ui(self):
        """Setup the widget's UI components"""
        self.setMinimumSize(self._size, self._size)
        
        # Set overall layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Create indicator widget
        self.indicator = QWidget()
        self.indicator.setFixedSize(self._size, self._size)
        layout.addWidget(self.indicator)
        
        # Create label if text is provided
        if self._text:
            self.label = QLabel(self._text)
            layout.addWidget(self.label)
        else:
            self.label = None
        
        # Setup sizing
        if self._text:
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        else:
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.setFixedSize(self._size, self._size)
    
    def set_status(self, status, text=None):
        """
        Set the status of the indicator
        
        Args:
            status: New status (success, warning, error, info, offline, active)
            text: Optional new text label
        """
        if status != self._status or (text is not None and text != self._text):
            self._status = status
            
            if text is not None:
                self._text = text
                if self.label:
                    self.label.setText(text)
                elif text:
                    # Create label if it doesn't exist
                    self.label = QLabel(text)
                    self.layout().addWidget(self.label)
                    self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            
            # Update animation state
            self._update_animation()
            
            # Force repaint
            self.update()
    
    def set_pulsing(self, pulsing):
        """
        Enable or disable pulsing animation
        
        Args:
            pulsing: True to enable pulsing, False to disable
        """
        if pulsing != self._pulsing:
            self._pulsing = pulsing
            self._update_animation()
    
    def _update_animation(self):
        """Update animation state based on status and pulsing setting"""
        # Stop any existing animation
        self._animation.stop()
        
        # Active status or pulsing enabled
        if self._pulsing or self._status == self.STATUS_ACTIVE:
            self._animation.start()
    
    def get_opacity(self):
        """Get the current opacity value"""
        return self._opacity
    
    def set_opacity(self, opacity):
        """Set the opacity value and update"""
        if self._opacity != opacity:
            self._opacity = opacity
            self.update()
    
    # Define opacity property for animation
    opacity = Property(float, get_opacity, set_opacity)
    
    def paintEvent(self, event: QPaintEvent):
        """Paint the indicator"""
        if not hasattr(self, 'indicator'):
            return
        
        painter = QPainter(self.indicator)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get the correct color for current status
        color = self._colors.get(self._status, self._colors[self.STATUS_OFFLINE])
        
        # Apply opacity if animating
        if self._status == self.STATUS_ACTIVE or self._pulsing:
            color.setAlphaF(self._opacity)
        
        # Calculate the indicator rect
        rect = self.indicator.rect().adjusted(1, 1, -1, -1)
        
        # Draw the indicator
        painter.setPen(QPen(color.darker(120), 1))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(rect)
        
        # Add a highlight effect
        highlight_color = QColor(255, 255, 255, 70)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(highlight_color))
        painter.drawEllipse(rect.adjusted(rect.width() * 0.2, rect.height() * 0.2, 
                                         -rect.width() * 0.6, -rect.height() * 0.4))
        
        painter.end()
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def set_size(self, size):
        """Set the size of the indicator"""
        if size != self._size:
            self._size = size
            if hasattr(self, 'indicator'):
                self.indicator.setFixedSize(size, size)
                self.setMinimumSize(size, size)
                if not self._text:
                    self.setFixedSize(size, size)
                self.update()
    
    def get_status(self):
        """Get the current status"""
        return self._status
    
    def get_text(self):
        """Get the current status text"""
        return self._text


class StatusIndicatorGroup(QWidget):
    """
    A group of status indicators that can be used to show system component statuses.
    """
    
    def __init__(self, parent=None, vertical=False):
        """
        Initialize status indicator group
        
        Args:
            parent: Parent widget
            vertical: If True, indicators are arranged vertically
        """
        super().__init__(parent)
        
        self.indicators = {}
        self.vertical = vertical
        
        # Setup layout
        if vertical:
            self.layout = QVBoxLayout(self)
        else:
            self.layout = QHBoxLayout(self)
        
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)
        
        # Optional separator line
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.VLine if not vertical else QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        self.separator.setVisible(False)
    
    def add_indicator(self, name, status=None, text=None, size=16):
        """
        Add a status indicator to the group
        
        Args:
            name: Unique name for this indicator
            status: Initial status
            text: Text label
            size: Indicator size
            
        Returns:
            StatusIndicator: The created indicator
        """
        indicator = StatusIndicator(self, status, text, size)
        self.indicators[name] = indicator
        self.layout.addWidget(indicator)
        return indicator
    
    def add_separator(self):
        """Add a separator line between indicators"""
        if not self.separator.isVisible():
            self.layout.addWidget(self.separator)
            self.separator.setVisible(True)
    
    def set_status(self, name, status, text=None):
        """
        Set the status of a specific indicator
        
        Args:
            name: Name of the indicator
            status: New status
            text: Optional new text
        """
        if name in self.indicators:
            self.indicators[name].set_status(status, text)
    
    def get_indicator(self, name):
        """
        Get a specific indicator by name
        
        Args:
            name: Name of the indicator
            
        Returns:
            StatusIndicator or None
        """
        return self.indicators.get(name)
    
    def clear(self):
        """Remove all indicators"""
        for indicator in self.indicators.values():
            self.layout.removeWidget(indicator)
            indicator.deleteLater()
        
        self.indicators.clear()
        self.separator.setVisible(False)


# Example usage
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Status Indicator Example")
    window.setGeometry(100, 100, 400, 300)
    
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    layout = QVBoxLayout(central_widget)
    
    # Individual indicators
    status_success = StatusIndicator(status=StatusIndicator.STATUS_SUCCESS, text="System Online")
    status_warning = StatusIndicator(status=StatusIndicator.STATUS_WARNING, text="Low Disk Space")
    status_error = StatusIndicator(status=StatusIndicator.STATUS_ERROR, text="Connection Failed")
    status_active = StatusIndicator(status=StatusIndicator.STATUS_ACTIVE, text="Processing...")
    
    layout.addWidget(status_success)
    layout.addWidget(status_warning)
    layout.addWidget(status_error)
    layout.addWidget(status_active)
    
    # Indicator group
    group = StatusIndicatorGroup()
    group.add_indicator("database", StatusIndicator.STATUS_SUCCESS, "Database")
    group.add_indicator("api", StatusIndicator.STATUS_WARNING, "API")
    group.add_separator()
    group.add_indicator("background", StatusIndicator.STATUS_ACTIVE, "Background Tasks")
    
    layout.addWidget(group)
    
    window.show()
    
    sys.exit(app.exec())