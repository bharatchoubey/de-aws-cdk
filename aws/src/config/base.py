from __future__ import annotations

from abc import ABC, abstractmethod

from config.models.base import BaseConfig


class BaseConfigLoader(ABC):
    """
    Abstract contract for all config loaders.

    Subclasses decide the file format (YAML, JSON, etc.) and the
    mapping from raw data → typed config models.  Callers always
    interact through this interface, never through a concrete loader.
    """

    @abstractmethod
    def load(self, service: str, env: str) -> BaseConfig:
        """
        Load and return a validated config object for the given service/env pair.

        Args:
            service: service name matching the config file (e.g. 'ssm')
            env:     deployment environment (e.g. 'dev', 'prod')

        Returns:
            A fully validated BaseConfig subclass instance.
        """

    @abstractmethod
    def _read_file(self, path: str) -> dict:
        """Read the config file at *path* and return a raw Python dict."""

    @abstractmethod
    def _validate(self, data: dict) -> None:
        """
        Validate the raw dict before model construction.

        Raise ValueError with a descriptive message on any violation.
        """
