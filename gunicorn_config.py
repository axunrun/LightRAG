# gunicorn_config.py
import os
import logging
from lightrag.kg.shared_storage import finalize_share_data
from lightrag.api.lightrag_server import LightragPathFilter

# Get log directory path from environment variable
log_dir = os.getenv("LOG_DIR", os.getcwd())
log_file_path = os.path.abspath(os.path.join(log_dir, "lightrag.log"))

# Get log file max size and backup count from environment variables
log_max_bytes = int(os.getenv("LOG_MAX_BYTES", 10485760))  # Default 10MB
log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", 5))  # Default 5 backups

# These variables will be set by run_with_gunicorn.py
workers = None
bind = None
loglevel = None
certfile = None
keyfile = None

# Enable preload_app option
preload_app = True

# Use Uvicorn worker
worker_class = "uvicorn.workers.UvicornWorker"

# Other Gunicorn configurations
timeout = int(os.getenv("TIMEOUT", 150))  # Default 150s to match run_with_gunicorn.py
keepalive = int(os.getenv("KEEPALIVE", 5))  # Default 5s

# Logging configuration
errorlog = os.getenv("ERROR_LOG", log_file_path)  # Default write to lightrag.log
accesslog = os.getenv("ACCESS_LOG", log_file_path)  # Default write to lightrag.log

logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": log_file_path,
            "maxBytes": log_max_bytes,
            "backupCount": log_backup_count,
            "encoding": "utf8",
        },
    },
    "filters": {
        "path_filter": {
            "()": "lightrag.api.lightrag_server.LightragPathFilter",
        },
    },
    "loggers": {
        "lightrag": {
            "handlers": ["console", "file"],
            "level": loglevel.upper() if loglevel else "INFO",
            "propagate": False,
        },
        "gunicorn": {
            "handlers": ["console", "file"],
            "level": loglevel.upper() if loglevel else "INFO",
            "propagate": False,
        },
        "gunicorn.error": {
            "handlers": ["console", "file"],
            "level": loglevel.upper() if loglevel else "INFO",
            "propagate": False,
        },
        "gunicorn.access": {
            "handlers": ["console", "file"],
            "level": loglevel.upper() if loglevel else "INFO",
            "propagate": False,
            "filters": ["path_filter"],
        },
    },
}


def on_starting(server):
    """
    Executed when Gunicorn starts, before forking the first worker processes
    You can use this function to do more initialization tasks for all processes
    """
    print("=" * 80)
    print(f"GUNICORN MASTER PROCESS: on_starting jobs for {workers} worker(s)")
    print(f"Process ID: {os.getpid()}")
    print("=" * 80)

    # Memory usage monitoring
    try:
        import psutil

        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        msg = (
            f"Memory usage after initialization: {memory_info.rss / 1024 / 1024:.2f} MB"
        )
        print(msg)
    except ImportError:
        print("psutil not installed, skipping memory usage reporting")

    print("Gunicorn initialization complete, forking workers...\n")


def on_exit(server):
    """
    Executed when Gunicorn is shutting down.
    This is a good place to release shared resources.
    """
    print("=" * 80)
    print("GUNICORN MASTER PROCESS: Shutting down")
    print(f"Process ID: {os.getpid()}")
    print("=" * 80)

    # Release shared resources
    finalize_share_data()

    print("=" * 80)
    print("Gunicorn shutdown complete")
    print("=" * 80)


def post_fork(server, worker):
    """
    Executed after a worker has been forked.
    This is a good place to set up worker-specific configurations.
    """
    # Set lightrag logger level in worker processes using gunicorn's loglevel
    from lightrag.utils import logger

    logger.setLevel(loglevel.upper())

    # Disable uvicorn.error logger in worker processes
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.setLevel(logging.CRITICAL)
    uvicorn_error_logger.handlers = []
    uvicorn_error_logger.propagate = False

    # Add log filter to uvicorn.access handler in worker processes
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    path_filter = LightragPathFilter()
    uvicorn_access_logger.addFilter(path_filter)
