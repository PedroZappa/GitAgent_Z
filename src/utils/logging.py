import logging
import sys
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install
from config.settings import settings

# Install rich traceback handler
install(show_locals=True)


def setup_logging() -> logging.Logger:
    """Setup logging configuration with Rich"""

    # Create logs directory
    log_dir = settings.config_dir / "logs"
    log_dir.mkdir(exist_ok=True, parents=True)

    # Configure root logger
    logger = logging.getLogger("gitagent")
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Rich console handler for terminal output
    console = Console(stderr=True)
    rich_handler = RichHandler(
        console=console,
        show_path=False,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
    )
    rich_handler.setLevel(logging.INFO)

    # File handler for detailed logs
    file_handler = logging.FileHandler(log_dir / "gitagent.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # Formatters
    rich_formatter = logging.Formatter("%(message)s", datefmt="[%X]")

    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )

    rich_handler.setFormatter(rich_formatter)
    file_handler.setFormatter(file_formatter)

    logger.addHandler(rich_handler)
    logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = setup_logging()
