from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
PUBLIC_DIR = ROOT / "public"
ARTIFACTS_DIR = ROOT / "artifacts"


def load_yaml(name: str) -> dict:
    path = CONFIG_DIR / name

    if not path.exists():
        raise FileNotFoundError(
            f"Nie znaleziono konfiguracji: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8"
    ) as handle:
        result = yaml.safe_load(handle)

    if not isinstance(result, dict):
        raise ValueError(
            f"Konfiguracja {name} "
            "nie jest słownikiem."
        )

    return result


def load_project_config() -> dict:
    return load_yaml("project.yaml")


def load_methodology() -> dict:
    return load_yaml("methodology.yaml")
