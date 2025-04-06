"""
Utility functions for the scraper.
"""

import os
import logging
import colorlog
import time

def setup_logger(log_file=None, console_level=logging.INFO, file_level=logging.DEBUG):
    """
    Set up logging configuration.
    
    Args:
        log_file: Path to the log file (optional)
        console_level: Logging level for console output
        file_level: Logging level for file output
        
    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger('visdom_scraper')
    logger.setLevel(logging.DEBUG)
    logger.handlers = []  # Clear existing handlers
    
    # Color formatter for console output
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # Console handler
    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(console_formatter)
    logger.addHandler(console)
    
    # File handler (if log_file is provided)
    if log_file:
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler = logging.FileHandler(log_file, 'a', encoding='utf-8')
        file_handler.setLevel(file_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def ensure_dir_exists(directory):
    """
    Ensure that the specified directory exists.
    
    Args:
        directory: Directory path to check/create
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

def format_duration(seconds):
    """
    Format a duration in seconds to a human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        str: Formatted duration string (HH:MM:SS or MM:SS)
    """
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"
