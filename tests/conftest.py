import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def mock_api():
    """Start the simulated job-board API once for the end-to-end tests."""
    try:
        requests.get("http://127.0.0.1:8765/health", timeout=1)
        yield None
        return
    except requests.RequestException:
        pass
    proc = subprocess.Popen([sys.executable, str(ROOT / "client_systems/job_board_api/mock_job_board_api.py")],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        time.sleep(0.25)
        try:
            requests.get("http://127.0.0.1:8765/health", timeout=1)
            break
        except requests.RequestException:
            continue
    yield proc
    proc.terminate()


@pytest.fixture
def isolated_cfg(tmp_path):
    """Real config, but every write goes to a temporary folder - tests never touch output/."""
    from pipeline.config import load_config
    cfg = load_config()
    cfg["paths"] = {k: str(tmp_path / k) for k in ("raw", "output", "logs")}
    cfg["paths"]["warehouse"] = str(tmp_path / "data" / "warehouse.sqlite")
    return cfg
