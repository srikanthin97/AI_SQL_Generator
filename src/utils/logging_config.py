import logging
import os
import sys

def setup_logging(log_level: int = logging.INFO) -> None:
    """Configures structured console logging for development and production pipelines."""
    logger = logging.getLogger("ai_sql_generator")
    logger.setLevel(log_level)
    
    # Avoid duplicate handlers if setup multiple times
    if logger.handlers:
        return

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler("logs/app.log", encoding="utf-8")
    file_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    logger.info("Structured logging framework initialized.")
