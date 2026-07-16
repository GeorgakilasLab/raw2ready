"""Logging Configuration module.

Sets up centralized console and rotating file logging for the application.
"""

import os
import logging
import logging.handlers
from pathlib import Path


def setup_logging(
    log_level=logging.INFO,
    log_dir="logs",
    log_filename="app.log",
    max_file_size=10*1024*1024,
    backup_count=5,
    console_logging=True,
    log_date_format='%Y-%m-%d %H:%M:%S',
    log_encoding_format='utf-8'
):
    """Configures application-wide logging system handlers.

    Args:
        log_level: Log level severity indicator. Defaults to logging.INFO.
        log_dir: Directory where logs should be created. Defaults to "logs".
        log_filename: Output log file name. Defaults to "app.log".
        max_file_size: Max size in bytes before rotating. Defaults to 10MB (10*1024*1024).
        backup_count: Number of historical files to keep. Defaults to 5.
        console_logging: Whether to output logs to standard output. Defaults to True.
        log_date_format: Formatting rules for datetime values. Defaults to '%Y-%m-%d %H:%M:%S'.
        log_encoding_format: Characters set representation encoding. Defaults to 'utf-8'.

    Returns:
        The configured root Logger instance.
    """

    #-------------------------------------------
    # USE GLOBAL RAW2READY DIRECTORY
    #-------------------------------------------
    from src.utils.paths import ensure_dirs
    DIRS = ensure_dirs()
    log_path = DIRS["logs"]

    #-------------------------------------------
    # Create logger
    logger = logging.getLogger('legacy2leaf_app')
    logger.setLevel(log_level)

    logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt=log_date_format
    )

    #-------------------------------------------
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / log_filename,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding=log_encoding_format
    )

    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    #-------------------------------------------
    # Console handler
    if console_logging:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logger.info(f"Logging initialized ? {log_path / log_filename}")

    return logger


def get_logger(name=None):
    """Retrieves a logger instance under the main application name hierarchy.

    Args:
        name: Sub-logger namespace identifier. Defaults to None.

    Returns:
        The Logger instance.
    """
    if name:

        return logging.getLogger(f'legacy2leaf_app.{name}')
    
    return logging.getLogger('legacy2leaf_app')
