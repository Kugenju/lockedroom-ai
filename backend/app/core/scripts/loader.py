"""Load and validate script YAML files."""

from pathlib import Path

import yaml
from app.models.script import Script

# backend/app/scripts (this file lives in backend/app/core/scripts/)
_DEFAULT_DIR = Path(__file__).resolve().parents[2] / "scripts"


def load_script(script_id: str, scripts_dir: str | Path | None = None) -> Script:
    base = Path(scripts_dir) if scripts_dir else _DEFAULT_DIR
    path = base / f"{script_id}.yaml"
    if not path.exists():
        available = sorted(p.stem for p in base.glob("*.yaml"))
        raise FileNotFoundError(f"script {script_id!r} not found in {base}; available: {available}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"script file {path} is not a YAML mapping")
    return Script(**data)


def list_scripts(scripts_dir: str | Path | None = None) -> list[str]:
    base = Path(scripts_dir) if scripts_dir else _DEFAULT_DIR
    return sorted(p.stem for p in base.glob("*.yaml"))
