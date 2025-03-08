#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, Qt

# Add project root to path to enable imports
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Import GUI modules
from gui.main_window import MainWindow
from gui.theme import Theme

def main():
    # Enable high DPI scaling
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("LLM Product Information Extractor")
    
    # Apply theme
    theme = Theme()
    app.setStyleSheet(theme.get_stylesheet())
    
    # Create and show main window
    main_window = MainWindow()
    main_window.show()
    
    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()