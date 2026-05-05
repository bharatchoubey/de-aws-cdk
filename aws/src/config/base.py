from __future__ import annotations

from abc import ABC, abstractmethod

from config.models.base import BaseConfig


class BaseConfigLoader(ABC):
    """
    Abstract contract for all config loaders.

    Subclasses decide the file format (YAML, JSON, etc.) and the
    mapping from raw data → typed config models.  Callers always
    interact through this interface, never through a concrete loader.

    Config path convention:
        configs/{env}/{project}/{region}/{service}.yaml

    All four dimensions (env, project, region, service) are passed
    explicitly to ``load()`` so the path is unambiguous and the
    caller — not the loader — decides which combination to load.
    """

    @abstractmethod
    def load(self, service: str, env: str, project: str, region: str) -> BaseConfig:
        """
        Load and return a validated config object for the given combination.

        Args:
            service: service name matching the config file stem (e.g. 'ssm')
            env:     deployment environment directory (e.g. 'dev', 'prod')
            project: project directory within the env (e.g. 'myapp')
            region:  AWS region directory (e.g. 'us-east-1')

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
