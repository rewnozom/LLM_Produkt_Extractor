#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# gui/components/toggle_switch.py

from PySide6.QtWidgets import (
    QWidget, QCheckBox, QSlider, QLabel, QHBoxLayout,
    QApplication, QVBoxLayout, QSizePolicy
)
from PySide6.QtCore import (
    Qt, QSize, QPropertyAnimation, QEasingCurve, 
    Property, Signal, QRect, QPoint
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPaintEvent, 
    QFont, QFontMetrics, QMouseEvent
)


class ToggleSwitch(QWidget):
    """
    A modern toggle switch widget for boolean settings.
    
    Features:
    - Animated sliding effect
    - Customizable colors and sizes
    - Optional text labels
    - Hover and focus effects
    - Keyboard navigation support
    """
    
    # Signal emitted when the toggle state changes
    toggled = Signal(bool)
    
    def __init__(
        self, 
        parent=None, 
        checked=False, 
        text=None, 
        text_position="right", 
        width=40, 
        height=20
    ):
        """
        Initialize the toggle switch widget
        
        Args:
            parent: Parent widget
            checked: Initial state (True = ON, False = OFF)
            text: Optional text label
            text_position: Position of the text ("left", "right", "top", "bottom")
            width: Width of the toggle switch
            height: Height of the toggle switch
        """
        super().__init__(parent)
        
        # State
        self._checked = checked
        self._text = text
        self._text_position = text_position
        
        # Customizable properties
        self._track_radius = height / 2
        self._thumb_radius = (height - 4) / 2
        self._margin = 2
        
        # Position for animation (0.0 to 1.0)
        self._position = 1.0 if checked else 0.0
        
        # Hover and focus state
        self._hover = False
        self._focus = False
        
        # Colors
        self._track_color_on = QColor(59, 130, 246)    # Blue
        self._track_color_off = QColor(156, 163, 175)  # Gray
        self._thumb_color_on = QColor(255, 255, 255)   # White 
        self._thumb_color_off = QColor(255, 255, 255)  # White
        self._hover_color = QColor(0, 0, 0, 30)        # Semi-transparent black
        self._disabled_color = QColor(200, 200, 200)   # Light gray
        
        # Text font and color
        self._text_color = QColor(75, 85, 99)          # Gray 600
        self._text_color_disabled = QColor(156, 163, 175)  # Gray 400
        
        # Setup animation
        self._animation = QPropertyAnimation(self, b"position")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.InOutSine)
        
        # Setup widget
        self.setFixedWidth(width)
        self.setFixedHeight(height)
        self.setup_ui()
        
        # Enable focus
        self.setFocusPolicy(Qt.StrongFocus)
    
    def setup_ui(self):
        """Set up the UI layout"""
        layout = None
        
        # Choose layout based on text position
        if self._text:
            if self._text_position == "left" or self._text_position == "right":
                layout = QHBoxLayout(self)
            else:  # top or bottom
                layout = QVBoxLayout(self)
            
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)
            
            # Create text label
            self.label = QLabel(self._text)
            self.label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            
            # Add widgets in the correct order
            if self._text_position == "left" or self._text_position == "top":
                layout.addWidget(self.label)
                layout.addStretch(1)
            else:
                layout.addStretch(1)
                layout.addWidget(self.label)
        
        # Set minimum size based on toggle dimensions
        self._toggle_rect = QRect(0, 0, self.width(), self.height())
        
        # Calculate overall size based on text
        if self._text:
            text_width = QFontMetrics(self.label.font()).horizontalAdvance(self._text)
            if self._text_position == "left" or self._text_position == "right":
                self.setMinimumWidth(self.width() + text_width + 10)
            else:
                self.setMinimumHeight(self.height() + 20)
    
    def get_position(self):
        """Get the current position for animation property"""
        return self._position
    
    def set_position(self, position):
        """Set the position and update the widget"""
        if position != self._position:
            self._position = position
            self.update()
    
    # Define the position property for animation
    position = Property(float, get_position, set_position)
    
    def paintEvent(self, event: QPaintEvent):
        """Paint the toggle switch"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Set the right colors based on state
        if self.isEnabled():
            track_color = self._track_color_on if self._checked else self._track_color_off
            thumb_color = self._thumb_color_on if self._checked else self._thumb_color_off
            text_color = self._text_color
        else:
            track_color = self._disabled_color
            thumb_color = self._disabled_color.lighter(130)
            text_color = self._text_color_disabled
        
        # Get the rect for the toggle switch
        track_rect = self._toggle_rect
        if self._text:
            # Adjust the rect position based on layout
            if self._text_position == "right":
                track_rect.setWidth(self.width() - self.label.width() - 10)
            elif self._text_position == "left":
                track_rect.setX(self.label.width() + 10)
                track_rect.setWidth(self.width() - self.label.width() - 10)
            elif self._text_position == "bottom":
                track_rect.setHeight(self.height() - self.label.height() - 6)
            elif self._text_position == "top":
                track_rect.setY(self.label.height() + 6)
                track_rect.setHeight(self.height() - self.label.height() - 6)
        
        # Calculate track path
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(track_color))
        
        # Draw track (rounded rectangle)
        track_path = QRect(
            track_rect.x(),
            track_rect.y() + (track_rect.height() - 2 * self._track_radius) / 2,
            track_rect.width(),
            2 * self._track_radius
        )
        painter.drawRoundedRect(track_path, self._track_radius, self._track_radius)
        
        # Draw thumb (circle)
        thumb_radius = self._thumb_radius
        thumb_x = track_path.x() + self._margin + (
            (track_path.width() - 2 * self._margin - 2 * thumb_radius) * self._position
        )
        thumb_y = track_path.y() + (track_path.height() - 2 * thumb_radius) / 2
        
        # Draw shadow
        if self.isEnabled():
            shadow_color = QColor(0, 0, 0, 30)
            painter.setBrush(QBrush(shadow_color))
            painter.drawEllipse(
                QPoint(thumb_x + thumb_radius + 1, thumb_y + thumb_radius + 1),
                thumb_radius, thumb_radius
            )
        
        # Draw thumb
        painter.setBrush(QBrush(thumb_color))
        painter.drawEllipse(
            QPoint(thumb_x + thumb_radius, thumb_y + thumb_radius),
            thumb_radius, thumb_radius
        )
        
        # Draw hover effect
        if self._hover and self.isEnabled():
            painter.setBrush(QBrush(self._hover_color))
            painter.drawEllipse(
                QPoint(thumb_x + thumb_radius, thumb_y + thumb_radius),
                thumb_radius + 2, thumb_radius + 2
            )
        
        # Draw focus ring
        if self._focus and self.isEnabled():
            focus_pen = QPen(self._track_color_on.lighter(130))
            focus_pen.setWidth(1)
            painter.setPen(focus_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(
                track_path.adjusted(-2, -2, 2, 2),
                self._track_radius + 1, self._track_radius + 1
            )
        
        painter.end()
    
    def animate_toggle(self):
        """Animate the toggle switch"""
        self._animation.stop()
        
        if self._checked:
            self._animation.setStartValue(0.0)
            self._animation.setEndValue(1.0)
        else:
            self._animation.setStartValue(1.0)
            self._animation.setEndValue(0.0)
        
        self._animation.start()
    
    def toggle(self):
        """Toggle the switch state with animation"""
        self._checked = not self._checked
        self.animate_toggle()
        self.toggled.emit(self._checked)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events"""
        if event.button() == Qt.LeftButton:
            self.toggle()
            event.accept()
    
    def enterEvent(self, event):
        """Handle mouse enter events"""
        self._hover = True
        self.update()
    
    def leaveEvent(self, event):
        """Handle mouse leave events"""
        self._hover = False
        self.update()
    
    def focusInEvent(self, event):
        """Handle focus in events"""
        self._focus = True
        self.update()
    
    def focusOutEvent(self, event):
        """Handle focus out events"""
        self._focus = False
        self.update()
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Space or event.key() == Qt.Key_Return:
            self.toggle()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def isChecked(self):
        """Get the current state"""
        return self._checked
    
    def setChecked(self, checked):
        """Set the current state"""
        if checked != self._checked:
            self._checked = checked
            self._position = 1.0 if checked else 0.0
            self.update()
    
    def setText(self, text):
        """Set the label text"""
        if hasattr(self, 'label'):
            self.label.setText(text)
            self._text = text
            # Recalculate size
            self.setup_ui()
            self.update()
    
    def setColors(self, track_on=None, track_off=None, thumb_on=None, thumb_off=None):
        """Set custom colors for the toggle switch"""
        if track_on:
            self._track_color_on = QColor(track_on)
        if track_off:
            self._track_color_off = QColor(track_off)
        if thumb_on:
            self._thumb_color_on = QColor(thumb_on)
        if thumb_off:
            self._thumb_color_off = QColor(thumb_off)
        self.update()
    
    def sizeHint(self):
        """Suggested size for the widget"""
        return QSize(60, 28)


