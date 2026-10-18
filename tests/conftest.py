from pathlib import Path


def pytest_configure(config):
    # pytest creates basetemp itself, but its parent must exist on fresh clones.
    Path('tmp').mkdir(exist_ok=True)
