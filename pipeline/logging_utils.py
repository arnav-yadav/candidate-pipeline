"""Console + file logging. Every line says which stage it came from."""
import logging
from pathlib import Path


def get_logger(log_dir: Path, run_id: str) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"pipeline.{run_id}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", "%H:%M:%S")
        for h in (logging.StreamHandler(), logging.FileHandler(log_dir / f"run_{run_id}.log")):
            h.setFormatter(fmt)
            logger.addHandler(h)
    return logger
