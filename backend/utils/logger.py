import os
import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any, Optional

class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "query_id": getattr(record, "query_id", None),
            "step": getattr(record, "step", None),
            "message": record.getMessage(),
        }
        
        # Add step-specific data object if provided
        data = getattr(record, "data", None)
        if data is not None:
            log_obj["data"] = data
            
        # Include exception traceback if available
        if record.exc_info:
            log_obj["error_traceback"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)

def get_logger(name: str = "wikimind") -> logging.Logger:
    """Configures and returns the structured JSON logger."""
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers if logger is already configured
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.INFO)
    
    # Read path from env, default to local logs directory for development outside Docker
    log_file_path = os.getenv("LOG_FILE_PATH", "logs/wikimind.log")
    
    # Ensure directory exists
    log_dir = os.path.dirname(log_file_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        
    # RotatingFileHandler: 10MB max size, 3 backup files (per Section 14)
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=10 * 1024 * 1024, 
        backupCount=3
    )
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    
    # Also log to console for development convenience
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    return logger

# Initialize the global logger instance
logger = get_logger()

# Convenience methods to enforce the structured schema
def log_info(query_id: str, step: str, message: str, data: Optional[dict[str, Any]] = None):
    logger.info(message, extra={"query_id": query_id, "step": step, "data": data})

def log_error(query_id: str, step: str, message: str, exc_info: bool = True, data: Optional[dict[str, Any]] = None):
    logger.error(message, extra={"query_id": query_id, "step": step, "data": data}, exc_info=exc_info)
    
def log_warning(query_id: str, step: str, message: str, data: Optional[dict[str, Any]] = None):
    logger.warning(message, extra={"query_id": query_id, "step": step, "data": data})
