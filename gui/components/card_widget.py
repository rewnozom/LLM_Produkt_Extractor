#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# gui/components/card_widget.py

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QSizePolicy, QGraphicsDropShadowEffect, QGridLayout,
    QScrollArea, QSpacerItem, QMenu, QToolButton
)
from PySide6.QtCore import Qt, QSize, Signal, QPoint, QRect, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush, QPaintEvent, QFont,
    QIcon, QPixmap, QImage, QLinearGradient, QGradient
)

class CardWidget(QFrame):
    """
    A modern card widget for displaying content with a title, optional image, 
    and action buttons.
    
    Features:
    - Customizable header, content and footer sections
    - Built-in hover and active states
    - Support for images and icons
    - Hierarchical importance levels (primary, secondary, ghost)
    - Click actions and custom buttons
    - Optional elevation with shadow effects
    """
    
    # Signals
    clicked = Signal()
    action_triggered = Signal(str)  # Action ID
    
    # Card importance levels
    LEVEL_PRIMARY = "primary"
    LEVEL_SECONDARY = "secondary"
    LEVEL_GHOST = "ghost"
    
    def __init__(
        self, 
        parent=None, 
        title=None, 
        content=None, 
        level=LEVEL_SECONDARY,
        image=None,
        icon=None,
        footer=None,
        selectable=False,
        elevation=1
    ):
        """
        Initialize the card widget
        
        Args:
            parent: Parent widget
            title: Card title (string or QWidget)
            content: Card content (string, QWidget, or list of widgets)
            level: Importance level (primary, secondary, ghost)
            image: Optional image (QPixmap, QImage, or path string)
            icon: Optional icon (QIcon or path string)
            footer: Optional footer content (string, QWidget, or list of widgets)
            selectable: Whether the card can be selected
            elevation: Shadow elevation level (0-3, 0 means no shadow)
        """
        super().__init__(parent)
        
        # Store properties
        self._title = title
        self._content = content
        self._level = level
        self._image = image
        self._icon = icon
        self._footer = footer
        self._selectable = selectable
        self._elevation = min(3, max(0, elevation)) 
        
        # State
        self._selected = False
        self._hover = False
        self._actions = {}  # Action buttons
        
        # Setup UI
        self._setup_ui()
        
        # Configure frame
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setMinimumSize(200, 100)
        
        # Set mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Apply shadow if needed
        self._apply_shadow()
        
        # Apply initial style
        self._update_style()
    
    def _setup_ui(self):
        """Setup the UI components of the card"""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(8)
        
        # Create header section if title or icon provided
        if self._title or self._icon:
            self.header = QWidget()
            self.header_layout = QHBoxLayout(self.header)
            self.header_layout.setContentsMargins(0, 0, 0, 0)
            
            # Add icon if provided
            if self._icon:
                self.icon_label = QLabel()
                if isinstance(self._icon, QIcon):
                    pixmap = self._icon.pixmap(QSize(24, 24))
                    self.icon_label.setPixmap(pixmap)
                elif isinstance(self._icon, str):
                    # Assume it's a path
                    pixmap = QPixmap(self._icon)
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        self.icon_label.setPixmap(pixmap)
                
                self.header_layout.addWidget(self.icon_label)
            
            # Add title
            if self._title:
                if isinstance(self._title, str):
                    self.title_label = QLabel(self._title)
                    font = self.title_label.font()
                    font.setPointSize(font.pointSize() + 1)
                    font.setBold(True)
                    self.title_label.setFont(font)
                else:
                    # Assume it's a widget
                    self.title_label = self._title
                
                self.header_layout.addWidget(self.title_label, 1)  # Title gets stretch
            
            # Add menu button if selectable
            if self._selectable:
                self.menu_button = QToolButton()
                self.menu_button.setIcon(QIcon.fromTheme("view-more", QIcon()))
                self.menu_button.setPopupMode(QToolButton.InstantPopup)
                self.menu_button.setAutoRaise(True)
                
                # Create menu
                self.menu = QMenu(self)
                select_action = self.menu.addAction("Select")
                select_action.triggered.connect(self.toggle_selection)
                
                self.menu_button.setMenu(self.menu)
                self.header_layout.addWidget(self.menu_button)
            
            self.main_layout.addWidget(self.header)
        
        # Add image if provided
        if self._image:
            self.image_label = QLabel()
            self.image_label.setAlignment(Qt.AlignCenter)
            self.image_label.setMinimumHeight(100)
            self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            
            # Set the image
            if isinstance(self._image, QPixmap):
                self.image_label.setPixmap(self._image.scaled(
                    self.image_label.width(), 150, 
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            elif isinstance(self._image, QImage):
                self.image_label.setPixmap(QPixmap.fromImage(self._image).scaled(
                    self.image_label.width(), 150, 
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            elif isinstance(self._image, str):
                pixmap = QPixmap(self._image)
                if not pixmap.isNull():
                    self.image_label.setPixmap(pixmap.scaled(
                        self.image_label.width(), 150, 
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    ))
            
            self.main_layout.addWidget(self.image_label)
        
        # Add content
        if self._content:
            if isinstance(self._content, str):
                self.content_label = QLabel(self._content)
                self.content_label.setWordWrap(True)
                self.content_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
                self.content_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.main_layout.addWidget(self.content_label, 1)  # Content gets stretch
            elif isinstance(self._content, QWidget):
                self.content_widget = self._content
                self.main_layout.addWidget(self.content_widget, 1)  # Content gets stretch
            elif isinstance(self._content, list):
                # Content is a list of widgets
                self.content_widget = QWidget()
                self.content_layout = QVBoxLayout(self.content_widget)
                self.content_layout.setContentsMargins(0, 0, 0, 0)
                self.content_layout.setSpacing(6)
                
                for widget in self._content:
                    self.content_layout.addWidget(widget)
                
                self.main_layout.addWidget(self.content_widget, 1)  # Content gets stretch
        
        # Add spacer between content and footer
        self.main_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Add footer if provided
        if self._footer:
            self.footer = QWidget()
            self.footer_layout = QHBoxLayout(self.footer)
            self.footer_layout.setContentsMargins(0, 4, 0, 0)
            self.footer_layout.setSpacing(6)
            
            if isinstance(self._footer, str):
                self.footer_label = QLabel(self._footer)
                self.footer_layout.addWidget(self.footer_label)
            elif isinstance(self._footer, QWidget):
                self.footer_layout.addWidget(self._footer)
            elif isinstance(self._footer, list):
                # Footer is a list of widgets
                for widget in self._footer:
                    self.footer_layout.addWidget(widget)
            
            self.main_layout.addWidget(self.footer)
    
    def _apply_shadow(self):
        """Apply shadow effect based on elevation"""
        if self._elevation > 0:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(self._elevation * 4)
            shadow.setColor(QColor(0, 0, 0, 50))
            shadow.setOffset(0, self._elevation)
            self.setGraphicsEffect(shadow)
    
    def _update_style(self):
        """Update the card's style based on its state"""
        style = "QFrame { border-radius: 4px; "
        
        # Background color based on level and state
        if self._level == self.LEVEL_PRIMARY:
            if self._selected:
                style += "background-color: #3b82f6; color: white; "  # Blue
            elif self._hover:
                style += "background-color: #60a5fa; color: white; "  # Lighter blue
            else:
                style += "background-color: #6889cf; color: white; "  # Muted blue
        elif self._level == self.LEVEL_SECONDARY:
            if self._selected:
                style += "background-color: #f3f4f6; "  # Light gray
            elif self._hover:
                style += "background-color: #f9fafb; "  # Lighter gray
            else:
                style += "background-color: #ffffff; "  # White
        else:  # GHOST level
            if self._selected:
                style += "background-color: #f3f4f6; border: 1px solid #e5e7eb; "
            elif self._hover:
                style += "background-color: #f9fafb; border: 1px solid #e5e7eb; "
            else:
                style += "background-color: transparent; border: 1px solid #e5e7eb; "
        
        style += "}"
        
        # Additional styling for title if it's a QLabel
        if hasattr(self, 'title_label') and isinstance(self.title_label, QLabel):
            if self._level == self.LEVEL_PRIMARY:
                style += "QLabel { color: white; }"
        
        self.setStyleSheet(style)
    
    def paintEvent(self, event: QPaintEvent):
        """Custom paint event for additional styling"""
        super().paintEvent(event)
        
        # Draw selection indicator if selected
        if self._selected:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            if self._level == self.LEVEL_PRIMARY:
                pen_color = QColor(255, 255, 255, 100)  # Semi-transparent white
            else:
                pen_color = QColor(59, 130, 246, 100)  # Semi-transparent blue
            
            pen = QPen(pen_color)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 4, 4)
            
            painter.end()
    
    def enterEvent(self, event):
        """Handle mouse enter event"""
        self._hover = True
        self._update_style()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave event"""
        self._hover = False
        self._update_style()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press event"""
        if event.button() == Qt.LeftButton:
            if self._selectable:
                self.toggle_selection()
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def add_action_button(self, action_id, text, icon=None, primary=False):
        """
        Add an action button to the card's footer
        
        Args:
            action_id: Unique identifier for the action
            text: Button text
            icon: Optional icon
            primary: If True, style as primary button
            
        Returns:
            QPushButton: The created button
        """
        # Create button
        button = QPushButton(text)
        
        if icon:
            if isinstance(icon, QIcon):
                button.setIcon(icon)
            elif isinstance(icon, str):
                button.setIcon(QIcon(icon))
        
        # Style the button
        if primary:
            button.setProperty("class", "primary")
        
        # Connect signal
        button.clicked.connect(lambda: self.action_triggered.emit(action_id))
        
        # Store the button
        self._actions[action_id] = button
        
        # Add to footer
        if hasattr(self, 'footer'):
            # We already have a footer
            self.footer_layout.addWidget(button)
        else:
            # Create a footer
            self.footer = QWidget()
            self.footer_layout = QHBoxLayout(self.footer)
            self.footer_layout.setContentsMargins(0, 4, 0, 0)
            self.footer_layout.addStretch(1)  # Push buttons to the right
            self.footer_layout.addWidget(button)
            
            self.main_layout.addWidget(self.footer)
        
        return button
    
    def toggle_selection(self):
        """Toggle the selection state of the card"""
        if self._selectable:
            self._selected = not self._selected
            self._update_style()
            self.update()
    
    def is_selected(self):
        """Check if the card is selected"""
        return self._selected
    
    def set_selected(self, selected):
        """Set the selection state of the card"""
        if self._selectable and selected != self._selected:
            self._selected = selected
            self._update_style()
            self.update()
    
    def set_title(self, title):
        """Set the card title"""
        self._title = title
        
        if hasattr(self, 'title_label'):
            if isinstance(self.title_label, QLabel) and isinstance(title, str):
                self.title_label.setText(title)
            elif isinstance(title, QWidget):
                # Replace old title widget
                self.header_layout.removeWidget(self.title_label)
                self.title_label.deleteLater()
                self.title_label = title
                self.header_layout.insertWidget(1, self.title_label, 1)
    
    def set_content(self, content):
        """Set the card content"""
        self._content = content
        
        # Remove old content
        if hasattr(self, 'content_label'):
            self.main_layout.removeWidget(self.content_label)
            self.content_label.deleteLater()
            delattr(self, 'content_label')
        
        if hasattr(self, 'content_widget'):
            self.main_layout.removeWidget(self.content_widget)
            self.content_widget.deleteLater()
            delattr(self, 'content_widget')
        
        # Add new content
        if isinstance(content, str):
            self.content_label = QLabel(content)
            self.content_label.setWordWrap(True)
            self.content_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            self.content_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.main_layout.insertWidget(self.main_layout.count() - 1, self.content_label, 1)
        elif isinstance(content, QWidget):
            self.content_widget = content
            self.main_layout.insertWidget(self.main_layout.count() - 1, self.content_widget, 1)
        elif isinstance(content, list):
            # Content is a list of widgets
            self.content_widget = QWidget()
            self.content_layout = QVBoxLayout(self.content_widget)
            self.content_layout.setContentsMargins(0, 0, 0, 0)
            self.content_layout.setSpacing(6)
            
            for widget in content:
                self.content_layout.addWidget(widget)
            
            self.main_layout.insertWidget(self.main_layout.count() - 1, self.content_widget, 1)
    
    def set_image(self, image):
        """Set the card image"""
        self._image = image
        
        if hasattr(self, 'image_label'):
            # Update existing image
            if isinstance(image, QPixmap):
                self.image_label.setPixmap(image.scaled(
                    self.image_label.width(), 150, 
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            elif isinstance(image, QImage):
                self.image_label.setPixmap(QPixmap.fromImage(image).scaled(
                    self.image_label.width(), 150, 
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            elif isinstance(image, str):
                pixmap = QPixmap(image)
                if not pixmap.isNull():
                    self.image_label.setPixmap(pixmap.scaled(
                        self.image_label.width(), 150, 
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    ))
        else:
            # Add new image
            self.image_label = QLabel()
            self.image_label.setAlignment(Qt.AlignCenter)
            self.image_label.setMinimumHeight(100)
            self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            
            # Set the image
            if isinstance(image, QPixmap):
                self.image_label.setPixmap(image.scaled(
                    self.image_label.width(), 150, 
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            elif isinstance(image, QImage):
                self.image_label.setPixmap(QPixmap.fromImage(image).scaled(
                    self.image_label.width(), 150, 
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            elif isinstance(image, str):
                pixmap = QPixmap(image)
                if not pixmap.isNull():
                    self.image_label.setPixmap(pixmap.scaled(
                        self.image_label.width(), 150, 
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    ))
            
            # Insert after header if exists
            insert_pos = 1 if hasattr(self, 'header') else 0
            self.main_layout.insertWidget(insert_pos, self.image_label)
    
    def set_level(self, level):
        """Set the card importance level"""
        if level in [self.LEVEL_PRIMARY, self.LEVEL_SECONDARY, self.LEVEL_GHOST]:
            self._level = level
            self._update_style()
    
    def get_action_button(self, action_id):
        """Get an action button by ID"""
        return self._actions.get(action_id)
    
    def remove_action(self, action_id):
        """Remove an action button"""
        if action_id in self._actions:
            button = self._actions[action_id]
            self.footer_layout.removeWidget(button)
            button.deleteLater()
            del self._actions[action_id]


class CardContainer(QScrollArea):
    """
    A container for displaying multiple cards in a grid or list layout
    """
    
    # Signal emitted when a card is selected
    card_selected = Signal(int)  # card index
    
    def __init__(self, parent=None, columns=2, spacing=10, layout_type="grid"):
        """
        Initialize the card container
        
        Args:
            parent: Parent widget
            columns: Number of columns in grid layout
            spacing: Spacing between cards
            layout_type: "grid" or "list"
        """
        super().__init__(parent)
        
        self._columns = columns
        self._spacing = spacing
        self._layout_type = layout_type
        self._cards = []
        self._selected_card = None
        
        # Setup UI
        self._setup_ui()
        
        # Configure scroll area
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    
    def _setup_ui(self):
        """Setup the UI components"""
        self.container = QWidget()
        
        if self._layout_type == "grid":
            self.layout = QGridLayout(self.container)
        else:  # list
            self.layout = QVBoxLayout(self.container)
        
        self.layout.setContentsMargins(self._spacing, self._spacing, self._spacing, self._spacing)
        self.layout.setSpacing(self._spacing)
        
        self.setWidget(self.container)
    
    def add_card(self, card):
        """
        Add a card to the container
        
        Args:
            card: CardWidget to add
            
        Returns:
            int: Index of the added card
        """
        if not isinstance(card, CardWidget):
            raise TypeError("Card must be a CardWidget instance")
        
        # Connect signals
        card.clicked.connect(lambda: self._handle_card_click(len(self._cards)))
        
        # Add card to layout
        if self._layout_type == "grid":
            row = len(self._cards) // self._columns
            col = len(self._cards) % self._columns
            self.layout.addWidget(card, row, col)
        else:  # list
            self.layout.addWidget(card)
        
        # Add to cards list
        self._cards.append(card)
        return len(self._cards) - 1
    
    def insert_card(self, index, card):
        """
        Insert a card at a specific index
        
        Args:
            index: Position to insert the card
            card: CardWidget to insert
            
        Returns:
            int: Index of the inserted card
        """
        if not isinstance(card, CardWidget):
            raise TypeError("Card must be a CardWidget instance")
        
        # Connect signals
        card.clicked.connect(lambda: self._handle_card_click(index))
        
        # Insert into cards list
        self._cards.insert(index, card)
        
        # Re-layout all cards
        self._relayout_cards()
        
        return index
    
    def remove_card(self, index):
        """
        Remove a card at the specified index
        
        Args:
            index: Index of the card to remove
            
        Returns:
            CardWidget: The removed card
        """
        if 0 <= index < len(self._cards):
            card = self._cards.pop(index)
            
            # Remove from layout
            if self._layout_type == "grid":
                self.layout.removeWidget(card)
            else:
                self.layout.removeWidget(card)
            
            # Re-layout all cards
            self._relayout_cards()
            
            return card
        else:
            raise IndexError("Card index out of range")
    
    def clear(self):
        """Remove all cards"""
        for card in self._cards:
            if self._layout_type == "grid":
                self.layout.removeWidget(card)
            else:
                self.layout.removeWidget(card)
            card.deleteLater()
        
        self._cards.clear()
        self._selected_card = None
    
    def get_card(self, index):
        """Get a card at the specified index"""
        if 0 <= index < len(self._cards):
            return self._cards[index]
        return None
    
    def get_cards(self):
        """Get all cards"""
        return self._cards.copy()
    
    def get_selected_card(self):
        """Get the selected card"""
        return self._selected_card
    
    def get_selected_index(self):
        """Get the index of the selected card"""
        if self._selected_card is None:
            return -1
        return self._cards.index(self._selected_card)
    
    def select_card(self, index):
        """Select a card by index"""
        if 0 <= index < len(self._cards):
            self._select_card(self._cards[index])
    
    def _handle_card_click(self, index):
        """Handle click on a card"""
        self.select_card(index)
    
    def _select_card(self, card):
        """Select a card and deselect the previous one"""
        if self._selected_card == card:
            return
        
        # Deselect previous card
        if self._selected_card:
            self._selected_card.set_selected(False)
        
        # Select new card
        card.set_selected(True)
        self._selected_card = card
        
        # Emit signal
        self.card_selected.emit(self._cards.index(card))
    
    def _relayout_cards(self):
        """Re-layout all cards after insertion or removal"""
        # Remove all cards from layout
        if self._layout_type == "grid":
            for i in reversed(range(self.layout.count())): 
                self.layout.itemAt(i).widget().setParent(None)
            
            # Add cards back to layout in correct order
            for i, card in enumerate(self._cards):
                row = i // self._columns
                col = i % self._columns
                self.layout.addWidget(card, row, col)
        else:
            for i in reversed(range(self.layout.count())): 
                self.layout.itemAt(i).widget().setParent(None)
            
            # Add cards back to layout in correct order
            for card in self._cards:
                self.layout.addWidget(card)
    
    def set_columns(self, columns):
        """Set the number of columns for grid layout"""
        if self._layout_type == "grid" and columns != self._columns:
            self._columns = columns
            self._relayout_cards()
    
    def set_layout_type(self, layout_type):
        """Set the layout type (grid or list)"""
        if layout_type not in ["grid", "list"]:
            raise ValueError("Layout type must be 'grid' or 'list'")
        
        if layout_type != self._layout_type:
            self._layout_type = layout_type
            
            # Create new layout
            old_layout = self.layout
            
            if layout_type == "grid":
                self.layout = QGridLayout()
            else:
                self.layout = QVBoxLayout()
            
            self.layout.setContentsMargins(self._spacing, self._spacing, self._spacing, self._spacing)
            self.layout.setSpacing(self._spacing)
            
            # Remove all widgets from old layout
            for i in reversed(range(old_layout.count())):
                old_layout.itemAt(i).widget().setParent(None)
            
            # Set new layout
            self.container.setLayout(self.layout)
            
            # Add cards to new layout
            self._relayout_cards()


# Example usage
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Card Widget Example")
    window.setGeometry(100, 100, 800, 600)
    
    # Create a card container
    container = CardContainer(columns=2, layout_type="grid")
    window.setCentralWidget(container)
    
    # Create some cards
    for i in range(5):
        # Create a card with different levels
        if i % 3 == 0:
            level = CardWidget.LEVEL_PRIMARY
        elif i % 3 == 1:
            level = CardWidget.LEVEL_SECONDARY
        else:
            level = CardWidget.LEVEL_GHOST
        
        card = CardWidget(
            title=f"Card {i+1}",
            content=f"This is the content of card {i+1}. It demonstrates the card widget's capabilities.",
            level=level,
            selectable=True,
            elevation=i % 4  # Different elevation levels
        )
        
        # Add action buttons
        card.add_action_button(f"action_{i}_1", "Details")
        card.add_action_button(f"action_{i}_2", "Delete", primary=True)
        
        # Add to container
        container.add_card(card)
    
    window.show()
    
    sys.exit(app.exec())