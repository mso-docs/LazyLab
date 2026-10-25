"""Bundled defaults work from an installed wheel as well as the source checkout."""
from importlib.resources import files
from pathlib import Path


def asset_path(relative):
    path=Path(relative)
    if path.exists():
        return path
    if str(path) not in {'configs/calibration.yaml','configs/demo.yaml','benchmarks/objectives','benchmarks/behavioral'}:
        return path
    bundled=files('slothlab').joinpath('data',str(path))
    return Path(str(bundled))
