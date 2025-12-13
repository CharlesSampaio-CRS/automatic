"""
Centralized Logging Configuration
Provides consistent logging across all modules
"""

import logging
import sys
from datetime import datetime
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    # Emoji for each level
    EMOJI = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️ ',
        'ERROR': '❌',
        'CRITICAL': '🔥'
    }
    
    def format(self, record):
        # Add color and emoji
        level_name = record.levelname
        color = self.COLORS.get(level_name, self.COLORS['RESET'])
        emoji = self.EMOJI.get(level_name, '')
        reset = self.COLORS['RESET']
        
        # Format the message
        record.levelname = f"{emoji} {color}{level_name}{reset}"
        return super().format(record)


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup a logger with consistent formatting
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (default: INFO)
        log_file: Optional file to write logs to
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(
        '%(levelname)s [%(name)s] %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler without colors (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger for a module
    
    Args:
        name: Module name (use __name__)
    
    Returns:
        Logger instance
    """
    return setup_logger(name)