class ToggleSwitch2(QCheckBox):
    """
    An alternative implementation of toggle switch that inherits from QCheckBox
    for better integration with Qt's form layouts and item views.
    
    This version is simpler but doesn't have as many customization options.
    """
    
    def __init__(self, parent=None, text=None):
        """
        Initialize the toggle switch
        
        Args:
            parent: Parent widget
            text: Optional text label
        """
        if text:
            super().__init__(text, parent)
        else:
            super().__init__(parent)
        
        # Dimensions
        self._track_width = 36
        self._track_height = 18
        self._thumb_size = 14
        self._thumb_margin = 2
        
        # Colors
        self._track_color_on = QColor(59, 130, 246)    # Blue
        self._track_color_off = QColor(156, 163, 175)  # Gray
        self._thumb_color = QColor(255, 255, 255)      # White
        self._disabled_color = QColor(200, 200, 200)   # Light gray
        
        # Set widget size
        self.setMinimumWidth(self._track_width + (30 if text else 0))
        
        # Set style sheet to prevent default QCheckBox appearance
        self.setStyleSheet("""
            QCheckBox::indicator {
                width: 0;
                height: 0;
            }
        """)
    
    def paintEvent(self, event: QPaintEvent):
        """Paint the toggle switch"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Text position
        text_rect = self.contentsRect()
        indicator_width = self._track_width
        text_rect.setLeft(indicator_width + 6)
        
        # Draw text if any
        if self.text():
            if self.isEnabled():
                painter.setPen(self.palette().color(self.foregroundRole()))
            else:
                painter.setPen(QColor(156, 163, 175))  # Disabled text color
            painter.drawText(text_rect, Qt.AlignVCenter, self.text())
        
        # Set the colors based on state
        if self.isEnabled():
            track_color = self._track_color_on if self.isChecked() else self._track_color_off
            thumb_color = self._thumb_color
        else:
            track_color = self._disabled_color
            thumb_color = self._disabled_color.lighter(130)
        
        # Draw track
        track_rect = QRect(0, (self.height() - self._track_height) // 2, 
                           self._track_width, self._track_height)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(track_rect, self._track_height // 2, self._track_height // 2)
        
        # Draw thumb
        thumb_pos = self._thumb_margin
        if self.isChecked():
            thumb_pos = self._track_width - self._thumb_size - self._thumb_margin
        
        thumb_rect = QRect(thumb_pos, 
                           (self.height() - self._thumb_size) // 2,
                           self._thumb_size, self._thumb_size)
        
        # Draw shadow
        if self.isEnabled():
            shadow_color = QColor(0, 0, 0, 30)
            painter.setBrush(QBrush(shadow_color))
            shadow_rect = thumb_rect.translated(1, 1)
            painter.drawEllipse(shadow_rect)
        
        # Draw thumb
        painter.setBrush(QBrush(thumb_color))
        painter.drawEllipse(thumb_rect)
        
        painter.end()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to toggle the switch"""
        if event.button() == Qt.LeftButton:
            self.setChecked(not self.isChecked())
            self.clicked.emit(self.isChecked())
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def sizeHint(self):
        """Suggested size for the widget"""
        size = super().sizeHint()
        return QSize(max(size.width(), self._track_width + 30), 
                    max(size.height(), self._track_height + 4))


# Example usage
if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    
    window = QWidget()
    window.setWindowTitle("Toggle Switch Example")
    window.setGeometry(100, 100, 300, 300)
    
    layout = QVBoxLayout(window)
    
    # Create toggle switches with different configurations
    toggle1 = ToggleSwitch(text="Enable feature", checked=True)
    toggle2 = ToggleSwitch(text="Notifications", text_position="left")
    toggle3 = ToggleSwitch()  # No text
    
    # Custom colors
    toggle4 = ToggleSwitch(text="Custom colors")
    toggle4.setColors(track_on="#10b981", track_off="#374151")  # Green/Dark gray
    
    # Disabled toggle
    toggle5 = ToggleSwitch(text="Disabled toggle", checked=True)
    toggle5.setEnabled(False)
    
    # Alternative implementation
    toggle6 = ToggleSwitch2(text="Alternative style")
    
    # Connect signals
    toggle1.toggled.connect(lambda checked: print(f"Toggle 1: {'ON' if checked else 'OFF'}"))
    
    # Add to layout
    layout.addWidget(QLabel("Toggle Switches:"))
    layout.ad