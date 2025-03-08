#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ./ visualisering/visualiseringshanterare.py

"""
Avancerad loggnings- och visualiseringshanterare för LLM-baserad Produktinformationsextraktor

Denna modul innehåller:
1. ColoredLogger - En utökad loggningsklass med färgkodade meddelanden
2. TerminalVisualizer - Kraftfull visualisering av data, status och framsteg i terminalen
3. ProgressTracker - Spårning och visualisering av framsteg för långvariga operationer

Modulen möjliggör detaljerad och visuellt distinkt loggning av olika typer av information
i terminalen, vilket gör det lättare att följa komplexa arbetsflöden i realtid.
"""

import os
import sys
import time
import json
import logging
import threading
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union, Callable

# Försök importera rich-paketet för avancerad terminalformattering
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    from rich.logging import RichHandler
    from rich.layout import Layout
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Fallback terminalfärger om rich inte är tillgängligt
class TermColors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


class LogCategory(Enum):
    """Kategorier för loggmeddelanden"""
    GENERAL = "general"
    LLM_PROMPT = "prompt"
    LLM_RESPONSE = "llm_response"
    WORKFLOW = "workflow"
    REPORT = "report"
    ERROR = "error"
    WARNING = "warning"
    RETRY = "retry"
    EXTRACTION = "extraction"
    DEBUG = "debug"


class ColoredFormatter(logging.Formatter):
    """
    Anpassad formatterare för färgkodad loggning baserad på nivå och kategori
    """
    
    def __init__(self, fmt: str = None, color_config: Dict[str, str] = None):
        """
        Initierar formatteraren
        
        Args:
            fmt: Formatteringsformat
            color_config: Färgkonfiguration för olika kategorier
        """
        super().__init__(fmt or "%(asctime)s - %(levelname)s - %(message)s")
        
        # Standardfärgkonfiguration om ingen anges
        self.color_config = color_config or {
            LogCategory.GENERAL.value: TermColors.WHITE,
            LogCategory.LLM_PROMPT.value: TermColors.BLUE,
            LogCategory.LLM_RESPONSE.value: TermColors.GREEN,
            LogCategory.WORKFLOW.value: TermColors.CYAN,
            LogCategory.REPORT.value: TermColors.MAGENTA,
            LogCategory.ERROR.value: TermColors.RED,
            LogCategory.WARNING.value: TermColors.YELLOW,
            LogCategory.RETRY.value: TermColors.BRIGHT_RED,
            LogCategory.EXTRACTION.value: TermColors.BRIGHT_CYAN,
            LogCategory.DEBUG.value: TermColors.BRIGHT_BLACK
        }
        
        # Nivåfärger för standardloggar
        self.level_colors = {
            logging.DEBUG: TermColors.WHITE,
            logging.INFO: TermColors.BRIGHT_WHITE,
            logging.WARNING: TermColors.YELLOW,
            logging.ERROR: TermColors.RED,
            logging.CRITICAL: TermColors.BRIGHT_RED + TermColors.BOLD
        }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formaterar logposten med färger
        
        Args:
            record: Loggningsposten att formatera
            
        Returns:
            str: Det formaterade och färgkodade meddelandet
        """
        # Kontrollera om loggen har en kategori
        category = getattr(record, 'category', LogCategory.GENERAL.value)
        
        # Välj färg baserat på kategori eller nivå
        if category in self.color_config:
            color = self.color_config[category]
        else:
            color = self.level_colors.get(record.levelno, TermColors.WHITE)
        
        # Formatera meddelandet
        formatted_message = super().format(record)
        
        # Lägg till färgkod och återställningskod
        return f"{color}{formatted_message}{TermColors.RESET}"


class ColoredLogger(logging.Logger):
    """
    Utökad loggningsklass med stöd för kategorier och färgkodning
    """
    
    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initierar loggaren
        
        Args:
            name: Loggarnamn
            level: Loggnivå
        """
        super().__init__(name, level)
        self.propagate = False  # Förhindra att meddelanden skickas till root-loggaren
    
    def _log_with_category(self, level: int, msg: str, category: LogCategory, *args, **kwargs) -> None:
        """
        Loggar ett meddelande med en specifik kategori
        
        Args:
            level: Loggnivå
            msg: Meddelandet att logga
            category: Kategori för meddelandet
            *args: Argument för formateringen
            **kwargs: Nyckelord för formateringen
        """
        if not self.isEnabledFor(level):
            return
        
        # Skapa en kopia av kwargs för att inte modifiera originalet
        extra = kwargs.pop('extra', {}).copy() if 'extra' in kwargs else {}
        extra['category'] = category.value
        
        # Logga med kategorin som extra-data
        super().log(level, msg, *args, extra=extra, **kwargs)
    
    def prompt(self, msg: str, *args, **kwargs) -> None:
        """Loggar ett LLM-prompt-meddelande"""
        self._log_with_category(logging.INFO, msg, LogCategory.LLM_PROMPT, *args, **kwargs)
    
    def llm_response(self, msg: str, *args, **kwargs) -> None:
        """Loggar ett LLM-svarsmeddelande"""
        self._log_with_category(logging.INFO, msg, LogCategory.LLM_RESPONSE, *args, **kwargs)
    
    def workflow(self, msg: str, *args, **kwargs) -> None:
        """Loggar ett arbetsflödesmeddelande"""
        self._log_with_category(logging.INFO, msg, LogCategory.WORKFLOW, *args, **kwargs)
    
    def report(self, msg: str, *args, **kwargs) -> None:
        """Loggar ett rapportmeddelande"""
        self._log_with_category(logging.INFO, msg, LogCategory.REPORT, *args, **kwargs)
    
    def retry(self, msg: str, *args, **kwargs) -> None:
        """Loggar ett återförsöksmeddelande"""
        self._log_with_category(logging.WARNING, msg, LogCategory.RETRY, *args, **kwargs)
    
    def extraction(self, msg: str, *args, **kwargs) -> None:
        """Loggar ett extraktionsmeddelande"""
        self._log_with_category(logging.INFO, msg, LogCategory.EXTRACTION, *args, **kwargs)


