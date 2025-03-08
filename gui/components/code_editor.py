#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# gui/components/code_editor.py

from PySide6.QtWidgets import (
    QPlainTextEdit, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QComboBox, QPushButton, QFrame, QApplication,
    QFileDialog, QMenu, QToolBar, QSplitter
)
from PySide6.QtGui import (
    QColor, QTextCharFormat, QFont, QSyntaxHighlighter,
    QPainter, QTextFormat, QAction, QKeySequence, QTextCursor
)
from PySide6.QtCore import (
    Qt, QRegularExpression, Signal, QRect, QSize,
    QStringListModel, QPoint
)

import re
import json


class LineNumberArea(QWidget):
    """Widget for displaying line numbers in the code editor"""
    
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
    
    def sizeHint(self):
        """Calculate the ideal width for the line number area"""
        return QSize(self.editor.line_number_area_width(), 0)
    
    def paintEvent(self, event):
        """Paint the line numbers"""
        self.editor.lineNumberAreaPaintEvent(event)


class JsonSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for JSON content"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.highlighting_rules = []
        
        # Define formats for different token types
        self.formats = {
            'keyword': self._create_format('#c586c0'),  # Control keywords like true, false, null
            'string': self._create_format('#ce9178'),   # String values
            'number': self._create_format('#b5cea8'),   # Numbers
            'property': self._create_format('#9cdcfe'),  # Property names
            'curly': self._create_format('#d4d4d4'),    # Curly braces
            'square': self._create_format('#d4d4d4'),   # Square brackets
            'colon': self._create_format('#d4d4d4'),    # Colons
            'comma': self._create_format('#d4d4d4'),    # Commas
            'comment': self._create_format('#6a9955')   # Comments
        }
        
        # Keywords pattern (true, false, null)
        keywords = ["\\btrue\\b", "\\bfalse\\b", "\\bnull\\b"]
        for pattern in keywords:
            rule = {
                'pattern': QRegularExpression(pattern),
                'format': self.formats['keyword']
            }
            self.highlighting_rules.append(rule)
        
        # String pattern (with proper escaping)
        rule = {
            'pattern': QRegularExpression("\".*?((?<!\\\\)\"|$)"),
            'format': self.formats['string']
        }
        self.highlighting_rules.append(rule)
        
        # Property pattern (match property names in quotes)
        rule = {
            'pattern': QRegularExpression("\"[^\"]*\"(?=\\s*:)"),
            'format': self.formats['property']
        }
        self.highlighting_rules.append(rule)
        
        # Number pattern
        rule = {
            'pattern': QRegularExpression("\\b\\d+(\\.\\d+)?([eE][-+]?\\d+)?\\b"),
            'format': self.formats['number']
        }
        self.highlighting_rules.append(rule)
        
        # Curly braces
        rule = {
            'pattern': QRegularExpression("[{}]"),
            'format': self.formats['curly']
        }
        self.highlighting_rules.append(rule)
        
        # Square brackets
        rule = {
            'pattern': QRegularExpression("[\\[\\]]"),
            'format': self.formats['square']
        }
        self.highlighting_rules.append(rule)
        
        # Colons
        rule = {
            'pattern': QRegularExpression(":"),
            'format': self.formats['colon']
        }
        self.highlighting_rules.append(rule)
        
        # Commas
        rule = {
            'pattern': QRegularExpression(","),
            'format': self.formats['comma']
        }
        self.highlighting_rules.append(rule)
        
        # Comments (not valid in JSON, but may be in relaxed formats)
        rule = {
            'pattern': QRegularExpression("//.*$|/\\*.*\\*/"),
            'format': self.formats['comment']
        }
        self.highlighting_rules.append(rule)
    
    def _create_format(self, color, style=None):
        """
        Create a text format with specified color and optional style
        
        Args:
            color: Color for the text (hex string or QColor)
            style: Optional font style
            
        Returns:
            QTextCharFormat: The created format
        """
        _color = QColor(color)
        _format = QTextCharFormat()
        _format.setForeground(_color)
        if style:
            _format.setFontWeight(style)
        return _format
    
    def highlightBlock(self, text):
        """Apply highlighting to the given block of text"""
        # Apply regular expression rules
        for rule in self.highlighting_rules:
            expression = rule['pattern']
            format = rule['format']
            
            match_iterator = expression.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)


class PromptSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for prompt templates with variables"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.highlighting_rules = []
        
        # Define formats for different token types
        self.formats = {
            'variable': self._create_format('#569cd6', QFont.Bold),  # {variable} placeholders
            'instruction': self._create_format('#c586c0'),  # <instruction> tags
            'comment': self._create_format('#6a9955'),      # Comments
            'heading': self._create_format('#f1c40f', QFont.Bold),  # Markdown headings
            'emphasis': self._create_format('#b5cea8'),     # Markdown *emphasis*
            'strong': self._create_format('#b5cea8', QFont.Bold),  # Markdown **strong**
            'list': self._create_format('#4ec9b0'),         # Markdown lists
            'code': self._create_format('#ce9178')          # Markdown code blocks
        }
        
        # Variable placeholders like {text} or {variable_name}
        rule = {
            'pattern': QRegularExpression("{[a-zA-Z0-9_]+}"),
            'format': self.formats['variable']
        }
        self.highlighting_rules.append(rule)
        
        # XML/HTML-like instruction tags
        rule = {
            'pattern': QRegularExpression("<[^>]+>"),
            'format': self.formats['instruction']
        }
        self.highlighting_rules.append(rule)
        
        # Comments
        rule = {
            'pattern': QRegularExpression("//.*$|/\\*.*\\*/"),
            'format': self.formats['comment']
        }
        self.highlighting_rules.append(rule)
        
        # Markdown headings
        rule = {
            'pattern': QRegularExpression("^#+ .*$"),
            'format': self.formats['heading']
        }
        self.highlighting_rules.append(rule)
        
        # Markdown emphasis (*text*)
        rule = {
            'pattern': QRegularExpression("\\*[^*\n]+\\*"),
            'format': self.formats['emphasis']
        }
        self.highlighting_rules.append(rule)
        
        # Markdown strong (**text**)
        rule = {
            'pattern': QRegularExpression("\\*\\*[^*\n]+\\*\\*"),
            'format': self.formats['strong']
        }
        self.highlighting_rules.append(rule)
        
        # Markdown lists
        rule = {
            'pattern': QRegularExpression("^\\s*[\\*\\-\\+] .*$"),
            'format': self.formats['list']
        }
        self.highlighting_rules.append(rule)
        
        # Numbered lists
        rule = {
            'pattern': QRegularExpression("^\\s*\\d+\\. .*$"),
            'format': self.formats['list']
        }
        self.highlighting_rules.append(rule)
        
        # Backtick code spans
        rule = {
            'pattern': QRegularExpression("`[^`\n]+`"),
            'format': self.formats['code']
        }
        self.highlighting_rules.append(rule)
    
    def _create_format(self, color, weight=None):
        """
        Create a text format with the specified color and optional weight
        
        Args:
            color: Color for the text (hex string or QColor)
            weight: Optional font weight
            
        Returns:
            QTextCharFormat: The created format
        """
        _color = QColor(color)
        _format = QTextCharFormat()
        _format.setForeground(_color)
        if weight:
            _format.setFontWeight(weight)
        return _format
    
    def highlightBlock(self, text):
        """Apply highlighting to the given block of text"""
        # Apply regular expression rules
        for rule in self.highlighting_rules:
            expression = rule['pattern']
            format = rule['format']
            
            match_iterator = expression.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)
        
        # Handle code blocks
        if text.startswith("```") or text.endswith("```"):
            self.setFormat(0, len(text), self.formats['code'])


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Python code"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.highlighting_rules = []
        
        # Define formats for different token types
        self.formats = {
            'keyword': self._create_format('#569cd6', QFont.Bold),  # Python keywords
            'builtin': self._create_format('#4ec9b0'),  # Built-in functions
            'class': self._create_format('#4ec9b0', QFont.Bold),  # Class names
            'function': self._create_format('#dcdcaa'),  # Function definitions
            'string': self._create_format('#ce9178'),   # String literals
            'comment': self._create_format('#6a9955'),  # Comments
            'self': self._create_format('#569cd6'),     # Self parameter
            'number': self._create_format('#b5cea8'),   # Number literals
            'decorator': self._create_format('#c586c0')  # Decorators
        }
        
        # Python keywords
        keywords = [
            "\\band\\b", "\\bas\\b", "\\bassert\\b", "\\bbreak\\b", "\\bclass\\b",
            "\\bcontinue\\b", "\\bdef\\b", "\\bdel\\b", "\\belif\\b", "\\belse\\b",
            "\\bexcept\\b", "\\bfalse\\b", "\\bfinally\\b", "\\bfor\\b", "\\bfrom\\b",
            "\\bglobal\\b", "\\bif\\b", "\\bimport\\b", "\\bin\\b", "\\bis\\b",
            "\\blambda\\b", "\\bnonlocal\\b", "\\bnot\\b", "\\bor\\b", "\\bpass\\b",
            "\\braise\\b", "\\breturn\\b", "\\btrue\\b", "\\btry\\b", "\\bwhile\\b",
            "\\bwith\\b", "\\byield\\b", "\\bNone\\b"
        ]
        
        # Built-in functions
        builtins = [
            "\\babs\\b", "\\ball\\b", "\\bany\\b", "\\bbin\\b", "\\bbool\\b",
            "\\bchr\\b", "\\bcomplex\\b", "\\bdict\\b", "\\bdivmod\\b", "\\benumerate\\b",
            "\\bfilter\\b", "\\bfloat\\b", "\\bformat\\b", "\\bfrozenset\\b", "\\bgetattr\\b",
            "\\bhash\\b", "\\bhelp\\b", "\\bhex\\b", "\\bint\\b", "\\bisinstance\\b",
            "\\bissubclass\\b", "\\biter\\b", "\\blen\\b", "\\blist\\b", "\\bmap\\b",
            "\\bmax\\b", "\\bmin\\b", "\\bnext\\b", "\\bobject\\b", "\\boct\\b",
            "\\bopen\\b", "\\bord\\b", "\\bpow\\b", "\\bprint\\b", "\\brange\\b",
            "\\brepr\\b", "\\breversed\\b", "\\bround\\b", "\\bset\\b", "\\bsetattr\\b",
            "\\bslice\\b", "\\bsorted\\b", "\\bstr\\b", "\\bsum\\b", "\\bsuper\\b",
            "\\btuple\\b", "\\btype\\b", "\\bvars\\b", "\\bzip\\b", "\\b__import__\\b"
        ]
        
        # Add keyword rules
        for pattern in keywords:
            rule = {
                'pattern': QRegularExpression(pattern),
                'format': self.formats['keyword']
            }
            self.highlighting_rules.append(rule)
        
        # Add built-in function rules
        for pattern in builtins:
            rule = {
                'pattern': QRegularExpression(pattern),
                'format': self.formats['builtin']
            }
            self.highlighting_rules.append(rule)
        
        # Class name (starts with uppercase letter)
        rule = {
            'pattern': QRegularExpression("\\b[A-Z][a-zA-Z0-9_]*\\b"),
            'format': self.formats['class']
        }
        self.highlighting_rules.append(rule)
        
        # Function definitions
        rule = {
            'pattern': QRegularExpression("\\bdef\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\("),
            'format': self.formats['function']
        }
        self.highlighting_rules.append(rule)
        
        # Self parameter
        rule = {
            'pattern': QRegularExpression("\\bself\\b"),
            'format': self.formats['self']
        }
        self.highlighting_rules.append(rule)
        
        # Double-quoted string
        rule = {
            'pattern': QRegularExpression("\".*?\""),
            'format': self.formats['string']
        }
        self.highlighting_rules.append(rule)
        
        # Single-quoted string
        rule = {
            'pattern': QRegularExpression("'.*?'"),
            'format': self.formats['string']
        }
        self.highlighting_rules.append(rule)
        
        # Single-line comment
        rule = {
            'pattern': QRegularExpression("#.*$"),
            'format': self.formats['comment']
        }
        self.highlighting_rules.append(rule)
        
        # Number literals
        rule = {
            'pattern': QRegularExpression("\\b[0-9]+\\b"),
            'format': self.formats['number']
        }
        self.highlighting_rules.append(rule)
        
        # Floating point numbers
        rule = {
            'pattern': QRegularExpression("\\b[0-9]+\\.[0-9]+\\b"),
            'format': self.formats['number']
        }
        self.highlighting_rules.append(rule)
        
        # Decorator
        rule = {
            'pattern': QRegularExpression("@[A-Za-z0-9_\\.]+"),
            'format': self.formats['decorator']
        }
        self.highlighting_rules.append(rule)
        
        # Multi-line strings (simple version, not accurate for all cases)
        self.triple_double_quote_regex = QRegularExpression('"""(?!.*""").*')
        self.triple_single_quote_regex = QRegularExpression("'''(?!.*''').*")
        
    def _create_format(self, color, weight=None):
        """Create a text format with the specified color and optional weight"""
        _color = QColor(color)
        _format = QTextCharFormat()
        _format.setForeground(_color)
        if weight:
            _format.setFontWeight(weight)
        return _format
    
    def highlightBlock(self, text):
        """Apply highlighting to the given block of text"""
        # Apply regular expression rules
        for rule in self.highlighting_rules:
            expression = rule['pattern']
            format = rule['format']
            
            match_iterator = expression.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)
        
        # Handle multi-line strings (very simplified)
        if '"""' in text or "'''" in text:
            # Check for triple-double-quotes
            match = self.triple_double_quote_regex.match(text)
            if match.hasMatch():
                self.setFormat(match.capturedStart(), match.capturedLength(), self.formats['string'])
            
            # Check for triple-single-quotes
            match = self.triple_single_quote_regex.match(text)
            if match.hasMatch():
                self.setFormat(match.capturedStart(), match.capturedLength(), self.formats['string'])


