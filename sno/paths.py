"""Repo paths. Outputs go under results/; committed inputs under config/."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
CONFIG = ROOT / "config"
WALLETS = CONFIG / "wallets"
LABELS = CONFIG / "labels"
SOURCES = CONFIG / "sources"

RESULTS.mkdir(parents=True, exist_ok=True)


def result(*parts: str) -> Path:
    return RESULTS.joinpath(*parts)


def wallet_file(name: str) -> Path:
    return WALLETS / name


def label_file(name: str) -> Path:
    return LABELS / name


def source_file(name: str) -> Path:
    return SOURCES / name
