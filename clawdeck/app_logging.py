import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _setup_logging():
    """Configure clawdeck logger with console and file handlers."""
    log_dir = Path.home() / ".clawdeck"
    try:
        log_dir.mkdir(exist_ok=True)
    except OSError:
        log_dir = Path("/tmp/.clawdeck")
        log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger("clawdeck")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console)

    try:
        file_handler = RotatingFileHandler(
            log_dir / "clawdeck.log", maxBytes=1_000_000, backupCount=3
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)
    except OSError:
        logger.warning("File logging unavailable; continuing with console logging only")

    return logger


logger = _setup_logging()
