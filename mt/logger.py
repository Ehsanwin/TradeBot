"""
MT5 Logging Configuration

Sets up logging for the MT5 trading system.
"""

import logging
import logging.handlers
import os
from pathlib import Path

def setup_logging(
    level: str = "INFO",
    log_file: str = "logs/mt5_trading.log",
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    max_size: str = "10MB",
    backup_count: int = 5,
    console_output: bool = True,
    file_output: bool = True
):
    """
    Setup logging configuration for MT5 trading system
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
        format_string: Log message format
        max_size: Maximum log file size
        backup_count: Number of backup log files
        console_output: Enable console output
        file_output: Enable file output
    """
    
    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(format_string)
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if file_output:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert max_size to bytes
        if max_size.upper().endswith('MB'):
            max_bytes = int(max_size[:-2]) * 1024 * 1024
        elif max_size.upper().endswith('KB'):
            max_bytes = int(max_size[:-2]) * 1024
        else:
            max_bytes = int(max_size)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    logger.info(f"MT5 logging configured - Level: {level}, File: {log_file if file_output else 'disabled'}")

def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance with specified name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)
