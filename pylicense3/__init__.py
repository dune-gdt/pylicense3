"""Top-level package for pylicense3."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version('pylicense3')
except PackageNotFoundError:
    __version__ = '0.0.0'