class CodeEditor(QPlainTextEdit):
    """
    A code editor widget with syntax highlighting, line numbers,
    and various editing features useful for prompts, JSON, and Python.
    """
    
    # Signal to notify when content has changed
    content_changed = Signal()
    
    # Available syntax highlighting modes
    HIGHLIGHT_MODES = ["None", "Prompt", "JSON", "Python"]
    
    def __init__(self, parent=None, highlight_mode="None"):
        """
        Initialize the code editor
        
        Args:
            parent: Parent widget
            highlight_mode: Syntax highlighting mode ("None", "Prompt", "JSON", "Python")
        """
        super().__init__(parent)
        
        # Setup editor properties
        font = QFont("Consolas, 'Courier New', monospace")
        font.setPointSize(10)
        self.setFont(font)
        
        # Set tab stop width (4 spaces)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)
        
        # Create line number area
        self.line_number_area = LineNumberArea(self)
        
        # Create highlighter (initially None)
        self.highlighter = None
        
        # Set highlight mode
        self.set_highlight_mode(highlight_mode)
        
        # Connect signals
        self.updateRequest.connect(self.update_line_number_area)
        self.textChanged.connect(self.content_changed)
        
        # Update line number area width
        self.update_line_number_area_width()
        
        # Add right margin line at column 80
        self.show_right_margin = True
        self.right_margin_column = 80
        
        # Create toolbar actions
        self._setup_actions()
    
    def _setup_actions(self):
        """Set up editor actions for toolbar integration"""
        self.actions = {}
        
        # Undo/Redo
        self.actions['undo'] = self.createAction("Undo", "Undo the last action", 
                                                QKeySequence.Undo, self.undo)
        self.actions['redo'] = self.createAction("Redo", "Redo the last undone action", 
                                                QKeySequence.Redo, self.redo)
        
        # Cut/Copy/Paste
        self.actions['cut'] = self.createAction("Cut", "Cut the selected text", 
                                               QKeySequence.Cut, self.cut)
        self.actions['copy'] = self.createAction("Copy", "Copy the selected text", 
                                                QKeySequence.Copy, self.copy)
        self.actions['paste'] = self.createAction("Paste", "Paste text from clipboard", 
                                                 QKeySequence.Paste, self.paste)
        
        # Selection
        self.actions['select_all'] = self.createAction("Select All", "Select all text", 
                                                      QKeySequence.SelectAll, self.selectAll)
        
        # Indentation
        self.actions['indent'] = self.createAction("Indent", "Increase indentation", 
                                                  QKeySequence("Tab"), self.indent)
        self.actions['unindent'] = self.createAction("Unindent", "Decrease indentation", 
                                                    QKeySequence("Shift+Tab"), self.unindent)
        
        # Code formatting
        self.actions['format'] = self.createAction("Format", "Format code", 
                                                 QKeySequence("Ctrl+Shift+F"), self.format_code)
        
        # Toggle comment
        self.actions['toggle_comment'] = self.createAction("Toggle Comment", "Toggle comment for selection", 
                                                         QKeySequence("Ctrl+/"), self.toggle_comment)
    
    def createAction(self, text, tooltip, shortcut, slot):
        """Helper to create a QAction"""
        action = QAction(text, self)
        action.setToolTip(tooltip)
        action.setShortcut(shortcut)
        action.triggered.connect(slot)
        return action
    
    def create_toolbar(self):
        """Create a toolbar with editor actions"""
        toolbar = QToolBar("Editor", self)
        
        toolbar.addAction(self.actions['undo'])
        toolbar.addAction(self.actions['redo'])
        toolbar.addSeparator()
        
        toolbar.addAction(self.actions['cut'])
        toolbar.addAction(self.actions['copy'])
        toolbar.addAction(self.actions['paste'])
        toolbar.addSeparator()
        
        toolbar.addAction(self.actions['indent'])
        toolbar.addAction(self.actions['unindent'])
        toolbar.addSeparator()
        
        toolbar.addAction(self.actions['format'])
        toolbar.addAction(self.actions['toggle_comment'])
        
        return toolbar
    
    def line_number_area_width(self):
        """Calculate the width needed for the line number area"""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space
    
    def update_line_number_area_width(self):
        """Update the viewport margins to accommodate the line number area"""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
    
    def update_line_number_area(self, rect, dy):
        """Update the line number area when needed"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()
    
    def resizeEvent(self, event):
        """Handle resize events to adjust the line number area"""
        super().resizeEvent(event)
        
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(),
                                              self.line_number_area_width(), cr.height()))
    
    def lineNumberAreaPaintEvent(self, event):
        """Paint the line number area"""
        painter = QPainter(self.line_number_area)
        
        # Fill background
        bg_color = self.palette().color(self.palette().Base)
        painter.fillRect(event.rect(), bg_color.darker(105))
        
        # Draw line numbers
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        
        # Line number color
        pen_color = self.palette().color(self.palette().Text)
        pen_color.setAlpha(130)  # Semi-transparent
        
        # Current line color
        current_line_color = QColor("#3b82f6")  # Blue
        
        # Get current line number
        current_line = self.textCursor().blockNumber()
        
        # Draw for each visible block
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                
                # Use different color for current line
                if block_number == current_line:
                    painter.setPen(current_line_color)
                else:
                    painter.setPen(pen_color)
                
                # Draw the line number right-aligned
                width = self.line_number_area.width() - 5
                height = self.fontMetrics().height()
                painter.drawText(0, top, width, height, Qt.AlignRight, number)
            
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1
    
    def paintEvent(self, event):
        """Handle paint events to add custom drawing to the editor"""
        super().paintEvent(event)
        
        # Draw right margin line if enabled
        if self.show_right_margin:
            painter = QPainter(self.viewport())
            margin_x = self.fontMetrics().horizontalAdvance(' ') * self.right_margin_column
            margin_x -= self.horizontalScrollBar().value()
            
            # Only draw if visible
            if margin_x > 0 and margin_x < self.viewport().width():
                margin_color = QColor("#4b5563")  # Gray
                margin_color.setAlpha(50)
                
                painter.setPen(margin_color)
                painter.drawLine(margin_x, 0, margin_x, self.viewport().height())
    
    def set_highlight_mode(self, mode):
        """
        Set the syntax highlighting mode
        
        Args:
            mode: Highlighting mode ("None", "Prompt", "JSON", "Python")
        """
        # Remove existing highlighter if any
        if self.highlighter:
            self.highlighter.setDocument(None)
            self.highlighter = None
        
        # Create new highlighter based on mode
        if mode == "Prompt":
            self.highlighter = PromptSyntaxHighlighter(self.document())
        elif mode == "JSON":
            self.highlighter = JsonSyntaxHighlighter(self.document())
        elif mode == "Python":
            self.highlighter = PythonSyntaxHighlighter(self.document())
        
        # Update document to refresh highlighting
        if self.highlighter:
            self.highlighter.rehighlight()
    
    def indent(self):
        """Indent the selected text"""
        cursor = self.textCursor()
        
        if cursor.hasSelection():
            # Get the selected text
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            
            # Make sure start is at the beginning and end is at the end
            cursor.setPosition(start)
            start_block = cursor.blockNumber()
            
            cursor.setPosition(end)
            end_block = cursor.blockNumber()
            
            # Start a full edit operation
            cursor.beginEditBlock()
            
            # Move to start block
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.StartOfBlock)
            
            # Add indentation to each line
            for _ in range(start_block, end_block + 1):
                cursor.insertText("    ")  # 4 spaces for indentation
                if not cursor.movePosition(QTextCursor.NextBlock) and cursor.blockNumber() == end_block:
                    break
            
            cursor.endEditBlock()
        else:
            # If no selection, just insert spaces at cursor position
            cursor.insertText("    ")
    
    def unindent(self):
        """Decrease indentation of the selected text"""
        cursor = self.textCursor()
        
        if cursor.hasSelection():
            # Get the selected text
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            
            # Make sure start is at the beginning and end is at the end
            cursor.setPosition(start)
            start_block = cursor.blockNumber()
            
            cursor.setPosition(end)
            end_block = cursor.blockNumber()
            
            # Start a full edit operation
            cursor.beginEditBlock()
            
            # Move to start block
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.StartOfBlock)
            
            # Remove indentation from each line
            for _ in range(start_block, end_block + 1):
                line_text = cursor.block().text()
                
                # Check for spaces or tabs at the beginning
                if line_text.startswith("    "):
                    # Remove four spaces
                    cursor.deleteChar()
                    cursor.deleteChar()
                    cursor.deleteChar()
                    cursor.deleteChar()
                elif line_text.startswith("\t"):
                    # Remove one tab
                    cursor.deleteChar()
                elif line_text.startswith(" "):
                    # Remove up to 4 leading spaces
                    for i in range(min(4, len(line_text) - len(line_text.lstrip(" ")))):
                        cursor.deleteChar()
                
                if not cursor.movePosition(QTextCursor.NextBlock) and cursor.blockNumber() == end_block:
                    break
            
            cursor.endEditBlock()
    
    def toggle_comment(self):
        """Toggle comments for the selected text"""
        cursor = self.textCursor()
        
        if not cursor.hasSelection():
            # If no selection, select the current line
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)
        
        # Get the selected text
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        
        # Make sure start is at the beginning and end is at the end
        cursor.setPosition(start)
        start_block = cursor.blockNumber()
        
        cursor.setPosition(end)
        end_block = cursor.blockNumber()
        
        # Start a full edit operation
        cursor.beginEditBlock()
        
        # Determine comment character based on highlight mode
        if self.highlighter and isinstance(self.highlighter, PythonSyntaxHighlighter):
            comment_str = "# "
        else:
            comment_str = "// "
        
        # Check if all selected lines are already commented
        all_commented = True
        
        # Move to start block
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.StartOfBlock)
        
        # Check each line
        for _ in range(start_block, end_block + 1):
            line_text = cursor.block().text().lstrip()
            if not (line_text.startswith("# ") or line_text.startswith("//") or line_text.startswith("/*")):
                all_commented = False
                break
            
            if not cursor.movePosition(QTextCursor.NextBlock) and cursor.blockNumber() == end_block:
                break
        
        # Move back to start block
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.StartOfBlock)
        
        # Toggle comments on each line
        for _ in range(start_block, end_block + 1):
            line_start = cursor.position()
            line_text = cursor.block().text()
            indentation = len(line_text) - len(line_text.lstrip())
            
            # Move to first non-whitespace character
            for _ in range(indentation):
                cursor.movePosition(QTextCursor.Right)
            
            if all_commented:
                # Remove comment
                if line_text.lstrip().startswith("# "):
                    cursor.deleteChar()
                    cursor.deleteChar()
                elif line_text.lstrip().startswith("// "):
                    cursor.deleteChar()
                    cursor.deleteChar()
                    cursor.deleteChar()
                elif line_text.lstrip().startswith("/*"):
                    # Delete until */
                    end_pos = line_text.find("*/", indentation + 2)
                    if end_pos >= 0:
                        for _ in range(end_pos - line_start + 2):
                            cursor.deleteChar()
            else:
                # Add comment
                cursor.insertText(comment_str)
            
            if not cursor.movePosition(QTextCursor.NextBlock) and cursor.blockNumber() == end_block:
                break
        
        cursor.endEditBlock()
    
    def format_code(self):
        """Format the code according to the current highlighting mode"""
        # Get current text
        text = self.toPlainText()
        
        # Format based on highlight mode
        if self.highlighter and isinstance(self.highlighter, JsonSyntaxHighlighter):
            # Format JSON
            try:
                parsed = json.loads(text)
                formatted = json.dumps(parsed, indent=4)
                self.setPlainText(formatted)
            except json.JSONDecodeError as e:
                # Show error without changing text
                cursor = self.textCursor()
                current_pos = cursor.position()
                
                # Try to position cursor at error location
                try:
                    line_no = e.lineno - 1
                    col_no = e.colno - 1
                    
                    cursor.setPosition(0)
                    for _ in range(line_no):
                        cursor.movePosition(QTextCursor.NextBlock)
                    
                    for _ in range(col_no):
                        cursor.movePosition(QTextCursor.Right)
                    
                    self.setTextCursor(cursor)
                except:
                    # If positioning fails, keep current position
                    cursor.setPosition(current_pos)
                    self.setTextCursor(cursor)
                
                # Show error in status bar if available
                if hasattr(self, 'status_message'):
                    self.status_message.emit(f"JSON Error: {str(e)}")
                
        elif self.highlighter and isinstance(self.highlighter, PythonSyntaxHighlighter):
            # Format Python (simplified)
            # In a real implementation, you might use the 'black' or 'autopep8' library
            lines = text.split('\n')
            formatted_lines = []
            indent_level = 0
            
            for line in lines:
                # Strip existing indentation
                stripped = line.lstrip()
                
                # Skip empty lines
                if not stripped:
                    formatted_lines.append("")
                    continue
                
                # Adjust indent level based on line content
                if any(stripped.startswith(token) for token in ['else:', 'elif ', 'except:', 'finally:', 'except ']):
                    # These continue a block at the same level as the previous block
                    indent_level = max(0, indent_level - 1)
                
                # Calculate indentation
                indentation = '    ' * indent_level
                
                # Add indented line
                formatted_lines.append(indentation + stripped)
                
                # Adjust indent level for next line
                if stripped.endswith(':'):
                    indent_level += 1
                elif any(token in stripped for token in ['return ', 'break', 'continue', 'raise ', 'pass']):
                    indent_level = max(0, indent_level - 1)
            
            # Replace text
            self.setPlainText('\n'.join(formatted_lines))
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        # Auto-indentation
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.handleReturnKey()
            return
        # Indent with Tab key
        elif event.key() == Qt.Key_Tab and self.textCursor().hasSelection():
            self.indent()
            return
        # Unindent with Shift+Tab
        elif event.key() == Qt.Key_Backtab:
            self.unindent()
            return
        # Handle other keys normally
        super().keyPressEvent(event)
    
    def handleReturnKey(self):
        """Handle Return key press with auto-indentation"""
        cursor = self.textCursor()
        
        # Get current line text before cursor
        cursor.movePosition(QTextCursor.StartOfBlock)
        line_start_pos = cursor.position()
        cursor = self.textCursor()  # Get cursor position again to restore it
        
        current_line = self.document().findBlockByNumber(cursor.blockNumber()).text()
        current_indentation = len(current_line) - len(current_line.lstrip())
        
        # Create indentation string
        indentation = ' ' * current_indentation
        
        # Determine if we should increase indentation (line ends with ':')
        if current_line.rstrip().endswith(':'):
            indentation += '    '  # Add 4 spaces
        
        # Insert newline and indentation
        cursor.insertText('\n' + indentation)
    
    def contextMenuEvent(self, event):
        """Customize the context menu"""
        menu = QMenu(self)
        
        # Add standard actions
        menu.addAction(self.actions['undo'])
        menu.addAction(self.actions['redo'])
        menu.addSeparator()
        menu.addAction(self.actions['cut'])
        menu.addAction(self.actions['copy'])
        menu.addAction(self.actions['paste'])
        menu.addAction(self.actions['select_all'])
        menu.addSeparator()
        
        # Add code formatting actions
        menu.addAction(self.actions['indent'])
        menu.addAction(self.actions['unindent'])
        menu.addAction(self.actions['toggle_comment'])
        menu.addAction(self.actions['format'])
        
        # Add syntax highlighting submenu
        highlight_menu = menu.addMenu("Syntax Highlighting")
        for mode in self.HIGHLIGHT_MODES:
            action = QAction(mode, self)
            action.setCheckable(True)
            
            # Check current mode
            if (self.highlighter is None and mode == "None") or \
               (isinstance(self.highlighter, PromptSyntaxHighlighter) and mode == "Prompt") or \
               (isinstance(self.highlighter, JsonSyntaxHighlighter) and mode == "JSON") or \
               (isinstance(self.highlighter, PythonSyntaxHighlighter) and mode == "Python"):
                action.setChecked(True)
            
            action.triggered.connect(lambda checked, m=mode: self.set_highlight_mode(m))
            highlight_menu.addAction(action)
        
        # Show the menu
        menu.exec(event.globalPos())
    
    def save_to_file(self, file_path=None):
        """
        Save content to a file
        
        Args:
            file_path: Path to save the file (if None, opens a file dialog)
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        if file_path is None:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save File", "", 
                "All Files (*);;Text Files (*.txt);;Python Files (*.py);;JSON Files (*.json)"
            )
            
            if not file_path:
                return False
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.toPlainText())
            return True
        except Exception as e:
            # Show error if applicable
            if hasattr(self, 'status_message'):
                self.status_message.emit(f"Error saving file: {str(e)}")
            return False
    
    def load_from_file(self, file_path=None):
        """
        Load content from a file
        
        Args:
            file_path: Path to load the file from (if None, opens a file dialog)
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        if file_path is None:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Open File", "", 
                "All Files (*);;Text Files (*.txt);;Python Files (*.py);;JSON Files (*.json)"
            )
            
            if not file_path:
                return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.setPlainText(f.read())
            
            # Try to determine and set highlight mode based on file extension
            if file_path.endswith('.py'):
                self.set_highlight_mode("Python")
            elif file_path.endswith('.json'):
                self.set_highlight_mode("JSON")
            elif file_path.endswith('.md') or file_path.endswith('.txt'):
                self.set_highlight_mode("Prompt")
            
            return True
        except Exception as e:
            # Show error if applicable
            if hasattr(self, 'status_message'):
                self.status_message.emit(f"Error loading file: {str(e)}")
            return False


class CodeEditorWidget(QWidget):
    """A complete code editor widget with toolbar and additional controls"""
    
    # Signal when code changes
    code_changed = Signal(str)
    
    def __init__(self, parent=None, highlight_mode="None"):
        """
        Initialize the code editor widget
        
        Args:
            parent: Parent widget
            highlight_mode: Syntax highlighting mode
        """
        super().__init__(parent)
        
        # Setup UI
        self.setup_ui(highlight_mode)
        
        # Connect signals
        self.editor.content_changed.connect(self.on_code_changed)
    
    def setup_ui(self, highlight_mode):
        """Setup the UI components"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Control bar at top
        control_bar = QHBoxLayout()
        control_bar.setContentsMargins(2, 2, 2, 2)
        
        # Highlighting mode combo
        self.highlight_label = QLabel("Highlighting:")
        control_bar.addWidget(self.highlight_label)
        
        self.highlight_combo = QComboBox()
        self.highlight_combo.addItems(CodeEditor.HIGHLIGHT_MODES)
        self.highlight_combo.setCurrentText(highlight_mode)
        self.highlight_combo.currentTextChanged.connect(self.change_highlight_mode)
        control_bar.addWidget(self.highlight_combo)
        
        # Add buttons for common actions
        self.format_button = QPushButton("Format")
        self.format_button.setToolTip("Format code according to syntax rules")
        self.format_button.clicked.connect(self.format_code)
        control_bar.addWidget(self.format_button)
        
        # Add spacer
        control_bar.addStretch()
        
        # File buttons
        self.open_button = QPushButton("Open")
        self.open_button.setToolTip("Open a file")
        self.open_button.clicked.connect(self.load_from_file)
        control_bar.addWidget(self.open_button)
        
        self.save_button = QPushButton("Save")
        self.save_button.setToolTip("Save to a file")
        self.save_button.clicked.connect(self.save_to_file)
        control_bar.addWidget(self.save_button)
        
        layout.addLayout(control_bar)
        
        # Add editor
        self.editor = CodeEditor(self, highlight_mode)
        layout.addWidget(self.editor)
    
    def set_code(self, code):
        """Set the code in the editor"""
        self.editor.setPlainText(code)
    
    def get_code(self):
        """Get the code from the editor"""
        return self.editor.toPlainText()
    
    def on_code_changed(self):
        """Handle code changes"""
        self.code_changed.emit(self.get_code())
    
    def change_highlight_mode(self, mode):
        """Change the highlighting mode"""
        self.editor.set_highlight_mode(mode)
    
    def format_code(self):
        """Format the code"""
        self.editor.format_code()
    
    def save_to_file(self):
        """Save content to a file"""
        self.editor.save_to_file()
    
    def load_from_file(self):
        """Load content from a file"""
        result = self.editor.load_from_file()
        if result:
            # Update highlight mode combo to match
            if isinstance(self.editor.highlighter, PromptSyntaxHighlighter):
                self.highlight_combo.setCurrentText("Prompt")
            elif isinstance(self.editor.highlighter, JsonSyntaxHighlighter):
                self.highlight_combo.setCurrentText("JSON")
            elif isinstance(self.editor.highlighter, PythonSyntaxHighlighter):
                self.highlight_combo.setCurrentText("Python")
            else:
                self.highlight_combo.setCurrentText("None")


