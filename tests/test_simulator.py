"""The simulated client systems must be reproducible: same seed -> byte-identical files on every machine."""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "simulator" / "generate_client_systems.py"


def _generate(out: Path, hash_seed: str) -> dict:
    env = {**os.environ, "SIM_OUT_DIR": str(out), "PYTHONHASHSEED": hash_seed}
    subprocess.run([sys.executable, str(GENERATOR)], env=env, check=True, capture_output=True)
    return {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(out.rglob("*")) if p.is_file()}


def test_generator_is_deterministic_across_processes(tmp_path):
    # different hash seeds = different set/dict-of-str iteration orders; output must not depend on them
    first = _generate(tmp_path / "a", "1")
    second = _generate(tmp_path / "b", "2")
    assert first == second


def test_committed_client_systems_match_the_generator(tmp_path):
    generated = _generate(tmp_path / "g", "0")
    for rel, digest in generated.items():
        committed = (ROOT / rel) if rel.startswith("client_systems/") else ROOT / "simulator" / rel
        if committed.suffix == ".py":
            continue
        assert committed.exists(), f"{rel} is generated but not committed"
        assert hashlib.sha256(committed.read_bytes()).hexdigest() == digest, f"{rel} differs from the generator's output"
