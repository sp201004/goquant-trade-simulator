"""
Logging configuration for GoQuant Trade Simulator.
"""

import logging
import sys
from pathlib import Path
from loguru import logger


def setup_logging(level: str = "INFO", log_file: bool = True):
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Whether to log to file
    """
    # Remove default loguru handler
    logger.remove()
    
    # Add console handler with custom format
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True
    )
    
    # Add file handler if requested
    if log_file:
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        logger.add(
            logs_dir / "goquant_{time:YYYY-MM-DD}.log",
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            rotation="1 day",
            retention="7 days",
            compression="zip"
        )
    
    # Intercept standard logging
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Get corresponding Loguru level if it exists
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            
            # Find caller from where originated the logged message
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            
            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
    
    # Replace standard logging with loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Set levels for specific loggers
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)


def get_logger(name: str):
    """Get a logger instance."""
    return logger.bind(name=name)