# Example usage if run as a script
if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    
    # Example JSON for testing
    example_json = """{
        "name": "Product Extractor",
        "version": "1.0.0",
        "description": "LLM-based tool for extracting product information",
        "components": [
            {"name": "GUI", "status": "completed"},
            {"name": "Backend", "status": "in_progress"}
        ],
        "settings": {
            "theme": "dark",
            "max_threads": 4
        }
    }"""
    
    # Example Python for testing
    example_python = """def process_product(product_id, file_path):
    \"\"\"Process a product and extract information.\"\"\"
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract information
    result = extract_info(content)
    
    # Save the result
    save_result(product_id, result)
    
    return result

class ProductResult:
    def __init__(self, product_id):
        self.product_id = product_id
        self.data = {}
    
    def add_data(self, key, value):
        self.data[key] = value
        
    def __str__(self):
        return f"ProductResult({self.product_id})"
"""
    
    # Example prompt for testing
    example_prompt = """Analyze the following product documentation and extract compatibility information.

Product Documentation:
{text}

Extract all compatibility relationships between this product and other products.
For each relationship, identify:
1. The relation type (e.g., "works with", "compatible with", "fits", "replaces")
2. The related product (name, article number if available)
3. Any context that explains the compatibility relationship

Provide the results in the following JSON structure:
{
  "relations": [
    {
      "relation_type": "relation type",
      "related_product": "product name or ID",
      "context": "context about the compatibility",
      "confidence": 0.8
    }
  ]
}

Make sure to include a confidence score between 0 and 1 for each relation.
If no compatibility information is found, return an empty relations array.
"""
    
    # Create widget with tabs for different examples
    main_widget = QWidget()
    main_layout = QVBoxLayout(main_widget)
    
    # Create tab widget
    tabs = QTabWidget()
    
    # JSON Tab
    json_editor = CodeEditorWidget(highlight_mode="JSON")
    json_editor.set_code(example_json)
    tabs.addTab(json_editor, "JSON Example")
    
    # Python Tab
    python_editor = CodeEditorWidget(highlight_mode="Python")
    python_editor.set_code(example_python)
    tabs.addTab(python_editor, "Python Example")
    
    # Prompt Tab
    prompt_editor = CodeEditorWidget(highlight_mode="Prompt")
    prompt_editor.set_code(example_prompt)
    tabs.addTab(prompt_editor, "Prompt Example")
    
    main_layout.addWidget(tabs)
    
    # Set window properties
    main_widget.setWindowTitle("Code Editor Demo")
    main_widget.resize(800, 600)
    main_widget.show()
    
    sys.exit(app.exec())