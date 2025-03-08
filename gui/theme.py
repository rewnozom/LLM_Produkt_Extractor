#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class Theme:
    """
    Theme class for managing application styling
    """
    
    # Theme Colors
    COLORS = {
        'bg_primary': '#2b2929',          # Main background
        'bg_secondary': '#1a1a1a',        # Secondary background (widgets, panels)
        'bg_tertiary': '#262626',         # Tertiary background (hover states)
        'text_primary': '#d1cccc',        # Primary text color
        'text_secondary': '#a3a3a3',      # Secondary/dimmed text
        'accent_primary': '#fb923c',      # Primary accent (orange)
        'accent_secondary': '#ea580c',    # Secondary accent (darker orange)
        'accent_tertiary': '#c2410c',     # Tertiary accent (even darker orange)
        'border_color': 'rgba(82, 82, 82, 0.3)', # Border color
        'error': '#f43f5e',               # Error color
        'success': '#10b981',             # Success color
        'info': '#3b82f6',                # Info color
        'warning': '#f59e0b',             # Warning color
    }
    
    # Font Configurations
    FONTS = {
        'regular': {
            'family': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
            'size': 10,
            'weight': 'normal',
        },
        'heading': {
            'family': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
            'size': 16,
            'weight': 'bold',
        },
        'subheading': {
            'family': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
            'size': 14,
            'weight': 'bold',
        },
        'monospace': {
            'family': '"Courier New", Courier, monospace',
            'size': 10,
            'weight': 'normal',
        }
    }
    
    # Spacing and Sizing
    SPACING = {
        'xxs': 2,
        'xs': 4,
        'sm': 8,
        'md': 12,
        'lg': 16,
        'xl': 20,
        'xxl': 24
    }
    
    BORDER_RADIUS = {
        'sm': 3,
        'md': 4,
        'lg': 6,
        'xl': 8
    }
    
    def __init__(self):
        """Initialize theme"""
        pass
    
    def get_stylesheet(self):
        """Generate and return the complete application stylesheet"""
        return f"""
            /* General Application Styling */
            QWidget {{
                background-color: {self.COLORS['bg_primary']};
                color: {self.COLORS['text_primary']};
                font-family: {self.FONTS['regular']['family']};
                font-size: {self.FONTS['regular']['size']}pt;
            }}
            
            /* Main Window */
            QMainWindow, QDialog {{
                background-color: {self.COLORS['bg_primary']};
            }}
            
            /* Menu Bar */
            QMenuBar {{
                background-color: {self.COLORS['bg_secondary']};
                color: {self.COLORS['text_primary']};
                padding: {self.SPACING['xs']}px {self.SPACING['sm']}px;
            }}
            
            QMenuBar::item {{
                padding: {self.SPACING['sm']}px {self.SPACING['md']}px;
                background-color: transparent;
                border-radius: {self.BORDER_RADIUS['sm']}px;
            }}
            
            QMenuBar::item:selected {{
                background-color: {self.COLORS['bg_tertiary']};
            }}
            
            QMenuBar::item:pressed {{
                background-color: {self.COLORS['accent_primary']};
                color: {self.COLORS['bg_secondary']};
            }}
            
            /* Menus */
            QMenu {{
                background-color: {self.COLORS['bg_secondary']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['md']}px;
                padding: {self.SPACING['xs']}px;
            }}
            
            QMenu::item {{
                padding: {self.SPACING['sm']}px {self.SPACING['lg']}px;
                border-radius: {self.BORDER_RADIUS['sm']}px;
            }}
            
            QMenu::item:selected {{
                background-color: {self.COLORS['bg_tertiary']};
            }}
            
            QMenu::separator {{
                height: 1px;
                background-color: {self.COLORS['border_color']};
                margin: {self.SPACING['xs']}px {self.SPACING['sm']}px;
            }}
            
            /* Tab Widget */
            QTabWidget {{
                background-color: {self.COLORS['bg_primary']};
            }}
            
            QTabWidget::pane {{
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['md']}px;
                padding: {self.SPACING['xs']}px;
                background-color: {self.COLORS['bg_secondary']};
            }}
            
            QTabBar::tab {{
                background-color: {self.COLORS['bg_tertiary']};
                color: {self.COLORS['text_secondary']};
                padding: {self.SPACING['sm']}px {self.SPACING['lg']}px;
                margin-right: {self.SPACING['xs']}px;
                border-top-left-radius: {self.BORDER_RADIUS['md']}px;
                border-top-right-radius: {self.BORDER_RADIUS['md']}px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {self.COLORS['accent_primary']};
                color: {self.COLORS['bg_secondary']};
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: {self.COLORS['bg_primary']};
                color: {self.COLORS['text_primary']};
            }}
            
            /* Push Buttons */
            QPushButton {{
                background-color: {self.COLORS['bg_tertiary']};
                color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['md']}px;
                padding: {self.SPACING['sm']}px {self.SPACING['md']}px;
                min-height: 24px;
            }}
            
            QPushButton:hover {{
                background-color: {self.COLORS['accent_primary']};
                color: {self.COLORS['bg_secondary']};
            }}
            
            QPushButton:pressed {{
                background-color: {self.COLORS['accent_secondary']};
            }}
            
            QPushButton:disabled {{
                background-color: {self.COLORS['bg_secondary']};
                color: {self.COLORS['text_secondary']};
                border: 1px solid transparent;
            }}
            
            /* Primary Action Button */
            QPushButton[class="primary"] {{
                background-color: {self.COLORS['accent_primary']};
                color: {self.COLORS['bg_secondary']};
                font-weight: bold;
            }}
            
            QPushButton[class="primary"]:hover {{
                background-color: {self.COLORS['accent_secondary']};
            }}
            
            QPushButton[class="primary"]:pressed {{
                background-color: {self.COLORS['accent_tertiary']};
            }}
            
            /* Destructive Action Button */
            QPushButton[class="destructive"] {{
                background-color: {self.COLORS['error']};
                color: white;
            }}
            
            QPushButton[class="destructive"]:hover {{
                background-color: #e11d48;
            }}
            
            QPushButton[class="destructive"]:pressed {{
                background-color: #be123c;
            }}
            
            /* Tool Buttons */
            QToolButton {{
                background-color: {self.COLORS['bg_tertiary']};
                color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['md']}px;
                padding: {self.SPACING['xs']}px;
            }}
            
            QToolButton:hover {{
                background-color: {self.COLORS['accent_primary']};
                color: {self.COLORS['bg_secondary']};
            }}
            
            QToolButton:pressed {{
                background-color: {self.COLORS['accent_secondary']};
            }}
            
            /* Line Edit */
            QLineEdit {{
                background-color: {self.COLORS['bg_secondary']};
                color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['md']}px;
                padding: {self.SPACING['sm']}px;
                selection-background-color: {self.COLORS['accent_primary']};
            }}
            
            QLineEdit:focus {{
                border: 1px solid {self.COLORS['accent_primary']};
            }}
            
            QLineEdit:disabled {{
                background-color: {self.COLORS['bg_tertiary']};
                color: {self.COLORS['text_secondary']};
            }}
            
            /* Text Edit and Plain Text Edit */
            QTextEdit, QPlainTextEdit {{
                background-color: {self.COLORS['bg_secondary']};
                color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['md']}px;
                padding: {self.SPACING['sm']}px;
                selection-background-color: {self.COLORS['accent_primary']};
            }}
            
            QTextEdit:focus, QPlainTextEdit:focus {{
                border: 1px solid {self.COLORS['accent_primary']};
            }}
            
            /* Combo Box */
            QComboBox {{
                background-color: {self.COLORS['bg_secondary']};
                color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['md']}px;
                padding: {self.SPACING['sm']}px;
                padding-right: 20px;
                min-height: 24px;
            }}
            
            QComboBox:hover {{
                border: 1px solid {self.COLORS['accent_primary']};
            }}
            
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: right center;
                width: 20px;
                border-left: 1px solid {self.COLORS['border_color']};
            }}
            
            QComboBox::down-arrow {{
                width: 14px;
                height: 14px;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {self.COLORS['bg_secondary']};
                color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['border_color']};
                selection-background-color: {self.COLORS['accent_primary']};
                selection-color: {self.COLORS['bg_secondary']};
                outline: 0;
            }}
            
            /* Checkbox */
            QCheckBox {{
                color: {self.COLORS['text_primary']};
                spacing: {self.SPACING['sm']}px;
            }}
            
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['sm']}px;
                background-color: {self.COLORS['bg_secondary']};
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {self.COLORS['accent_primary']};
                border: 1px solid {self.COLORS['accent_primary']};
            }}
            
            QCheckBox::indicator:hover {{
                border: 1px solid {self.COLORS['accent_primary']};
            }}
            
            /* Radio Button */
            QRadioButton {{
                color: {self.COLORS['text_primary']};
                spacing: {self.SPACING['sm']}px;
            }}
            
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {self.COLORS['border_color']};
                border-radius: 8px;
                background-color: {self.COLORS['bg_secondary']};
            }}
            
            QRadioButton::indicator:checked {{
                background-color: {self.COLORS['accent_primary']};
                border: 1px solid {self.COLORS['accent_primary']};
            }}
            
            QRadioButton::indicator:hover {{
                border: 1px solid {self.COLORS['accent_primary']};
            }}
            
            /* Spinbox */
            QSpinBox, QDoubleSpinBox {{
                background-color: {self.COLORS['bg_secondary']};
                color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['md']}px;
                padding: {self.SPACING['sm']}px;
                padding-right: 20px;
            }}
            
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 1px solid {self.COLORS['accent_primary']};
            }}
            
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                background-color: {self.COLORS['bg_tertiary']};
                width: 20px;
            }}
            
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
                background-color: {self.COLORS['accent_primary']};
            }}
            
            /* Sliders */
            QSlider::groove:horizontal {{
                border: 1px solid {self.COLORS['border_color']};
                height: 4px;
                background: {self.COLORS['bg_tertiary']};
                margin: 0px;
                border-radius: 2px;
            }}
            
            QSlider::handle:horizontal {{
                background: {self.COLORS['accent_primary']};
                border: 1px solid {self.COLORS['accent_secondary']};
                width: 14px;
                height: 14px;
                margin: -6px 0;
                border-radius: 7px;
            }}
            
            QSlider::handle:horizontal:hover {{
                background: {self.COLORS['accent_secondary']};
            }}
            
            /* Progress Bar */
            QProgressBar {{
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['md']}px;
                background-color: {self.COLORS['bg_secondary']};
                text-align: center;
                color: {self.COLORS['text_primary']};
                font-weight: bold;
            }}
            
            QProgressBar::chunk {{
                background-color: {self.COLORS['accent_primary']};
                border-radius: {self.BORDER_RADIUS['sm']}px;
            }}
            
            /* Scroll Bar */
            QScrollBar:vertical {{
                border: none;
                background-color: {self.COLORS['bg_primary']};
                width: 12px;
                margin: 0px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {self.COLORS['bg_tertiary']};
                min-height: 30px;
                border-radius: 6px;
                margin: 1px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {self.COLORS['accent_primary']};
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            QScrollBar:horizontal {{
                border: none;
                background-color: {self.COLORS['bg_primary']};
                height: 12px;
                margin: 0px;
            }}
            
            QScrollBar::handle:horizontal {{
                background-color: {self.COLORS['bg_tertiary']};
                min-width: 30px;
                border-radius: 6px;
                margin: 1px;
            }}
            
            QScrollBar::handle:horizontal:hover {{
                background-color: {self.COLORS['accent_primary']};
            }}
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            
            /* Group Box */
            QGroupBox {{
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['md']}px;
                margin-top: 1.1em;
                padding-top: 0.5em;
                font-weight: bold;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 {self.SPACING['xs']}px;
                color: {self.COLORS['text_primary']};
            }}
            
            /* Splitter */
            QSplitter::handle {{
                background-color: {self.COLORS['border_color']};
            }}
            
            QSplitter::handle:horizontal {{
                width: 2px;
            }}
            
            QSplitter::handle:vertical {{
                height: 2px;
            }}
            
            /* Headers */
            QHeaderView::section {{
                background-color: {self.COLORS['bg_tertiary']};
                color: {self.COLORS['text_primary']};
                padding: {self.SPACING['sm']}px;
                border: 0px;
                border-right: 1px solid {self.COLORS['border_color']};
                border-bottom: 1px solid {self.COLORS['border_color']};
            }}
            
            QHeaderView::section:checked {{
                background-color: {self.COLORS['accent_primary']};
                color: {self.COLORS['bg_secondary']};
            }}
            
            /* Table View */
            QTableView {{
                background-color: {self.COLORS['bg_secondary']};
                color: {self.COLORS['text_primary']};
                gridline-color: {self.COLORS['border_color']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['md']}px;
                selection-background-color: {self.COLORS['accent_primary']};
                selection-color: {self.COLORS['bg_secondary']};
            }}
            
            QTableView::item {{
                padding: {self.SPACING['xs']}px;
                border-bottom: 1px solid {self.COLORS['border_color']};
            }}
            
            QTableView::item:selected {{
                background-color: {self.COLORS['accent_primary']};
            }}
            
            /* Tree View */
            QTreeView {{
                background-color: {self.COLORS['bg_secondary']};
                color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['md']}px;
                selection-background-color: {self.COLORS['accent_primary']};
                selection-color: {self.COLORS['bg_secondary']};
            }}
            
            QTreeView::item {{
                padding: {self.SPACING['xs']}px;
                border: none;
            }}
            
            QTreeView::item:selected {{
                background-color: {self.COLORS['accent_primary']};
            }}
            
            QTreeView::branch:selected {{
                background-color: {self.COLORS['accent_primary']};
            }}
            
            /* List View */
            QListView {{
                background-color: {self.COLORS['bg_secondary']};
                color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['md']}px;
                selection-background-color: {self.COLORS['accent_primary']};
                selection-color: {self.COLORS['bg_secondary']};
                outline: 0;
            }}
            
            QListView::item {{
                padding: {self.SPACING['sm']}px;
                border-bottom: 1px solid {self.COLORS['border_color']};
            }}
            
            QListView::item:selected {{
                background-color: {self.COLORS['accent_primary']};
            }}
            
            /* Status Bar */
            QStatusBar {{
                background-color: {self.COLORS['bg_secondary']};
                color: {self.COLORS['text_secondary']};
                border-top: 1px solid {self.COLORS['border_color']};
            }}
            
            /* Tool Bar */
            QToolBar {{
                background-color: {self.COLORS['bg_secondary']};
                border-bottom: 1px solid {self.COLORS['border_color']};
                spacing: {self.SPACING['sm']}px;
            }}
            
            QToolBar::separator {{
                width: 1px;
                background-color: {self.COLORS['border_color']};
                margin: {self.SPACING['xs']}px {self.SPACING['sm']}px;
            }}
            
            /* Dock Widgets */
            QDockWidget {{
                titlebar-close-icon: url(close.png);
                titlebar-normal-icon: url(float.png);
            }}
            
            QDockWidget::title {{
                text-align: left;
                background-color: {self.COLORS['bg_tertiary']};
                color: {self.COLORS['text_primary']};
                padding: {self.SPACING['sm']}px;
                spacing: {self.SPACING['sm']}px;
            }}
            
            QDockWidget::close-button, QDockWidget::float-button {{
                background-color: {self.COLORS['bg_tertiary']};
                border: none;
            }}
            
            QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
                background-color: {self.COLORS['accent_primary']};
            }}
            
            /* Labels */
            QLabel {{
                color: {self.COLORS['text_primary']};
            }}
            
            QLabel[heading="true"] {{
                font-family: {self.FONTS['heading']['family']};
                font-size: {self.FONTS['heading']['size']}pt;
                font-weight: {self.FONTS['heading']['weight']};
                color: {self.COLORS['text_primary']};
            }}
            
            QLabel[subheading="true"] {{
                font-family: {self.FONTS['subheading']['family']};
                font-size: {self.FONTS['subheading']['size']}pt;
                font-weight: {self.FONTS['subheading']['weight']};
                color: {self.COLORS['text_primary']};
            }}
            
            /* Custom Card Widget */
            QFrame[card="true"] {{
                background-color: {self.COLORS['bg_secondary']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: {self.BORDER_RADIUS['lg']}px;
            }}
            
            /* Error/success/warning styles */
            QLabel[alert="error"] {{
                color: {self.COLORS['error']};
            }}
            
            QLabel[alert="success"] {{
                color: {self.COLORS['success']};
            }}
            
            QLabel[alert="warning"] {{
                color: {self.COLORS['warning']};
            }}
            
            QLabel[alert="info"] {{
                color: {self.COLORS['info']};
            }}
            
            /* Custom code editor styling */
            QPlainTextEdit[monospace="true"] {{
                font-family: {self.FONTS['monospace']['family']};
                font-size: {self.FONTS['monospace']['size']}pt;
                font-weight: {self.FONTS['monospace']['weight']};
                background-color: {self.COLORS['bg_secondary']};
                color: {self.COLORS['text_primary']};
                selection-background-color: {self.COLORS['accent_primary']};
            }}
            
            /* Simple Toggle Switch */
            QPushButton[toggleswitch="true"] {{
                background-color: {self.COLORS['bg_tertiary']};
                color: {self.COLORS['text_primary']};
                border: 2px solid {self.COLORS['border_color']};
                border-radius: 14px;
                padding: 2px;
                min-width: 60px;
                min-height: 28px;
                text-align: right;
                padding-right: 10px;
            }}
            
            QPushButton[toggleswitch="true"]:checked {{
                background-color: {self.COLORS['accent_primary']};
                color: {self.COLORS['bg_secondary']};
                text-align: left;
                padding-left: 10px;
            }}
        """