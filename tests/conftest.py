"""Shared fixtures: import the validator by path, since tools/ is not a package."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


validate_blocks = _load("validate_blocks", "tools/validate_blocks.py")