class TerminalVisualizer:
    """
    Klass för avancerad visualisering i terminalen
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initierar visualiseraren
        
        Args:
            config: Konfiguration för visualiseringen
        """
        self.config = config or {}
        self.use_rich = RICH_AVAILABLE and self.config.get('use_rich', True)
        
        # Initiera rich-komponenter om tillgängliga
        if self.use_rich:
            self.console = Console()
            self.live_displays = {}
        
        # Färgkonfiguration
        self.colors = self.config.get('colors', {
            LogCategory.LLM_PROMPT.value: "blue",
            LogCategory.LLM_RESPONSE.value: "green",
            LogCategory.WORKFLOW.value: "cyan",
            LogCategory.REPORT.value: "magenta",
            LogCategory.ERROR.value: "red",
            LogCategory.WARNING.value: "yellow",
            LogCategory.RETRY.value: "bright_red",
            LogCategory.EXTRACTION.value: "bright_cyan",
            LogCategory.DEBUG.value: "dim"
        })
        
        # Konfigurera loggning
        self.setup_logging()
    
    def setup_logging(self) -> None:
        """Konfigurerar loggning med rich eller ColoredFormatter"""
        # Registrera vår anpassade loggarklass
        logging.setLoggerClass(ColoredLogger)
        
        if self.use_rich:
            # Konfigurera rich-loggning
            logging.basicConfig(
                level=self.config.get('log_level', logging.INFO),
                format="%(message)s",
                datefmt="[%X]",
                handlers=[RichHandler(rich_tracebacks=True)]
            )
        else:
            # Konfigurera standardloggning med färger
            color_formatter = ColoredFormatter()
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(color_formatter)
            
            root_logger = logging.getLogger()
            root_logger.setLevel(self.config.get('log_level', logging.INFO))
            root_logger.addHandler(console_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Hämtar en logger med anpassad konfiguration
        
        Args:
            name: Loggarnamn
            
        Returns:
            ColoredLogger: En konfigurerad logginstans
        """
        return logging.getLogger(name)
    
    def display_json(self, data: Dict[str, Any], title: str = None) -> None:
        """
        Visar JSON-data formaterad i konsolen
        
        Args:
            data: Data att visa
            title: Titel för visningen
        """
        if self.use_rich:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            syntax = Syntax(json_str, "json", theme="monokai")
            
            if title:
                self.console.print(Panel(syntax, title=title))
            else:
                self.console.print(syntax)
        else:
            if title:
                print(f"\n{TermColors.BOLD}{title}{TermColors.RESET}")
            print(json.dumps(data, indent=2, ensure_ascii=False))
    
    def display_markdown(self, markdown_text: str, title: str = None) -> None:
        """
        Visar markdown-formaterad text i konsolen
        
        Args:
            markdown_text: Markdown-text att visa
            title: Titel för visningen
        """
        if self.use_rich:
            md = Markdown(markdown_text)
            
            if title:
                self.console.print(Panel(md, title=title))
            else:
                self.console.print(md)
        else:
            if title:
                print(f"\n{TermColors.BOLD}{title}{TermColors.RESET}")
            print(markdown_text)
    
    def display_prompt(self, prompt: str, title: str = "LLM Prompt") -> None:
        """
        Visar en LLM-prompt formaterad i konsolen
        
        Args:
            prompt: Prompttext att visa
            title: Titel för visningen
        """
        if self.use_rich:
            self.console.print(Panel(prompt, title=title, border_style="blue"))
        else:
            color = self.colors.get(LogCategory.LLM_PROMPT.value, TermColors.BLUE)
            print(f"\n{TermColors.BOLD}{title}{TermColors.RESET}")
            print(f"{color}{prompt}{TermColors.RESET}")
    
    def display_response(self, response: str, title: str = "LLM Response") -> None:
        """
        Visar ett LLM-svar formaterat i konsolen
        
        Args:
            response: Svarstext att visa
            title: Titel för visningen
        """
        if self.use_rich:
            self.console.print(Panel(response, title=title, border_style="green"))
        else:
            color = self.colors.get(LogCategory.LLM_RESPONSE.value, TermColors.GREEN)
            print(f"\n{TermColors.BOLD}{title}{TermColors.RESET}")
            print(f"{color}{response}{TermColors.RESET}")
    
    def display_code(self, code: str, language: str = "python", title: str = None) -> None:
        """
        Visar kod formaterad i konsolen
        
        Args:
            code: Kod att visa
            language: Språk för syntaxmarkering
            title: Titel för visningen
        """
        if self.use_rich:
            syntax = Syntax(code, language, theme="monokai", line_numbers=True)
            
            if title:
                self.console.print(Panel(syntax, title=title))
            else:
                self.console.print(syntax)
        else:
            if title:
                print(f"\n{TermColors.BOLD}{title}{TermColors.RESET}")
            print(code)
    
    def display_table(self, headers: List[str], rows: List[List[Any]], title: str = None) -> None:
        """
        Visar en tabell i konsolen
        
        Args:
            headers: Tabellrubriker
            rows: Tabellrader
            title: Titel för tabellen
        """
        if self.use_rich:
            table = Table(title=title)
            
            # Lägg till rubriker
            for header in headers:
                table.add_column(header)
            
            # Lägg till rader
            for row in rows:
                table.add_row(*[str(cell) for cell in row])
            
            self.console.print(table)
        else:
            if title:
                print(f"\n{TermColors.BOLD}{title}{TermColors.RESET}")
            
            # Beräkna kolumnbredder
            col_widths = [len(h) for h in headers]
            for row in rows:
                for i, cell in enumerate(row):
                    col_widths[i] = max(col_widths[i], len(str(cell)))
            
            # Skapa skiljelinje
            separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
            
            # Skriv ut rubrikrad
            print(separator)
            header_row = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, col_widths)) + " |"
            print(header_row)
            print(separator)
            
            # Skriv ut datarader
            for row in rows:
                data_row = "| " + " | ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths)) + " |"
                print(data_row)
            
            print(separator)
    
    def create_progress_bar(self, total: int, description: str) -> 'ProgressTracker':
        """
        Skapar en framstegsspårare
        
        Args:
            total: Totalt antal enheter
            description: Beskrivning av uppgiften
            
        Returns:
            ProgressTracker: En framstegsspårare
        """
        return ProgressTracker(self, total, description)
    
    def start_live_display(self, name: str, generator_func: Callable[[], Any]) -> None:
        """
        Startar en live-uppdaterad visning
        
        Args:
            name: Namn på visningen
            generator_func: Funktion som genererar innehållet
        """
        if not self.use_rich:
            return
        
        if name in self.live_displays:
            self.stop_live_display(name)
        
        live = Live(generator_func(), refresh_per_second=4)
        live.start()
        self.live_displays[name] = (live, generator_func)
    
    def update_live_display(self, name: str) -> None:
        """
        Uppdaterar en live-visning
        
        Args:
            name: Namn på visningen att uppdatera
        """
        if not self.use_rich or name not in self.live_displays:
            return
        
        live, generator_func = self.live_displays[name]
        live.update(generator_func())
    
    def stop_live_display(self, name: str) -> None:
        """
        Stoppar en live-visning
        
        Args:
            name: Namn på visningen att stoppa
        """
        if not self.use_rich or name not in self.live_displays:
            return
        
        live, _ = self.live_displays[name]
        live.stop()
        del self.live_displays[name]
    
    def stop_all_live_displays(self) -> None:
        """Stoppar alla live-visningar"""
        if not self.use_rich:
            return
        
        for name in list(self.live_displays.keys()):
            self.stop_live_display(name)
    
    def clear_screen(self) -> None:
        """Rensar terminalskärmen"""
        if self.use_rich:
            self.console.clear()
        else:
            os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_error(self, error_msg: str, exception: Exception = None) -> None:
        """
        Visar ett felmeddelande
        
        Args:
            error_msg: Felmeddelandet att visa
            exception: Undantaget som orsakade felet
        """
        if self.use_rich:
            if exception:
                self.console.print(f"[bold red]{error_msg}[/bold red]")
                self.console.print_exception()
            else:
                self.console.print(Panel(error_msg, title="Error", border_style="red"))
        else:
            color = self.colors.get(LogCategory.ERROR.value, TermColors.RED)
            print(f"\n{color}{TermColors.BOLD}ERROR: {error_msg}{TermColors.RESET}")
            if exception:
                import traceback
                print(f"{color}{traceback.format_exc()}{TermColors.RESET}")


class ProgressTracker:
    """
    Klass för att spåra och visualisera framsteg för långvariga operationer
    """
    
    def __init__(self, visualizer: TerminalVisualizer, total: int, description: str):
        """
        Initierar framstegsspåraren
        
        Args:
            visualizer: Terminalvisualiseraren att använda
            total: Totalt antal enheter
            description: Beskrivning av uppgiften
        """
        self.visualizer = visualizer
        self.total = total
        self.description = description
        self.completed = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.update_interval = 0.1  # Sekunder mellan uppdateringar
        
        # Initiera progress bar baserat på om rich är tillgängligt
        if self.visualizer.use_rich:
            self.progress = Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeElapsedColumn(),
                TimeRemainingColumn()
            )
            self.task_id = self.progress.add_task(description, total=total)
            self.progress.start()
        else:
            # Enkel CLI-framstegsspårare
            print(f"\n{TermColors.BOLD}{description}{TermColors.RESET}")
            self._update_progress_bar()
    
    def update(self, increment: int = 1) -> None:
        """
        Uppdaterar framsteget
        
        Args:
            increment: Antal enheter att öka med
        """
        self.completed += increment
        current_time = time.time()
        
        # Uppdatera bara visningen om det har gått tillräckligt med tid
        if current_time - self.last_update_time >= self.update_interval:
            self.last_update_time = current_time
            
            if self.visualizer.use_rich:
                self.progress.update(self.task_id, completed=self.completed)
            else:
                self._update_progress_bar()
    
    def _update_progress_bar(self) -> None:
        """Uppdaterar enkel CLI-framstegsspårare"""
        percent = min(100, int(self.completed / self.total * 100))
        bar_length = 50
        filled_length = int(bar_length * percent / 100)
        
        # Skapa framstegsspåraren
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # Beräkna tid
        elapsed = time.time() - self.start_time
        if self.completed > 0:
            estimated_total = elapsed * self.total / self.completed
            remaining = estimated_total - elapsed
            time_info = f" | {int(elapsed)}s elapsed | ~{int(remaining)}s remaining"
        else:
            time_info = f" | {int(elapsed)}s elapsed"
        
        # Skriv ut framstegsspåraren
        print(f"\r{bar} {percent}% ({self.completed}/{self.total}){time_info}", end='')
        sys.stdout.flush()
        
        # Lägg till en ny rad om vi är klara
        if self.completed >= self.total:
            print()
    
    def close(self) -> None:
        """Stänger framstegsspåraren"""
        if self.visualizer.use_rich:
            self.progress.stop()
        else:
            # Säkerställ att den sista framstegsspåraren visas korrekt
            self._update_progress_bar()
            print()  # Lägg till en ny rad


def setup_logger(config: Dict[str, Any]) -> Tuple[logging.Logger, TerminalVisualizer]:
    """
    Konfigurerar och returnerar en logger och terminalvisualiserare
    
    Args:
        config: Konfiguration för loggning och visualisering
        
    Returns:
        Tuple[logging.Logger, TerminalVisualizer]: Logger och terminalvisualiserare
    """
    log_level = getattr(logging, config.get('log_level', 'INFO'))
    
    # Skapa visualiseraren
    visualizer_config = {
        'use_rich': config.get('use_rich', RICH_AVAILABLE),
        'log_level': log_level,
        'colors': config.get('colors', {})
    }
    visualizer = TerminalVisualizer(visualizer_config)
    
    # Hämta loggaren
    logger = visualizer.get_logger('llm_extractor')
    
    return logger, visualizer





